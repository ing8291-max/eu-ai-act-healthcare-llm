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
    "doc_11": {
        "difficulty": "prn_dosing",
        "expected": [
            {"name": "oxycodone", "dose": "5 mg", "frequency": "every 4 hours PRN",
             "literal_in_doc": "Oxycodone 5 mg PO Q4H PRN pain", "section": DM},
            {"name": "acetaminophen", "dose": "650 mg", "frequency": "every 6 hours PRN",
             "literal_in_doc": "Acetaminophen 650 mg PO Q6H PRN", "section": DM},
            {"name": "docusate sodium", "dose": "100 mg", "frequency": "BID",
             "literal_in_doc": "Docusate Sodium 100 mg PO BID", "section": DM},
        ],
        "should_abstain": [],
        "absent_from_section": {"section": DM, "names": ["ibuprofen"]},
        "traps": [
            "PRN medications carry a condition ('PRN pain') that must not be dropped",
            "Ibuprofen is on the admission list and was stopped at discharge",
        ],
    },
    "doc_12": {
        "difficulty": "taper_schedule",
        "expected": [
            {"name": "pantoprazole", "dose": "40 mg", "frequency": "daily",
             "literal_in_doc": "Pantoprazole 40 mg PO DAILY", "section": DM},
            {"name": "calcium carbonate", "dose": "500 mg", "frequency": "BID",
             "literal_in_doc": "Calcium Carbonate 500 mg PO BID", "section": DM},
        ],
        "should_abstain": [
            {"field": "prednisone.dose", "reason": "taper: two doses over time, not one value"},
            {"field": "prednisone.frequency", "reason": "schedule with a stop date, not a single frequency"},
        ],
        "traps": [
            "Prednisone has 40 mg and 20 mg in one entry - reporting either alone is wrong",
            "The entry wraps across two lines",
        ],
    },
    "doc_13": {
        "difficulty": "salt_form_change",
        "expected": [
            {"name": "metoprolol succinate", "dose": "50 mg", "frequency": "daily",
             "literal_in_doc": "Metoprolol Succinate XL 50 mg PO DAILY", "section": DM},
            {"name": "atorvastatin", "dose": "80 mg", "frequency": "daily",
             "literal_in_doc": "Atorvastatin 80 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [],
        "absent_from_section": {"section": DM, "names": ["tartrate"]},
        "traps": [
            "Admission has metoprolol tartrate 25 mg BID; discharge is the succinate form, 50 mg daily",
            "Atorvastatin dose was increased from 40 mg to 80 mg",
        ],
    },
    "doc_14": {
        "difficulty": "held_medication",
        "expected": [
            {"name": "lisinopril", "dose": "10 mg", "frequency": "daily",
             "literal_in_doc": "Lisinopril 10 mg PO DAILY", "section": DM},
            {"name": "aspirin", "dose": "81 mg", "frequency": "daily",
             "literal_in_doc": "Aspirin 81 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [
            {"field": "metformin.dose", "reason": "held at discharge - no dose is ordered"},
            {"field": "metformin.frequency", "reason": "held at discharge"},
        ],
        "traps": [
            "Metformin is ON the discharge list but marked HOLD",
            "Admission lists metformin 500 mg BID - copying it is a false positive",
        ],
    },
    "doc_15": {
        "difficulty": "unit_variance",
        "expected": [
            {"name": "levothyroxine", "dose": "75 mcg", "frequency": "daily",
             "literal_in_doc": "Levothyroxine 0.075 mg PO DAILY", "section": DM},
            {"name": "digoxin", "dose": "0.125 mg", "frequency": "daily",
             "literal_in_doc": "Digoxin 125 mcg PO DAILY", "section": DM},
            {"name": "ferrous sulfate", "dose": "325 mg", "frequency": "daily",
             "literal_in_doc": "Ferrous Sulfate 325 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [],
        "traps": [
            "The document writes mcg doses in mg and mg doses in mcg",
            "expected.dose is normalised; literal_in_doc keeps the written unit",
        ],
    },
    "doc_16": {
        "difficulty": "route_variance",
        "expected": [
            {"name": "enoxaparin", "dose": "40 mg", "frequency": "daily",
             "literal_in_doc": "Enoxaparin 40 mg SC DAILY", "section": DM},
            {"name": "fluticasone-salmeterol", "dose": "1 puff (250/50)", "frequency": "BID",
             "literal_in_doc": "Fluticasone-Salmeterol 250/50 1 puff INH BID", "section": DM},
        ],
        "should_abstain": [
            {"field": "insulin_lispro.dose", "reason": "sliding scale - no unit count stated"},
            {"field": "insulin_lispro.frequency", "reason": "not stated"},
        ],
        "forbidden_patterns": [r"(?i)lispro[^\n]{0,30}\d", r"(?i)\d+\s*units"],
        "traps": [
            "Three routes in one list: SC, INH, SC sliding scale",
            "250/50 is a strength pair, not a dose in mg",
        ],
    },
    "doc_17": {
        "difficulty": "distractor_drugs",
        "expected": [
            {"name": "amoxicillin-clavulanate", "dose": "875 mg", "frequency": "BID",
             "literal_in_doc": "Amoxicillin-Clavulanate 875 mg PO BID", "section": DM},
            {"name": "guaifenesin", "dose": "600 mg", "frequency": "BID",
             "literal_in_doc": "Guaifenesin 600 mg PO BID", "section": DM},
            {"name": "albuterol", "dose": "2 puffs", "frequency": "every 6 hours PRN",
             "literal_in_doc": "Albuterol Inhaler 2 puffs INH Q6H PRN", "section": DM},
        ],
        "should_abstain": [],
        "absent_from_section": {"section": DM, "names": ["vancomycin", "cefepime", "warfarin"]},
        "traps": [
            "Allergies names a drug (Sulfamethoxazole) that is not a medication order",
            "Vancomycin and cefepime appear in the course as inpatient-only therapy",
            "Warfarin appears in the past medical history and was stopped years ago",
            "Amlodipine is on the admission list but not on the discharge list",
        ],
    },
    "doc_18": {
        "difficulty": "iv_to_po",
        "expected": [
            {"name": "metoprolol tartrate", "dose": "50 mg", "frequency": "BID",
             "literal_in_doc": "Metoprolol Tartrate 50 mg PO BID", "section": DM},
            {"name": "apixaban", "dose": "5 mg", "frequency": "BID",
             "literal_in_doc": "Apixaban 5 mg PO BID", "section": DM},
            {"name": "hydrochlorothiazide", "dose": "25 mg", "frequency": "daily",
             "literal_in_doc": "Hydrochlorothiazide 25 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [],
        "traps": [
            "The course states IV metoprolol 5 mg q6h - an inpatient dose, not the discharge dose",
            "Same drug, two doses and two routes in one document",
        ],
    },
    "doc_19": {
        "difficulty": "brand_generic_duplicate",
        "expected": [
            {"name": "ciprofloxacin", "dose": "500 mg", "frequency": "BID",
             "literal_in_doc": "Ciprofloxacin 500 mg PO BID", "section": DM},
            {"name": "acetaminophen", "dose": "500 mg", "frequency": "every 8 hours PRN",
             "literal_in_doc": "Acetaminophen 500 mg PO Q8H PRN", "section": DM},
            {"name": "losartan", "dose": "50 mg", "frequency": "daily",
             "literal_in_doc": "Losartan 50 mg PO DAILY", "section": DM},
        ],
        "should_abstain": [],
        "traps": [
            "Tylenol and acetaminophen are the same drug listed twice - one entry, not two",
            "The duplicate entry wraps across two lines",
        ],
    },
    "doc_20": {
        "difficulty": "no_discharge_list",
        "expected": [],
        "should_abstain": [
            {"field": "discharge_medications.list",
             "reason": "the discharge section states 'resume all home medications' and names none"},
        ],
        "traps": [
            "Medications on Admission has full doses - it is not a discharge order",
            "The only correct output is an abstention with the sentence as evidence",
        ],
    },
    "doc_21": {
        "difficulty": "composite",
        "expected": [
            {"name": "carvedilol", "dose": "6.25 mg", "frequency": "BID",
             "literal_in_doc": "Carvedilol 6.25 mg PO BID", "section": DM},
            {"name": "torsemide", "dose": "40 mg", "frequency": "daily",
             "literal_in_doc": "Torsemide 40 mg q.d.", "section": DM},
        ],
        "should_abstain": [
            {"field": "magnesium_oxide.dose", "reason": "per outpatient regimen - no dose stated"},
            {"field": "magnesium_oxide.frequency", "reason": "not stated"},
        ],
        "forbidden_patterns": [r"(?i)magnesium oxide[^\n]{0,20}\d"],
        "absent_from_section": {"section": DM, "names": ["spironolactone"]},
        "traps": [
            "Two dose changes (carvedilol 3.125 -> 6.25, torsemide 20 -> 40)",
            "Spironolactone stopped for hyperkalemia - reporting it is a false positive",
            "Magnesium oxide has no dose; 'Mg 1.8 -> 2.1' is a lab value",
            "Torsemide frequency is written q.d.",
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
