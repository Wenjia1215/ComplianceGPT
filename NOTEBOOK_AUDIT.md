# Notebook Audit

Audit updated: 2026-10-03
Scope: every tracked `*.ipynb` file in the repository (15 notebooks), with a
manual source review of the four primary surfaces named in the dissertation
feedback.

## Advisor-named primary surfaces

| Requested surface | Repository status | Review result |
|---|---|---|
| `AblationStudy_S1_7.ipynb` | Present | Source cells reviewed; no external code block, copied-code marker, license header, or unattributed source URL identified. |
| `Single_Run_Demo.ipynb` | Present | Source cells reviewed; the notebook calls repository modules and contains no third-party code block requiring attribution. |
| `MicroAblation_S4b_S7a.ipynb` | No separate notebook in this release | The corresponding implementation is `experiments/micro_ablations/run_micro_ablations.py`; that runner was reviewed and imports the canonical repository retrieval implementation. |
| `QUR_Generator_UT.ipynb` | Present | Source cells reviewed; no external code block, copied-code marker, license header, or unattributed source URL identified. |

The absence of a separate micro-ablation notebook is recorded explicitly so
that the repository does not imply that a missing file was audited.

## Checks performed

- parsed all 15 notebooks as valid notebook JSON and recorded notebook format,
  cell counts, metadata keys, stored outputs, and error outputs;
- manually reviewed the source cells of the advisor-named entry points and the
  scripted micro-ablation replacement;
- searched all notebook source and stored outputs for common credential
  patterns, including GitHub, Hugging Face, OpenAI, Google, AWS, bearer-token,
  and private-key forms;
- reviewed source-cell URLs, Colab/Drive dependencies, and GitHub
  authentication paths;
- removed transient Colab/Jupyter UI serialization while preserving scientific
  content;
- retained stored outputs because several notebooks are historical execution
  evidence for the reported experiments.

## Findings and actions

- All 15 notebooks parse successfully; none contains a stored error output.
- No embedded credential value was detected. Stored messages that say a token
  is absent are status text, not credentials.
- No source block requiring third-party attribution was identified. This is a
  repository-content review, not independent proof of the authorship history of
  every line.
- The newer Batch 5C Revision 4 and Batch 5D Revision 5 frontier-baseline
  notebooks are now included in the audit. Their API-key instructions use
  Colab Secrets, and no key is stored in either notebook.
- Removed top-level `metadata.colab` and per-cell `metadata.colab`, duplicate
  `metadata.id`, and `metadata.outputId` fields from every notebook. Standard
  cell IDs, source cells, stored outputs, and execution counts were preserved.
  A semantic before/after hash check confirmed that sources, outputs, and
  execution counts were unchanged for all 15 notebooks.
- Colab-specific `/content/drive` paths and `drive.mount` calls remain because
  they are executable workflow dependencies rather than serialized UI
  metadata.
- The root `.gitignore` now excludes local environments, secret files,
  notebook checkpoints, Python/test caches, coverage/build products, editor
  state, and transient logs. It intentionally does not ignore experiment
  archives, CSV/JSON results, notebooks, or other frozen research artifacts.

## Audited notebooks

- `experiments/answerer_comparison/rq2_bf16_baseline/Batch_5B_Rev4_BF16_Baseline.ipynb`
- `experiments/answerer_comparison/rq2_control_gate_width/Batch_5A_Control_Gate_Width_Sweep.ipynb`
- `experiments/answerer_comparison/rq2_frontier_baseline/Batch_5C_Rev4_Frontier_API_Baseline.ipynb`
- `experiments/answerer_comparison/rq2_frontier_baseline_rev5/Batch_5D_Rev5_Frontier_API_Baseline.ipynb`
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
