# Retriever Performance Benchmark (S1–S7)

This artifact benchmarks **retrieval-only engineering cost** (latency) for the S1–S7 retriever systems using the **clause-level NIST 800-53 CCS** and pre-generated **QUR rewrites**. It is intended to support a “cost of accuracy improvements” discussion (e.g., BM25 → Dense → Hybrid → Rerank → ComplianceGPT retrieval).

## What this benchmark measures

**Included in per-query timing**
- Query-time retrieval for each system (BM25, dense, hybrid RRF).
- Cross-encoder reranking for S6 and S7 (when applied).
- For S7: multi-variant retrieval using the original query + up to `S7_MAX_REWRITES` rewrites.

**Excluded from per-query timing**
- Loading the CCS JSONL corpus.
- Building BM25 and dense indices (including embedding precomputation).
- Model downloads / initialization (bi-encoder + cross-encoder).
- Offline QUR generation (rewrites are loaded from CSV).

## Systems benchmarked

- **S1_bm25**: BM25 over **control-level aggregated text** (control_id groups clauses).
- **S2_dense**: bi-encoder dense retrieval (clause index) + aggregate to control_id ranking.
- **S5_hybrid_rrf**: fuse S1+S2 with Reciprocal Rank Fusion (RRF).
- **S6_hybrid_rerank**: S5 candidate pool → cross-encoder rerank → top-10.
- **S7_gated**: ComplianceGPT retrieval (variants + fusion + safe-blend rerank **with gate**).
- **S7_worst_always_rerank**: same as S7 but gate disabled (forces rerank).

## Run configuration used for the attached results

- Dataset: `rev5`
- Queries: `NUM_QUERIES=20` unique query_ids from QUR CSV (first N by default)
- Repeats per query: `5`  
  → total runs per system = `100`
- Returned top-K: `10` (top-10 control_ids)
- Candidate pool size (pre-rerank): `CANDIDATE_SET_SIZE=50`
- RRF parameter: `RRF_K_DEFAULT=60`
- S7 variants: original + up to `S7_MAX_REWRITES=3` rewrites  
  (`S7_REWRITE_WEIGHT=0.25`, `S7_REWRITE_JACCARD_MIN=0.15`)
- Rerank blending: `S7_RERANK_ALPHA=0.65`
- S7 rerank gate threshold (typical): `S7_RERANK_APPLY_MIN_MARGIN_RATIO=0.15`
- S7 rerank gate threshold (worst-case): `S7_RERANK_APPLY_MIN_MARGIN_RATIO_WORST=0.0`
- Dense model: `intfloat/e5-small-v2`
- Reranker model: `BAAI/bge-reranker-base`

### Data sources (paths as configured)
- CCS Rev5 JSONL: `/content/drive/MyDrive/compliance_data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl`
- CCS Rev4 JSONL: `/content/drive/MyDrive/compliance_data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl`
- QUR Rev5 CSV: `/content/drive/MyDrive/compliance_outputs/outputs_qur/qur_rewrites_rev5.csv`
- QUR Rev4 CSV: `/content/drive/MyDrive/compliance_outputs/outputs_qur/qur_rewrites_rev4.csv`
- QUR Error Bank CSV: `/content/drive/MyDrive/compliance_outputs/outputs_qur/qur_rewrites_error_bank.csv`

> Note: Gold CSVs are **not used** for latency measurement in this benchmark; queries are taken from the QUR CSV’s `original_query`.

## Results (latency in milliseconds)

| system                 |   n_runs |   mean_ms |   p50_ms |   p95_ms |   min_ms |   max_ms |
|:-----------------------|---------:|----------:|---------:|---------:|---------:|---------:|
| S1_bm25                |      100 |    8.7071 |   8.2569 |  13.0373 |   5.3508 |  15.2887 |
| S2_dense               |      100 |   12.0503 |  11.6152 |  12.4965 |  11.0578 |  36.5362 |
| S5_hybrid_rrf          |      100 |   29.3672 |  28.1871 |  38.7187 |  22.6246 |  43.1543 |
| S6_hybrid_rerank       |      100 |  625.698  | 636.507  | 660.387  | 532.89   | 661.896  |
| S7_gated               |      100 |  702.682  | 713.54   | 738.654  | 594.102  | 747.001  |
| S7_worst_always_rerank |      100 |  706.717  | 713.795  | 741.559  | 595.081  | 755.273  |

S7 gated: rerank_applied_rate = 0.950 (95/100)


### Interpretation (high-level)
- **Reranking dominates latency**: S6/S7 are ~0.6–0.7s vs S1/S2/S5 in ~10–30ms.
- **S7 overhead over S6** reflects multi-variant retrieval + fusion on top of reranking.
- In this run, **S7_gated applied reranking in 95% of runs**, so S7_gated ≈ S7_worst.

## About `S7_RERANK_APPLY_MIN_MARGIN_RATIO` (the “gate”)

S7 uses a **no-harm rerank gate** to skip cross-encoder reranking when the system believes the base ranking is already confident.

- Higher threshold → **rerank applied less often** → typically faster S7.
- Lower threshold → **rerank applied more often** → typically slower S7.
- Setting the threshold to `0.0` forces **always rerank** (worst-case upper bound).

When reporting latency, it is recommended to report either:
- both **typical** (gated) and **worst-case** (always rerank), or
- typical latency **plus** `rerank_applied_rate`.

## Reproducibility tips
- Run a warmup query before timing (already included).
- For GPU timing, synchronize before/after (already included).
- If one wants an unbiased sample of queries, replace `head(NUM_QUERIES)` with a seeded random sample.
- Record runtime hardware (CPU/GPU) for the paper; in Colab, run `!nvidia-smi`.

## Files produced
- `retriever_performance_benchmark_rev5_20q.csv` — the latency table as CSV
- `retriever_performance_benchmark_table.md` — the same table in Markdown for copy/paste
- This README
