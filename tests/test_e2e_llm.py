"""END-TO-END with the REAL LLM. Costs money, needs .env, results can vary run to run.

Skipped by default. Run on purpose:
    python -m pytest -m llm -v

Retrieval is replaced by SectionStore (no embeddings needed), everything else is real:
route -> retrieve -> real Claude extract -> verify -> emit/abstain.
Each case was checked against the answer key (synthetic_kit/tests/fixtures) BEFORE
being written here - expected values come from the key, never from memory.
"""
import os

import pytest

pytestmark = pytest.mark.llm

pytest.importorskip("langgraph")

from agents.graph import build_graph  # noqa: E402
from tests.fakes import SectionStore  # noqa: E402

if not os.environ.get("LLM_PROVIDER"):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

needs_key = pytest.mark.skipif(not os.environ.get("LLM_PROVIDER"),
                               reason="no LLM_PROVIDER in environment/.env")

# (doc_id, medication, expected dose or None for abstain, literal that must be cited, why)
CASES = [
    ("doc_02", "omeprazole", "20 mg", "Omeprazole 20 mg PO DAILY", "plain list"),
    ("doc_03", "lisinopril", "5 mg", "Lisinopril 5 mg PO DAILY", "admission list says 10 mg"),
    ("doc_08", "prednisone", "20 mg", "prednisone 20 mg daily", "dose only in prose"),
    ("doc_08", "albuterol", "2 puffs", "albuterol 2 puffs every 6 hours", "dose only in prose"),
    ("doc_02", "pantoprazole", None, None, "not in document; same-class omeprazole nearby"),
    ("doc_12", "prednisone", None, None, "taper: two doses"),
    ("doc_05", "gabapentin", None, None, "listed without a dose"),
]


@pytest.fixture(scope="module")
def app():
    return build_graph(SectionStore(), mode="A")


@needs_key
@pytest.mark.parametrize("doc_id, med, dose, literal, why", CASES,
                         ids=[f"{c[0]}-{c[1]}" for c in CASES])
def test_real_llm_end_to_end(app, doc_id, med, dose, literal, why):
    out = app.invoke({"doc_id": doc_id, "question": f"What is the discharge dose of {med}?",
                      "trace": [], "usage": []})
    trace = "\n".join(out["trace"])
    assert "TRUNCATED" not in trace, f"output cut off ({why})\n{trace}"
    r = out.get("result")
    if dose is None:
        assert r is None, f"should abstain ({why}) but answered {r and r['dose']}\n{trace}"
    else:
        assert r is not None, f"missed ({why}): {out.get('abstain_reason')}\n{trace}"
        assert r["dose"] == dose, f"wrong dose ({why})\n{trace}"
        assert literal in r["evidence_text"], f"cited the wrong text ({why})\n{trace}"
    assert out["usage"], "no LLM call was recorded"
