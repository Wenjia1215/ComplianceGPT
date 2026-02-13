
# Workflow: ComplianceGPT Retrieval Ablation

Step-by-step reproduction workflow of retrieval ablation study.

### **1. Bootstrap (Generate Raw Error Bank)**

* **Action:** Run **Section 1 ONLY** of `experiments/retriever_ablation/notebook/AblationStudy_S1_8.ipynb`.
* **What it does:** Runs S1 (BM25) to identify failed queries (Rank != 1).
* **Output:** `data/error_bank_v1/error_bank_v1.csv` (Raw).

### **2. Label (Human Loop)**

* **Action:** Open `error_bank_v1.csv` and manually populate the `failure_category` column.
* **Reference:** `Error_Bank_Labeling_Rationale.md`.
* **Output:** `data/error_bank_v1/error_bank_v1.csv` (Labeled).

### **3. Rewrite (QUR Generation)**

* **Action:** Run `src/compliancegpt/QUR_generator/QUR_Generator_UT.ipynb`.
* **Input:** `nist_sp800-53_rev5_gold-set_100q.csv`, `nist_sp800-53_rev4_gold-set_36q.csv`, and the labeled `error_bank_v1.csv`.
* **Output:** `data/qur_outputs/qur_rewrites_error_bank.csv`, `qur_rewrites_rev4.csv`, `qur_rewrites_rev5.csv`.

### **4. Experiment (Run S2–S8)**

* **Action:** Run Section 2 of the latest S1-S8 ablation notebook (the version that includes S7 performance + accuracy gating and enhancement ID canonicalization).
* **Input:** Uses rewrites from Step 3 for S6,S7,S8.
* **Output:** all files in `ablation_outputs`.

### **4b. Performance Benchmark (Latency + Gate Audit)**

* **Action:** Run the performance benchmark notebook that imports the production S7 retriever (src/compliancegpt/retriever/retriever_s7.py).
* **Purpose:** Quantify latency and confirm the pre-rerank skip gate reduces reranker calls while preserving retrieval quality.
* **Systems of interest:**
  - S7_gated (production gate enabled)
  - S7_worst_always_rerank (skip gate disabled; reranker always called)
* **Output:** benchmark CSV/MD artifacts (latency table, per-run data, and meta with reranker_called / rerank_applied counts).

### **5. Analyze (Generate Pivot Table)**

* **Action:** Run `experiments/retriever_ablation/error_analysis/error_mode_analyze.ipynb`.
* **Input:** 
`error_bank_v1.csv`,
	`system_1_bm25/S1_bm25_error_bank_rev4_results.csv`,
        `system_1_bm25/S1_bm25_error_bank_rev5_results.csv`
  
    `system_2_dense/S2_dense_error_bank_rev4_results.csv`,
        `system_2_dense/S2_dense_error_bank_rev5_results.csv`
    
 `system_5_hybrid_rrf/S5_hybrid_rrf_error_bank_rev4_results.csv`,
        `system_5_hybrid_rrf/S5_hybrid_rrf_error_bank_rev5_results.csv`
    
 `system_6_hybrid_rerank/S6_hybrid_rerank_error_bank_rev4_results.csv`,
        `system_6_hybrid_rerank/S6_hybrid_rerank_error_bank_rev5_results.csv`
    
 `system_7_compliance_gpt/S7_compliance_gpt_error_bank_rev4_results.csv`,
        `system_7_compliance_gpt/S7_compliance_gpt_error_bank_rev5_results.csv`
 .
* **Output:** `pivot_table.csv`, `pivot_table.md`, `merged_results_data.csv`.

Notes:
- Re-run after changes to S7 gating, control-id normalization, CCS version, or QUR rewrite set.
- Optional: include S3/S4/S8 result CSVs if you want the pivot table to compare those systems too.