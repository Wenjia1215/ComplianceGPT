# RQ2 Control Gate Width Sensitivity

The pass columns retain the execution-time contract/gold endpoint (C).
See the [result map](../../../../docs/EVALUATION_RESULTS.md) for the complete
seven-gate standard and the boundaries between scoring versions. Original
contracts and numeric measurements remain unchanged.

Result identity: `rq2_control_gate_width_v1`

The fixed-width sweep changes only the number of ranked controls admitted to the shared 24-record evidence window. The released adaptive gate is shown as an unchanged reference.

## REV5

| Gate | Legacy contract/gold pass (C) | Full clause coverage | Mean clause precision | Mean selected clauses | ODP sensitivity* | ODP specificity* |
|---|---:|---:|---:|---:|---:|---:|
| Adaptive v3 | 65/100 (0.650) | 65/100 (0.650) | 0.584 | 4.37 | 63/63 (1.000) | 17/37 (0.459) |
| Top 1 | 62/100 (0.620) | 62/100 (0.620) | 0.582 | 4.15 | 62/63 (0.984) | 17/37 (0.459) |
| Top 2 | 65/100 (0.650) | 65/100 (0.650) | 0.572 | 4.30 | 63/63 (1.000) | 16/37 (0.432) |
| Top 3 | 65/100 (0.650) | 65/100 (0.650) | 0.565 | 4.28 | 63/63 (1.000) | 16/37 (0.432) |
| Top 5 | 67/100 (0.670) | 67/100 (0.670) | 0.560 | 4.55 | 63/63 (1.000) | 12/37 (0.324) |

*ODP operating characteristics use the author labels and remain provisional until the blinded independent annotation is returned.*

## REV4

| Gate | Legacy contract/gold pass (C) | Full clause coverage | Mean clause precision | Mean selected clauses | ODP sensitivity* | ODP specificity* |
|---|---:|---:|---:|---:|---:|---:|
| Adaptive v3 | 29/36 (0.806) | 29/36 (0.806) | 0.505 | 4.03 | 19/19 (1.000) | 8/17 (0.471) |
| Top 1 | 26/36 (0.722) | 26/36 (0.722) | 0.497 | 3.89 | 19/19 (1.000) | 8/17 (0.471) |
| Top 2 | 29/36 (0.806) | 29/36 (0.806) | 0.511 | 3.86 | 19/19 (1.000) | 8/17 (0.471) |
| Top 3 | 29/36 (0.806) | 29/36 (0.806) | 0.511 | 3.97 | 19/19 (1.000) | 8/17 (0.471) |
| Top 5 | 28/36 (0.778) | 28/36 (0.778) | 0.491 | 4.17 | 19/19 (1.000) | 8/17 (0.471) |

*ODP operating characteristics use the author labels and remain provisional until the blinded independent annotation is returned.*

## Interpretation boundary

The existing gold-based citation-contract endpoint: full expected-clause coverage, source/revision/verbatim validity, and ODP/status consistency. It permits extra evidence.

Gate width is the only changed factor. ODP operating characteristics use author labels and are provisional pending blinded independent annotation.
