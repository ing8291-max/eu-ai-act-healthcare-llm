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
