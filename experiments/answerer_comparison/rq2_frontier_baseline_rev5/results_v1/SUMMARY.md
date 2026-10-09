# Batch 5D — Revision 5 Frontier API Baseline

Result identity: `rq2_frontier_baseline_rev5_v1`

All systems use the same 100 frozen Revision 5 questions, ordered evidence windows, ASK policy, and strict-pass standard.

## Primary and supporting outcomes

| System | Strict pass [95% CI] | Full clause coverage | Runtime pass | Clause precision | Clause recall | Mean words |
|---|---:|---:|---:|---:|---:|---:|
| ComplianceGPT, 4-bit selector | 65/100 (0.650) [0.553, 0.736] | 65/100 (0.650) | 100/100 (1.000) | 0.584 | 0.835 | 220.7 |
| Gemini 3.5 Flash, free-form | 56/100 (0.560) [0.462, 0.653] | 67/100 (0.670) | 99/100 (0.990) | 0.696 | 0.775 | 60.2 |
| Qwen2.5-7B, free-form 4-bit | 21/100 (0.210) [0.142, 0.300] | 53/100 (0.530) | 42/100 (0.420) | 0.530 | 0.690 | 45.4 |

## Paired strict-pass test

| Comparison | ComplianceGPT only | Gemini only | Both pass | Neither pass | Exact two-sided McNemar p |
|---|---:|---:|---:|---:|---:|
| ComplianceGPT vs Gemini 3.5 Flash | 18 | 9 | 47 | 26 | 0.12207812 |

On these 100 paired rows, ComplianceGPT and Gemini 3.5 Flash are not statistically distinguishable on strict pass. The point estimate is not used as evidence of direction.

## Coverage-complete rejections

| System | Coverage-complete | Strict pass within coverage | Lost | Realization loss [95% CI] |
|---|---:|---:|---:|---:|
| ComplianceGPT, 4-bit selector | 65 | 65 | 0 | 0/65 (0.000) [0.000, 0.056] |
| Gemini 3.5 Flash, free-form | 67 | 56 | 11 | 11/67 (0.164) [0.094, 0.271] |
| Qwen2.5-7B, free-form 4-bit | 53 | 21 | 32 | 32/53 (0.604) [0.469, 0.724] |

Two-sided Fisher exact p for ComplianceGPT versus Gemini realization loss: `0.00062991132`.

The coverage-complete subsets differ by system; this descriptive comparison does not replace the paired end-to-end test.

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

## Strict-pass standard

Full gold governing-control and required-clause coverage; valid revision, source and verbatim evidence; gold-policy parameter/status consistency; exact, unique eligible sources in the matched evidence window; complete retained-parameter accounting; actual citation use in the answer body; complete question-relevant obligations; faithful claims and parameter meaning. Extra evidence is permitted when these conditions hold. Correct paraphrases can pass. Clarification value domains are not scored.

All conditions are mandatory. Semantic conditions use versioned source inspection or a sufficient complete-retention proof; judgments are not independently adjudicated. Uncertain cases receive no strict credit and remain in the denominator. The saved outputs are assessed retrospectively; paired tests are exploratory and unadjusted.

See [the complete standard](../../../../src/answerer_comparison/README.md) and [three detailed examples](../../STRICT_PASS_EXAMPLES.md).
