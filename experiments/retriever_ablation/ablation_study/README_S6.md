# System 6 — Hybrid + Reranker (S6)

*(Notebook: `AblationStudy_s1-7.ipynb` — S6 Cells)*

## 1. Overview

This README describes **System 6 (S6)**, the sixth experiment in the ComplianceGPT ablation study and the first system to use a **high-precision cross-encoder reranker**.

This system is a direct continuation of **System 5**. It is built on the hypothesis that **S5 (Hybrid RRF)** is an excellent **high-recall** system, but its precision is damaged by **“lexical noise”** from BM25.

**Architecture (two-stage pipeline):**
- **Stage 1 (Candidate Generation):** Use **S5 (Hybrid RRF)** to generate a high-recall candidate set (`CANDIDATE_SET_SIZE = 50`).
- **Stage 2 (Reranking):** Feed these 50 candidates into a powerful **cross-encoder** model to re-sort them based on deep semantic relevance.

**Core question:**  
*Can a high-cost, high-precision reranker sift through the high-recall candidate list from S5 to fix its precision problems and achieve a new state-of-the-art performance?*

---

## 2. Experimental Purpose

The S6 experiment is designed to answer three specific research questions:

1. **Does a Reranker Add Value?**  
   Does adding a reranking stage on top of S5 (Hybrid RRF) provide a significant performance boost in precision (**Recall@1, MRR@10**)?

2. **Can S6 Solve the “Error Bank Problem”?**  
   In S5, we saw that S2 (Dense-Only) outperformed S5 on the Error Bank. This suggested S5’s hybrid list was “noisy.” Can the S6 reranker “clean up” this noise and finally beat the S2 (Dense) baseline on these hardest queries?

3. **Is S6 the New Champion?**  
   Does this new two-stage architecture become the best-performing system so far, setting a new bar for the final S7 (ComplianceGPT) system to beat?

---

## 3. Setup & Prerequisites

S6 is **not** a standalone experiment. It depends on all the models and data loaded for **System 1** and **System 2**.

### Requirements Before Running S6

| Requirement | Reason |
|---|---|
| **S1, S2 models in memory** | S6 requires the S1 BM25 models (`bm25_rev5`) and S2 Dense retrievers (`dense_retriever_rev5`). |
| **S1 data in memory** | S6 requires the S1 `rev5_docs` and `rev4_docs` to create the `id_to_text_map`. |
| **S6 helper function must exist** | The new `get_hybrid_reranked_rank` function must be defined. |
| **Reranker model must be loaded** | The `CrossEncoder` model (`ms-marco-MiniLM-L-6-v2`) must be loaded. |
| **S1 Gold Sets must exist** | S6 evaluates against the original queries. |

### In-Memory Objects Needed (from S1 & S2)

| Object | From System | Description |
|---|---|---|
| `bm25_rev5`, `bm25_rev4` | S1 | The trained BM25 models. |
| `rev5_ids`, `rev4_ids` | S1 | The list of control IDs for BM25. |
| `rev5_docs`, `rev4_docs` | S1 | The raw document text, used to build the text maps. |
| `dense_retriever_rev5` | S2 | The trained Dense retriever (model + FAISS index). |
| `dense_retriever_rev4` | S2 | The trained Dense retriever (model + FAISS index). |
| `display_summary_report` | S1 | Helper function to print metrics. |
| `save_summary_report` | S1 | Helper function to save the markdown report. |

### New Functions/Classes Introduced for S6

| Object | Purpose |
|---|---|
| `CrossEncoder` | The class from `sentence-transformers` used to load the reranker model. |
| `get_hybrid_reranked_rank` | The core S6 engine. It performs the S5 hybrid fusion first to get candidates, then passes them to the reranker for final scoring. |

### Input Files Required

S6 uses the original S1 gold standard queries:

- `nist_sp800-53_rev5_gold-set_100q.csv`  
- `nist_sp800-53_rev4_gold-set_36q.csv`  
- `error_bank_v1.csv`

---

## 4. Workflow & Logic

The S6 evaluation is a **two-stage** process for each query:

### Stage 1: Candidate Generation (S5 Hybrid RRF)

1. **Load Original Query:** The original query from the S1 gold set is loaded.  
2. **Run Dual Search:** Two searches in parallel to get a wide candidate list (`n=50`):  
   - **Lexical Search:** `bm25_rev5.get_top_n(query, n=50)` (S1 logic)  
   - **Semantic Search:** `dense_retriever_rev5.search(query, top_k=50)` (S2 logic)  
3. **Fuse Results (RRF):** The two resulting lists are fused using **RRF** (`k=60`).  
4. **Create Candidate Set:** The fused list is re-sorted, and the **top 50** (`CANDIDATE_SET_SIZE`) documents are selected as the high-recall candidate set.

### Stage 2: Reranking

5. **Fetch Text:** Retrieve the full document text for all 50 candidates using the `id_to_text_map` (created from S1’s `rev5_docs`).  
6. **Rerank:** Create 50 `(original_query, passage_text)` pairs and feed them to the `cross_encoder.predict()` model.  
7. **Find Final Rank:** Re-sort the 50 candidates by the new, high-precision cross-encoder score and locate the final rank of the `gold_control_id` (**only if it is in the top 10**).  
8. **Save Results:** Record the final rank and save all results to the S6 directory.

---

## 5. Outputs

All outputs are saved under:

```
/content/drive/MyDrive/ablation_outputs/system_6_hybrid_rerank/
```

| File | Description |
|---|---|
| `S6_hybrid_rerank_rev5_results.csv` | Detailed results for 100 reranked Rev.5 queries. |
| `S6_hybrid_rerank_rev4_results.csv` | Detailed results for 36 reranked Rev.4 queries. |
| `S6_hybrid_rerank_error_bank_rev5_results.csv` | Results for 23 reranked Rev.5 Error Bank queries. |
| `S6_hybrid_rerank_error_bank_rev4_results.csv` | Results for 11 reranked Rev.4 Error Bank queries. |
| `S6_hybrid_rerank_report.md` | Summary report with all 4 performance tables. |

---

## 6. Analysis & Key Findings

### ✅ Key Finding 1: **S6 is the New State-of-the-Art.**

The S6 (Hybrid + Reranker) system achieves the highest scores seen so far, soundly beating all previous systems (S1–S5) across all datasets.

**Rev. 5 (Overall) — nDCG@10**

| System | Description | nDCG@10 | Finding |
|---|---|---:|---|
| **S1** | BM25 | 0.8857 | Baseline |
| **S2** | Dense | 0.8870 | Baseline |
| **S5** | Hybrid RRF | 0.9369 | Strong |
| **S6** | Hybrid + Rerank | 0.9551 | **New SOTA** |

**Rev. 4 (Overall) — nDCG@10**

| System | Description | nDCG@10 | Finding |
|---|---|---:|---|
| **S1** | BM25 | 0.7715 | Baseline |
| **S2** | Dense | 0.8856 | Strong |
| **S5** | Hybrid RRF | 0.8601 | (Slightly worse than S2) |
| **S6** | Hybrid + Rerank | 0.9590 | **Massive Gain** |

---

### ✅ Key Finding 2: **S6 Solved the “Error Bank Problem.”**

This is the most critical finding. In S5, we observed that S2 (Dense) was superior to S5 (Hybrid) on the Error Bank. **S6 has fixed this completely.**

**Error Bank (Rev. 5) — MRR@10**

| System | Description | MRR@10 | Finding |
|---|---|---:|---|
| **S1** | BM25 | 0.3966 | (Fails) |
| **S2** | Dense (Best so far) | 0.7399 | (Strong) |
| **S5** | Hybrid RRF | 0.7152 | (S2 was better) |
| **S6** | Hybrid + Rerank | 0.8106 | **New SOTA** |

**Conclusion:** This proves our hypothesis from S5. S5 (Hybrid) successfully generated a **high-recall** candidate list (**Recall@10 = 1.0000**), but its precision was low. The **S6 reranker** successfully “sifted” through this list, found the correct semantic matches, and promoted them to the top—solving the very problem S5 introduced.

---

## 📌 Final Conclusion

**System 6 (Hybrid + Reranker)** is a **highly effective, high-precision** retrieval pipeline.

It proves that a **two-stage architecture** (`(S1+S2) -> RRF -> Reranker`) is extremely powerful. It combines the **high-recall** candidate generation of a fast, fused system (S5) with the **high-precision** scoring of a slow, complex model (cross-encoder).

This system sets a very high bar and serves as the final component for the **ultimate “ComplianceGPT” retriever (S7)**, which will test if adding QUR can eke out even more performance.
