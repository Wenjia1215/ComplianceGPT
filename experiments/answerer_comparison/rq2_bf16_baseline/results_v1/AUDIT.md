# Independent Batch 5B audit

Audit date: 2026-09-29

## Integrity checks

- The supplied ZIP passed CRC testing and contained 16 safe relative paths,
  with no absolute path, parent traversal, or backslash path.
- All 15 files registered by `manifests/outputs.json` matched their SHA-256
  values. The canonical file-map hash also matched
  `e265388b72d758b0d05e2bf55899f9b45622b51f497bdf17d8465d3ded97ce3b`.
- The registered gold CSV independently matched SHA-256
  `80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2`.
- Each of the BF16 baseline, frozen 4-bit baseline, and frozen 4-bit
  ComplianceGPT files contained the same 36 unique query IDs.
- Context hashes, order-sensitive evidence-window hashes, model identity, and
  model/tokenizer revisions matched for every paired row.
- The 36 stored contexts matched the BF16 CSV context and evidence-window
  hashes.
- Metrics below were recomputed from the CSV rows, contract JSON, verifier
  metrics, and registered gold rows without accepting `summary.json` as the
  source of truth. Every reconstructed aggregate matched `summary.json`.

## Runtime checks

- GPU: NVIDIA A100-SXM4-40GB, compute capability 8.0, native BF16 supported.
- Model/tokenizer: `Qwen/Qwen2.5-7B-Instruct` at immutable revision
  `a09a35458c702b33eeacc393d103063234e8bc28`.
- Floating parameters: 339 tensors and 7,615,616,512 parameters, all reported
  as `torch.bfloat16`.
- Quantization flags: all false; no HF quantizer or quantization configuration.
- Frozen evidence source archive:
  `56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328`.

## Independently reconstructed metrics

| Metric | BF16 baseline | 4-bit baseline | 4-bit ComplianceGPT |
|---|---:|---:|---:|
| Strict verifier pass | 8/36 (0.222) | 8/36 (0.222) | 29/36 (0.806) |
| Full gold-clause coverage | 20/36 (0.556) | 18/36 (0.500) | 29/36 (0.806) |
| Runtime contract pass | 14/36 (0.389) | 13/36 (0.361) | 36/36 (1.000) |
| Mean gold-clause recall | 0.664 | 0.596 | 0.886 |
| Mean gold-clause precision | 0.575 | 0.488 | 0.505 |
| Mean selected clauses | 2.89 | 3.33 | 4.03 |
| Author-label ODP sensitivity | 0/19 | 0/19 | 19/19 |

## Paired analysis

For BF16 versus the 4-bit baseline, six rows passed under both precisions and
26 failed under both. BF16 gained strict pass on query IDs 24 and 29, while it
lost strict pass on IDs 22 and 32. The discordance table is therefore 2 versus
2, and the exact two-sided McNemar value is `1.0`.

Full clause coverage improved on IDs 3, 5, 20, 24, 27, 29, and 36, but regressed
on IDs 4, 8, 12, 28, and 32. Runtime contract validity improved on IDs 24 and
28 and regressed on ID 22. These mixed row-level changes explain why the small
descriptive gains do not translate into a strict-pass improvement.

For BF16 baseline versus frozen ComplianceGPT, eight rows passed under both,
seven failed under both, zero passed only under BF16, and 21 passed only under
ComplianceGPT. The exact two-sided McNemar value is
`9.5367431640625e-07`.

## Interpretation

True BF16 slightly increased full clause coverage, runtime contract pass, and
mean clause precision relative to the same free-form model in 4-bit. It did
not change aggregate strict pass and did not recover any author-label ODP
sensitivity: all 36 BF16 outputs still used status `OK`, including the 19
author-labeled ODP rows. The dominant gap from ComplianceGPT therefore remains
answer-construction and contract/ODP behavior, not merely model-weight
precision.

This 36-row fixed-context study estimates quantization sensitivity for one
model and one prompt. It is not a frontier-model comparison, and the ODP
operating characteristics remain provisional pending blinded annotation.
