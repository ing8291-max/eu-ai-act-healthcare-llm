"""Verify every fixture against its source document.

Checks, per document:
  1. each expected literal appears in the document exactly once
  2. that occurrence sits inside the section named in the fixture
  3. no forbidden pattern appears (proves abstain targets have no value)
  4. names listed under absent_from_section do not appear in that section
  5. PHI placeholders are exactly three underscores

Prints the character offsets of each literal - these are the
evidence_span values a correct agent should return.
"""
import json
import pathlib
import re
import sys

HEADERS = [
    "Chief Complaint:", "Major Surgical or Invasive Procedure:",
    "History of Present Illness:", "Past Medical History:", "Social History:",
    "Family History:", "Physical Exam:", "Pertinent Results:",
    "Brief Hospital Course:", "Medications on Admission:",
    "Discharge Medications:", "Discharge Disposition:", "Discharge Diagnosis:",
    "Discharge Condition:", "Discharge Instructions:", "Followup Instructions:",
]


def section_spans(doc: str) -> dict[str, tuple[int, int]]:
    found = []
    for h in HEADERS:
        m = re.search(rf"^{re.escape(h)}", doc, flags=re.M)
        if m:
            found.append((m.start(), h[:-1]))
    found.sort()
    spans = {}
    for i, (start, name) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(doc)
        spans[name] = (start, end)
    return spans


def main() -> int:
    fails = 0
    fixtures = sorted(pathlib.Path("tests/fixtures").glob("doc_*.json"))
    if not fixtures:
        print("no fixtures found - run scripts/build_fixtures.py first")
        return 1

    for f in fixtures:
        fx = json.loads(f.read_text(encoding="utf-8"))
        doc = pathlib.Path(fx["source"]).read_text(encoding="utf-8")
        spans = section_spans(doc)
        problems = []

        for med in fx["expected"]:
            lit, sec = med["literal_in_doc"], med["section"]
            hits = [m.start() for m in re.finditer(re.escape(lit), doc)]
            if len(hits) != 1:
                problems.append(f"literal {lit!r} found {len(hits)} times (need 1)")
                continue
            start = hits[0]
            end = start + len(lit)
            s0, s1 = spans.get(sec, (-1, -1))
            if not (s0 <= start and end <= s1):
                problems.append(f"literal {lit!r} not inside section {sec!r}")
            med["_span"] = (start, end)

        for pat in fx.get("forbidden_patterns", []):
            m = re.search(pat, doc)
            if m:
                problems.append(f"forbidden pattern {pat!r} matched {m.group(0)!r}")

        absent = fx.get("absent_from_section")
        if absent:
            s0, s1 = spans[absent["section"]]
            body = doc[s0:s1].lower()
            for name in absent["names"]:
                if name.lower() in body:
                    problems.append(f"{name!r} must not appear in {absent['section']!r}")

        bad_phi = re.findall(r"(?<!_)_{2}(?!_)|_{4,}", doc)
        if bad_phi:
            problems.append(f"PHI placeholder not exactly '___': {bad_phi[:3]}")

        tag = "FAIL" if problems else "ok  "
        print(f"{tag} {fx['doc_id']}  [{fx['difficulty']}]")
        for med in fx["expected"]:
            if "_span" in med:
                s, e = med["_span"]
                print(f"       {med['name']:<22} evidence_span=[{s}, {e}]")
        for ab in fx.get("should_abstain", []):
            print(f"       abstain: {ab['field']}")
        for p in problems:
            print(f"       !! {p}")
        fails += len(problems)

    print()
    print("FAIL" if fails else f"OK - {len(fixtures)} documents, all checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
