# System 3 — BM25 + Query Rewrites (S3)

*(Notebook: `AblationStudy_S1-7.ipynb`)*

## 1\. Overview

This README describes **System 3 (S3)**, the third major experiment for the ComplianceGPT retrieval evaluation.

S3 serves as a critical ablation study component. It evaluates the performance of the **System 1 (BM25 Baseline)** retriever against the **new Query Rewrite (QUR)** gold sets.

The primary function of this experiment is to **isolate and measure the impact of the Query Rewrite (QUR) component in isolation** against a purely lexical retriever.
This system tests the *semantic-on-lexical mismatch*:

> *What happens when semantically-paraphrased queries are fed into a model that relies on exact keyword matching?*

-----

## 2\. Experimental Purpose

The S3 experiment is designed to answer three specific research questions:

1.  **Does paraphrasing a query (preserving semantics) while changing its words help or hurt BM25?**
    BM25 relies on keyword overlap—rewriting may remove those exact keywords.

2.  **Can rewritten queries fix total retrieval failures from S1?**
    (Hypothesis: rewrites may introduce missing keywords that S1 failed to match, improving Recall.)

3.  **Do rewrites damage the performance of queries that were originally successful in S1?**
    (Hypothesis: yes — rewrites remove the exact lexical terms BM25 needs.)

-----

## 3\. Setup & Prerequisites

S3 is **not a standalone experiment**. It must be executed **after System 1** in the same runtime session.

### Requirements Before Running S3

| Requirement | Reason |
| :--- | :--- |
| S1 must be fully executed | S3 uses S1 models, objects, and helper functions |
| S1 in-memory objects required | S3 reuses BM25 models & ID lists for evaluation |
| S3 rewrite CSVs must exist | S3 loads the new rewritten queries to evaluate |

### In-Memory Objects Needed from S1

  * `bm25_rev5`, `rev5_ids`
  * `bm25_rev4`, `rev4_ids`
  * Helper functions:
      * `evaluate_gold`
      * `display_summary_report`
      * `save_summary_report`

### Input Files Required

**S1 Ground Truth Sets:**

  * `nist_sp800-53_rev5_gold-set_100q.csv`
  * `nist_sp800-53_rev4_gold-set_36q.csv`
  * `error_bank_v1.csv`

**S3 Query Rewrite Sets:**

  * `qur_rewrites_rev5.csv`
  * `qur_rewrites_rev4.csv`
  * `qur_rewrites_error_bank.csv`

-----

## 4\. Workflow & Logic

The S3 evaluation uses a 5-stage process:

1.  **Load All Datasets**
    Imports all six CSVs (3 S1 + 3 S3 rewrite sets).

2.  **Select the Best Rewrite Per Query**
    S3 data includes multiple rewrites — only the top-ranked rewrite (`rewrite_rank == 1`) is kept.

3.  **Merge S1 + S3 Data**
    Each rewritten query is merged with S1 ground truth:

| Merge Left (S1) | Merge Right (S3) | Purpose |
| :--- | :--- | :--- |
| `question` | `original_query` | Attach ground truth (control_id, odp_required) to rewritten query |

4.  **Evaluate Rewritten Queries**
    S1 BM25 models (`bm25_rev5`, `bm25_rev4`) are used to rank documents using the rewritten query text.

5.  **Save Results & Reports**
    The evaluation results and summary report files are exported to the configured S3 directory.

-----

## 5\. Outputs

All outputs are saved under:

```
/content/drive/MyDrive/ablation_outputs/system_3/
```

| File | Description |
| :--- | :--- |
| `S3_bm25_qur_rev5_results.csv` | Detailed results for 100 rewritten Rev.5 queries |
| `S3_bm25_qur_rev4_results.csv` | Detailed results for 36 rewritten Rev.4 queries |
| `S3_bm25_qur_error_bank_rev5_results.csv` | Results for 23 rewritten Rev.5 Error Bank queries |
| `S3_bm25_qur_error_bank_rev4_results.csv` | Results for 11 rewritten Rev.4 Error Bank queries |
| `S3_bm25_qur_report.md` | Summary report with 4 performance tables |

-----

## 6\. Analysis & Key Findings

### ✅ Key Finding 1: **Semantic Rewriting Damages BM25**

BM25 performance dropped **significantly** across all datasets when using rewritten queries.

  * Rev.5 Recall@1: **0.7600 → 0.5000**
  * Rev.5 nDCG@10: **0.8857 → 0.6660**

This confirms that **BM25 depends on exact lexical overlap** — paraphrasing removes critical matching tokens.

-----

### ⚠️ Key Finding 2: **Error Bank — Minor Fixes, Major Damage**

| Observation | Impact |
| :--- | :--- |
| Some previously failed queries now succeed | (S3 Recall@1 > 0 for Error Bank) |
| Most originally working queries now fail | Huge drop in Recall@5 and @10 |

Example (Rev.5 Error Bank, Recall@5):

| System | Recall@5 |
| :--- | :--- |
| S1 (BM25) | 0.9130 |
| S3 (QUR+BM25) | 0.3913 |

**Conclusion:** Rewrites fixed a few failures but broke far more previously successful queries.

-----

### 📌 Final Conclusion

> **System 3 (QUR + BM25) is an invalid retrieval strategy.**

S3 introduces a **semantic component** (the rewritten query) into a **lexical system** (BM25), causing incompatibility.

This failure proves that naively replacing the original query is the wrong approach. It directly **motivates the need for System 4 (QUR-RRF)**, which tests if **fusing** the results from the original query and its rewrites using RRF is the correct way to leverage query variations with a lexical retriever.
