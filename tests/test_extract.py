"""LLM extract, tested with a FAKE LLM: no API key, no cost, same result every run.

What is tested is our code around the model: finding the quote in the original
document, handling bad output, retry feedback and token bookkeeping.
"""
import pathlib
from types import SimpleNamespace

from agents.nodes import locate, make_extract, section_span, verify_evidence

DATA = pathlib.Path("synthetic_kit/data/synthetic")


def doc(doc_id):
    return (DATA / f"{doc_id}.txt").read_text(encoding="utf-8")


def fake_llm(reply, seen=None, stop_reason="end_turn", blocks=("text",)):
    """Returns a fixed reply and records the prompt it was given."""
    def ask(system, user):
        if seen is not None:
            seen.append(user)
        return {"text": reply, "input_tokens": 100, "output_tokens": 10, "ms": 5, "model": "fake",
                "stop_reason": stop_reason, "blocks": list(blocks)}
    return ask


def state_for(doc_id, med, section="Discharge Medications", attempts=0, **extra):
    d = doc(doc_id)
    s0, s1 = section_span(d, section)
    chunk = SimpleNamespace(page_content=d[s0:s1],
                            metadata={"char_start": s0, "char_end": s1, "section": section})
    st = {"doc_id": doc_id, "doc_text": d, "med_name": med, "section_plan": [section],
          "section_idx": 0, "attempts": attempts, "chunks": [chunk]}
    st.update(extra)
    return st


def run(mode, reply, st, seen=None):
    out = make_extract(mode, llm=fake_llm(reply, seen))(st)
    verdict = verify_evidence({**st, **out})["verdict"]
    return out, verdict


# ---- quote -> position in the original document (code, not the model)
def test_quote_with_list_number_is_located():
    st = state_for("doc_03", "lisinopril")
    out, verdict = run("A", '{"found": true, "quote": "1. Lisinopril 5 mg PO DAILY"}', st)
    c = out["candidate"]
    assert st["doc_text"][c["char_start"]:c["char_end"]] == "Lisinopril 5 mg PO DAILY"
    assert c["dose"] == "5 mg" and verdict == "ok"


def test_admission_line_is_not_preferred_over_discharge_line():
    # "lisinopril 10 mg PO daily" is the admission list; the model must not get credit for it
    st = state_for("doc_03", "lisinopril")
    _, verdict = run("A", '{"found": true, "quote": "lisinopril 10 mg PO daily"}', st)
    assert verdict == "wrong_section"


def test_wrapped_line_joined_by_model_is_located():
    # in doc_12 the taper wraps onto the next line; a model may join it with a space
    d = doc("doc_12")
    quote = "Prednisone 40 mg PO daily for 3 days, then 20 mg PO daily for 3 days, then stop"
    s0, s1 = locate(d, quote, [])
    assert d[s0:s1].split() == quote.split()
    _, verdict = run("A", f'{{"found": true, "quote": "{quote}"}}', state_for("doc_12", "prednisone"))
    assert verdict == "multiple_doses"


def test_invented_quote_fails_verification():
    st = state_for("doc_03", "lisinopril")
    out, verdict = run("A", '{"found": true, "quote": "Lisinopril 50 mg PO DAILY"}', st)
    assert out["candidate"]["char_start"] == -1 and verdict == "span_mismatch"


def test_other_drug_quote_fails_verification():
    st = state_for("doc_02", "pantoprazole")
    _, verdict = run("A", '{"found": true, "quote": "Omeprazole 20 mg PO DAILY"}', st)
    assert verdict in ("name_mismatch", "span_mismatch", "wrong_section")


# ---- bad or empty model output
def test_found_false_means_not_found():
    out, verdict = run("A", '{"found": false, "quote": ""}', state_for("doc_03", "warfarin"))
    assert out["candidate"] is None and verdict == "not_found"


def test_unparseable_output_is_not_an_answer():
    out, verdict = run("A", "Sure! The dose is 5 mg.", state_for("doc_03", "lisinopril"))
    assert out["candidate"] is None and verdict == "not_found"
    assert "unparseable" in out["trace"][0]


def test_cut_off_output_is_labelled_truncated_not_unparseable():
    # 10/11 doc_08: 300/300 output tokens, empty text -> looked like "not found"
    st = state_for("doc_08", "prednisone", section="Discharge Instructions")
    ask = fake_llm("", stop_reason="max_tokens", blocks=("thinking",))
    out = make_extract("A", llm=ask)(st)
    assert out["candidate"] is None
    assert "TRUNCATED" in out["trace"][0] and "thinking" in out["trace"][0]


# ---- retry feedback and bookkeeping
def test_retry_prompt_explains_the_rejection():
    seen = []
    prev = {"evidence_text": "Omeprazole 20 mg PO DAILY", "char_start": 0, "char_end": 0}
    st = state_for("doc_02", "pantoprazole", attempts=1, candidate=prev, verdict="name_mismatch")
    run("A", '{"found": false, "quote": ""}', st, seen)
    assert "rejected (name_mismatch)" in seen[0]


def test_first_attempt_has_no_feedback():
    seen = []
    run("A", '{"found": false, "quote": ""}', state_for("doc_02", "pantoprazole"), seen)
    assert "rejected" not in seen[0]


def test_usage_is_recorded_per_call():
    out, _ = run("A", '{"found": true, "quote": "Lisinopril 5 mg PO DAILY"}',
                 state_for("doc_03", "lisinopril"))
    assert out["usage"] == [{"node": "extract", "mode": "A", "attempt": 1, "input_tokens": 100,
                             "output_tokens": 10, "ms": 5, "model": "fake",
                             "stop_reason": "end_turn"}]
    assert out["attempts"] == 1


# ---- mode D gets the whole document, mode A only the chunks
def test_context_differs_by_mode():
    st = state_for("doc_03", "lisinopril")
    seen_a, seen_d = [], []
    run("A", '{"found": false, "quote": ""}', st, seen_a)
    run("D", '{"found": false, "quote": ""}', st, seen_d)
    ctx_a = seen_a[0].split("CONTEXT:")[1]
    ctx_d = seen_d[0].split("CONTEXT:")[1]
    assert "Medications on Admission:" not in ctx_a
    assert "Medications on Admission:" in ctx_d
