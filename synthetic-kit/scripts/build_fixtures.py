"""Write ground-truth fixtures for the 10 synthetic discharge summaries.

Each fixture is the answer key. It was written BEFORE the document text,
and the document was written to contain these values verbatim.
"""
import json
import pathlib

DM = "Discharge Medications"
DI = "Discharge Instructions"

FIXTURES = {
    "doc_01": {
        "difficulty": "baseline",
        "expected": [
            {"name": "metoprolol tartrate", "dose": "25 mg", "frequency": "BID",
             "literal_in_doc": "Metoprolol Tartrate 25 mg PO BID", "section": DM},
            {"name": "atorvastatin", "dose": "40 mg", "frequency": "daily",
             "literal_in_doc": "Atorvastatin 40 mg PO DAILY", "section": DM},
            {"name": "aspirin", "dose": "81 mg", "frequency": "daily",
             "literal_in_doc": "Aspirin 81 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [],
        "traps": [],
    },
    "doc_02": {
        "difficulty": "baseline",
        "expected": [
            {"name": "levothyroxine", "dose": "75 mcg", "frequency": "daily",
             "literal_in_doc": "Levothyroxine Sodium 75 mcg PO DAILY", "section": DM},
            {"name": "omeprazole", "dose": "20 mg", "frequency": "daily",
             "literal_in_doc": "Omeprazole 20 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [],
        "traps": [],
    },
    "doc_03": {
        "difficulty": "dose_change",
        "expected": [
            {"name": "lisinopril", "dose": "5 mg", "frequency": "daily",
             "literal_in_doc": "Lisinopril 5 mg PO DAILY", "section": DM},
            {"name": "furosemide", "dose": "40 mg", "frequency": "daily",
             "literal_in_doc": "Furosemide 40 mg PO DAILY", "section": DM},
            {"name": "metoprolol tartrate", "dose": "25 mg", "frequency": "BID",
             "literal_in_doc": "Metoprolol Tartrate 25 mg PO BID", "section": DM},
        ],
        "should_abstain": [],
        "traps": [
            "Medications on Admission lists lisinopril 10 mg - wrong value if the admission section is used",
            "Brief Hospital Course also mentions 5 mg in prose - correct value, but not the discharge list",
        ],
    },
    "doc_04": {
        "difficulty": "dose_change",
        "expected": [
            {"name": "warfarin", "dose": "2.5 mg", "frequency": "daily",
             "literal_in_doc": "Warfarin 2.5 mg PO DAILY", "section": DM},
            {"name": "pantoprazole", "dose": "40 mg", "frequency": "daily",
             "literal_in_doc": "Pantoprazole 40 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [],
        "traps": [
            "Medications on Admission lists warfarin 5 mg",
            "Brief Hospital Course states the prior dose of 5 mg daily in prose",
        ],
    },
    "doc_05": {
        "difficulty": "missing_dose",
        "expected": [
            {"name": "amlodipine", "dose": "5 mg", "frequency": "daily",
             "literal_in_doc": "Amlodipine 5 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [
            {"field": "gabapentin.dose", "reason": "listed without a dose"},
            {"field": "gabapentin.frequency", "reason": "listed without a frequency"},
        ],
        "forbidden_patterns": [r"(?i)gabapentin[^\n]{0,20}\d"],
        "traps": [
            "Gabapentin is on the discharge list with no dose anywhere in the document",
            "Medications on Admission is empty - there is no prior dose to fall back on",
        ],
    },
    "doc_06": {
        "difficulty": "missing_dose",
        "expected": [
            {"name": "metformin", "dose": "1000 mg", "frequency": "BID",
             "literal_in_doc": "Metformin 1000 mg PO BID", "section": DM},
        ],
        "should_abstain": [
            {"field": "insulin_glargine.dose", "reason": "resume home dose - no units stated"},
            {"field": "insulin_glargine.frequency", "reason": "not stated"},
        ],
        "forbidden_patterns": [r"(?i)glargine[^\n]{0,30}\d", r"(?i)\d+\s*units"],
        "traps": [
            "Insulin glargine appears three times (admission, prose, discharge) with no unit count",
        ],
    },
    "doc_07": {
        "difficulty": "discontinuation",
        "expected": [
            {"name": "sertraline", "dose": "50 mg", "frequency": "daily",
             "literal_in_doc": "Sertraline 50 mg PO DAILY", "section": DM},
            {"name": "amlodipine", "dose": "5 mg", "frequency": "daily",
             "literal_in_doc": "Amlodipine 5 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [],
        "absent_from_section": {"section": DM, "names": ["trazodone"]},
        "traps": [
            "Trazodone 50 mg is on the admission list but was discontinued - reporting it is a false positive",
        ],
    },
    "doc_08": {
        "difficulty": "narrative_only",
        "expected": [
            {"name": "prednisone", "dose": "20 mg", "frequency": "daily",
             "literal_in_doc": "prednisone 20 mg daily", "section": DI},
            {"name": "albuterol", "dose": "2 puffs", "frequency": "every 6 hours",
             "literal_in_doc": "albuterol 2 puffs every 6 hours", "section": DI},
        ],
        "should_abstain": [],
        "traps": [
            "Discharge Medications section only says 'See discharge instructions.'",
            "Values appear only in prose under Discharge Instructions",
            "Admission lists 'albuterol inhaler PRN' without a dose",
        ],
    },
    "doc_09": {
        "difficulty": "abbreviation_variance",
        "expected": [
            {"name": "hydrochlorothiazide", "dose": "25 mg", "frequency": "daily",
             "literal_in_doc": "Hydrochlorothiazide 25 mg q.d.", "section": DM},
            {"name": "carvedilol", "dose": "12.5 mg", "frequency": "BID",
             "literal_in_doc": "Carvedilol 12.5 mg twice daily", "section": DM},
            {"name": "rosuvastatin", "dose": "10 mg", "frequency": "nightly",
             "literal_in_doc": "Rosuvastatin 10 mg QHS", "section": DM},
        ],
        "should_abstain": [],
        "traps": [
            "Three different frequency notations: q.d. / twice daily / QHS",
            "expected.frequency is normalised; literal_in_doc is not",
        ],
    },
    "doc_10": {
        "difficulty": "composite",
        "expected": [
            {"name": "furosemide", "dose": "20 mg", "frequency": "daily",
             "literal_in_doc": "Furosemide 20 mg PO DAILY", "section": DM},
            {"name": "digoxin", "dose": "0.125 mg", "frequency": "daily",
             "literal_in_doc": "Digoxin 0.125 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [
            {"field": "potassium_chloride.dose", "reason": "per outpatient regimen - no dose stated"},
            {"field": "potassium_chloride.frequency", "reason": "not stated"},
        ],
        "forbidden_patterns": [
            r"(?i)potassium chloride[^\n]{0,20}\d",
            r"(?i)\bKCl\b",
            r"(?i)\d+\s*mEq",
        ],
        "traps": [
            "Medications on Admission lists furosemide 40 mg; discharge is 20 mg",
            "Brief Hospital Course states the prior 40 mg dose in prose",
            "Potassium chloride has no dose anywhere; 'K 3.3 -> 4.1' is a lab value, not a dose",
        ],
    },
}


def main() -> None:
    out = pathlib.Path("tests/fixtures")
    out.mkdir(parents=True, exist_ok=True)
    for doc_id, fx in FIXTURES.items():
        record = {
            "doc_id": doc_id,
            "source": f"data/synthetic/{doc_id}.txt",
            "synthetic": True,
            **fx,
        }
        (out / f"{doc_id}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print(f"wrote {len(FIXTURES)} fixtures to {out}/")


if __name__ == "__main__":
    main()
