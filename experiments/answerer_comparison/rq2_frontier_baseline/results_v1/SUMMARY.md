# Batch 5C — Rev. 4 Frontier API Baseline

Result identity: `rq2_frontier_baseline_v1`

All systems use the same 36 questions, ordered evidence windows, ASK policy, and strict-pass standard. The frontier baseline inherits the frozen free-form prompt and parser without API tools or schema-constrained decoding.

| System | Strict pass | Full clause coverage | Runtime contract pass | Mean clause precision | Mean selected clauses | ODP sensitivity* |
|---|---:|---:|---:|---:|---:|---:|
| Frontier API baseline | 22/36 (0.611) | 28/36 (0.778) | 33/36 (0.917) | 0.615 | 3.06 | 18/19 (0.947) |
| Qwen generative baseline, 4-bit | 6/36 (0.167) | 18/36 (0.500) | 13/36 (0.361) | 0.488 | 3.33 | 0/19 (0.000) |
| ComplianceGPT, 4-bit | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 0.505 | 4.03 | 19/19 (1.000) |

## Paired strict-pass comparisons

| Comparison (left vs right) | Left only | Right only | Exact McNemar p |
|---|---:|---:|---:|
| Frontier vs Qwen 4-bit baseline | 17 | 1 | 0.0001449585 |
| Frontier vs 4-bit ComplianceGPT | 3 | 10 | 0.092285156 |
| ComplianceGPT vs Qwen 4-bit baseline | 24 | 1 | 1.5497208e-06 |

## Coverage-complete rejections

| System | Coverage-complete | Strict pass within coverage | Lost | Realization loss |
|---|---:|---:|---:|---:|
| Frontier API baseline | 28 | 22 | 6 | 6/28 (0.214) |
| Qwen generative baseline, 4-bit | 18 | 6 | 12 | 12/18 (0.667) |
| ComplianceGPT, 4-bit | 29 | 29 | 0 | 0/29 (0.000) |

Two-sided Fisher exact p for ComplianceGPT versus Gemini realization loss: `0.010381872`.

The coverage-complete subsets differ by system; this descriptive comparison does not replace the paired end-to-end test.

## Interpretation boundary

This is a stronger-system baseline, not an isolation of weight precision or architecture. Questions, model-visible evidence, prompt/parser, ODP policy, and verifier are fixed, but the API model and serving runtime differ. The requested model is a named stable Gemini model; response IDs, server-reported model versions, raw outputs, and token usage are retained. API sampling may not reproduce byte-identical outputs.

*ODP operating characteristics use author labels and are not independently adjudicated.*

## Strict-pass standard

Full gold governing-control and required-clause coverage; valid revision, source and verbatim evidence; gold-policy parameter/status consistency; exact, unique eligible sources in the matched evidence window; complete retained-parameter accounting; actual citation use in the answer body; complete question-relevant obligations; faithful claims and parameter meaning. Extra evidence is permitted when these conditions hold. Correct paraphrases can pass. Clarification value domains are not scored.

All conditions are mandatory. Semantic conditions use versioned source inspection or a sufficient complete-retention proof; judgments are not independently adjudicated. Uncertain cases receive no strict credit and remain in the denominator. The saved outputs are assessed retrospectively; paired tests are exploratory and unadjusted.

See [the complete standard](../../../../src/answerer_comparison/README.md) and [three detailed examples](../../STRICT_PASS_EXAMPLES.md).
