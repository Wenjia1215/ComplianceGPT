# Batch 5B — Rev. 4 BF16 Generative Baseline

Result identity: `rq2_bf16_baseline_v1`

Only the free-form baseline's model-weight precision changes from 4-bit to BF16. The model revision, prompt, decoding, questions, ordered evidence windows, ODP policy, and verifier are held fixed.

| System | Strict pass | Full clause coverage | Runtime contract pass | Mean clause precision | Mean selected clauses | ODP sensitivity* |
|---|---:|---:|---:|---:|---:|---:|
| Generative baseline, BF16 | 8/36 (0.222) | 20/36 (0.556) | 14/36 (0.389) | 0.575 | 2.89 | 0/19 (0.000) |
| Generative baseline, 4-bit (frozen) | 8/36 (0.222) | 18/36 (0.500) | 13/36 (0.361) | 0.488 | 3.33 | 0/19 (0.000) |
| ComplianceGPT, 4-bit (frozen) | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 0.505 | 4.03 | 19/19 (1.000) |

## Paired strict-pass comparisons

| Comparison (left vs right) | Left only | Right only | Exact McNemar p |
|---|---:|---:|---:|
| BF16 baseline vs 4-bit baseline | 2 | 2 | 1 |
| BF16 baseline vs 4-bit ComplianceGPT | 0 | 21 | 9.5367432e-07 |

## Interpretation boundary

This study isolates model-weight precision within the same Qwen2.5-7B free-form baseline. It is neither a frontier-model comparison nor a retraining study. A BF16 change estimates quantization sensitivity on these 36 fixed Rev. 4 rows.

*ODP operating characteristics use author labels and remain provisional until blinded independent annotation is returned.*
