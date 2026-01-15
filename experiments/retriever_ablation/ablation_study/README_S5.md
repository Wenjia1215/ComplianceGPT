# System 5 — Hybrid Retrieval (BM25 + Dense + RRF) (S5)

*(Notebook: `AblationStudy_S1-7.ipynb` — S5 Cells)*

## 1. Overview

This README describes **System 5 (S5)**, the fifth experiment and the first true **hybrid** retriever in the ComplianceGPT ablation study.

This system addresses a core hypothesis of modern retrieval: that **neither lexical search (BM25) nor semantic search (Dense) is sufficient on its own**. S5 combines the two, fusing their results to get the best of both worlds.

The primary function of this experiment is to measure the effect of combining the **S1** and **S2** retrievers using **Reciprocal Rank Fusion (RRF)**. This system answers the question:

> Can we combine the keyword-matching strength of **S1 (BM25)** and the semantic-understanding of **S2 (Dense)** to create a single, superior retriever that outperforms both?

---

## 2. Experimental Purpose

The S5 experiment is designed to answer three specific research questions:

1. **Are S1 (BM25) and S2 (Dense) complementary?**  
   Do they find different correct documents for the same query, which can be combined for a higher recall?

2. **Can a simple, unweighted RRF fusion** of these two systems create a new state-of-the-art baseline for our main datasets (Rev. 5 and Rev. 4)?

3. **How does this hybrid system perform on the Error Bank?**  
   Does the “lexical noise” from BM25 hurt the strong semantic performance of S2, or does BM25 help S2 on some queries?

---

## 3. Setup & Prerequisites

S5 is **not** a standalone experiment. It must be executed **after both System 1 and System 2** in the same runtime session, as it depends directly on the models they create.

### Requirements Before Running S5

| Requirement | Reason |
|---|---|
| **S1 must be fully executed** | S5 requires the S1 BM25 models (`bm25_rev5`, `bm25_rev4`) to be in memory. |
| **S2 must be fully executed** | S5 requires the S2 Dense retrievers (`dense_retriever_rev5`, `dense_retriever_rev4`) to be in memory. |
| **S5 helper function must exist** | The new `get_hybrid_rrf_rank` function must be defined. |
| **S1 Gold Sets must exist** | S5 evaluates against the original queries, not the QUR sets. |

### In-Memory Objects Needed (from S1 & S2)

| Object | From System | Description |
|---|---|---|
| `bm25_rev5` | S1 | The trained BM25 model for NIST Rev. 5. |
| `rev5_ids` | S1 | The list of control IDs matching the BM25 index. |
| `bm25_rev4` | S1 | The trained BM25 model for NIST Rev. 4. |
| `rev4_ids` | S1 | The list of control IDs matching the BM25 index. |
| `dense_retriever_rev5` | S2 | The trained Dense retriever (model + FAISS index) for Rev. 5. |
| `dense_retriever_rev4` | S2 | The trained Dense retriever (model + FAISS index) for Rev. 4. |
| `display_summary_report` | S1 | Helper function to print metrics. |
| `save_summary_report` | S1 | Helper function to save the markdown report. |

### New Functions Introduced for S5

| Function | Purpose |
|---|---|
| `get_hybrid_rrf_rank` | The core S5 engine. It takes a query, runs it against both the BM25 and Dense models, and performs RRF to find the final rank of the gold document. |

### Input Files Required

S5 uses the original S1 gold standard queries:

- `nist_sp800-53_rev5_gold-set_100q.csv`  
- `nist_sp800-53_rev4_gold-set_36q.csv`  
- `error_bank_v1.csv`

---

## 4. Workflow & Logic

The S5 evaluation uses a **5-stage process** for each query:

1. **Load S1 Gold Set**  
   The evaluation loops through the original S1 query sets (e.g., `rev5_gold`).

2. **Run Dual Search**  
   For a single query, the `get_hybrid_rrf_rank` function runs two searches in parallel:
   - **Lexical Search**: `bm25_rev5.get_top_n(query)` (S1 logic)  
   - **Semantic Search**: `dense_retriever_rev5.search(query)` (S2 logic)

3. **Fuse Results (RRF)**  
   The two resulting lists of control IDs are fused using **Reciprocal Rank Fusion** (with `k=60`).  
   A combined score is calculated for every unique document found in either list.

4. **Find Final Rank**  
   The fused list is re-sorted by the new RRF scores. The final rank of the `gold_control_id` is found in this new hybrid list.

5. **Save Results & Reports**  
   The final rank is recorded, and the process repeats. The results are saved to the S5 output directory.

---

## 5. Outputs

All outputs are saved under:

```
/content/drive/MyDrive/ablation_outputs/system_5_hybrid_rrf/
```

| File | Description |
|---|---|
| `S5_hybrid_rrf_rev5_results.csv` | Detailed results for 100 hybrid-fused Rev.5 queries. |
| `S5_hybrid_rrf_rev4_results.csv` | Detailed results for 36 hybrid-fused Rev.4 queries. |
| `S5_hybrid_rrf_error_bank_rev5_results.csv` | Results for 23 hybrid-fused Rev.5 Error Bank queries. |
| `S5_hybrid_rrf_error_bank_rev4_results.csv` | Results for 11 hybrid-fused Rev.4 Error Bank queries. |
| `S5_hybrid_rrf_report.md` | Summary report with all 4 performance tables. |

---

## 6. Analysis & Key Findings

### ✅ Key Finding 1: S5 is the new State-of-the-Art for the main dataset.

S5 shows a **massive performance gain** on the main NIST Rev. 5 dataset, proving that S1 (BM25) and S2 (Dense) are highly complementary. They are finding different correct documents, and **RRF** is successfully combining them.

**Rev. 5 (Overall) — MRR@10**

| System | Description | MRR@10 | Finding |
|---|---|---:|---|
| **S1** | BM25 (Baseline) | 0.8512 | Baseline |
| **S2** | Dense (Baseline) | 0.8524 | Baseline |
| **S5** | Hybrid (S1+S2) | 0.9153 | **Significant Gain** |

Furthermore, S5 achieves **1.0000** for both **Recall@5** and **Recall@10** on the Rev. 5 set, meaning the correct answer was always in the top 5 for ODP-related queries and in the top 10 for all queries.

---

### Key Finding 2: S2 (Dense-Only) is still King of the “Error Bank”

A crucial finding is that for the hardest query sets (Rev. 4 and the Error Bank), **S5 performs slightly worse than S2 (Dense-Only)**.

**Error Bank (Rev. 5) — MRR@10**

| System | Description | MRR@10 |
|---|---|---:|
| **S1** | BM25 (Baseline) | 0.3966 |
| **S2** | Dense (Baseline) | 0.7399 |
| **S5** | Hybrid (S1+S2) | 0.7152 |

**Conclusion:** This is a critical insight. It proves that the **Error Bank queries are true semantic failures** that BM25 cannot solve. When we fuse S1 (BM25) with S2 (Dense), the “bad” lexical scores from BM25 are adding **noise** and slightly polluting the superior results from S2.

---

## Final Conclusion

**System 5 (Hybrid RRF) is the best “all-around” retriever.**

It provides a significant boost on the main dataset (Rev. 5) and still performs very well on the harder datasets (Rev. 4, Error Bank), far surpassing the S1 and S4 baselines.

Its results motivate the need for **System 6**. S5 provides the perfect, **high-recall candidate set (Recall@10 = 1.0000)** for a reranker to work on. The job of S6 will be to take the high-recall list from S5 and *“clean up” the noise* introduced by BM25, aiming to get the best of all worlds.
