# Intra-annotator test-retest agreement

## Frozen inputs

- Completed workbook SHA-256: `7815a13223f356a69ae67ce4f989d2eb01c79c598510cd1c3bf3dd9598f61ca2`
- Frozen at: 2026-10-02T12:08:35-04:00
- Canonical sample commitment: `a6582b20ea6605395627dd0229981be6841ef76e55af022526ce773f71a686c0`
- Revealed mapping SHA-256: `2f8c0915a6791e55b4bcff58c5db6f17c29da54dfc81bcd82780ef79bc04db0e`

The original and second labels were compared only after the completed workbook was hashed. The analysis treats clause and ODP fields as sets, ignores order and surrounding whitespace, and treats `NONE` as an empty set. Jaccard similarity is 1.0 when both sets are empty.

## Results

| Metric | Overall | Revision 4 | Revision 5 |
| --- | ---: | ---: | ---: |
| Control exact agreement | 29/30 (96.7%) | 8/8 (100.0%) | 21/22 (95.5%) |
| Control Cohen's kappa | 0.965 | 1.000 | 0.952 |
| Clause-set exact agreement | 16/30 (53.3%) | 4/8 (50.0%) | 12/22 (54.5%) |
| Clause-set mean Jaccard | 0.796 | 0.703 | 0.829 |
| ODP-set exact agreement | 26/30 (86.7%) | 7/8 (87.5%) | 19/22 (86.4%) |
| ODP-set mean Jaccard | 0.887 | 0.875 | 0.891 |
| All three components exact | 16/30 (53.3%) | 4/8 (50.0%) | 12/22 (54.5%) |

## Row-level disagreement audit

| Blind ID | Rev. | Original row | Different components | Added in retest | Missing from retest |
| --- | --- | ---: | --- | --- | --- |
| IR-001 | 5 | 36 | clauses | — | clauses: ir-2_smt.a |
| IR-003 | 4 | 8 | clauses | — | clauses: ca-7_smt |
| IR-004 | 5 | 12 | clauses | — | clauses: au-3_smt |
| IR-005 | 5 | 89 | clauses, ODPs | clauses: sc-13_smt.a, sc-13_smt.b; ODPs: sc-13_odp.01, sc-13_odp.02 | — |
| IR-006 | 5 | 80 | clauses | clauses: ra-9_gdn | — |
| IR-007 | 5 | 67 | clauses | clauses: ps-3_gdn | — |
| IR-008 | 5 | 96 | clauses | clauses: sr-2_gdn | — |
| IR-010 | 4 | 28 | clauses, ODPs | — | clauses: ps-3_smt.b; ODPs: ps-3_prm_1 |
| IR-015 | 5 | 71 | control, clauses, ODPs | control: PT-3; clauses: pt-3_smt.a, pt-3_smt.c; ODPs: pt-03_odp.01, pt-03_odp.02 | control: PT-2 |
| IR-017 | 4 | 3 | clauses | — | clauses: at-2_smt.a, at-2_smt.b, at-2_smt.c |
| IR-021 | 5 | 73 | clauses, ODPs | clauses: pt-4_smt; ODPs: pt-04_odp | — |
| IR-026 | 5 | 61 | clauses | clauses: pm-2_smt | — |
| IR-028 | 5 | 84 | clauses | — | clauses: sa-10_smt |
| IR-029 | 4 | 14 | clauses | clauses: ia-5_smt.a, ia-5_smt.b, ia-5_smt.c, ia-5_smt.d, ia-5_smt.e, ia-5_smt.h, ia-5_smt.i | clauses: ia-5_gdn |

## Interpretation boundary

This is an intra-annotator test-retest check of label stability. It is weaker than independent adjudication and does not establish that the labels are externally correct.
