# Error Bank by Failure Mode: Retrieval Analysis (Updated)

**Date:** January 21, 2026  
**Status:** Needs refresh after JSONL rebuild  
**Author:** Wen  

---

## 1. Purpose

This document summarizes retrieval performance **by failure mode** on the curated Error Bank.
The Error Bank is defined as queries where **BM25 mis‑ranks the gold clause (bm25_rank != 1)**.

## 2. Current Error Bank Snapshot

- rows: 39
- failure_category_counts: {'Generic Phrasing': 18, 'Terminology Mismatch': 18, 'Semantic Gap': 3}

## 3. What changed?

The clause-level Canonical Clause Store (JSONL) was rebuilt (same intended control content, different JSONL structure/text).
Because BM25 is lexical, this can shift rankings and therefore change Error Bank membership and per-mode counts.

## 4. Next step to regenerate the pivot table

To reproduce the original “MRR@10 by failure mode” table (S1..S7, etc.), re-run the same analysis script/notebook you used for:
- `bm25_rev5_detailed_results.csv`, `bm25_rev4_detailed_results.csv`
- plus each system’s detailed results

Then compute MRR@10 restricted to `error_bank_v1_labeled.csv`, grouped by `failure_category`.

(We intentionally do **not** include a stale pivot table here.)
