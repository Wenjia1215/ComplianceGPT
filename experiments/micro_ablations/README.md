# README: Validation Study for S4 and S7 Retrieval Architectures

## 1. Objective

This notebook provides a focused validation study for two key architectural decisions within the S4 (QUR-RRF) and S7 (ComplianceGPT) retrieval pipelines.

Following a main S1–S7 ablation study which identified S7 as the state-of-the-art retriever, this experiment performs a **micro-ablation** to rigorously justify its specific component design over simpler, plausible alternatives.

The study tests two primary hypotheses:

1. **S7 Reranker Input:**  
   Is the optimal input for the final reranking stage the original user query or the best AI-generated rewrite?

2. **S4 Fusion Strategy:**  
   Is the "full fusion" of all AI-generated rewrites superior to a simpler fusion of only the single best rewrite?


## 2. Hypotheses Under Test

To understand the hypotheses, it's crucial to understand the technical design of the S7 and S4 pipelines.

### Hypothesis 1 (S7 Reranker Input)

The S7 (ComplianceGPT) pipeline is a **two-stage system** designed for maximum accuracy. It combines:

- a fast **high-recall retrieval** stage, and  
- a slow **high-precision reranking** stage.

#### Stage 1: High-Recall Retrieval (The "Net")

The goal of this stage is to quickly search the entire 1,000+ document database and find a **Top 50** list of potential candidates. It casts a wide net by fusing three different search results using Reciprocal Rank Fusion (RRF):

- **BM25(Q_orig):** A lexical search using the original query.  
- **BM25(Q_all_rewrites):** Lexical searches using all AI-generated rewrites.  
- **Dense(Q_orig):** A semantic (Bi-Encoder) search using the original query.

#### Stage 2: High-Precision Reranking (The "Judge")

This stage takes the Top 50 candidates from Stage 1 and meticulously re-scores them to find the single best answer. It uses a powerful Cross-Encoder AI model, which is slow but highly accurate.

The critical design choice is **what to feed this “Judge” as the query**:

- **Baseline (S7 Standard):**  
  The reranker is fed the original user query `Q_orig`.  
  - Assumption: `Q_orig` is the truest representation of user intent, and the Cross-Encoder is powerful enough to understand it, even if it is lexically imperfect.

- **Alternative (Ablation a):**  
  The reranker is fed the best AI-generated rewrite `Q_best_rewrite`.  
  - Assumption: this "cleaner," more explicit query would be a better input for the Judge, leading to a more accurate final ranking.

This experiment tests **which query input for Stage 2 yields higher precision**.

---

### Hypothesis 2 (S4 Fusion Strategy)

The S4 (QUR-RRF) system is a **simpler, single-stage retriever**. It only uses lexical search (BM25) and fuses the results from the original query and its AI-generated rewrites.

- **Baseline (S4 Standard):**  
  The system fuses the results from the original query + **all generated rewrites** (`Q_orig + Q_all_rewrites`).  
  - Assumption: this "high recall" approach provides the richest set of candidates for RRF to find the correct answer, even if some rewrites are noisy.

- **Alternative (Ablation b):**  
  The system fuses only the original query + the **single best rewrite** (`Q_orig + Q_best_rewrite`).  
  - Assumption: this is a "higher precision," lower-noise input that avoids poor-quality rewrites, potentially leading to a better final ranking.

This experiment tests whether the **"full fusion" strategy** is measurably superior to the **"best-only" fusion**.


## 3. Methodology

To ensure a fair and reproducible comparison, this notebook implements a self-contained `ComplianceGPTRetriever` class. This class encapsulates:

- all necessary models (BM25, Bi-Encoder, Cross-Encoder), and  
- all required data (corpora, QUR spreadsheets).

The core `retrieve()` method accepts a **mode flag** to isolate and test each hypothesis against the same gold-standard queries (Rev. 5, Rev. 4, and Error Bank).

### Retrieval Mode Definitions

**Standard S7 (Baseline for H1):**

- **Stage 1 (RRF):**  
  Fuses `BM25(Q_orig)`, `BM25(Q_all_rewrites)`, and `Dense(Q_orig)` to get the Top 50 candidates.
- **Stage 2 (Rerank):**  
  Feeds `(Q_orig, Candidate)` pairs into the Cross-Encoder for final scoring.

**Ablation (a) — Test for H1:**

- **Stage 1 (RRF):**  
  Identical to Standard S7: fuse `BM25(Q_orig)`, `BM25(Q_all_rewrites)`, and `Dense(Q_orig)` to get the Top 50 candidates.
- **Stage 2 (Rerank):**  
  Feeds `(Q_best_rewrite, Candidate)` pairs into the Cross-Encoder.  
  - The only change from Standard S7 is the reranker input.

---

**Standard S4 (Baseline for H2):**

- **Stage 1 (RRF):**  
  Fuses `BM25(Q_orig)` and `BM25(Q_all_rewrites)`.
- **Stage 2 (Rerank):**  
  None (single-stage retriever).

**Ablation (b) — Test for H2:**

- **Stage 1 (RRF):**  
  Fuses `BM25(Q_orig)` and `BM25(Q_best_rewrite)`.  
  - The only change from Standard S4 is the subset of rewrites used.
- **Stage 2 (Rerank):**  
  None.


## 4. Results & Conclusions

The results of the experiment, also saved in  
`Comparison_Report-MicroAblation_S4_S7_Validation.md`, confirm both original hypotheses.

---

### Conclusion 1: Reranking with the Original Query is Decisively Superior

The S7 (Standard) pipeline **significantly outperformed** the S7a (Rerank Best) ablation on all datasets. This validates the design choice that the original, unfiltered user query is the **most valuable and reliable signal** for the final, precision-focused reranking stage.

Using an AI-generated rewrite—even the "best" one—introduces an interpretation risk that measurably degrades performance.

#### S7 (Standard) vs. S7a (Rerank Best) — MRR@10

| Dataset              | S7 (Standard) MRR@10 | S7a (Rerank Best) MRR@10 |
|----------------------|----------------------:|--------------------------:|
| Rev. 5 Overall       |                0.9448 |                    0.8177 |
| Rev. 4 Overall       |                0.9444 |                    0.8449 |
| Error Bank (Rev. 5)  |                0.8323 |                    0.6982 |
| Error Bank (Rev. 4)  |                0.8182 |                    0.7879 |

---

### Conclusion 2: Full-Rewrite Fusion is More Robust and Effective

The S4 (Standard) pipeline, which fuses **all** generated rewrites, outperformed the S4b (RRF Best) ablation on the primary Rev. 5 and Rev. 4 datasets. This demonstrates that the high recall generated by the full set of rewrites provides a more **robust candidate pool** for RRF to surface the correct answer.

The simpler "best-only" approach, while competitive, is less effective overall. This justifies the **"superhybrid" RRF design** used in Stage 1 of the S7 pipeline.

#### S4 (Standard) vs. S4b (RRF Best) — MRR@10

| Dataset              | S4 (Standard) MRR@10 | S4b (RRF Best) MRR@10 |
|----------------------|----------------------:|-----------------------:|
| Rev. 5 Overall       |                0.7802 |                 0.7674 |
| Rev. 4 Overall       |                0.8114 |                 0.7782 |
| Error Bank (Rev. 5)  |                0.4493 |                 0.3968 |
| Error Bank (Rev. 4)  |                0.5586 |                 0.5833 |

> **Note:** The S4b ablation’s minor win on the 11-query Rev. 4 Error Bank is not considered significant enough to outweigh its losses on the larger, primary datasets.

