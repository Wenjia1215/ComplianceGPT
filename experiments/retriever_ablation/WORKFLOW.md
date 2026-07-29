# Workflow: ComplianceGPT Retrieval Ablation

This document gives the step-by-step reproduction workflow for the reported S1–S7 retrieval ablation study.

---

## 1. Bootstrap: Generate the Raw ErrorBank

**Action:** Run the ErrorBank bootstrap section of:

```text
experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb
```

**What it does:** Runs the BM25 baseline to identify failed queries for diagnostic analysis.

**Output:**

```text
data/error_bank/error_bank_v1.csv
```

---

## 2. Label: Human Annotation Loop

**Action:** Open `error_bank_v1.csv` and manually populate the `failure_category` column.

**Reference:**

```text
data/error_bank/Labeling_Rationale.md
```

**Output:** A labeled ErrorBank file with fixed diagnostic categories.

---

## 3. Rewrite: QUR Generation

**Action:** Run:

```text
src/compliancegpt/QUR_generator/QUR_Generator_UT.ipynb
```

**Input:**

- `nist_sp800-53_rev5_gold-set_100q.csv`
- `nist_sp800-53_rev4_gold-set_36q.csv`
- labeled `error_bank_v1.csv`

**Output:**

- `data/qur_outputs/qur_rewrites_error_bank.csv`
- `data/qur_outputs/qur_rewrites_rev4.csv`
- `data/qur_outputs/qur_rewrites_rev5.csv`

---

## 4. Experiment: Run S1–S7

**Action:** Run the recorded S1–S7 ablation notebook:

```text
experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb
```

**Input:** Uses the CCS, gold sets, ErrorBank, and QUR rewrite outputs from Step 3.

**Output:** Per-system result files under:

```text
experiments/retriever_ablation/ablation_outputs/
```

---

## 5. Performance Benchmark: Latency and Gate Audit

**Action:** Run the performance benchmark notebook that imports the checked S7 retriever source:

```text
src/compliancegpt/retriever/retriever_s7.py
```

**Purpose:** Measure retrieval-only latency and reranker-call behavior for one
diagnostic workload. The stored benchmark uses a 0.01 skip margin, while the
recorded RQ1 notebook and current checked source use 0.10; its latency is not an
exact measurement of either reported S7 state.

**Systems of interest:**

- `S7_gated`: benchmark configuration with the skip gate enabled.
- `S7_worst_always_rerank`: same ranking/rerank pipeline but skip gate disabled.

**Output:** Benchmark CSV/MD artifacts, including latency tables, per-run data, and reranker audit fields such as `reranker_called` and `rerank_applied`.

---

## 6. Analyze: Generate ErrorBank Pivot Table

**Action:** Run:

```bash
python experiments/retriever_ablation/error_analysis/run_error_mode_analysis.py
```

The script joins ErrorBank labels to recorded retrieval rows by
`(version, question_id)` and validates the question and gold control before
writing the category reports.

**Input:**

- `data/error_bank/error_bank_v1.csv`
- `system_1_bm25/S1_bm25_error_bank_rev4_results.csv`
- `system_1_bm25/S1_bm25_error_bank_rev5_results.csv`
- `system_2_dense/S2_dense_error_bank_rev4_results.csv`
- `system_2_dense/S2_dense_error_bank_rev5_results.csv`
- `system_5_hybrid_rrf/S5_hybrid_rrf_error_bank_rev4_results.csv`
- `system_5_hybrid_rrf/S5_hybrid_rrf_error_bank_rev5_results.csv`
- `system_6_hybrid_rerank/S6_hybrid_rerank_error_bank_rev4_results.csv`
- `system_6_hybrid_rerank/S6_hybrid_rerank_error_bank_rev5_results.csv`
- `system_7_compliance_gpt/S7_compliance_gpt_error_bank_rev4_results.csv`
- `system_7_compliance_gpt/S7_compliance_gpt_error_bank_rev5_results.csv`

**Output:**

- `pivot_table.csv`
- `pivot_table.md`
- `merged_results_data.csv`

---

## Notes

Re-run this workflow after changes to S7 gating, control-ID normalization, CCS version, or QUR rewrite files.
