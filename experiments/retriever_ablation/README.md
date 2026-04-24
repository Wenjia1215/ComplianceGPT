# ComplianceGPT Retrieval Ablation Study (S1–S7)

This directory contains the frozen retrieval ablation study for ComplianceGPT. The active dissertation evaluation compares seven retrieval systems (S1–S7) on NIST SP 800-53 Rev.5 and Rev.4 using gold-standard QA sets, ODP subsets, and the diagnostic ErrorBank.

The goal is to measure retrieval reliability using Recall@K, MRR@10, and nDCG@10, and to justify S7 as the final ComplianceGPT retriever design used by the answerer pipeline.

---

## 1) Datasets / Inputs

All systems run on the same Canonical Clause Store (CCS):

- `NIST_SP-800-53_rev5_catalog.jsonl`
- `NIST_SP-800-53_rev4_catalog.jsonl`

Gold evaluation sets:

- `nist_sp800-53_rev5_gold-set_100q.csv`
- `nist_sp800-53_rev4_gold-set_36q.csv`

Diagnostic set:

- `error_bank_v1.csv` — derived from baseline failures and used to stress-test semantic mismatch cases.

Query rewrite sets used by S3, S4, and S7:

- `qur_rewrites_rev5.csv`
- `qur_rewrites_rev4.csv`
- `qur_rewrites_error_bank.csv`

---

## 2) Systems Evaluated (S1–S7)

| System | Name | Core Idea |
|---|---|---|
| S1 | BM25 baseline | Keyword-based lexical retrieval baseline |
| S2 | Dense baseline | Semantic retrieval using embeddings |
| S3 | Rewrite-only | Replace query with rewrite, then BM25 |
| S4 | QUR-RRF | BM25 over original query plus rewrites, fused with RRF |
| S5 | Hybrid RRF | Fuse BM25 and dense retrieval using RRF |
| S6 | Hybrid + Rerank | Rerank S5 candidates using a cross-encoder |
| S7 | ComplianceGPT Retriever | Filtered rewrites plus hybrid ranking stack plus safe reranking and clause extraction |

---

## 3) How to Run

This experiment is designed to run in a single notebook session so BM25, dense indexes, and reranker resources can be reused across systems.

1. Open the main notebook:
   - `AblationStudy_S1_7_clean.ipynb`
2. Mount Google Drive.
3. In the configuration cell, set the correct file paths for CCS, gold sets, ErrorBank, and QUR rewrite files.
4. Run all cells from top to bottom.
5. The notebook saves per-system result CSVs and per-system report markdown files.

---

## 4) Outputs

Outputs are written under:

```text
/content/drive/MyDrive/ComplianceGPT_v2/experiments/retriever_ablation/ablation_outputs
```

Each active system has its own folder:

- `system_1_bm25/`
- `system_2_dense/`
- `system_3_rewrite_only/`
- `system_4_qur_rrf/`
- `system_5_hybrid_rrf/`
- `system_6_hybrid_rerank/`
- `system_7_compliance_gpt/`

Each folder contains:

- `*_rev5_results.csv`
- `*_rev4_results.csv`
- `*_error_bank_rev5_results.csv`
- `*_error_bank_rev4_results.csv`
- `*_report.md`

---

## 5) Results Summary

For consolidated tables and result interpretation, see:

- `RESULTS.md`

For system design rationale, see:

- `SYSTEMS.md`
