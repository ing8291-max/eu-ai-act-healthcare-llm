"""Whole graph + evaluate() on all 53 questions with FAKE retrieval and FAKE LLMs.

No API key, no embeddings, no cost. This checks the plumbing before real money is spent:
  - a model that copies the right line  -> must reach 46/46, 7/7, 0 wrong
  - a model that quotes another drug    -> must produce 0 wrong answers (verify blocks it)
  - a model that invents a line         -> must produce 0 wrong answers (verify blocks it)
"""
import re

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_core")

from langchain_core.documents import Document  # noqa: E402

from agents.evaluate import evaluate  # noqa: E402
from agents.graph import build_graph  # noqa: E402
from agents.nodes import DATA_DIR, DOSE_RE, make_extract, section_span  # noqa: E402

DRUG_RE = re.compile(r"^Drug: (.+)$", re.M)
SECTION_RE = re.compile(r'Use only the section "([^"]+)"')


class SectionStore:
    """Stands in for Chroma: returns the whole requested section as one chunk."""
    def similarity_search_with_score(self, query, k=3, filter=None):
        cond = {list(c)[0]: list(c.values())[0] for c in filter["$and"]}
        doc = (DATA_DIR / f"{cond['doc_id']}.txt").read_text(encoding="utf-8")
        span = section_span(doc, cond["section"])
        if span is None:
            return []
        meta = {"doc_id": cond["doc_id"], "section": cond["section"],
                "char_start": span[0], "char_end": span[1]}
        return [(Document(page_content=doc[span[0]:span[1]], metadata=meta), 0.5)]


def _section_lines(user):
    """Lines of the target section inside the prompt's CONTEXT."""
    section = SECTION_RE.search(user).group(1)
    ctx = user.split("CONTEXT:\n<<<\n", 1)[1].rsplit("\n>>>", 1)[0]
    span = section_span(ctx, section)
    body = ctx[span[0]:span[1]] if span else ctx       # mode A: context is already the section
    return [ln for ln in body.splitlines() if ln.strip()]


def _reply(quote):
    return {"text": '{"found": %s, "quote": %s}' % ("true" if quote else "false",
                                                    '"%s"' % quote.replace('"', "'")),
            "input_tokens": len(_reply.last) // 4, "output_tokens": 15, "ms": 1, "model": "fake"}


def honest_llm(system, user):
    _reply.last = user
    med = DRUG_RE.search(user).group(1)
    hit = next((ln for ln in _section_lines(user) if med in ln.lower()), "")
    return _reply(hit.strip())


def other_drug_llm(system, user):
    _reply.last = user
    med = DRUG_RE.search(user).group(1)
    hit = next((ln for ln in _section_lines(user)
                if DOSE_RE.search(ln) and med not in ln.lower()), "")
    return _reply(hit.strip())


def inventing_llm(system, user):
    _reply.last = user
    med = DRUG_RE.search(user).group(1)
    return _reply(f"{med.title()} 999 mg PO DAILY")


@pytest.mark.parametrize("mode", ["A", "D"])
def test_honest_model_gets_everything(mode):
    app = build_graph(SectionStore(), extractor=make_extract(mode, llm=honest_llm))
    s = evaluate(app, run_name=f"fake-{mode}", verbose=False, save=False)
    assert (s["correct"], s["abstain_ok"], s["wrong"]) == (46, 7, 0)
    assert s["llm_calls"] >= s["questions"]          # at least one call per question


@pytest.mark.parametrize("llm", [other_drug_llm, inventing_llm])
def test_bad_model_never_produces_a_wrong_answer(llm):
    app = build_graph(SectionStore(), extractor=make_extract("A", llm=llm))
    s = evaluate(app, run_name="fake-bad", verbose=False, save=False)
    assert s["wrong"] == 0
    assert s["llm_calls"] <= 4 * s["questions"]       # 2 sections x 2 attempts at most
