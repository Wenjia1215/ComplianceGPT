# Notebook audit

Audit date: **2026-10-10**

Audited source commit: `3427dca90921fad88afa3fc179cb6980fb1d1a42`

This read-only audit covers all **20 tracked notebooks**. It replaces the
2026-09-29 inventory of 13 notebooks. Notebook paths, bytes, cells, execution
counts, metadata, and outputs remain unchanged. No notebook was executed.

The [machine-readable inventory](docs/NOTEBOOK_INVENTORY.json) records full-file
SHA-256 values, cell-source hashes, notebook formats, output types, credential
reference names, source-URL counts, and environmental dependencies. See
[Environments and execution modes](docs/ENVIRONMENTS.md) before running a notebook.

## Checks and findings

- Parsed every notebook as JSON and checked its core cell, metadata, output,
  and execution-count fields. This does not claim full notebook-schema validation.
- Read all 227 cells, including 177 code cells, and inspected stored outputs.
  Of the code cells, 141 have execution counts; these counts alone do not prove
  a complete experiment.
- Scanned source and stored outputs for common Hugging Face, GitHub, Google,
  service-API, and AWS credential patterns, plus literal key, token, password,
  and secret assignments. No credential value candidate was detected under
  these checks. Pattern scans do not establish exhaustive secret detection.
- Recorded Colab Secrets, interactive credential input, repository bootstrap,
  and Drive dependencies. `GEMINI_API_KEY`, `GITHUB_TOKEN`, `userdata.get`, and
  `getpass` are references or input mechanisms, not stored credential values.
- Found no top-level serialized widget metadata. No widget state was removed
  in this audit.
- Found one stored `RuntimeError`, in the preserved natural-question authority-
  check attempt. Its [prior-attempt record](experiments/external_validity/natural_questions_v2/prior_attempt/README.md)
  explains the failure; the completed run has a separate execution notebook.
  Retaining this error preserves the recorded attempt.
- Retained all stored outputs, including successful BF16, Gemini, natural-
  question, and constant-sensitivity execution records. No model or API call
  was made for this audit.

## Complete inventory

“Code cells with counts” means that the notebook stores a non-null execution
count for that many code cells. A launcher can contain executed setup cells
without recording a completed experiment. Confirm completion against its
result manifest and execution record.

| Notebook | Role | Cells | Code cells with counts | Stored errors |
|---|---|---:|---:|---:|
| [experiments/answerer_comparison/rq2_bf16_baseline/Batch_5B_Rev4_BF16_Baseline.ipynb](experiments/answerer_comparison/rq2_bf16_baseline/Batch_5B_Rev4_BF16_Baseline.ipynb) | Completed BF16 execution record | 10 | 9 | 0 |
| [experiments/answerer_comparison/rq2_control_gate_width/Batch_5A_Control_Gate_Width_Sweep.ipynb](experiments/answerer_comparison/rq2_control_gate_width/Batch_5A_Control_Gate_Width_Sweep.ipynb) | Registered control-gate launch notebook | 10 | 0 | 0 |
| [experiments/answerer_comparison/rq2_frontier_baseline/Batch_5C_Rev4_Frontier_API_Baseline.ipynb](experiments/answerer_comparison/rq2_frontier_baseline/Batch_5C_Rev4_Frontier_API_Baseline.ipynb) | Completed Revision 4 API execution record | 14 | 9 | 0 |
| [experiments/answerer_comparison/rq2_frontier_baseline_rev5/Batch_5D_Rev5_Frontier_API_Baseline.ipynb](experiments/answerer_comparison/rq2_frontier_baseline_rev5/Batch_5D_Rev5_Frontier_API_Baseline.ipynb) | Completed Revision 5 API execution record | 13 | 9 | 0 |
| [experiments/answerer_comparison/rq2_matched/RQ2_Matched_Window_Rerun.ipynb](experiments/answerer_comparison/rq2_matched/RQ2_Matched_Window_Rerun.ipynb) | Matched-window launch notebook | 7 | 6 | 0 |
| [experiments/external_validity/natural_questions_v2/Batch_Natural_Questions_v2.ipynb](experiments/external_validity/natural_questions_v2/Batch_Natural_Questions_v2.ipynb) | Repaired natural-question launch notebook | 10 | 0 | 0 |
| [experiments/external_validity/natural_questions_v2/prior_attempt/Batch_Natural_Questions_v2_authority_check_failed.ipynb](experiments/external_validity/natural_questions_v2/prior_attempt/Batch_Natural_Questions_v2_authority_check_failed.ipynb) | Preserved failed authority-check attempt | 10 | 5 | 1 |
| [experiments/external_validity/natural_questions_v2/results_v1/Batch_Natural_Questions_v2_executed.ipynb](experiments/external_validity/natural_questions_v2/results_v1/Batch_Natural_Questions_v2_executed.ipynb) | Completed natural-question execution record | 10 | 7 | 0 |
| [experiments/retriever_ablation/constant_sensitivity/Batch_RQ1_Constant_Sensitivity.ipynb](experiments/retriever_ablation/constant_sensitivity/Batch_RQ1_Constant_Sensitivity.ipynb) | Registered constant-sensitivity launch notebook | 10 | 0 | 0 |
| [experiments/retriever_ablation/constant_sensitivity/results/rq1_constant_sensitivity_v1/Batch_RQ1_Constant_Sensitivity_Executed.ipynb](experiments/retriever_ablation/constant_sensitivity/results/rq1_constant_sensitivity_v1/Batch_RQ1_Constant_Sensitivity_Executed.ipynb) | Completed constant-sensitivity execution record | 10 | 7 | 0 |
| [experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb](experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb) | Historical primary retrieval evaluation | 15 | 0 | 0 |
| [experiments/retriever_ablation/performance_benchmark/Performance_Benchmark.ipynb](experiments/retriever_ablation/performance_benchmark/Performance_Benchmark.ipynb) | Historical performance diagnostic | 8 | 7 | 0 |
| [src/3_canonical_examples/ComplianceGPT_test_clean.ipynb](src/3_canonical_examples/ComplianceGPT_test_clean.ipynb) | Canonical ComplianceGPT example | 5 | 4 | 0 |
| [src/3_canonical_examples/qwen7b_naked_test_clean.ipynb](src/3_canonical_examples/qwen7b_naked_test_clean.ipynb) | Canonical free-form example | 5 | 4 | 0 |
| [src/compliancegpt/QUR_generator/QUR_Generator_UT.ipynb](src/compliancegpt/QUR_generator/QUR_Generator_UT.ipynb) | Query-rewrite workflow and unit checks | 12 | 9 | 0 |
| [src/compliancegpt/pipeline/batch_run/rev4/Batch_Run_rev4.ipynb](src/compliancegpt/pipeline/batch_run/rev4/Batch_Run_rev4.ipynb) | Historical Revision 4 batch workflow | 17 | 14 | 0 |
| [src/compliancegpt/pipeline/batch_run/rev5/Batch_Run.ipynb](src/compliancegpt/pipeline/batch_run/rev5/Batch_Run.ipynb) | Historical Revision 5 batch workflow | 18 | 15 | 0 |
| [src/compliancegpt/pipeline/single_run/Acceptance_Tests.ipynb](src/compliancegpt/pipeline/single_run/Acceptance_Tests.ipynb) | Single-run acceptance notebook | 23 | 20 | 0 |
| [src/compliancegpt/pipeline/single_run/Single_Run_Demo.ipynb](src/compliancegpt/pipeline/single_run/Single_Run_Demo.ipynb) | Single-query demonstration | 10 | 8 | 0 |
| [src/generative_answerer/Single_Run_Generative.ipynb](src/generative_answerer/Single_Run_Generative.ipynb) | Single-query free-form demonstration | 10 | 8 | 0 |


## Execution boundary

Colab imports, Drive mounts, and `/content/drive` paths belong to their recorded
environments. Historical runners also enforce registered source and input
hashes. Use the execution commit in the result manifest when reproducing a
formal run, and write new outputs outside the repository.

The secondary micro-ablation uses
[`run_micro_ablations.py`](experiments/micro_ablations/run_micro_ablations.py);
there is no separate micro-ablation notebook in this snapshot.
