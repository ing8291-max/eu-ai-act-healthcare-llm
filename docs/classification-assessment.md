# Classification Assessment — EU AI Act

**System**: Medical Extraction Agent
**Assessed against**: Regulation (EU) 2024/1689, consolidated text of
27 July 2026 (CELEX 02024R1689-20260727)
**Date**: 2026-09-11
**Status**: Not high-risk
**Obligation**: None. Art. 6(4) applies only to systems referred to in
Annex III. This document is produced voluntarily.

---

## 1. Intended purpose

The system extracts medication entries — name, dose, frequency — from
clinical discharge summaries. For each value it returns the character
offsets in the source document where the value appears, and verifies
that the value is present at those offsets before emitting it. Where no
supporting span is found after a bounded retry, the system abstains
rather than producing a value.

The system does not diagnose, prescribe, prioritise patients, determine
eligibility for any service, or produce any decision about a natural
person. Output is an intermediate artifact for human review.

Development and evaluation use synthetic discharge summaries. No real
patient data is processed.

---

## 2. Route under Art. 6(1) — Annex I

| Condition | Assessment |
|---|---|
| 6(1)(a) safety component of, or itself a product covered by Union harmonisation legislation in Annex I | Not met. The system is not placed on the market as, or as part of, a product regulated under Annex I legislation. |
| 6(1)(b) that product required to undergo third-party conformity assessment under the same legislation | Not reached. Condition (a) fails and both must hold. |

Paragraphs 1a–1c were considered. 1a excludes systems used solely for
non-safety purposes; 1b returns to scope any system whose failure or
malfunctioning would endanger health and safety. The distinction turns
on failure consequences rather than intended use.

Under the current intended purpose the output is reviewed by a
clinician before any clinical use, and the system does not act on a
patient. This assessment would require revision if the output were
consumed automatically by a downstream clinical system.

**Conclusion: 6(1) does not apply.**

---

## 3. Route under Art. 6(2) — Annex III

All eight areas reviewed.

| Area | Applies |
|---|---|
| 1. Biometrics | No |
| 2. Critical infrastructure | No |
| 3. Education and vocational training | No |
| 4. Employment and worker management | No |
| 5. Access to essential services | See below |
| 6. Law enforcement | No |
| 7. Migration, asylum and border control | No |
| 8. Administration of justice and democratic processes | No |

### Area 5 in detail

| Sub-point | Applies | Reason |
|---|---|---|
| 5(a) eligibility for public assistance benefits and services, including healthcare services | No | The system makes no eligibility determination. It reports document content. |
| 5(b) creditworthiness and credit scoring | No | Out of domain. |
| 5(c) risk assessment and pricing in life and health insurance | No | No risk scoring of individuals is performed. |
| 5(d) emergency call triage and dispatch priority, including emergency patient triage | No | No prioritisation between patients is performed. |

**Conclusion: 6(2) does not apply. The system is outside Annex III.**

---

## 4. Consequences of this conclusion

Art. 6(3) is not reached — it is a derogation from 6(2) and applies only
to systems within Annex III.

Art. 6(4) is not triggered for the same reason. The documentation and
registration duties in that paragraph attach to providers of Annex III
systems that conclude they are not high-risk. This assessment is
therefore voluntary.

---

## 5. Conditions that would change this conclusion

This assessment is bound to the intended purpose stated in section 1.
It must be revisited if any of the following occurs.

- Output is consumed automatically by a clinical system without human
  review — 6(1) and 1b would require reconsideration.
- The system is applied to patient prioritisation or triage — 5(d).
- The system is applied to insurance risk assessment or pricing — 5(c).
- The system is used to determine eligibility for healthcare benefits
  or services — 5(a).
- Profiling of natural persons is introduced — always high-risk under
  6(3), final subparagraph.

---

## 6. Controls implemented regardless of classification

The following are not required by the Regulation at this
classification. They are implemented because the system is not useful
without them.

| Control | Rationale |
|---|---|
| Deterministic evidence verification | Values are emitted only if present at the offsets the model cites. |
| Bounded retry and abstention | Two failed verifications produce a recorded abstention rather than a value. |
| Structured audit logging | Every run is traceable by `run_id` with per-node inputs and outputs. |
| Labelled regression set | Accuracy, abstention rate and false-positive rate are measured, not asserted. |

---

## Revision history

| Date | Change |
|---|---|
| 2026-09-11 | Initial assessment. Not high-risk. |
