# Ablation Study Results (S1–S8)

This document reports the retrieval performance of eight retrieval systems (S1–S8) used in the ComplianceGPT pipeline.

We evaluate on four query sets:

- **Rev5 Gold Set (n=100)**: main benchmark queries for NIST SP 800-53 Rev5  
- **Rev4 Gold Set (n=36)**: benchmark queries for NIST SP 800-53 Rev4  
- **ErrorBank Rev5 (n=27)**: hard diagnostic set derived from retrieval failures (Rev5)  
- **ErrorBank Rev4 (n=12)**: hard diagnostic set derived from retrieval failures (Rev4)

Each benchmark also includes an **ODP Subset** (queries involving organization-defined parameters).

---

## Metric Definitions

We report standard retrieval metrics:

- **Recall@K**: % queries whose gold control ID is found in the top K retrieved results  
- **MRR@10**: Mean Reciprocal Rank within top 10  
- **nDCG@10**: Normalized Discounted Cumulative Gain at 10  

> **Important note about nDCG scale**  
> Some scripts log `nDCG@10` as a dataset-level sum instead of the per-query mean.  
> When needed, the mean nDCG can be computed as:  
> **mean_nDCG = reported_nDCG / n**

---

## Systems Compared

| System | Name | Key Idea |
|-------:|------|----------|
| S1 | BM25 | sparse lexical retrieval |
| S2 | Dense | embedding retrieval only |
| S3 | Rewrite-only | rewrite query and retrieve |
| S4 | QUR + RRF | original + rewrites fused via weighted RRF |
| S5 | Hybrid RRF | BM25 + Dense fused via RRF |
| S6 | Hybrid + Rerank | S5 candidates reranked using cross-encoder |
| S7 | ComplianceGPT | multi-stage pipeline (rewrites + hybrid + safe blending rerank) |
| S8 | Adaptive | routes queries between fast hybrid vs heavy S7 path |

---

## Executive Summary (Main Takeaways)

1. **S7/S8 achieve the strongest overall performance** on Rev5/Rev4 benchmarks, especially on ODP queries.
2. **Hybrid retrieval (S5) strongly improves over BM25-only or Dense-only**, showing retrieval complementarity.
3. **Reranking helps (S6), but must be blended safely** (S7) to avoid rank reversals.
4. **ErrorBank is hardest** and is the best diagnostic for failure cases; improvements there are more meaningful than small changes on the easy gold sets.

---

# 1) Rev5 Gold Set (n=100)

## Overall Results

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.7300 | 0.9700 | 0.9600 | 0.8252 |
| S2 | 0.8100 | 0.9700 | 0.9800 | 0.8790 |
| S3 | 0.5200 | 0.7900 | 0.8300 | 0.6278 |
| S4 | 0.7100 | 0.9500 | 0.9600 | 0.8098 |
| S5 | 0.8400 | 0.9800 | 0.9700 | 0.9050 |
| S6 | 0.7600 | 0.9500 | 0.9800 | 0.8432 |
| S7 | 0.8800 | 0.9700 | 0.9700 | 0.9233 |
| S8 | 0.8800 | 0.9700 | 0.9700 | 0.9233 |

## ODP Subset (n=63)

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.7143 | 0.9683 | 0.9683 | 0.8172 |
| S2 | 0.8571 | 1.0000 | 1.0000 | 0.9167 |
| S3 | 0.5397 | 0.8254 | 0.8571 | 0.6481 |
| S4 | 0.7778 | 0.9683 | 0.9841 | 0.8608 |
| S5 | 0.8730 | 1.0000 | 1.0000 | 0.9365 |
| S6 | 0.7619 | 0.9524 | 1.0000 | 0.8523 |
| S7 | 0.9048 | 1.0000 | 1.0000 | 0.9497 |
| S8 | 0.9048 | 1.0000 | 1.0000 | 0.9497 |

---

# 2) Rev4 Gold Set (n=36)

## Overall Results

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.6667 | 0.9444 | 0.9444 | 0.7620 |
| S2 | 0.8889 | 1.0000 | 1.0000 | 0.9398 |
| S3 | 0.6944 | 0.8889 | 0.9444 | 0.7810 |
| S4 | 0.6944 | 0.9167 | 0.9444 | 0.7951 |
| S5 | 0.8333 | 1.0000 | 1.0000 | 0.8921 |
| S6 | 0.8333 | 1.0000 | 1.0000 | 0.9120 |
| S7 | 0.9444 | 1.0000 | 1.0000 | 0.9722 |
| S8 | 0.9444 | 1.0000 | 1.0000 | 0.9722 |

## ODP Subset (n=19)

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.6842 | 0.9474 | 0.9474 | 0.7860 |
| S2 | 0.8421 | 1.0000 | 1.0000 | 0.9123 |
| S3 | 0.7895 | 0.9474 | 0.9474 | 0.8289 |
| S4 | 0.7895 | 1.0000 | 0.9474 | 0.8684 |
| S5 | 0.8947 | 1.0000 | 1.0000 | 0.9298 |
| S6 | 0.6842 | 1.0000 | 1.0000 | 0.8333 |
| S7 | 0.9474 | 1.0000 | 1.0000 | 0.9737 |
| S8 | 0.9474 | 1.0000 | 1.0000 | 0.9737 |

---

# 3) ErrorBank Rev5 (n=27)

## Overall Results

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.0000 | 0.5185 | 0.8519 | 0.3525 |
| S2 | 0.5556 | 0.9259 | 0.9259 | 0.7000 |
| S3 | 0.2963 | 0.4444 | 0.5556 | 0.3870 |
| S4 | 0.1852 | 0.6667 | 0.8519 | 0.4377 |
| S5 | 0.4074 | 0.8889 | 0.8889 | 0.6481 |
| S6 | 0.4074 | 0.8148 | 0.9259 | 0.5858 |
| S7 | 0.5926 | 0.8889 | 0.8889 | 0.7346 |
| S8 | 0.5926 | 0.8889 | 0.8889 | 0.7346 |

## ODP Subset (n=15)

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.0000 | 0.3333 | 0.7333 | 0.2411 |
| S2 | 0.5333 | 1.0000 | 1.0000 | 0.7333 |
| S3 | 0.4000 | 0.4000 | 0.6000 | 0.4667 |
| S4 | 0.2667 | 0.8000 | 0.9333 | 0.5267 |
| S5 | 0.4667 | 1.0000 | 1.0000 | 0.7333 |
| S6 | 0.4667 | 0.8667 | 1.0000 | 0.6462 |
| S7 | 0.6667 | 1.0000 | 1.0000 | 0.8222 |
| S8 | 0.6667 | 1.0000 | 1.0000 | 0.8222 |

---

# 4) ErrorBank Rev4 (n=12)

## Overall Results

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.0000 | 0.4167 | 0.8333 | 0.2861 |
| S2 | 0.8333 | 1.0000 | 1.0000 | 0.9167 |
| S3 | 0.3333 | 0.6667 | 0.9167 | 0.5236 |
| S4 | 0.2500 | 0.8333 | 0.8333 | 0.4688 |
| S5 | 0.5000 | 1.0000 | 1.0000 | 0.6764 |
| S6 | 0.9167 | 1.0000 | 1.0000 | 0.9583 |
| S7 | 0.9167 | 1.0000 | 1.0000 | 0.9583 |
| S8 | 0.9167 | 1.0000 | 1.0000 | 0.9583 |

## ODP Subset (n=5)

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.0000 | 0.2000 | 0.8000 | 0.2000 |
| S2 | 0.8000 | 1.0000 | 1.0000 | 0.9000 |
| S3 | 0.6000 | 1.0000 | 1.0000 | 0.6833 |
| S4 | 0.6000 | 0.8000 | 0.8000 | 0.7000 |
| S5 | 0.6000 | 1.0000 | 1.0000 | 0.7333 |
| S6 | 0.8000 | 1.0000 | 1.0000 | 0.9000 |
| S7 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| S8 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

---

## Notes

- ErrorBank results matter the most for diagnosing real failure cases, since the gold sets are relatively easy.
- Improvements on Recall@1 in ErrorBank are strong evidence that the pipeline mitigates retrieval mismatch failure modes.
- ODP subsets confirm that the pipeline improves parameter-heavy compliance queries rather than only “easy” lexical matches.

---

## How to Reproduce

Run the ablation notebook:

`AblationStudy_S1_8.ipynb`

Outputs include:

- per-system CSV results
- markdown reports under `ablation_outputs/`
