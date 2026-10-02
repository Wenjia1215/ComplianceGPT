# Batch 5B — Rev. 4 BF16 Generative Baseline

[Open the Batch 5B notebook in Colab](https://colab.research.google.com/github/Wenjia1215/ComplianceGPT/blob/main/experiments/answerer_comparison/rq2_bf16_baseline/Batch_5B_Rev4_BF16_Baseline.ipynb)

This registered follow-on study addresses the RQ2 quantization-asymmetry concern. It reruns the 36-row Revision 4 free-form generative baseline with `Qwen/Qwen2.5-7B-Instruct` loaded in true BF16 instead of 4-bit. The model revision, system and user prompts, deterministic decoding, parse retries, questions, ordered evidence windows, `ASK` ODP policy, and offline verifier remain fixed.

The result identity is `rq2_bf16_baseline_v1`. It never edits or replaces the frozen RQ2 v3 result family. The frozen 4-bit generative baseline and frozen 4-bit ComplianceGPT output are copied from the validated v3 archive and used only as unchanged paired references.

The completed, independently checked result is recorded under
[`results_v1/`](results_v1/). The supplied Google Drive export has SHA-256
`4039e67453d46b12ad214a3759d16e5a4c9f1028353dd6e253fca06f3b57a561`;
all 15 registered payload hashes and the output-manifest identity were
revalidated. The notebook now retains the successful A100 execution output.

## Registered boundary

- Framework: NIST SP 800-53 Revision 4 only.
- Questions: the same 36 rows used in RQ2 v3.
- Model: `Qwen/Qwen2.5-7B-Instruct` at revision `a09a35458c702b33eeacc393d103063234e8bc28`.
- Changed factor: generative-baseline weight precision, from 4-bit to `torch.bfloat16`.
- Frozen prompt SHA-256: `91ba0d840befd5517fbec7595f640333bcb8df8e63301e80552dad841744fdef`.
- Retrieval: none. The runner consumes the immutable ordered Rev. 4 contexts in RQ2 v3.
- Hardware: a CUDA GPU with native BF16 and enough memory. A100 is preferred; L4 is supported. T4 is intentionally rejected because it has no native BF16 execution path.

The runner extracts the exact RQ2 v3 source tree from commit `be862bcadfa61b474d795303e01ce9394909fdcc` and verifies every runtime-relevant source hash recorded by that experiment. This prevents later pipeline changes from becoming an unregistered second factor.

## Deterministic preparation without a GPU

From the repository root:

```bash
python experiments/answerer_comparison/rq2_bf16_baseline/run_bf16_baseline.py \
  --output-dir /tmp/rq2_bf16_baseline_v1 \
  --prepare-only
```

This verifies the frozen archive and source commit, extracts the 36 contexts and both reference outputs, validates every context and order-sensitive evidence-window hash, and writes `PREPARED_CONTEXTS.md`. It performs no model inference and is not a completed Batch 5B result.

## Full GPU run

Install the recorded dependencies, then use a persistent output directory:

```bash
python -m pip install -r experiments/answerer_comparison/rq2_matched/requirements-colab.txt
python experiments/answerer_comparison/rq2_bf16_baseline/run_bf16_baseline.py \
  --output-dir /content/drive/MyDrive/rq2_bf16_baseline_v1
```

The runner verifies that every floating model parameter is `torch.bfloat16`, that no 4-bit/8-bit quantizer is attached, and that the model and tokenizer resolve to the registered commit. It checkpoints after every question. Re-running the same command validates completed rows and resumes at the next unfinished question. A changed source, context, prompt, generation setting, package version, model identity, precision, or GPU family is rejected once model rows exist.

The completed directory contains:

- `contracts/rev4_generative_baseline_bf16.csv` — 36 checkpointed BF16 outputs;
- `references/` — unchanged frozen 4-bit outputs and v3 provenance;
- `manifests/` — source, runtime, generation, run, and output hashes;
- `summary.json` and `SUMMARY.md` — descriptive metrics and paired exact McNemar tests; and
- a sibling `rq2_bf16_baseline_v1.zip` archive.

## Metrics and interpretation

The summary reports strict verifier pass, full gold-clause coverage, clause recall and precision, answer and citation burden, runtime contract validity, and author-label ODP operating characteristics. It provides paired exact McNemar comparisons for BF16 versus the frozen 4-bit baseline and for BF16 baseline versus frozen 4-bit ComplianceGPT.

This experiment estimates quantization sensitivity within one 7B model on 36
fixed Rev. 4 rows. It is not a frontier-model baseline, a retraining result, or
evidence about other models. ODP sensitivity, specificity, and precision use
current author labels and have not been independently adjudicated.

## Recorded finding

True BF16 left strict pass unchanged at 8/36 versus 8/36 for the frozen 4-bit
baseline. Two rows improved and two regressed (`p = 1.0`, paired exact
two-sided McNemar). BF16 modestly increased full clause coverage from 18/36 to
20/36 and runtime contract pass from 13/36 to 14/36, but both precision modes
had 0/19 author-label ODP sensitivity.

Frozen 4-bit ComplianceGPT passed 29/36. Against BF16 it had 21 exclusive
passes, while BF16 had none (`p = 9.5367432e-07`). The principal RQ2 gap is
therefore not explained by the baseline's original 4-bit quantization. See
[`results_v1/AUDIT.md`](results_v1/AUDIT.md) for integrity checks and the
independent reconstruction.
