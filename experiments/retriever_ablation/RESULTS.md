# Ablation Study Results (S1–S7)

This document reports the frozen retrieval performance of seven systems (S1–S7). The S7 rows belong to the notebook-local implementation preserved with these outputs; current-source results are reported separately under `experiments/micro_ablations/`.

We evaluate on four query sets:

- **Rev5 Gold Set (n=100)**: main benchmark queries for NIST SP 800-53 Rev5  
- **Rev4 Gold Set (n=36)**: benchmark queries for NIST SP 800-53 Rev4  
- **ErrorBank Rev5 (n=24)**: hard diagnostic set derived from retrieval failures (Rev5)  
- **ErrorBank Rev4 (n=13)**: hard diagnostic set derived from retrieval failures (Rev4)

Each benchmark also includes an **ODP Subset** (queries involving organization-defined parameters).

---

## Metric Definitions

The evaluator uses one normalized gold control per question. It reports:

- **Recall@K**: historical field name for the proportion of queries whose one
  gold control ID is found in the top K retrieved results; this is a query hit
  rate, not set recall over all required clauses  
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

---

## Executive Summary (Main Takeaways)

1. **Frozen S7 leads the ablation ladder on the main Rev5/Rev4 gold sets and performs strongly on ODP subsets.**  
2. **Hybrid retrieval (S5) is competitive but not uniformly stronger than both single-channel baselines.** Dense S2 is stronger on several Rev4 measures.  
3. **Reranking (S6) is mixed**: it can help significantly on harder sets (e.g., ErrorBank-Rev4 overall) but may reduce Recall@1 versus pure hybrid on easier sets.  
4. **ErrorBank is a targeted diagnostic derived from BM25 failures.** It helps localize difficult cases but does not estimate failure prevalence or population performance.

---

# 1) Rev5 Gold Set (n=100)

## Overall Results

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.7600 | 0.9600 | 0.9800 | 0.8518 |
| S2 | 0.8400 | 1.0000 | 1.0000 | 0.9053 |
| S3 | 0.5100 | 0.7800 | 0.8600 | 0.6287 |
| S4 | 0.7800 | 0.9600 | 0.9800 | 0.8509 |
| S5 | 0.8900 | 0.9900 | 0.9900 | 0.9400 |
| S6 | 0.8000 | 0.9600 | 1.0000 | 0.8742 |
| S7 | 0.9000 | 0.9900 | 1.0000 | 0.9460 |

## ODP Subset (n=63)

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.7778 | 0.9683 | 0.9841 | 0.8644 |
| S2 | 0.8254 | 1.0000 | 1.0000 | 0.8960 |
| S3 | 0.5238 | 0.8254 | 0.8889 | 0.6532 |
| S4 | 0.8413 | 0.9683 | 0.9841 | 0.8981 |
| S5 | 0.9048 | 1.0000 | 1.0000 | 0.9524 |
| S6 | 0.7619 | 0.9524 | 1.0000 | 0.8531 |
| S7 | 0.9206 | 1.0000 | 1.0000 | 0.9603 |

---

# 2) Rev4 Gold Set (n=36)

## Overall Results

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.6389 | 0.9167 | 0.9167 | 0.7454 |
| S2 | 0.8889 | 1.0000 | 1.0000 | 0.9398 |
| S3 | 0.5833 | 0.9167 | 0.9167 | 0.7245 |
| S4 | 0.6944 | 0.9167 | 0.9167 | 0.7880 |
| S5 | 0.8056 | 0.9722 | 1.0000 | 0.8790 |
| S6 | 0.8056 | 1.0000 | 1.0000 | 0.8981 |
| S7 | 0.9167 | 1.0000 | 1.0000 | 0.9583 |

## ODP Subset (n=19)

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.7368 | 0.9474 | 0.9474 | 0.8246 |
| S2 | 0.8421 | 1.0000 | 1.0000 | 0.9123 |
| S3 | 0.7368 | 0.8947 | 0.8947 | 0.7939 |
| S4 | 0.8421 | 0.9474 | 0.9474 | 0.8860 |
| S5 | 0.8947 | 0.9474 | 1.0000 | 0.9286 |
| S6 | 0.6316 | 1.0000 | 1.0000 | 0.8070 |
| S7 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

---

# 3) ErrorBank Rev5 (n=24)

## Overall Results

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.0000 | 0.8333 | 0.9167 | 0.3827 |
| S2 | 0.6667 | 1.0000 | 1.0000 | 0.7896 |
| S3 | 0.2083 | 0.5417 | 0.6667 | 0.3667 |
| S4 | 0.2917 | 0.8750 | 0.9167 | 0.5132 |
| S5 | 0.5417 | 0.9583 | 0.9583 | 0.7500 |
| S6 | 0.5417 | 0.8333 | 1.0000 | 0.6807 |
| S7 | 0.7083 | 0.9583 | 1.0000 | 0.8375 |

## ODP Subset (n=14)

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.0000 | 0.8571 | 0.9286 | 0.3899 |
| S2 | 0.7143 | 1.0000 | 1.0000 | 0.8000 |
| S3 | 0.2143 | 0.5714 | 0.7143 | 0.3786 |
| S4 | 0.4286 | 0.8571 | 0.9286 | 0.6131 |
| S5 | 0.5714 | 1.0000 | 1.0000 | 0.7857 |
| S6 | 0.5714 | 0.7857 | 1.0000 | 0.6900 |
| S7 | 0.7857 | 1.0000 | 1.0000 | 0.8929 |

---

# 4) ErrorBank Rev4 (n=13)

## Overall Results

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.0000 | 0.7692 | 0.7692 | 0.2949 |
| S2 | 0.8462 | 1.0000 | 1.0000 | 0.9231 |
| S3 | 0.0769 | 0.7692 | 0.7692 | 0.3526 |
| S4 | 0.1538 | 0.7692 | 0.7692 | 0.4128 |
| S5 | 0.4615 | 0.9231 | 1.0000 | 0.6648 |
| S6 | 0.8462 | 1.0000 | 1.0000 | 0.9231 |
| S7 | 0.7692 | 1.0000 | 1.0000 | 0.8846 |

## ODP Subset (n=5)

| System | Recall@1 | Recall@5 | Recall@10 | MRR@10 |
|-------:|---------:|---------:|----------:|-------:|
| S1 | 0.0000 | 0.8000 | 0.8000 | 0.3333 |
| S2 | 0.8000 | 1.0000 | 1.0000 | 0.9000 |
| S3 | 0.2000 | 0.6000 | 0.6000 | 0.3167 |
| S4 | 0.4000 | 0.8000 | 0.8000 | 0.5667 |
| S5 | 0.6000 | 0.8000 | 1.0000 | 0.7286 |
| S6 | 0.6000 | 1.0000 | 1.0000 | 0.8000 |
| S7 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

---

## Notes

- ErrorBank results support failure analysis within a selected set of known hard
  cases; they do not support population-level inference.
- Early-rank changes in ErrorBank are descriptive evidence about those cases,
  not proof that a retrieval design generally eliminates a failure mode.
- ODP-subset metrics measure governing-control rank for questions whose gold
  material contains ODPs. They do not measure exact parameter recovery or ODP
  policy correctness.

---

## How to Reproduce

Run the ablation notebook:

`AblationStudy_S1_7.ipynb`

Outputs include:

- per-system CSV results
- markdown reports under `ablation_outputs/`
