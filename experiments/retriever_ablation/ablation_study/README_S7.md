# System 7 — ComplianceGPT (QUR + Hybrid + Reranker) (S7)

*(Notebook: `AblationStudy_S1-7.ipynb` — S7 Cells)*

## 1. Overview

This README describes **System 7 (S7)**, the **ultimate retriever** and the final experiment in the ComplianceGPT ablation study.

This system—representing the full **“ComplianceGPT Retriever”** (as defined in `DrSadjadi_advise5.docx`)—combines all the most successful, validated components from the previous six experiments into a single, comprehensive pipeline.

**Architecture (S7):**

```
(S4 [BM25 + QUR-RRF] + S2 [Dense]) -> RRF -> S6 [Reranker]
```

This system is designed to create the most robust candidate list possible—a **superhybrid** list—by fusing both lexical query rewrites (S4) and semantic results (S2), and then applying the high-precision reranker (S6) to find the best possible answer.

**Core question:**  
*Does adding the QUR component (from S4) to the S6 (Hybrid + Reranker) system provide a final, measurable performance boost to create the best possible retriever?*

---

## 2. Experimental Purpose

S7 validates the final architecture and answers three key questions:

1. **Does QUR still add value?**  
   We know S6 (Hybrid + Reranker) is extremely strong. Does adding S4’s QUR-RRF component on top of it provide a final, statistically significant boost, or have we hit a performance ceiling?

2. **Can S7 solve the “Hardest Cases”?**  
   Can this **superhybrid** system outperform S6 on the most difficult queries—namely the **Error Bank**—by feeding the reranker an even better candidate list?

3. **Is S7 the definitive winner?**  
   Does S7 emerge as the **new state-of-the-art** across all four test datasets, justifying its position as the final, “ultimate” retriever?

---

## 3. Setup & Prerequisites

S7 is the most complex system and **depends on S1, S2, and S6** components being in the same runtime session.

### Requirements Before Running S7

| Requirement | Reason |
|---|---|
| **S1, S2, S6 models in memory** | S7 re-uses all models: BM25, Dense, and the Reranker. |
| **S1, S2, S6 helper functions** | S7’s logic builds upon functions from all previous systems. |
| **S1 Gold Sets & QUR Sets** | S7 needs the original queries (for S2) and the rewrite CSVs (for S4). |

### In-Memory Objects Needed (from S1, S2, S6)

| Object | From System | Description |
|---|---|---|
| `bm25_rev5`, `bm25_rev4` | S1 | The trained BM25 models. |
| `rev5_ids`, `rev4_ids` | S1 | The list of control IDs for BM25. |
| `rev5_docs`, `rev4_docs` | S1 | The raw document text, used to build the text maps. |
| `dense_retriever_rev5` | S2 | The trained Dense retriever (model + FAISS index). |
| `dense_retriever_rev4` | S2 | The trained Dense retriever (model + FAISS index). |
| `cross_encoder` | S6 | The loaded `ms-marco-MiniLM-L-6-v2` reranker model. |
| `rev5_id_to_text` | S6 | The dictionary mapping control IDs to their full text. |
| `rev4_id_to_text` | S6 | The dictionary mapping control IDs to their full text. |

### New Functions Introduced for S7

| Function | Purpose |
|---|---|
| `get_compliance_gpt_rank` | The core S7 engine. Performs the **superhybrid** RRF fusion (S4 + S2) and then passes the resulting candidate list to the cross-encoder for a final reranking. |

### Input Files Required

**S1 Gold Sets:**
- `nist_sp800-53_rev5_gold-set_100q.csv`
- `nist_sp800-53_rev4_gold-set_36q.csv`
- `error_bank_v1.csv`

**QUR Rewrite Sets:**
- `qur_rewrites_rev5.csv`
- `qur_rewrites_rev4.csv`
- `qur_rewrites_error_bank.csv`

---

## 4. Workflow & Logic

S7 uses a **two-stage** pipeline that combines all previous systems:

### Stage 1: Candidate Generation (**“Superhybrid” RRF**)

1. **Load Original Query:** Load the original query from the S1 gold set.  
2. **Fetch S4 (QUR-RRF) Results:**  
   - Fetch the original query and all of its rewrites (e.g., 3 rewrites) from the QUR CSVs.  
   - Run a **BM25** search for all 4 of these queries.  
   - Add the results from all 4 searches to an **RRF score pool**.  
3. **Fetch S2 (Dense) Results:**  
   - Run a single **Dense** search using the original query.  
   - Add these results to the same **RRF score pool** from Step 2.  
4. **Create Candidate Set:**  
   - Finalize RRF scores and sort the pool.  
   - Select the **top 50** (`CANDIDATE_SET_SIZE`) documents as the high-recall candidate set.

### Stage 2: Reranking (**S6 Logic**)

5. **Fetch Text:** Retrieve the full document text for all 50 candidates using the `id_to_text_map`.  
6. **Rerank:** Build 50 `(original_query, passage_text)` pairs and feed them to the **cross-encoder** model to get new, high-precision scores.  
7. **Find Final Rank:** Re-sort the 50 candidates by the new reranker score and locate the final rank of the `gold_control_id`.  
8. **Save Results:** Record the final rank and save all outputs to the S7 directory.

---

## 5. Outputs

All outputs are saved under:

```
/content/drive/MyDrive/ablation_outputs/system_7_compliance_gpt/
```

| File | Description |
|---|---|
| `S7_compliance_gpt_rev5_results.csv` | Detailed results for 100 “ultimate” Rev.5 queries. |
| `S7_compliance_gpt_rev4_results.csv` | Detailed results for 36 “ultimate” Rev.4 queries. |
| `S7_compliance_gpt_error_bank_rev5_results.csv` | Results for 23 “ultimate” Rev.5 Error Bank queries. |
| `S7_compliance_gpt_error_bank_rev4_results.csv` | Results for 11 “ultimate” Rev.4 Error Bank queries. |
| `S7_compliance_gpt_report.md` | The final summary report with all 4 performance tables. |

---

## 6. Analysis & Key Findings

### Key Finding 1: **S7 (ComplianceGPT) is the Definitive Winner.**

S7 achieves the highest performance in every single test category, confirming its status as the **ultimate** retriever. It successfully combines the strengths of all previous systems.

**Rev. 5 (Overall) — MRR@10**

| System | Description | MRR@10 | Finding |
|---|---|---:|---|
| **S5** | Hybrid RRF | 0.9153 | (Strong) |
| **S6** | Hybrid + Rerank | 0.9398 | (Stronger) |
| **S7** | ComplianceGPT | 0.9448 | **Best** |

---

### Key Finding 2: **QUR Provides the Final, Critical Boost.**

The most important comparison is **S7 vs. S6**. The only difference is that S7 includes the **QUR** component. The results show this addition provides a clear, measurable benefit.

**Error Bank (Rev. 5) — MRR@10**

| System | Description | MRR@10 |
|---|---|---:|
| **S2** | Dense (Semantic Best) | 0.7399 |
| **S6** | Hybrid + Rerank | 0.8106 |
| **S7** | ComplianceGPT | 0.8323 |

**Conclusion:** The query rewrites (QUR) are successfully finding relevant documents that even the S6 pipeline missed. By adding these documents to the candidate pool before reranking, S7 gives the reranker a better set of options, allowing it to find the correct answer more often—**especially for the hardest queries**.

---

### Key Finding 3: **All Components are Vindicated.**

These results successfully validate **Dr. Sadjadi’s** proposed architecture (**QUR + Hybrid + Reranker**). The **7-system ablation** now tells a complete story:

- **S1 / S2** set the baselines.  
- **S3 / S4** proved that **fusing (RRF)** is the correct way to use QUR.  
- **S5 (Hybrid)** proved that fusing S1 and S2 is superior to either alone.  
- **S6 (Hybrid + Rerank)** proved that adding a reranker to S5’s high-recall list provides a massive precision boost.  
- **S7 (ComplianceGPT)** proved that adding the final QUR component on top of S6 provides the last, critical performance gain—resulting in the best system overall.

---

## 📌 Final Conclusion

**System 7 (ComplianceGPT)** is the **optimal and final** retrieval system.

It successfully integrates all components into a single pipeline, demonstrating **state-of-the-art performance** on all evaluation datasets. It has been validated as the most **robust and accurate** retriever for this task.
