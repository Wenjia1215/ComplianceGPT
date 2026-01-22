# Error Bank (MisRank>1) — Build Specification & Rationale (Updated)

> **Status:** current CSV = `error_bank_v1.csv` (labeled copy: `error_bank_v1_labeled.csv`)

## Context: Canonical Clause Store Rebuild

The underlying NIST SP 800-53 clause-level JSONL corpus was rebuilt to fix earlier JSON→JSONL interpretation issues.
The control content is intended to be equivalent, but the **JSONL structure and text formatting changed**, which can shift BM25 tokenization/lexical matches and therefore change which queries fall into the Error Bank.

## Why an Error Bank?

We maintain a focused *challenge set* of query–gold pairs where BM25 mis-ranks the correct (gold) clause.
This set enables:
- consistent regression testing (fixed hard cases),
- targeted debugging of failure modes,
- per-failure-mode reporting (e.g., MRR@10 by category).

## Source Data

- Baseline BM25 detailed results per revision:
  - `bm25_rev5_detailed_results.csv`
  - `bm25_rev4_detailed_results.csv`

## Inclusion Rules (this version)

- **MisRank policy:** include a row **iff `bm25_rank > 1`** (gold appears at rank 2 or lower).
- **Rank 0 / NotFound:** rows where gold is not found in the BM25 top‑K are kept (bm25_rank = 0) when present.
- **Scope:** combine qualifying rows from both Rev.5 (n=100) and Rev.4 (n=36) gold sets.
- **One failure reason per row:** label each row with exactly **one** `failure_category` from:
  - `Terminology Mismatch`
  - `Generic Phrasing`
  - `Semantic Gap`

## Current Dataset Snapshot (updated)

```
- rows: 39
- failure_category_counts: {'Generic Phrasing': 18, 'Terminology Mismatch': 18, 'Semantic Gap': 3}
```

## Column Schema (current)

| Column | Description |
|---|---|
| `id` | Stable row ID (string or int). |
| `question_id` | ID from the gold set. |
| `question` | The original question text. |
| `framework` | Framework name (e.g., `NIST_800-53`). |
| `version` | Revision: `rev5` or `rev4`. |
| `gold_control_id` | Gold/target control ID for the query. |
| `bm25_rank` | Rank position of the gold clause (0 = not found in top‑K). |
| `top_1_hit` | The control ID at rank‑1. |
| `retrieved_control_ids` | List string of retrieved control IDs in rank order. |
| `odp_required` | Optional flag indicating whether ODP handling is needed (if provided upstream). |
| `is_hit_at_1/5/10` | Convenience booleans derived from `bm25_rank`. |
| `system_meta` | Debug metadata (e.g., which system produced the row). |
| `failure_category` | Manual label: `Terminology Mismatch` / `Generic Phrasing` / `Semantic Gap`. |
| `label_rationale` | One-line justification for the label. |

## Notes for Reporting

When presenting results, group the Error Bank by `failure_category` and show per-mode improvements for each retrieval system.
