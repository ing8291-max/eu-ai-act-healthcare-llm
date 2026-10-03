# Synthetic discharge summaries — Golden Dataset v0

10 fictional discharge summaries in MIMIC-IV-Note format, with an answer
key for each. No real patient data. All PHI fields are `___`.

## Layout

```
data/synthetic/doc_01.txt ... doc_10.txt   documents (RAG corpus)
tests/fixtures/doc_01.json ... doc_10.json answer keys (test set)
scripts/build_fixtures.py                  regenerates the answer keys
scripts/check_fixtures.py                  verifies keys against documents
```

## Verify

```bash
python scripts/check_fixtures.py
```

Expected last line: `OK - 10 documents, all checks passed`.
It also prints the `evidence_span` a correct agent should return for
every expected value.

## What each document tests

| Doc | Type | What it checks |
|---|---|---|
| 01, 02 | baseline | basic extraction |
| 03, 04 | dose change | admission dose differs from discharge dose |
| 05, 06 | missing dose | agent must abstain, not guess |
| 07 | discontinuation | stopped drug must not be reported |
| 08 | narrative only | values only in prose, no list |
| 09 | notation variance | q.d. / twice daily / QHS |
| 10 | composite | dose change + missing dose together |
| 11 | PRN dosing | "PRN pain" condition must survive; stopped ibuprofen |
| 12 | taper | one entry holds 40 mg then 20 mg then stop → abstain |
| 13 | salt form | tartrate 25 BID on admission → succinate XL 50 daily |
| 14 | held med | metformin is on the list but marked HOLD → abstain |
| 15 | unit variance | 0.075 mg = 75 mcg, 125 mcg = 0.125 mg |
| 16 | route variance | SC / INH / sliding scale; 250/50 is a strength |
| 17 | distractors | allergy drug, inpatient-only IV antibiotics, old warfarin |
| 18 | IV → PO | IV metoprolol 5 mg in prose vs PO 50 mg at discharge |
| 19 | brand duplicate | Tylenol and acetaminophen are one medication |
| 20 | no list | "Resume all home medications" → abstain, do not copy admission |
| 21 | composite | 2 dose changes + discontinuation + missing dose + q.d. |

## Fixture fields

- `expected[].dose`, `frequency` — normalised answer, used for accuracy
- `expected[].literal_in_doc` — exact text in the document, used for
  offset verification; appears exactly once
- `expected[].section` — section the answer must come from
- `should_abstain` — fields with no supporting text; the correct output
  is an abstention
- `forbidden_patterns` — regexes that must NOT match the document; proves
  the abstain targets really have no value
- `synthetic: true` — marks the data as generated (EU AI Act Art. 10(2)(h)
  known gap: not representative of real clinical text)
