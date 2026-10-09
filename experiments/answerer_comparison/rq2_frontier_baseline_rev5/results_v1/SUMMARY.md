# Batch 5D — Revision 5 Frontier API Baseline

Result identity: `rq2_frontier_baseline_rev5_v1`

Current [Answer-content strict pass](../../answer_content_strict_pass/README.md): ComplianceGPT **65/100 (65%)**, Gemini **56/100 (56%)**, Qwen 4-bit baseline **21/100 (21%)**. See the [complete re-evaluation](../../answer_content_strict_pass/results_v1/SUMMARY.md). The archived tables below retain the original legacy strict-pass endpoint and historical statistics.

All systems use the same 100 frozen Revision 5 questions, ordered evidence windows, ASK policy, and offline verifier. The primary registered comparison is ComplianceGPT versus Gemini 3.5 Flash.

## Primary and supporting outcomes

| System | Legacy strict pass [95% CI] | Full clause coverage | Runtime pass | Clause precision | Clause recall | Mean words |
|---|---:|---:|---:|---:|---:|---:|
| ComplianceGPT, 4-bit selector | 65/100 (0.650) [0.553, 0.736] | 65/100 (0.650) | 100/100 (1.000) | 0.584 | 0.835 | 220.7 |
| Gemini 3.5 Flash, free-form | 66/100 (0.660) [0.563, 0.745] | 67/100 (0.670) | 99/100 (0.990) | 0.696 | 0.775 | 60.2 |
| Qwen2.5-7B, free-form 4-bit | 25/100 (0.250) [0.175, 0.343] | 53/100 (0.530) | 42/100 (0.420) | 0.530 | 0.690 | 45.4 |

## Registered paired legacy strict-pass test

| Comparison | ComplianceGPT only | Gemini only | Both pass | Neither pass | Exact two-sided McNemar p |
|---|---:|---:|---:|---:|---:|
| ComplianceGPT vs Gemini 3.5 Flash | 11 | 12 | 54 | 23 | 1 |

On these 100 paired rows, ComplianceGPT and Gemini 3.5 Flash are not statistically distinguishable on strict pass. The point estimate is not used as evidence of direction.

## Coverage-complete rejections

| System | Coverage-complete | Strict pass within coverage | Lost | Realization loss [95% CI] |
|---|---:|---:|---:|---:|
| ComplianceGPT, 4-bit selector | 65 | 65 | 0 | 0/65 (0.000) [0.000, 0.056] |
| Gemini 3.5 Flash, free-form | 67 | 66 | 1 | 1/67 (0.015) [0.003, 0.080] |
| Qwen2.5-7B, free-form 4-bit | 53 | 25 | 28 | 28/53 (0.528) [0.397, 0.656] |

Two-sided Fisher exact p for ComplianceGPT versus Gemini realization loss: `1`.

ComplianceGPT's observed zero realization loss is predicted by construction; it confirms that the implementation matches the citation-contract specification on the coverage-complete rows.

## ODP status operating point

| System | Sensitivity [95% CI] | Specificity [95% CI] | Status precision [95% CI] | Exact ODP set on positive rows |
|---|---:|---:|---:|---:|
| ComplianceGPT, 4-bit selector | 63/63 (1.000) [0.943, 1.000] | 17/37 (0.459) [0.310, 0.616] | 63/83 (0.759) [0.657, 0.838] | 55/63 (0.873) |
| Gemini 3.5 Flash, free-form | 56/63 (0.889) [0.788, 0.945] | 31/37 (0.838) [0.689, 0.923] | 56/62 (0.903) [0.805, 0.955] | 46/63 (0.730) |
| Qwen2.5-7B, free-form 4-bit | 0/63 (0.000) [0.000, 0.057] | 37/37 (1.000) [0.906, 1.000] | 0/0 (NA) | 21/63 (0.333) |

ODP sensitivity and specificity are reported together. These values use the current author labels and are not independently adjudicated.

## Interpretation boundary

This is a stronger-system baseline, not an isolation of weight precision or architecture. Questions, model-visible evidence, prompt/parser, ODP policy, and verifier are fixed, but the API model and serving runtime differ. The strict-pass comparison measures agreement with the implemented author-labeled rules; it does not establish legal sufficiency or auditor approval. The mechanistic claim concerns realization loss and runtime-verifiable guarantees, not universal accuracy superiority.
