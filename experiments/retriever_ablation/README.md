# ComplianceGPT Retrieval Ablation Study (S1–S8)

This repository contains the retrieval ablation study for ComplianceGPT.
We evaluate 8 retrieval systems (S1–S8) on NIST SP 800-53 Rev.5 and Rev.4
using gold-standard QA sets, an ODP subset, and a diagnostic Error Bank.

The goal is to measure retrieval reliability (Recall@K / MRR / nDCG) and
justify the final ComplianceGPT retriever design.

---

## 1) Datasets / Inputs

All systems run on the same Canonical Clause Store (CCS):
- `NIST_SP-800-53_rev5_catalog.jsonl`
- `NIST_SP-800-53_rev4_catalog.jsonl`

Gold evaluation sets:
- `nist_sp800-53_rev5_gold-set_100q.csv`
- `nist_sp800-53_rev4_gold-set_36q.csv`

Diagnostic set:
- `error_bank_v1.csv` (derived from baseline failures; used to stress-test semantic mismatch cases)

Query rewrite sets (used by S3/S4/S7/S8):
- `qur_rewrites_rev5.csv`
- `qur_rewrites_rev4.csv`
- `qur_rewrites_error_bank.csv`

---

## 2) Systems Evaluated (S1–S8)

| System | Name | Core Idea |
|---|---|---|
| S1 | BM25 baseline | Keyword-based lexical retrieval baseline |
| S2 | Dense baseline | Semantic retrieval using embeddings |
| S3 | Rewrite-only | Replace query with rewrite, then BM25 (tests lexical mismatch) |
| S4 | QUR-RRF | BM25 over {original + rewrites}, fused with RRF |
| S5 | Hybrid RRF | Fuse BM25 + Dense using RRF |
| S6 | Hybrid + Rerank | Rerank S5 candidates using a cross-encoder |
| S7 | ComplianceGPT Retriever | Super-hybrid: (QUR-RRF + Dense) → RRF → Rerank |
| S8 | Adaptive Routing | FAST path (S5) vs HEAVY path (S7), based on confidence gating |

---

## 3) How to Run (Reproducibility)

This experiment is designed to run in a single notebook session so all models
(BM25, Dense index, Reranker) can be reused across systems.

1. Open the main notebook:
   - `AblationStudy_S1_8.ipynb`
2. Mount Google Drive.
3. In the CONFIG cell, set correct file paths for CCS + gold sets.
4. Run all cells from top to bottom.
5. The notebook will save per-system result CSVs and per-system report markdown files.

---

## 4) Outputs

Outputs are written under:

`/content/drive/MyDrive/ablation_outputs/`

Each system has its own folder:
- `system_1_bm25/`
- `system_2_dense/`
- `system_3_rewrite_only/`
- `system_4_qur_rrf/`
- `system_5_hybrid_rrf/`
- `system_6_hybrid_rerank/`
- `system_7_compliance_gpt/`
- `system_8_adaptive/`

Each folder contains:
- `*_rev5_results.csv`
- `*_rev4_results.csv`
- `*_error_bank_rev5_results.csv`
- `*_error_bank_rev4_results.csv`
- `*_report.md` (summary tables)

---

## 5) Results Summary

For consolidated tables and the narrative of what each system proves, see:
- `RESULTS.md`; 
For Design Rationale, see: 
- `SYSTEMS.md`
