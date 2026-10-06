"""verify_evidence must only accept evidence from the discharge sections.

Run from the project root:  python -m pytest tests -q
"""
import pathlib

import pytest

from agents.nodes import section_at, verify_evidence

DOC03 = pathlib.Path("synthetic_kit/data/synthetic/doc_03.txt").read_text(encoding="utf-8")


def _verdict(doc, line, med="lisinopril"):
    i = doc.index(line)
    state = {"doc_text": doc, "med_name": med,
             "candidate": {"dose": None, "frequency": None, "evidence_text": line,
                           "char_start": i, "char_end": i + len(line), "section": "?"}}
    return verify_evidence(state)["verdict"]


@pytest.mark.parametrize("line, section, verdict", [
    ("Lisinopril 5 mg PO DAILY", "Discharge Medications", "ok"),
    ("lisinopril 10 mg PO daily", "Medications on Admission", "wrong_section"),
    ("Lisinopril was restarted at a reduced dose of 5 mg daily prior to",
     "Brief Hospital Course", "wrong_section"),
])
def test_section_check(line, section, verdict):
    assert section_at(DOC03, DOC03.index(line)) == section
    assert _verdict(DOC03, line) == verdict


def test_span_mismatch_is_caught():
    line = "Lisinopril 5 mg PO DAILY"
    i = DOC03.index(line)
    state = {"doc_text": DOC03, "med_name": "lisinopril",
             "candidate": {"dose": "5 mg", "frequency": "DAILY", "evidence_text": line,
                           "char_start": i + 1, "char_end": i + 1 + len(line), "section": "?"}}
    assert verify_evidence(state)["verdict"] == "span_mismatch"


def test_other_drug_line_is_rejected():
    # asked for pantoprazole, model cites a different drug's line in the right section
    doc02 = pathlib.Path("synthetic_kit/data/synthetic/doc_02.txt").read_text(encoding="utf-8")
    assert _verdict(doc02, "Omeprazole 20 mg PO DAILY", med="pantoprazole") == "name_mismatch"
