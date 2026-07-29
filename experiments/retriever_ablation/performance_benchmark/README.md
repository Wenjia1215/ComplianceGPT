---

# Retriever Performance Benchmark (S1–S7)

This artifact benchmarks the **retrieval-only engineering cost (latency)** for the S1–S7 retriever systems using the clause-level **NIST SP 800-53 CCS** and pre-generated **QUR rewrites**.

The stored `S7_gated` configuration uses a 0.01 rerank-skip margin. The recorded
RQ1 notebook and current checked S7 source use 0.10. These measurements are
therefore a diagnostic gate workload, not the exact latency of either reported
S7 implementation state.

---

## What this Benchmark Measures

**Included in per-query timing:**

* **Retrieval:** Query-time retrieval for each system (BM25, dense, hybrid RRF).
* **Reranking:** Cross-encoder reranking for S6 and S7 (only when the reranker is actually called).
* **S7 Pipeline:** Multi-variant retrieval (Original + `S7_MAX_REWRITES`), Fusion, and Optional Reranking.

**Excluded from per-query timing:**

* Loading the CCS JSONL corpus.
* Building indices (BM25, Dense) and embedding precomputation.
* Model downloads/initialization.
* Offline QUR generation (rewrites are loaded from CSV).

---

## Systems Benchmarked

| ID | System Description |
| --- | --- |
| **S1_bm25** | BM25 over control-level aggregated text (control_id groups clauses). |
| **S2_dense** | Bi-encoder dense retrieval + aggregate to control_id ranking. |
| **S5_hybrid_rrf** | Fuse S1 + S2 with Reciprocal Rank Fusion (RRF). |
| **S6_hybrid_rerank** | S5 candidate pool → Cross-encoder rerank → Top-10. |
| **S7_gated** | ComplianceGPT retrieval (Variants + Fusion + **Performance/Accuracy Gated Rerank**). |
| **S7_worst** | Same as S7 but **forces reranker usage** (Upper-bound latency). |

---

## Run Configuration

**Metadata**

* **Timestamp:** `2026-02-12T17:10:58Z`
* **Dataset:** `rev5` (20 queries, 5 repeats, 100 runs total)
* **Hyperparams:** `top_k=10`, `candidate_set_size=50`, `rrf_k=60`

**Models**

* **Dense:** `intfloat/e5-small-v2`
* **Reranker:** `BAAI/bge-reranker-base`

**S7 Specifics**

* **Rewrites:** `Max=3`, `Weight=0.25`, `Jaccard_Min=0.15`
* **Rerank Alpha:** `0.65`
* **Gates:**
* *Performance (Skip):* `Enabled=True`, `Min_Base_Margin=0.01`
* *Accuracy (Apply):* `Min_Margin=0.15`



---

## Results (Latency in Milliseconds)

*Note: Time is measured in ms. Lower is better.*

| System | Runs | Mean | P50 (Median) | P95 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- |
| **S1_bm25** | 100 | **8.69** | 8.65 | 12.18 | 4.67 | 15.29 |
| **S2_dense** | 100 | **13.71** | 12.55 | 18.91 | 11.77 | 22.65 |
| **S5_hybrid_rrf** | 100 | **29.82** | 30.02 | 36.52 | 21.18 | 40.29 |
| **S7_gated** | 100 | **150.62** | **87.12** | **729.90** | 73.93 | 735.60 |
| **S6_hybrid_rerank** | 100 | **629.37** | 640.86 | 681.13 | 519.13 | 687.05 |
| **S7_worst_always** | 100 | **732.40** | 729.56 | 757.34 | 715.93 | 764.71 |

> **Key Observation:**
> **S7_gated** latency is strongly bimodal.
> * **Fast Path (P50 ≈ 87ms):** Most runs skip the reranker.
> * **Slow Path (P95 ≈ 730ms):** A minority of runs trigger the reranker (comparable to S7_worst).
> * The **Mean (150ms)** reflects the weighted mix of these two paths.
> 
> 

---

## Gate Audit

This run records behavior for both the **Performance Gate** (Pre-Rerank) and **Accuracy Gate** (Post-Rerank).

### 1. Performance Gate (Skip Logic)

* **Reranker Called Rate:** `10%` (10/100 runs)
* **Skip Reason:** `base_confident` (90/100 runs)

### 2. Accuracy Gate (No-Harm Logic)

* **Rerank Applied Rate:** `0%` (0/100 runs)
* **Interpretation:** The reranker was called 10 times. In all 10 cases, it proposed a new Top-1, but the margin was too low (`< 0.15`), so the system reverted to the base ordering.

---

## Generated Files

1. `retriever_performance_benchmark_rev5_20q.csv` (Summary table)
2. `retriever_performance_benchmark_runs_rev5_20q.csv` (Per-run logs)
3. `retriever_performance_benchmark_table_rev5_20q.md` (Markdown summary)
4. `retriever_performance_benchmark_meta_rev5_20q.json` (Full config & audit stats)
