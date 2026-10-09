# Batch 5C — Rev. 4 Frontier API Baseline

Result identity: `rq2_frontier_baseline_v1`

Current [Answer-content strict pass](../../answer_content_strict_pass/README.md): ComplianceGPT **29/36 (80.6%)**, Gemini **22/36 (61.1%)**, Qwen **4-bit** baseline **6/36 (16.7%)**. See the [complete re-evaluation](../../answer_content_strict_pass/results_v1/SUMMARY.md). The archived tables below retain the original legacy strict-pass endpoint; the BF16 baseline is outside this re-evaluation.

All systems use the same 36 questions, ordered evidence windows, ASK policy, and offline verifier. The frontier baseline inherits the frozen free-form prompt and parser without API tools or schema-constrained decoding.

| System | Legacy strict pass | Full clause coverage | Runtime contract pass | Mean clause precision | Mean selected clauses | ODP sensitivity* |
|---|---:|---:|---:|---:|---:|---:|
| Frontier API baseline | 24/36 (0.667) | 28/36 (0.778) | 33/36 (0.917) | 0.615 | 3.06 | 18/19 (0.947) |
| Qwen generative baseline, BF16 | 8/36 (0.222) | 20/36 (0.556) | 14/36 (0.389) | 0.575 | 2.89 | 0/19 (0.000) |
| Qwen generative baseline, 4-bit | 8/36 (0.222) | 18/36 (0.500) | 13/36 (0.361) | 0.488 | 3.33 | 0/19 (0.000) |
| ComplianceGPT, 4-bit | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 0.505 | 4.03 | 19/19 (1.000) |

## Paired legacy strict-pass comparisons

| Comparison (left vs right) | Left only | Right only | Exact McNemar p |
|---|---:|---:|---:|
| Frontier vs Qwen BF16 baseline | 18 | 2 | 0.00040245056 |
| Frontier vs Qwen 4-bit baseline | 18 | 2 | 0.00040245056 |
| Frontier vs 4-bit ComplianceGPT | 3 | 8 | 0.2265625 |

## Interpretation boundary

This is a stronger-system baseline, not an isolation of weight precision or architecture. Questions, model-visible evidence, prompt/parser, ODP policy, and verifier are fixed, but the API model and serving runtime differ. The requested model is a named stable Gemini model; response IDs, server-reported model versions, raw outputs, and token usage are retained. API sampling may not reproduce byte-identical outputs.

*ODP operating characteristics use author labels and remain provisional until blinded independent annotation is returned.*
