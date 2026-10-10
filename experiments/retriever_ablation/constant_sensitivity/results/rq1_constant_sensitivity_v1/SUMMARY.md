# Primary RQ1 constant sensitivity

Result identity: `rq1_constant_sensitivity_v1`.
Execution source: `a066453a317bba365db707b71745e49fee28811a`.
Protocol SHA-256: `f094327ea5a63f2f25043c1c6f4f0f84bb5bc0f57326bcb374fa4a4c14a6123b`.

Seven conditions share identical inferred channel/cross-encoder scores for each question.
The historical primary notebook logic and frozen rewrites are retained.

## rev4

| Condition | Success@1 | Success@5 | Success@10 | MRR@10 | nDCG@10 | Logical calls | Adopted |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0.8889 | 1.0000 | 1.0000 | 0.9444 | 0.9590 | 34 | 30 |
| alpha_minus20 | 0.9167 | 1.0000 | 1.0000 | 0.9583 | 0.9692 | 34 | 31 |
| alpha_plus20 | 0.8611 | 1.0000 | 1.0000 | 0.9259 | 0.9451 | 34 | 29 |
| adoption_minus20 | 0.9444 | 1.0000 | 1.0000 | 0.9722 | 0.9795 | 34 | 32 |
| adoption_plus20 | 0.8889 | 1.0000 | 1.0000 | 0.9444 | 0.9590 | 34 | 30 |
| skip_minus20 | 0.8889 | 1.0000 | 1.0000 | 0.9444 | 0.9590 | 33 | 29 |
| skip_plus20 | 0.8889 | 1.0000 | 1.0000 | 0.9444 | 0.9590 | 35 | 31 |

## rev5

| Condition | Success@1 | Success@5 | Success@10 | MRR@10 | nDCG@10 | Logical calls | Adopted |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0.9000 | 0.9900 | 1.0000 | 0.9443 | 0.9584 | 84 | 81 |
| alpha_minus20 | 0.9000 | 0.9900 | 0.9900 | 0.9433 | 0.9555 | 84 | 79 |
| alpha_plus20 | 0.8800 | 0.9900 | 1.0000 | 0.9344 | 0.9511 | 84 | 79 |
| adoption_minus20 | 0.9000 | 0.9900 | 1.0000 | 0.9443 | 0.9584 | 84 | 81 |
| adoption_plus20 | 0.9000 | 0.9900 | 1.0000 | 0.9443 | 0.9584 | 84 | 81 |
| skip_minus20 | 0.9000 | 0.9900 | 1.0000 | 0.9443 | 0.9584 | 79 | 76 |
| skip_plus20 | 0.9000 | 0.9900 | 1.0000 | 0.9443 | 0.9584 | 91 | 87 |

## pooled

| Condition | Success@1 | Success@5 | Success@10 | MRR@10 | nDCG@10 | Logical calls | Adopted |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 0.8971 | 0.9926 | 1.0000 | 0.9444 | 0.9585 | 118 | 111 |
| alpha_minus20 | 0.9044 | 0.9926 | 0.9926 | 0.9473 | 0.9591 | 118 | 110 |
| alpha_plus20 | 0.8750 | 0.9926 | 1.0000 | 0.9322 | 0.9495 | 118 | 108 |
| adoption_minus20 | 0.9118 | 0.9926 | 1.0000 | 0.9517 | 0.9640 | 118 | 113 |
| adoption_plus20 | 0.8971 | 0.9926 | 1.0000 | 0.9444 | 0.9585 | 118 | 111 |
| skip_minus20 | 0.8971 | 0.9926 | 1.0000 | 0.9444 | 0.9585 | 112 | 105 |
| skip_plus20 | 0.8971 | 0.9926 | 1.0000 | 0.9444 | 0.9585 | 126 | 118 |

## Historical comparison and limits

New baseline retains the historical top-10 order in 65/136 queries, gold rank in 134/136, and gate/variant flags in 135/136.
Historical model revisions were not recorded; new model revisions and runtime are pinned here. Any drift is reported and the historical headline scores remain unchanged.

This exploratory local sensitivity check does not remove evaluation-set tuning bias or establish held-out validity. Paired p-values are unadjusted; bootstrap intervals use paired query resampling. Governing-control labels are author references, not independently adjudicated truth. The complete-candidate probes enable skip-gate counterfactuals; logical call counts are not measured latency savings.

All seven conditions, per-query ranks, gate effects, Wilson intervals, paired comparisons, historical differences and complete candidate score caches are retained. No condition is selected as a replacement main result.
