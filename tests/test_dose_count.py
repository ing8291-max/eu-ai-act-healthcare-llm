"""verify must abstain when a discharge line has no dose or more than one dose."""
import pathlib

import pytest

from agents.nodes import verify_evidence

DATA = pathlib.Path("synthetic_kit/data/synthetic")


def _verdict(doc_id, line, med):
    doc = (DATA / f"{doc_id}.txt").read_text(encoding="utf-8")
    i = doc.index(line)
    state = {"doc_text": doc, "med_name": med,
             "candidate": {"dose": None, "frequency": None, "evidence_text": line,
                           "char_start": i, "char_end": i + len(line), "section": "?"}}
    return verify_evidence(state)["verdict"]


@pytest.mark.parametrize("doc_id, line, med, verdict", [
    # no number + unit on the line -> no single dose to report
    ("doc_05", "Gabapentin - continue home regimen", "gabapentin", "no_dose"),
    ("doc_14", "HOLD Metformin until creatinine is rechecked by your doctor", "metformin", "no_dose"),
    # taper: 40 mg then 20 mg -> two doses, must not pick one
    ("doc_12", "Prednisone 40 mg PO daily for 3 days, then 20 mg PO daily for 3",
     "prednisone", "multiple_doses"),
])
def test_dose_count(doc_id, line, med, verdict):
    assert _verdict(doc_id, line, med) == verdict
