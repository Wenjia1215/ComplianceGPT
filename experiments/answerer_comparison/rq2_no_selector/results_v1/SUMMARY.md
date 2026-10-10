# RQ2 No-Selector Ablation

Result identity: `rq2_no_selector_v1`

The no-selector path retains every record in each frozen RQ2 v3 evidence window. It performs no model inference, fallback, rescue, or hierarchy expansion.

## Complete strict-pass assessment

The complete seven-gate standard gives the following results for the original
saved contracts:

| Revision | ComplianceGPT selector | Original no-selector |
|---|---:|---:|
| Rev. 5 | 65/100 | 7/100 |
| Rev. 4 | 29/36 | 3/36 |

The original no-selector contracts contain empty clarification-request lists.
Among outputs passing C, 85 Revision 5 rows and 32 Revision 4 rows fail complete
retained-parameter accounting. This gap does not isolate the selector's effect.
The [versioned assessment](../strict_pass_v1/README.md) records every predicate
and the unchanged input hashes. A request-repaired replay is a separate condition.

The tables below retain the historical execution measurements. Their pass row
measures the legacy contract/gold check (C), rather than all seven gates.

## REV5

| Measure | Selector v3 | No selector v1 | Delta |
|---|---:|---:|---:|
| Legacy contract/gold pass (C) | 65/100 (0.650) | 92/100 (0.920) | +0.270 |
| Full gold-clause coverage | 65/100 (0.650) | 93/100 (0.930) | +0.280 |
| Right governing control | 97/100 (0.970) | 97/100 (0.970) | +0.000 |
| Mean selected clauses | 4.37 | 12.10 | +7.73 |
| Mean additional clauses | 1.75 | 8.85 | +7.10 |
| Mean gold-clause precision | 0.584 | 0.306 | -0.278 |
| Mean answer words | 220.7 | 601.7 | +381.0 |
| Mean citation characters | 48.8 | 143.2 | +94.4 |
| Exact ODP-list agreement | 55/63 (0.873) | 24/63 (0.381) | -0.492 |
| `PARAMS_REQUIRED` on author-labeled non-ODP rows | 20/37 (0.541) | 29/37 (0.784) | +0.243 |

No-selector p95 selected clauses: 24.0; p95 answer words: 1283.5.

## REV4

| Measure | Selector v3 | No selector v1 | Delta |
|---|---:|---:|---:|
| Legacy contract/gold pass (C) | 29/36 (0.806) | 35/36 (0.972) | +0.167 |
| Full gold-clause coverage | 29/36 (0.806) | 35/36 (0.972) | +0.167 |
| Right governing control | 36/36 (1.000) | 36/36 (1.000) | +0.000 |
| Mean selected clauses | 4.03 | 14.17 | +10.14 |
| Mean additional clauses | 2.08 | 11.78 | +9.69 |
| Mean gold-clause precision | 0.505 | 0.215 | -0.290 |
| Mean answer words | 167.2 | 604.9 | +437.8 |
| Mean citation characters | 45.1 | 168.2 | +123.1 |
| Exact ODP-list agreement | 12/19 (0.632) | 2/19 (0.105) | -0.526 |
| `PARAMS_REQUIRED` on author-labeled non-ODP rows | 9/17 (0.529) | 14/17 (0.824) | +0.294 |

No-selector p95 selected clauses: 24.0; p95 answer words: 954.5.

## Interpretation boundary

Higher coverage does not by itself establish a better operational answer. The additional-evidence, precision, and answer-length measures quantify the review burden created by retaining the whole window. Non-ODP status expansion is reported descriptively and is not called a false-positive rate without independent adjudication.
