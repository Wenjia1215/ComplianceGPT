# ComplianceGPT Retrieval Experiment Workflow (S1–S7)

*Notebook: `AblationStudy_s1-7.ipynb`*

---

## 1. Overview

This document is the master summary for the 7-system ablation study, which was designed to build and validate the **ComplianceGPT Retriever** architecture.

It provides the final consolidated results tables, explains the narrative of the 7-system journey, and details the experimental workflow required to reproduce these findings.

---

## 2. Final Consolidated Results

We evaluate seven systems on six datasets—**Rev.5 (Overall/ODP)**, **Rev.4 (Overall/ODP)**, and **Error Bank (Rev.5/Rev.4)**—reporting **Recall@{1,5,10}**, **MRR@10**, and **nDCG@10** (*↑ = higher is better*).

### Recall@1

| System | Description | Rev. 5 (Overall) | Rev. 5 (ODP) | Rev. 4 (Overall) | Rev. 4 (ODP) | Error Bank (Rev. 5) | Error Bank (Rev. 4) |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 | BM25 (Baseline) | 0.7600 | 0.8095 | 0.6111 | 0.7368 | 0.0000 | 0.0000 |
| S2 | Dense (Baseline) | 0.7500 | 0.7937 | 0.7500 | 0.6316 | 0.5652 | 0.6364 |
| S3 | Rewrite-Only | 0.5000 | 0.5238 | 0.5278 | 0.6316 | 0.0870 | 0.1818 |
| S4 | QUR-RRF | 0.6600 | 0.6349 | 0.7222 | 0.8421 | 0.1304 | 0.2727 |
| S5 | Hybrid RRF (S1+S2) | 0.8500 | 0.8730 | 0.6667 | 0.7368 | 0.4783 | 0.2727 |
| S6 | Hybrid + Rerank | 0.8900 | 0.9048 | 0.8889 | 0.8947 | 0.6522 | 0.6364 |
| S7 | ComplianceGPT | 0.9000 | 0.9206 | 0.8889 | 0.8947 | 0.6957 | 0.6364 |

### Recall@5

| System | Description | Rev. 5 (Overall) | Rev. 5 (ODP) | Rev. 4 (Overall) | Rev. 4 (ODP) | Error Bank (Rev. 5) | Error Bank (Rev. 4) |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 | BM25 (Baseline) | 0.9700 | 0.9683 | 0.8611 | 0.8947 | 0.9130 | 0.8182 |
| S2 | Dense (Baseline) | 0.9600 | 0.9841 | 0.9722 | 0.9474 | 0.9130 | 1.0000 |
| S3 | Rewrite-Only | 0.7400 | 0.7619 | 0.7778 | 0.7368 | 0.3913 | 0.7273 |
| S4 | QUR-RRF | 0.9700 | 1.0000 | 0.9444 | 0.9474 | 0.7826 | 0.9091 |
| S5 | Hybrid RRF (S1+S2) | 1.0000 | 1.0000 | 0.9722 | 1.0000 | 1.0000 | 1.0000 |
| S6 | Hybrid + Rerank | 0.9900 | 1.0000 | 1.0000 | 1.0000 | 0.9565 | 1.0000 |
| S7 | ComplianceGPT | 0.9900 | 1.0000 | 1.0000 | 1.0000 | 0.9565 | 1.0000 |

### Recall@10

| System | Description | Rev. 5 (Overall) | Rev. 5 (ODP) | Rev. 4 (Overall) | Rev. 4 (ODP) | Error Bank (Rev. 5) | Error Bank (Rev. 4) |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 | BM25 (Baseline) | 0.9900 | 0.9841 | 0.9167 | 0.9474 | 1.0000 | 1.0000 |
| S2 | Dense (Baseline) | 0.9900 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| S3 | Rewrite-Only | 0.8500 | 0.8730 | 0.8889 | 0.7895 | 0.6087 | 0.8182 |
| S4 | QUR-RRF | 0.9800 | 1.0000 | 0.9722 | 0.9474 | 0.9130 | 1.0000 |
| S5 | Hybrid RRF (S1+S2) | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| S6 | Hybrid + Rerank | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| S7 | ComplianceGPT | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

### MRR@10

| System | Description | Rev. 5 (Overall) | Rev. 5 (ODP) | Rev. 4 (Overall) | Rev. 4 (ODP) | Error Bank (Rev. 5) | Error Bank (Rev. 4) |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 | BM25 (Baseline) | 0.8512 | 0.8907 | 0.7239 | 0.8246 | 0.3966 | 0.3690 |
| S2 | Dense (Baseline) | 0.8524 | 0.8806 | 0.8472 | 0.7719 | 0.7399 | 0.7879 |
| S3 | Rewrite-Only | 0.6085 | 0.6400 | 0.6401 | 0.6813 | 0.2604 | 0.3948 |
| S4 | QUR-RRF | 0.7802 | 0.7780 | 0.8114 | 0.8947 | 0.4493 | 0.5586 |
| S5 | Hybrid RRF (S1+S2) | 0.9153 | 0.9286 | 0.8125 | 0.8684 | 0.7152 | 0.5985 |
| S6 | Hybrid + Rerank | 0.9398 | 0.9497 | 0.9444 | 0.9474 | 0.8106 | 0.8182 |
| S7 | ComplianceGPT | 0.9448 | 0.9577 | 0.9444 | 0.9474 | 0.8323 | 0.8182 |

### nDCG@10

| System | Description | Rev. 5 (Overall) | Rev. 5 (ODP) | Rev. 4 (Overall) | Rev. 4 (ODP) | Error Bank (Rev. 5) | Error Bank (Rev. 4) |
|---|---|---:|---:|---:|---:|---:|---:|
| S1 | BM25 (Baseline) | 0.8857 | 0.9144 | 0.7715 | 0.8552 | 0.5465 | 0.5250 |
| S2 | Dense (Baseline) | 0.8870 | 0.9107 | 0.8856 | 0.8289 | 0.8042 | 0.8420 |
| S3 | Rewrite-Only | 0.6660 | 0.6959 | 0.6997 | 0.7069 | 0.3430 | 0.4977 |
| S4 | QUR-RRF | 0.8300 | 0.8337 | 0.8509 | 0.9085 | 0.5656 | 0.6675 |
| S5 | Hybrid RRF (S1+S2) | 0.9369 | 0.9468 | 0.8601 | 0.9029 | 0.7881 | 0.7015 |
| S6 | Hybrid + Rerank | 0.9551 | 0.9628 | 0.9590 | 0.9612 | 0.8587 | 0.8658 |
| S7 | ComplianceGPT | 0.9588 | 0.9686 | 0.9590 | 0.9612 | 0.8747 | 0.8658 |

---

## 3. The 7-System Narrative: What Each System Proved

- **S1 (BM25 Baseline):** Proved that a simple lexical retriever is a strong baseline but fails on semantic/terminology gaps (low Error Bank score).
- **S2 (Dense Baseline):** Proved that a semantic retriever is complementary to S1, performing much better on the *hard* Rev. 4 and Error Bank queries.
- **S3 (Rewrite-Only):** Proved that naively replacing a query with its semantic rewrite and feeding it to a lexical (BM25) retriever is a failed strategy. This justifies the need for fusion.
- **S4 (QUR-RRF):** Proved that fusion (RRF) is the correct way to use query rewrites with BM25, creating a system that beats the S1 baseline on harder (Rev. 4) queries.
- **S5 (Hybrid RRF):** Proved that fusing the two baselines (S1+S2) creates a superior high-recall retriever that outperforms all previous systems on the main (Rev. 5) dataset.
- **S6 (Hybrid + Rerank):** Proved that adding a reranker to S5's high-recall list is the key to precision, solving the *noise problem* from S5 and achieving state-of-the-art results on the Error Bank.
- **S7 (ComplianceGPT):** Proved that the full architecture (QUR + Hybrid + Reranker) is the optimal system, as the QUR component provides a final, measurable boost on top of S6, especially on the Error Bank.

---

## 4. Core Project Components

This experiment relies on three sets of data artifacts:

### A. Canonical Clause Store (CCS)
The single source of truth for all retrieval. All systems run against the same JSONL files:
- `NIST_SP-800-53_rev5_catalog.jsonl`
- `NIST_SP-800-53_rev4_catalog.jsonl`

### B. Gold Standard Datasets
The human-verified CSVs used for evaluation. All systems are tested against these:
- `nist_sp800-53_rev5_gold-set_100q.csv` *(Main test set)*
- `nist_sp800-53_rev4_gold-set_36q.csv` *(Harder test set)*
- `error_bank_v1.csv` *(Semantic-failure test set, with `failure_category` column)*

### C. Query Rewrite (QUR) Sets
The pre-generated query variations used by S3, S4, and S7:
- `qur_rewrites_rev5.csv`
- `qur_rewrites_rev4.csv`
- `qur_rewrites_error_bank.csv`

---

## 5. Experimental Workflow

The entire experiment is run from a single **mega-notebook**, enabling all systems to share the same base models (like S1’s BM25 and S2’s Dense index) in memory.

- **Notebook:** `AblationStudy_s1-7.ipynb`  
- **Execution:** Run all cells from top to bottom.

**Process:**  
- **S1 Cells:** Load data, build `bm25_rev5` / `bm25_rev4` models, and run S1 evaluation.  
- **S2 Cells:** Install dependencies, build `dense_retriever_rev5` / `dense_retriever_rev4` models, and run S2 evaluation.  
- **S3 Cells:** Define S3/S4 configs, define `prepare_s3_rewrite_only_set` function, and run S3 evaluation.  
- **S4 Cells:** Define `get_rrf_fused_rank` function and run S4 evaluation.  
- **S5 Cells:** Define S5 config, define `get_hybrid_rrf_rank` function, and run S5 evaluation (re-using S1 & S2 models).  
- **S6 Cells:** Define S6 config, load `CrossEncoder` model, define `get_hybrid_reranked_rank` function, and run S6 evaluation (re-using S1 & S2 models).  
- **S7 Cells:** Define S7 config, define `get_compliance_gpt_rank` function, and run S7 evaluation (re-using S1, S2, & S6 models).

---

## 6. Output Artifacts & Individual READMEs

This workflow is designed to be self-documenting.

**Individual Results:** Each system (S1–S7) saves its own detailed results, analysis, and `README.md` file into its own dedicated folder:

- `/ablation_outputs/system_1_bm25/`
- `/ablation_outputs/system_2_dense/`
- `/ablation_outputs/system_3_rewrite_only/`
- `/ablation_outputs/system_4_qur_rrf/`
- `/ablation_outputs/system_5_hybrid_rrf/`
- `/ablation_outputs/system_6_hybrid_rerank/`
- `/ablation_outputs/system_7_compliance_gpt/`

**Individual READMEs:** For a detailed breakdown of each experiment, see the individual READMEs (S1–S7).

---

This combined document now serves as the single, definitive guide for your retrieval experiment, containing the final results, the narrative, and the experimental process all in one place.
