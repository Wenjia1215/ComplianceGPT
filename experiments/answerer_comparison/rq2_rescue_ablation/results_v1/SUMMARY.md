# RQ2 ODP-Statement Rescue Ablation

The pass rows below retain the legacy contract/gold check (C). See the
[result map](../../../../docs/EVALUATION_RESULTS.md) for the complete seven-gate
assessment and its distinct scoring identity. Original contracts and numeric
measurements remain unchanged.

Result identity: `rq2_rescue_ablation_v1`

The replay reconstructs the frozen selector path immediately before bounded ODP-statement rescue. It performs no retrieval or model inference. Every rescue-on replay must reproduce the frozen core contract before an on/off effect is reported.

## REV5

Rescue activates on 22/100 rows and adds 44 identifier occurrences (8 expected-gold occurrences).

| Measure | Rescue off | Rescue on | Delta |
|---|---:|---:|---:|
| Legacy contract/gold pass (C) | 59/100 (0.590) | 65/100 (0.650) | +0.060 |
| Full gold-clause coverage | 59/100 (0.590) | 65/100 (0.650) | +0.060 |
| Right governing control | 97/100 (0.970) | 97/100 (0.970) | +0.000 |
| `PARAMS_REQUIRED` on gold ODP rows | 55/63 (0.873) | 63/63 (1.000) | +0.127 |
| False complete on gold ODP rows | 8/63 (0.127) | 0/63 (0.000) | -0.127 |
| Exact ODP-list agreement | 47/63 (0.746) | 55/63 (0.873) | +0.127 |
| `PARAMS_REQUIRED` on labeled non-ODP rows | 6/37 (0.162) | 20/37 (0.541) | +0.378 |
| Mean selected clauses | 3.93 | 4.37 | +0.44 |
| Mean additional clauses | 1.39 | 1.75 | +0.36 |
| Mean gold-clause precision | 0.622 | 0.584 | -0.038 |
| Mean answer words | 208.0 | 220.7 | +12.7 |
| Mean surfaced ODPs | 1.53 | 1.97 | +0.44 |

## REV4

Rescue activates on 2/36 rows and adds 6 identifier occurrences (0 expected-gold occurrences).

| Measure | Rescue off | Rescue on | Delta |
|---|---:|---:|---:|
| Legacy contract/gold pass (C) | 29/36 (0.806) | 29/36 (0.806) | +0.000 |
| Full gold-clause coverage | 29/36 (0.806) | 29/36 (0.806) | +0.000 |
| Right governing control | 36/36 (1.000) | 36/36 (1.000) | +0.000 |
| `PARAMS_REQUIRED` on gold ODP rows | 19/19 (1.000) | 19/19 (1.000) | +0.000 |
| False complete on gold ODP rows | 0/19 (0.000) | 0/19 (0.000) | +0.000 |
| Exact ODP-list agreement | 12/19 (0.632) | 12/19 (0.632) | +0.000 |
| `PARAMS_REQUIRED` on labeled non-ODP rows | 7/17 (0.412) | 9/17 (0.529) | +0.118 |
| Mean selected clauses | 3.86 | 4.03 | +0.17 |
| Mean additional clauses | 1.92 | 2.08 | +0.17 |
| Mean gold-clause precision | 0.513 | 0.505 | -0.008 |
| Mean answer words | 157.8 | 167.2 | +9.3 |
| Mean surfaced ODPs | 1.25 | 1.36 | +0.11 |

## Interpretation boundary

This is a deterministic replay over fixed frozen selector outputs. Non-ODP status expansion is descriptive and is not called a false-positive rate or specificity estimate without independent adjudication.
