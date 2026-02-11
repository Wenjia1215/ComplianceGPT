# Retriever Performance Benchmark (S1–S7)

This artifact benchmarks **retrieval-only engineering cost** (latency) for the S1–S7 retriever systems using the **clause-level NIST 800-53 CCS** and pre-generated **QUR rewrites**.

## What this benchmark measures

**Included in per-query timing**
- Query-time retrieval for each system (BM25, dense, hybrid RRF).
- Cross-encoder reranking for S6 and S7 (when the reranker is called).
- For S7: multi-variant retrieval using the original query + up to `S7_MAX_REWRITES` rewrites, then fusion and (optional) reranking.

**Excluded from per-query timing**
- Loading the CCS JSONL corpus.
- Building BM25 and dense indices (including embedding precomputation).
- Model downloads / initialization (bi-encoder + cross-encoder).
- Offline QUR generation (rewrites are loaded from CSV).

## Systems benchmarked

- **S1_bm25**: BM25 over control-level aggregated text (control_id groups clauses).
- **S2_dense**: bi-encoder dense retrieval (clause index) + aggregate to control_id ranking.
- **S5_hybrid_rrf**: fuse S1+S2 with Reciprocal Rank Fusion (RRF).
- **S6_hybrid_rerank**: S5 candidate pool → cross-encoder rerank → top-10.
- **S7_gated**: ComplianceGPT retrieval (variants + fusion + gated rerank).
- **S7_worst_always_rerank**: same as S7 but forces reranker usage and always applies reranked ordering (upper-bound latency).

## Run configuration used for the attached results

This README describes the run whose meta file reports:
- `timestamp_iso = 2026-02-11T03:28:00.718126Z`w
- `dataset = rev5`, `num_queries = 20`, `repeats_per_query = 5` (100 runs per system)
- `top_k = 10`, `candidate_set_size = 50`, `rrf_k_default = 60`
- Dense model: `intfloat/e5-small-v2`
- Reranker model: `BAAI/bge-reranker-base`
- S7 rewrites: `S7_MAX_REWRITES = 3`, `S7_REWRITE_WEIGHT = 0.25`, `S7_REWRITE_JACCARD_MIN = 0.15`
- S7 rerank blending: `S7_RERANK_ALPHA = 0.65`
- **Accuracy gate (no-harm apply gate):** `S7_RERANK_APPLY_MIN_MARGIN_RATIO = 0.15`
- **Performance gate (pre-rerank skip gate):**
  - `S7_RERANK_SKIP_ENABLED = true`
  - `S7_RERANK_SKIP_MIN_BASE_MARGIN_RATIO = 0.10`
  - `S7_RERANK_SKIP_REQUIRE_TOP1_AGREEMENT = false`

## Results (latency in milliseconds)

| system                 |   n_runs |   mean_ms |    p50_ms |   p95_ms |    min_ms |   max_ms |
|:-----------------------|---------:|----------:|----------:|---------:|----------:|---------:|
| S1_bm25                |      100 |   8.65864 |   8.37988 |  12.148  |   4.26301 |  14.547  |
| S2_dense               |      100 |  13.0646  |  12.3125  |  17.3595 |  11.6571  |  19.0787 |
| S5_hybrid_rrf          |      100 |  30.0895  |  29.7993  |  36.8857 |  21.8507  |  38.0392 |
| S7_gated               |      100 | 411.1     | 585.434   | 716.157  |  78.4888  | 762.257  |
| S6_hybrid_rerank       |      100 | 600.595   | 626.218   | 646.635  | 497.723   | 659.571  |
| S7_worst_always_rerank |      100 | 679.135   | 690.307   | 730.836  | 545.586   | 746.833  |

## Gate audit (report both performance + accuracy behavior)

This run includes two distinct “gates,” and we record both:

1) **Performance gate (pre-rerank skip)**
- `s7_reranker_called_rate = 0.55` (55/100 runs called the reranker)
- `s7_skip_reason_counts = {"base_confident": 45}`

2) **Accuracy gate (post-rerank apply / no-harm)**
- `s7_rerank_applied_rate = 0.50` (50/100 runs applied the reranked ordering)

## Interpreting the S7 numbers

- S7’s latency is bimodal: ~45% of runs skip the reranker (fast path), ~55% call the reranker (slow path). This is why the mean drops substantially while the median (`p50`) is still in the rerank regime.
- Mean latency improvement from worst-case to gated:
  - `679.135 ms - 411.1 ms = 268.035 ms` (~39.47% reduction vs worst-case S7).
- Note: always compare gated S7 against both **S6** (always reranks) and **S7_worst** (upper bound), because the reranker call rate changes with the skip threshold.

## Files produced

- `retriever_performance_benchmark_rev5_20q.csv` — summary table as CSV (per system).
- `retriever_performance_benchmark_runs_rev5_20q.csv` — per-run logs (for debugging tail latency + gate behavior).
- `retriever_performance_benchmark_table_rev5_20q.md` — the same summary table in Markdown.
- `retriever_performance_benchmark_meta_rev5_20q.json` — run config + gate audit stats (recommended to cite in the paper).
- This README
