"""Nodes of the medication-extraction agent.

Every node takes the shared AgentState and returns ONLY the fields it changes.
`trace` is appended to (see Annotated[..., operator.add] in state.py).
"""
import json
import pathlib
import re

from .llm import call_llm
from .state import AgentState

DATA_DIR = pathlib.Path("synthetic_kit/data/synthetic")

# number + unit: 5 mg / 0.075 mg / 75 mcg / 2 puffs / 20 mEq
DOSE_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|mL|units?|puffs?|mEq)\b", re.I)
# frequency words that appear in the synthetic notes (temporary, LLM replaces this in S04)
FREQ_RE = re.compile(
    r"\b(?:Q\d+H(?: PRN)?|every \d+ hours(?: PRN)?|PRN|BID|TID|QHS|DAILY|daily|"
    r"q\.d\.|twice daily|nightly)\b", re.I)
# "What is the discharge dose of lisinopril?" -> "lisinopril"
QUESTION_RE = re.compile(r"dose of\s+(.+?)\s*\?*\s*$", re.I)

SECTION_PLAN = ["Discharge Medications", "Discharge Instructions"]
# evidence may only come from these sections (Medications on Admission = comparison only)
ALLOWED_SECTIONS = {"Discharge Medications", "Discharge Instructions"}
HEADER_RE = re.compile(r"^([A-Z][A-Za-z /]+):\s*$", re.M)


def section_at(doc: str, pos: int) -> str:
    """Name of the section that contains character position `pos`."""
    name = "Header"
    for m in HEADER_RE.finditer(doc):
        if m.start() > pos:
            break
        name = m.group(1)
    return name


def section_span(doc: str, name: str):
    """(start, end) of the body of section `name`, or None if the header is missing."""
    heads = list(HEADER_RE.finditer(doc))
    for i, m in enumerate(heads):
        if m.group(1) == name:
            end = heads[i + 1].start() if i + 1 < len(heads) else len(doc)
            return m.end(), end
    return None


MAX_ATTEMPTS = 2


# ---------------------------------------------------------------- load_document
def load_document(state: AgentState) -> dict:
    text = (DATA_DIR / f"{state['doc_id']}.txt").read_text(encoding="utf-8")
    return {"doc_text": text,
            "trace": [f"load_document: {state['doc_id']} ({len(text)} chars)"]}


# ---------------------------------------------------------------- route_intent
def route_intent(state: AgentState) -> dict:
    m = QUESTION_RE.search(state["question"].strip())
    med = m.group(1).strip().lower() if m else ""
    return {"med_name": med,
            "section_plan": SECTION_PLAN,
            "section_idx": 0,
            "attempts": 0,
            "trace": [f"route_intent: med={med!r}, plan={SECTION_PLAN}"]}


# ---------------------------------------------------------------- retrieve
def make_retrieve(vectorstore, threshold=None, k=3):
    """retrieve needs the vector store, so it is built by a factory.

    threshold=None turns the distance filter off (for the on/off comparison).
    """
    def retrieve(state: AgentState) -> dict:
        section = state["section_plan"][state["section_idx"]]
        pairs = vectorstore.similarity_search_with_score(
            state["question"], k=k,
            filter={"$and": [{"doc_id": state["doc_id"]}, {"section": section}]},
        )
        kept = [d for d, dist in pairs if threshold is None or dist < threshold]
        dists = ", ".join(f"{dist:.2f}" for _, dist in pairs) or "-"
        return {"chunks": kept,
                "trace": [f"retrieve[{section}]: found {len(pairs)} (dist {dists}), kept {len(kept)}"]}
    return retrieve


# ---------------------------------------------------------------- fallback_section
def fallback_section(state: AgentState) -> dict:
    nxt = state["section_idx"] + 1
    return {"section_idx": nxt,
            "attempts": 0,                      # new section -> retries counted from 0
            "trace": [f"fallback_section: -> {state['section_plan'][nxt]}"]}


# ---------------------------------------------------------------- extract (regex, kept for comparison)
def extract_regex(state: AgentState) -> dict:
    """Regex extractor used before S04. Kept so old results stay reproducible.

    Finds the first line that mentions the drug inside the retrieved chunks and
    reports that line with its exact position in the ORIGINAL document.
    """
    med, doc = state["med_name"], state["doc_text"]
    candidate = None
    for d in state["chunks"]:
        s0, s1 = d.metadata["char_start"], d.metadata["char_end"]
        pos = s0
        for line in doc[s0:s1].splitlines(keepends=True):
            if med and med in line.lower():
                body = line.rstrip("\n")
                lead = len(body) - len(body.lstrip(" 0123456789."))   # drop "1. "
                start = pos + lead
                text = body[lead:].rstrip()
                dose = DOSE_RE.search(text)
                freq = FREQ_RE.search(text)
                candidate = {"dose": dose.group(0) if dose else None,
                             "frequency": freq.group(0) if freq else None,
                             "evidence_text": text,
                             "char_start": start,
                             "char_end": start + len(text),
                             "section": d.metadata["section"]}
                break
            pos += len(line)
        if candidate:
            break
    found = candidate["evidence_text"] if candidate else None
    return {"candidate": candidate,
            "attempts": state["attempts"] + 1,
            "trace": [f"extract (attempt {state['attempts'] + 1}): {found!r}"]}


# ---------------------------------------------------------------- extract (LLM)
SYSTEM_PROMPT = ("You read hospital discharge summaries. You never infer, convert or "
                 "calculate doses. You only copy text that is already in the document.")

USER_PROMPT = """Drug: {med}

Find the line in the CONTEXT that states the discharge dose of {med}.
Rules:
- Use only the section "{section}". Ignore every other section, especially "Medications on Admission".
- Copy that line exactly as written, character for character. Do not correct, shorten or merge lines.
- If {med} is not mentioned in that section, return found=false and an empty quote.
- Answer with JSON only: {{"found": true or false, "quote": "<the copied line>"}}
{feedback}
CONTEXT:
<<<
{context}
>>>"""

LIST_NO_RE = re.compile(r"^\s*\d+\.\s*")


def locate(doc: str, quote: str, ranges):
    """Find the model's quote in the ORIGINAL document. The model never gives positions.

    1. exact match inside the preferred ranges (retrieved chunks / target section)
    2. exact match anywhere (verify will judge the section)
    3. whitespace-tolerant match (model joined a line that wraps in the document)
    Returns (start, end) or None.
    """
    q = LIST_NO_RE.sub("", quote.strip())             # drop "1. " list numbers
    if not q:
        return None
    for s0, s1 in ranges:
        i = doc.find(q, s0, s1)
        if i >= 0:
            return i, i + len(q)
    i = doc.find(q)
    if i >= 0:
        return i, i + len(q)
    m = re.search(r"\s+".join(map(re.escape, q.split())), doc)
    return (m.start(), m.end()) if m else None


def _parse(text: str):
    """{"found": bool, "quote": str} or None if the output is not usable JSON."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or "found" not in obj:
        return None
    return {"found": bool(obj["found"]), "quote": str(obj.get("quote") or "")}


def make_extract(mode="A", llm=None):
    """LLM extractor.

    mode "A": context = retrieved chunks
    mode "D": context = whole document; the target section is named in the prompt
    llm: function(system, user) -> dict; defaults to call_llm (tests pass a fake)
    """
    if mode not in ("A", "D"):
        raise ValueError(f"mode must be 'A' or 'D', got {mode!r}")

    def extract(state: AgentState) -> dict:
        ask = llm or call_llm
        med, doc = state["med_name"], state["doc_text"]
        section = state["section_plan"][state["section_idx"]]
        attempt = state["attempts"] + 1

        if mode == "A":
            context = "\n---\n".join(d.page_content for d in state["chunks"])
            ranges = [(d.metadata["char_start"], d.metadata["char_end"]) for d in state["chunks"]]
        else:
            context = doc
            span = section_span(doc, section)
            ranges = [span] if span else []

        feedback = ""
        prev = state.get("candidate")
        if state["attempts"] > 0 and prev and state.get("verdict") in (
                "span_mismatch", "name_mismatch", "wrong_section"):
            feedback = (f"\nYour previous quote was rejected ({state['verdict']}): "
                        f"{prev['evidence_text']!r}. Copy the exact line for {med} "
                        f"from the section \"{section}\".\n")

        out = ask(SYSTEM_PROMPT, USER_PROMPT.format(
            med=med, section=section, feedback=feedback, context=context))
        usage = {"node": "extract", "mode": mode, "attempt": attempt,
                 "input_tokens": out["input_tokens"], "output_tokens": out["output_tokens"],
                 "ms": out["ms"], "model": out.get("model")}

        parsed = _parse(out["text"])
        if parsed is None:
            note, candidate = f"unparseable output {out['text'][:60]!r}", None
        elif not parsed["found"]:
            note, candidate = "found=false", None
        else:
            pos = locate(doc, parsed["quote"], ranges)
            if pos is None:            # quote is not in the document -> verify says span_mismatch
                text, s0, s1 = parsed["quote"], -1, -1
            else:
                s0, s1 = pos
                text = doc[s0:s1]
            dose, freq = DOSE_RE.search(text), FREQ_RE.search(text)
            candidate = {"dose": dose.group(0) if dose else None,
                         "frequency": freq.group(0) if freq else None,
                         "evidence_text": text, "char_start": s0, "char_end": s1,
                         "section": section}
            note = repr(text)

        return {"candidate": candidate, "attempts": attempt, "usage": [usage],
                "trace": [f"extract[{mode}] (attempt {attempt}, "
                          f"{out['input_tokens']}+{out['output_tokens']} tok, {out['ms']} ms): {note}"]}

    return extract


# ---------------------------------------------------------------- verify_evidence
def verify_evidence(state: AgentState) -> dict:
    """Independent check: re-open the document at the cited position."""
    c, doc = state.get("candidate"), state["doc_text"]
    if c is None:
        verdict = "not_found"                                   # drug not in this section
    elif doc[c["char_start"]:c["char_end"]] != c["evidence_text"]:
        verdict = "span_mismatch"                               # cited position is wrong
    elif state["med_name"] not in c["evidence_text"].lower():
        verdict = "name_mismatch"                               # cited a different drug's line
    elif section_at(doc, c["char_start"]) not in ALLOWED_SECTIONS:
        verdict = "wrong_section"                               # e.g. quoted the admission list
    else:
        doses = DOSE_RE.findall(c["evidence_text"])
        if not doses:
            verdict = "no_dose"                                 # drug listed, no dose
        elif len(doses) > 1:
            verdict = "multiple_doses"                          # e.g. a taper
        else:
            verdict = "ok"
    return {"verdict": verdict, "trace": [f"verify_evidence: {verdict}"]}


# ---------------------------------------------------------------- emit_result
def emit_result(state: AgentState) -> dict:
    c = state["candidate"]
    assert c is not None, "emit_result is only reached when verify says ok"
    result = {"doc_id": state["doc_id"],
              "medication": state["med_name"],
              "dose": c["dose"],
              "frequency": c["frequency"],
              "evidence_text": c["evidence_text"],
              "evidence_span": [c["char_start"], c["char_end"]],
              "section": c["section"],
              "admission": state.get("admission")}       # filled by compare_admission (next session)
    return {"result": result, "trace": [f"emit_result: {c['dose']} {c['frequency']}"]}


# ---------------------------------------------------------------- abstain
REASONS = {
    "no_dose": "the drug is listed but no dose is written",
    "multiple_doses": "more than one dose for this drug (e.g. a taper) - no single value",
    "not_found": "the drug was not found in any searched section",
    "span_mismatch": "the cited position could not be verified after retries",
    "wrong_section": "the only evidence found is outside the discharge sections",
    "name_mismatch": "the cited line does not mention the requested drug",
}


def abstain(state: AgentState) -> dict:
    v = state.get("verdict")
    if not state.get("chunks") and v is None:
        reason = "no relevant chunk in any searched section"
    else:
        reason = REASONS.get(v, "could not verify an answer")
    return {"result": None, "abstain_reason": reason, "trace": [f"abstain: {reason}"]}
