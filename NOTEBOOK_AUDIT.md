# Notebook Audit

Audit date: 2026-09-29

This audit covers every `*.ipynb` file in the repository (13 notebooks). The
secondary micro-ablation is implemented by
`experiments/micro_ablations/run_micro_ablations.py`; there is no separate
MicroAblation notebook in this release.

## Checks performed

- parsed every notebook as valid notebook JSON and recorded its format,
  metadata keys, and cell count;
- searched notebook source and stored outputs for common credential patterns,
  including API keys, bearer tokens, Hugging Face tokens, passwords, and
  secrets;
- reviewed source-cell external URLs and Colab/GitHub authentication paths;
- checked for transient serialized Jupyter widget state;
- retained stored outputs because several notebooks are historical execution
  evidence for the reported experiments.

## Findings and actions

- No embedded credential value was detected. Two stored Hugging Face messages
  explicitly report that `HF_TOKEN` was absent; they do not contain a token.
- The matched-window rerun notebook instructs users to store a read-only GitHub
  token in Colab Secrets and never paste it into code. No token is stored in
  the notebook.
- The Batch 5A control-gate notebook clones the public repository at its
  registered runner commit and requires no GitHub or Hugging Face credential.
- The Batch 5B BF16 notebook mounts Google Drive in its first code cell, clones
  the public repository at its registered runner commit, and requires no
  GitHub or Hugging Face credential. It fetches the recorded RQ2 v3 source
  commit so the runner can verify and reconstruct that exact source tree.
- Colab-specific `/content/drive` paths and `drive.mount` calls remain because
  they are part of the recorded Colab workflows. They are environmental
  dependencies, not portable local paths.
- Transient top-level `widgets` state was removed from 10 notebooks. This
  removes UI serialization without changing cells, source code, execution
  counts, or stored outputs.
- The remaining notebook source-cell URLs are limited to the GitHub bootstrap
  paths in the matched-window rerun and Batch 5A notebooks. No unattributed
  block identified by this audit required removal. This repository audit does
  not, by itself, prove the authorship history of every code fragment.

## Audited notebooks

- `experiments/answerer_comparison/rq2_control_gate_width/Batch_5A_Control_Gate_Width_Sweep.ipynb`
- `experiments/answerer_comparison/rq2_bf16_baseline/Batch_5B_Rev4_BF16_Baseline.ipynb`
- `experiments/answerer_comparison/rq2_matched/RQ2_Matched_Window_Rerun.ipynb`
- `experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb`
- `experiments/retriever_ablation/performance_benchmark/Performance_Benchmark.ipynb`
- `src/3_canonical_examples/ComplianceGPT_test_clean.ipynb`
- `src/3_canonical_examples/qwen7b_naked_test_clean.ipynb`
- `src/compliancegpt/QUR_generator/QUR_Generator_UT.ipynb`
- `src/compliancegpt/pipeline/batch_run/rev4/Batch_Run_rev4.ipynb`
- `src/compliancegpt/pipeline/batch_run/rev5/Batch_Run.ipynb`
- `src/compliancegpt/pipeline/single_run/Acceptance_Tests.ipynb`
- `src/compliancegpt/pipeline/single_run/Single_Run_Demo.ipynb`
- `src/generative_answerer/Single_Run_Generative.ipynb`
