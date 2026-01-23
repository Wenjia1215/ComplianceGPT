
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

* **Action:** Run **Section 2** of `AblationStudy_S1_8.ipynb`.
* **Input:** Uses rewrites from Step 3 for S6,S7,S8.
* **Output:** all files in `ablation_outputs`.

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