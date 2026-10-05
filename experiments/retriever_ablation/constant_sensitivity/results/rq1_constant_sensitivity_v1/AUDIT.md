# Primary RQ1 sensitivity: verified results

The seven registered conditions were completed on all 136 frozen questions. Each condition used the same captured lexical, dense and cross-encoder scores for a given question. Every captured probe and all 952 condition evaluations reproduced exactly in a separate replay. Statistical summaries were checked with separate calculations.

Local ranking changes occurred. In particular, reducing the blend weight moved one Revision 5 governing control from rank 10 to rank 11. This result supports reporting a limited sensitivity range; it does not support complete parameter invariance or a new superiority claim.

## Registration and verification

- Scientific execution commit: `a066453a317bba365db707b71745e49fee28811a`.
- Registered protocol SHA-256: `f094327ea5a63f2f25043c1c6f4f0f84bb5bc0f57326bcb374fa4a4c14a6123b`.
- Original uploaded archive SHA-256: `0106042b93d2fb15b754dfd70a983db85cfd1cf716f6cb68f22ac95b421be680`.
- Captured runtime: NVIDIA A100-SXM4-40GB, CUDA 12.4, Python 3.13.15, float32, deterministic algorithms enabled and TF32 disabled.
- Payload checks: all 144 payload SHA-256 records, the ZIP CRCs, 136 unique cache files and the complete 136 × 7 evaluation matrix.
- Upstream checks: all 15 recorded model files matched the immutable upstream revisions; native weight hashes were checked against the upstream LFS SHA-256 values.
- Corpus checks: 538 lexical score vectors and rankings were recomputed; 26900 returned dense texts were checked against the source record plus the historical control/title/kind header.
- 6800 complete cross-encoder pairs are retained. All ungated probes and 952 decisions replayed without another neural inference run.
- Per-query ranks, means, Wilson intervals, paired gains/losses, exact McNemar p-values and the registered 10,000-resample paired bootstrap intervals were separately recomputed. Numerical comparisons used an absolute tolerance of 1e-13; replayed report files were byte-identical.
- The artifact audit passed 126,681 checks, including verification of the binary archive parts and the exact reconstructed ZIP. The audit covers artifact consistency and computations; it is not independent expert adjudication of the labels.
- The two failed optional-dependency loading attempts remain in the original archive. No registered question or unfavorable condition was excluded.

See [audit.json](audit.json) for category counts and limits, and [model_verification.json](model_verification.json) for the immutable source URLs and file hashes.

## Registered conditions and endpoints

Blend α = 0.65 was tested at 0.52 and 0.78; fixed adoption margin 0.15 at 0.12 and 0.18; and skip margin 0.10 at 0.08 and 0.12. Each change was made separately. Other settings, question text, labels and rewrite files remained fixed. These are three selected retrieval decision constants; the study does not establish that they are empirically the three most influential constants in the entire system.

| Condition | Rev. 4 Success@1 | Rev. 5 Success@1 | Rev. 5 Success@10 | Rev. 5 MRR@10 | Rev. 5 nDCG@10 |
|---|---:|---:|---:|---:|---:|
| baseline | 32/36 | 90/100 | 100/100 | 0.9443 | 0.9584 |
| alpha_minus20 | 33/36 | 90/100 | 99/100 | 0.9433 | 0.9555 |
| alpha_plus20 | 31/36 | 88/100 | 100/100 | 0.9344 | 0.9511 |
| adoption_minus20 | 34/36 | 90/100 | 100/100 | 0.9443 | 0.9584 |
| adoption_plus20 | 32/36 | 90/100 | 100/100 | 0.9443 | 0.9584 |
| skip_minus20 | 32/36 | 90/100 | 100/100 | 0.9443 | 0.9584 |
| skip_plus20 | 32/36 | 90/100 | 100/100 | 0.9443 | 0.9584 |

Revision 5 Success@1 ranges from 88/100 to 90/100 and Success@10 from 99/100 to 100/100. Revision 4 Success@1 ranges from 31/36 to 34/36, with Success@5 and Success@10 at 36/36 for every condition. Revision 5 Success@5 is 99/100 for every condition. The complete per-revision and pooled endpoint tables are in [SUMMARY.md](SUMMARY.md); exact values, Wilson intervals and all paired comparisons are in [summary.json](summary.json).

For Revision 5 query 23, the reference control CM-4 moves from rank 10 under the fresh baseline to rank 11 at α = 0.52, and to rank 9 at α = 0.78. It remains in the 50-control order. This is a loss from the evaluated top-10 window, not from the full candidate pool. Increasing α to 0.78 also loses two Revision 5 top-1 reference matches. Adoption and skip changes leave the evaluated Revision 5 gold ranks unchanged, although control order and gate decisions can change.

## Paired comparisons against the fresh shared baseline

All p-values below are exact two-sided, exploratory and unadjusted. No Success@1/5/10 comparison reaches p < 0.05; the minimum p-value is 0.25. Every paired MRR/nDCG bootstrap interval contains zero. These are small-sample comparisons and do not establish equivalence or parameter invariance.

| Stratum | Condition | Success@1 losses / gains | McNemar p | ΔMRR@10 | Paired 95% interval | ΔnDCG@10 | Paired 95% interval |
|---|---|---:|---:|---:|---|---:|---|
| rev4 | alpha_minus20 | 0 / 1 | 1.0000 | 0.01389 | [0.00000, 0.04167] | 0.01025 | [0.00000, 0.03076] |
| rev4 | alpha_plus20 | 1 / 0 | 1.0000 | -0.01852 | [-0.05556, 0.00000] | -0.01389 | [-0.04167, 0.00000] |
| rev4 | adoption_minus20 | 0 / 2 | 0.5000 | 0.02778 | [0.00000, 0.06944] | 0.02050 | [0.00000, 0.05126] |
| rev4 | adoption_plus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |
| rev4 | skip_minus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |
| rev4 | skip_plus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |
| rev5 | alpha_minus20 | 0 / 0 | 1.0000 | -0.00100 | [-0.00300, 0.00000] | -0.00289 | [-0.00867, 0.00000] |
| rev5 | alpha_plus20 | 2 / 0 | 0.5000 | -0.00989 | [-0.02822, 0.00344] | -0.00726 | [-0.02095, 0.00274] |
| rev5 | adoption_minus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |
| rev5 | adoption_plus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |
| rev5 | skip_minus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |
| rev5 | skip_plus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |
| pooled | alpha_minus20 | 0 / 1 | 1.0000 | 0.00294 | [-0.00221, 0.01103] | 0.00059 | [-0.00638, 0.00814] |
| pooled | alpha_plus20 | 3 / 0 | 0.2500 | -0.01217 | [-0.02933, 0.00123] | -0.00902 | [-0.02180, 0.00096] |
| pooled | adoption_minus20 | 0 / 2 | 0.5000 | 0.00735 | [0.00000, 0.01838] | 0.00543 | [0.00000, 0.01357] |
| pooled | adoption_plus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |
| pooled | skip_minus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |
| pooled | skip_plus20 | 0 / 0 | 1.0000 | 0.00000 | [0.00000, 0.00000] | 0.00000 | [0.00000, 0.00000] |

## Gate tradeoffs

For the baseline, the guards prevent four top-1 reference errors and block five reference corrections relative to the ungated blended proposal. These categories use the unchanged author labels, not an independent correctness assessment. Score-margin guards can retain a reference-correct base rank and can also prevent a reference-correct rerank; they do not guarantee preservation of correct top-1 answers.

| Stratum | Gate | Queries | Prevented reference errors | Blocked reference corrections |
|---|---|---:|---:|---:|
| rev4 | skip | 2 | 0 | 0 |
| rev4 | adoption | 4 | 1 | 3 |
| rev5 | skip | 16 | 2 | 0 |
| rev5 | adoption | 3 | 1 | 2 |
| pooled | skip | 18 | 2 | 0 |
| pooled | adoption | 7 | 2 | 5 |

On Revision 5, changing the skip margin changes logical reranker calls from 79 to 91, compared with 84 at baseline, while leaving the measured gold ranks unchanged. The complete-candidate capture phase scores every question, including ones the logical skip gate would bypass. These counts are counterfactual gate decisions, not measured latency or cost savings.

## Historical baseline drift

The fresh baseline preserves the historical top-10 order in 65/136 questions, gold rank in 134/136 and gate/variant flags in 135/136. The two gold-rank differences are:

| Revision | Query ID | Historical rank | Fresh rank | Gate/variant flags unchanged |
|---|---|---:|---:|---|
| rev4 | 28 | 1 | 2 | no |
| rev5 | 12 | 2 | 3 | yes |

Historical immutable model revisions and a complete runtime record were not retained. The source of this drift is not established by this study. Comparisons among the seven sensitivity conditions use the fresh shared baseline; saved historical RQ1 tables remain unchanged. All historical order/rank/flag comparisons are retained in [historical_baseline_comparison.jsonl](historical_baseline_comparison.jsonl).

## Scope and writing obligations

- Report all seven conditions and the top-10 loss. Do not replace the historical headline configuration with whichever setting scores highest here.
- State that this is a one-factor local sensitivity study on the author-labeled benchmark. Interactions, other constants, other corpora, the ErrorBank and authentic-user questions were not evaluated in this matrix.
- Disclose the provenance and tuning history of every reported constant separately. This study does not recover a missing development-set history or remove optimistic bias from tuning on the evaluation benchmark.
- Keep artifact reproducibility separate from independent correctness. Independent expert adjudication remains a separate study; this audit does not provide it.
- Keep the fresh/historical baseline distinction explicit and describe the causal source of drift as unestablished.
- Describe logical gate counts as counterfactual decisions, not measured speed or cost savings.

## Reproduce the audit

The [archive_parts](archive_parts) directory contains two binary parts of the original uploaded ZIP and their manifest. The audit command verifies and assembles them into the exact original ZIP outside the checkout. It then checks payloads, replays the study, recomputes statistics and verifies model files against their immutable upstream sources. The ZIP and its payloads are preserved byte for byte.

Use a clean checkout, the scientific dependencies recorded in the requirements file, SciPy for the separate statistical checks, network access to the pinned Hugging Face sources, and a new output directory. Neural inference is not repeated.

```bash
PYTHONPATH=src:. python experiments/retriever_ablation/constant_sensitivity/audit_results.py \
  --repo . \
  --archive experiments/retriever_ablation/constant_sensitivity/results/rq1_constant_sensitivity_v1/archive_parts \
  --output-dir /tmp/rq1_constant_sensitivity_audit
```

The audit output includes the reconstructed original ZIP, an unchanged extracted original, a separate replay copy, `audit.json` and `model_verification.json`.
