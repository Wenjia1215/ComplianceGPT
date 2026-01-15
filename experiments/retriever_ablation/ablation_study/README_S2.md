# README: System 2 — Dense Retriever (e5-small-v2)

*(Notebook: `AblationStudy_S1-7.ipynb`)*

## 1. Overview

This document describes **System 2 (Dense Retriever)**, the second phase of the ComplianceGPT retrieval experiments. This system replaces the lexical (keyword-based) BM25 retriever from System 1 with a modern, semantic (meaning-based) dense retriever.

**Primary purposes:**

- **Establish semantic performance:** Measure the effectiveness of a state-of-the-art dense embedding model on the NIST SP 800-53 (Rev. 5 and Rev. 4) gold-standard query sets.
- **Identify complementary strengths:** Compare performance directly against the System 1 (BM25) baseline to understand differences between lexical and semantic search for this task.
- **Analyze failures:** Evaluate against the **Error Bank** (queries that S1 failed on) to test whether a semantic approach can resolve lexical failures.

**Model:** `intfloat/e5-small-v2` — a high-performing, efficient sentence-transformer model.

---

## 2. Methodology & Design Rationale

This section explains what was built and why specific design choices were made.

### A. Embedding Model: `intfloat/e5-small-v2`

- **What:** The `intfloat/e5-small-v2` model from Hugging Face was used. This is a **384‑dimension** sentence‑embedding model.
- **Why:** The **E5** family is state-of-the-art for semantic similarity tasks, trained on diverse data to understand query meaning even with different wording. The **small** variant balances performance and efficiency (speed/VRAM), ideal for this experiment.
- **Implementation:** As required by E5, all **queries** are prefixed with `query: ` and all **documents** with `passage: ` before encoding.

### B. Indexing Engine: FAISS

- **What:** `faiss.IndexFlatIP` is used to build the vector index.
- **Why:** **FAISS** is the industry standard for high-speed vector search. `IndexFlatIP` (inner product) was chosen because:  
  1) E5 outputs **normalized embeddings** (vector norm ≈ 1).  
  2) For normalized vectors, **Inner Product ≡ Cosine Similarity**, the standard metric for semantic similarity.

### C. Document Processing (**Critical Fix**)

- **What:** To ensure a fair, apples‑to‑apples comparison with System 1, S2 **reuses** the **same document parser**: the `load_corpus_jsonl` + `extract_text_from_record` path from S1.
- **Why:** An early S2 bug (`extract_text_from_record_S2`) parsed only control IDs, producing a broken index.
- **The Fix:** By reusing S1’s corpus loader, both S1 (BM25) and S2 (Dense) index **identical text content** per control, isolating the variable under test: **lexical vs. semantic retrieval**.

---

## 3. Workflow

S2 code is appended to the S1 notebook and relies on S1 helper functions (e.g., `load_corpus_jsonl`, `display_summary_report`).

1. **Run System 1:** Execute all S1 cells first.
2. **Install S2 Dependencies:** Run the `pip install` cell to get `sentence-transformers` and `faiss-cpu`.
3. **Run S2 MAIN Cell:** The final cell (`EZyz0vGJ_k4C`) executes the S2 workflow:
   - Loads Rev. 5 & Rev. 4 corpora using the S1 parser.
   - Builds two separate `e5-small-v2` FAISS indexes in memory.
   - Loads the Rev. 5, Rev. 4, and Error Bank gold sets.
   - Runs evaluations for all datasets.
   - Prints final summary reports.
   - Saves all S2 outputs to `/ablation_outputs/system_2/`.

---

## 4. Results & Analysis

The performance of System 2 reveals critical insights into the nature of compliance queries.

### A. Main Gold Set Performance (S1 vs. S2)

This table compares the baseline performance (**Recall@1**) on the standard gold sets.

| System | Metric | Rev. 5 (100q) | Rev. 4 (36q) |
| :--- | :--- | ---: | ---: |
| S1 (BM25) | Recall@1 | 0.7600 | 0.6111 |
| S2 (Dense) | Recall@1 | 0.7500 | 0.7500 |

**Analysis**
- **Rev. 5:** Dense (0.7500) ≈ BM25 (0.7600) ⇒ queries are largely answerable via strong keyword matching; semantic-only adds little.
- **Rev. 4:** Dense (0.7500) ≫ BM25 (0.6111) ⇒ Rev. 4 queries are more **semantic** (phrasing/synonyms differ from source text), where dense excels.

### B. Error Bank Analysis (S1 vs. S2)

The Error Bank contains only queries that S1 (BM25) **failed** (Recall@1 = 0.00).

| System | Metric | Error Bank (Rev. 5) | Error Bank (Rev. 4) |
| :--- | :--- | ---: | ---: |
| S1 (BM25) | Recall@1 | 0.0000 | 0.0000 |
| S2 (Dense) | Recall@1 | 0.5652 | 0.6364 |

**Analysis**
- **“Aha!” moment:** S2 correctly answers **56%+ (Rev. 5)** and **63%+ (Rev. 4)** of queries that S1 completely missed.
- **Complementarity:** BM25 fails when wording diverges; Dense succeeds by matching **meaning** (semantics) rather than exact **words** (lexicals).

### C. Key Finding: Complementary Failures

- **S2 Overall (Rev. 5):** `Recall@10 = 0.9900` — S2 missed exactly **one** query in Top‑10.
- **S2 Error Bank (Rev. 5):** `Recall@10 = 1.0000` — S2 retrieved **all** S1‑failure queries in Top‑10.

**Conclusion:** The single S2 miss **was not** in the Error Bank, implying it’s a query that **S1 got right**. This demonstrates **complementary failure modes**: some queries are “easy” for BM25 (keyword‑anchored) but “hard” for Dense, and vice‑versa.

### D. Overall Conclusion

- **S1 (BM25):** Slightly stronger on Rev. 5; fails on semantic queries.
- **S2 (Dense):** Stronger on Rev. 4; fixes most S1 failures; can miss keyword‑anchored cases.

**Implication:** The results demonstrate that S1 and S2 have **complementary strengths**. Neither system is a clear winner across all datasets. This strongly motivates the need for a **Hybrid System (System 5)** that fuses BM25 and Dense, leveraging both lexical and semantic strengths. The failure of S1 on the Error Bank also motivates separate experiments (S3, S4) to investigate if query rewriting can address these lexical gaps.

---

## 5. Outputs

All artifacts are saved to:  
`/content/drive/MyDrive/ablation_outputs/system_2/`

- `S2_dense_rev5_results.csv` — Per‑query results for the 100 Rev. 5 questions.
- `S2_dense_rev4_results.csv` — Per‑query results for the 36 Rev. 4 questions.
- `S2_dense_report.md` — Markdown file containing the four summary tables.
- `S2_dense_error_bank_rev5_results.csv` — Detailed results for the Rev. 5 Error Bank.
- `S2_dense_error_bank_rev4_results.csv` — Detailed results for the Rev. 4 Error Bank.
