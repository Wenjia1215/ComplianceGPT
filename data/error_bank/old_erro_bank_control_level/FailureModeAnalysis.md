# Error Bank by Failure Mode: Retrieval Analysis

**Date:** November 12, 2025
**Status:** Complete
**Author:** Wen

---

## 1. Purpose

This document provides a detailed analysis of retrieval system performance against a curated **Error Bank** of difficult queries.

The goal is to **show where each component helps** by generating a pivot table of retrieval performance (**MRR@10**) for 5 system against three specific failure modes.

This analysis uses the **re-categorized** `error_bank_v1.csv`, which distributes the **34** failed queries across all three failure categories.

---

## 2. Data Source Summary

* **Master File:** `/content/drive/MyDrive/compliance_data/error_bank/error_bank_v1.csv`
* **Total Queries Analyzed:** 34

**Failure Category Counts**

| Failure Category     | Count |
| -------------------- | ----: |
| Generic Phrasing     |    20 |
| Terminology Mismatch |    13 |
| Semantic Gap         |     1 |

---

## 3. Final Pivot Table (MRR@10 by Failure Mode)

This table shows the **Mean Reciprocal Rank (MRR@10)** for each of the 5 systems against the 3 failure categories.

| failure_category     | S1_MRR | S2_MRR | S5_MRR | S6_MRR | S7_MRR |
| -------------------- | -----: | -----: | -----: | -----: | -----: |
| Generic Phrasing     | 0.3744 | 0.7896 | 0.6642 | 0.8500 | 0.8500 |
| Semantic Gap         | 0.5000 | 0.5000 | 0.5000 | 0.5000 | 0.5000 |
| Terminology Mismatch | 0.3996 | 0.7225 | 0.7115 | 0.7802 | 0.8187 |

---

## 4. Key Findings & Analysis

* **S1 (BM25) Fails Consistently.** MRR@10 < 0.40 for the two main failure categories (Generic Phrasing, Terminology Mismatch), confirming weak baseline performance.
* **S2 (Dense) is the Primary Solution.** Largest single leap:

  * Generic Phrasing: **+0.4152** (0.3744 → 0.7896)
  * Terminology Mismatch: **+0.3229** (0.3996 → 0.7225)
    Semantic retrieval is the correct primary fix for these failure types.
* **S6 (Hybrid + Reranker) Adds Key Precision.** Improves Generic Phrasing from **0.7896 → 0.8500**, showing the reranker’s value in selecting the true best answer from dense candidates.
* **S7 (ComplianceGPT) Wins on Terminology.** Highest score for Terminology Mismatch (**0.8187**), demonstrating that **QUR** adds measurable value by bridging difficult vocabulary gaps beyond the reranker alone.
* **The “Hardest Case” (Semantic Gap).** The single Semantic Gap query (QID 60) yields **0.5000 MRR** (Rank 2) across all systems—highlighting an open challenge and a valuable avenue for future research.

---

## 5. Conclusion

The results validate the **S7 (ComplianceGPT)** architecture: its components—**Dense**, **Reranker**, and **QUR**—each address specific, diagnosed failure modes of the **S1 (BM25)** baseline. The superiority of S7 is **systematic and component-driven**, not incidental.
