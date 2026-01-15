# System 4 — BM25 + Query Rewrites + RRF (S4)

*(Notebook: `AblationStudy_S1-7.ipynb`)*

## 1. Overview

This README describes **System 4 (S4)**, a key component of the ComplianceGPT retrieval evaluation.

S4 is the direct solution to the problem identified in System 3. It tests a robust fusion-based approach, **BM25 + QUR-RRF**, which combines the lexical baseline with semantic query variations.

The primary function of this experiment is to **measure the effect of query fusion**.
> _What happens when we combine the results from the high-precision original query with the results from its semantic rewrites using Reciprocal Rank Fusion (RRF)?_

---

## 2. Experimental Purpose

The S4 experiment is designed to answer three specific research questions:

1.  **Can RRF solve the "semantic-on-lexical mismatch" failure** observed in S3?
2.  **Can fusing the original query with rewrites create a retriever that is more robust** than the S1 (BM25) baseline, especially on complex or poorly-phrased queries?
3.  **Does this fusion approach improve performance on the "hard" queries** from the Error Bank where S1 originally failed?

---

## 3. Setup & Prerequisites

S4 is **not a standalone experiment**. It must be executed **after System 1** in the same runtime session.

### Requirements Before Running S4

| Requirement | Reason |
| :--- | :--- |
| S1 must be fully executed | S4 uses S1 models, objects, and helper functions. |
| S1 in-memory objects required | S4 reuses `bm25_rev5`, `bm25_rev4`, `rev5_ids`, `rev4_ids`. |
| S4 helper function must be defined | The `get_rrf_fused_rank` function must be in memory. |
| QUR rewrite CSVs must exist | S4 loads all rewrites (not just rank 1) to perform fusion. |

### In-Memory Objects Needed from S1

* `bm25_rev5`, `rev5_ids`
* `bm25_rev4`, `rev4_ids`
* Helper functions:
    * `display_summary_report`
    * `save_summary_report`

### Input Files Required

**S1 Ground Truth Sets:**
* `nist_sp800-53_rev5_gold-set_100q.csv`
* `nist_sp800-53_rev4_gold-set_36q.csv`
* `error_bank_v1.csv`

**QUR Query Rewrite Sets:**
* `qur_rewrites_rev5.csv`
* `qur_rewrites_rev4.csv`
* `qur_rewrites_error_bank.csv`

---

## 4. Workflow & Logic

The S4 evaluation uses a 7-stage process for *each* query:

1.  **Load All Datasets**
    Imports all six CSVs (3 S1 gold sets + 3 QUR rewrite sets).
2.  **Fetch All Queries**
    For a single original query, it fetches the original query text *and* all of its associated rewrites (e.g., 1 original + 3 rewrites).
3.  **Run N Searches**
    It runs a separate BM25 search for *each* of these 4 queries, generating 4 distinct ranked lists.
4.  **Fuse Results (RRF)**
    All 4 result lists are combined into a single new ranked list using Reciprocal Rank Fusion (RRF).
5.  **Find Final Rank**
    The rank of the `gold_control_id` is found within this *newly fused* list.
6.  **Evaluate**
    The final rank (or 0 if not found) is stored. This loop repeats for all queries.
7.  **Save Results & Reports**
    The final evaluation results and summary report files are exported to the configured S4 directory.

---

## 5. Outputs

All outputs are saved under:
`/content/drive/MyDrive/ablation_outputs/system_4_qur_rrf/`

| File | Description |
| :--- | :--- |
| `S4_qur_rrf_rev5_results.csv` | Detailed results for 100 fused Rev.5 queries |
| `S4_qur_rrf_rev4_results.csv` | Detailed results for 36 fused Rev.4 queries |
| `S4_qur_rrf_error_bank_rev5_results.csv` | Results for 23 fused Rev.5 Error Bank queries |
| `S4_qur_rrf_error_bank_rev4_results.csv` | Results for 11 fused Rev.4 Error Bank queries |
| `S4_qur_rrf_report.md` | Summary report with 4 performance tables |

---

## 6. Analysis & Key Findings

### Key Finding 1: **RRF Solves the S3 Failure & Improves on S1**

S4 performance not only recovers from the S3 drop but *improves* upon the S1 baseline for more complex datasets.

**Rev. 4 (Overall) — MRR@10**
| System | Description | MRR@10 | Finding |
| :--- | :--- | ---: | :--- |
| S1 | BM25 (Baseline) | 0.7239 | Baseline |
| S3 | Rewrite-Only | 0.6401 | **Failure** |
| S4 | **QUR-RRF** | **0.8114** | **Success** |

**Rev. 4 (ODP-Subset) — nDCG@10**
| System | Description | nDCG@10 | Finding |
| :--- | :--- | ---: | :--- |
| S1 | BM25 (Baseline) | 0.8552 | Baseline |
| S3 | Rewrite-Only | 0.7069 | **Failure** |
| S4 | **QUR-RRF** | **0.9085** | **Success** |


This confirms that **fusion is the correct strategy**. It successfully combines the lexical precision of the original query with the semantic breadth of the rewrites.

---

### Key Finding 2: **Trade-off on "Easy" Queries**

For the "easier" Rev. 5 dataset, the fusion approach (S4) performs slightly worse than the highly-tuned S1 baseline, though it is still a massive improvement over S3.

**Rev. 5 (Overall) — MRR@10**
| System | Description | MRR@10 |
| :--- | :--- | ---: |
| S1 | BM25 (Baseline) | 0.8512 |
| S3 | Rewrite-Only | 0.6085 |
| S4 | **QUR-RRF** | 0.7802 |

**Conclusion:** For simple queries where S1's keywords are already perfect, adding semantic rewrites can introduce some noise. However, for complex queries (Rev. 4, Error Bank), this "noise" is actually a **robustness feature** that finds answers S1 would have missed.

---

### Final Conclusion

> **System 4 (QUR + RRF) is a valid and robust retrieval strategy.**

It successfully solves the "semantic-on-lexical mismatch" from S3. By proving that **fusion is the correct way to use query rewrites with BM25**, S4 validates a critical *component* of the final architecture.

This system's logic (fusing original query + rewrites in a lexical search) will be combined with S2 (Dense) and S6 (Reranker) to build the ultimate **System 7 (ComplianceGPT)** retriever.
