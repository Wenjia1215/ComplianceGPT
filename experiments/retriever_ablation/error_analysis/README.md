# Error Mode Analysis Notebook — README (Tool Documentation)

This document describes **how** `error_mode_analyze.ipynb` works, the exact input/output contracts it expects, and how to interpret the artifacts it produces. It intentionally avoids embedding dataset-specific conclusions so the README remains correct across runs.

---

## 1) Purpose and Scope

### Purpose
The goal of this notebook is to diagnose **why retrieval fails** on a curated challenge set (the **Error Bank**) by analyzing performance **broken down by failure category** (“error modes”).

Concretely, the notebook:

1. Loads the **labeled Error Bank** (per-question failure categories).
2. Loads each system’s **Error Bank retrieval result CSVs** (e.g., S1–S7 for Rev4/Rev5).
3. Converts the gold item’s `rank` into a per-question **RR@10** score.
4. Merges RR@10 columns with Error Bank labels.
5. Produces a **pivot table**: mean RR@10 grouped by `failure_category` for each system.

### Scope
- This notebook is for **Error Bank analysis only** (challenge-set diagnostics).
- It does **not** compute full-dataset metrics across the entire gold set.
- The pivot table produced here is a **category breakdown of RR@10** (equivalent to MRR@10 when there is one gold item per query).

---

## 2) What is an “Error Mode”?

In this project, “error mode” refers to the Error Bank label column:

- `failure_category` (exactly one label per Error Bank item)

Category definitions and labeling guidance live in `Labeling_Rationale.md`. The notebook treats `failure_category` purely as a grouping key; it does not validate category semantics.

---

## 3) Input Contracts (Critical)

This notebook depends on **strict schema and join-key alignment** between the Error Bank and the system result CSVs. If the labels cannot be attached, the pivot table becomes meaningless.

### 3.1 Error Bank CSV (Required)

**File**: `error_bank_v1.csv` (path configured inside the notebook)

**Required columns**
- `question_id`
- `question`
- `failure_category`

**Optional but recommended**
- `version` (e.g., `rev4` / `rev5`) to prevent collisions when IDs are reused across datasets.

**Requirements**
- `failure_category` must be populated (not empty / not NaN).
- `question_id` should be stable and consistent with the system output CSVs.
- If you have both Rev4 and Rev5 items in the Error Bank, strongly consider using `version` in joins.

### 3.2 System Result CSVs (Required)

For each system, the notebook reads one or more Error Bank result CSVs (commonly Rev4 and Rev5).

**Required columns**
- `question_id`
- `rank`

**Notes**
- The notebook computes RR@10 from `rank`. It does **not** require a precomputed `mrr@10` column.
- Additional columns (e.g., `is_hit_at_1`, `retrieved_control_ids`) may be present, but are not required for the pivot.

---

## 4) Computation Details

### 4.1 RR@10 (Reciprocal Rank at 10)
For each row in a system result CSV:

- If `1 <= rank <= 10`, then `RR@10 = 1 / rank`.
- Otherwise (`rank` is 0, >10, NaN, or missing), `RR@10 = 0.0`.

When each query has exactly one relevant “gold” item, the mean RR@10 across queries is equivalent to **MRR@10**.

### 4.2 Per-question aggregation
If multiple rows exist for the same question (e.g., across multiple files), the notebook aggregates to one score per question per system (typically by taking the maximum RR@10 per question).

### 4.3 Label attachment and join keys
To compute the pivot, the notebook must attach `failure_category` to the merged results table. The most robust identity in this project is:

- `(question_id, question, version)` when `version` is available.

If you join only on `question_id` in a dataset where IDs collide across versions, label attachment can fail or become incorrect.

---

## 5) Outputs

The notebook produces three artifacts:

1. **`merged_results_data.csv`**  
   A row-level merged dataset containing:
   - Error Bank identifiers (`question_id`, `question`, optionally `version`)
   - `failure_category` (if successfully attached)
   - one RR@10 column per system (e.g., `S1_MRR`, `S2_MRR`, ..., `S7_MRR`)

   Use this file for row-level debugging and case study sampling.

2. **`pivot_table.csv`**  
   A pivot table (CSV) with:
   - rows: `failure_category`
   - columns: system RR@10 means (MRR@10-equivalent)
   - values: mean RR@10 per category

3. **`pivot_table.md`**  
   The same pivot table rendered as Markdown (useful for directly pasting into reports).

---

## 6) Interpretation Guide (How to read the pivot)

The pivot table answers:

> “Within each failure category, how highly does each system rank the gold item on average (within top-10)?”

Guidelines:
- Larger values indicate better ranking of the gold item (closer to the top).
- Compare systems within the same row to see which approach is more effective for that error mode.
- If you want an explicit improvement view, compute deltas such as `(S7 − S1)` per category outside the notebook (or extend the notebook to add delta columns).

This README does not assume any system improves any category; it only explains how to interpret the numbers.

---

## 7) Troubleshooting (Most common failure modes)

### 7.1 Pivot table is empty (header only)
Typical causes:
- `failure_category` is missing/NaN for all rows after merge (group-by drops NaN keys), or
- the merged dataset is empty due to missing inputs.

Actions:
- Confirm the loaded Error Bank file is the labeled one (non-empty `failure_category`).
- Inspect `merged_results_data.csv` to verify `failure_category` is present and non-null.

### 7.2 Pivot table shows mostly or only `UNLABELED`
This indicates that labels could not be attached for most rows.

Common causes:
- `question_id` dtype mismatch (string vs int) across files.
- ID collisions across Rev4/Rev5 without using `version` in joins.
- `question` text mismatch between Error Bank and result CSVs (normalization differences).
- Non-unique join key in the Error Bank.

Actions:
- Cast `question_id` to string in both sources before merging.
- Include `version` in the join key if both Rev4 and Rev5 exist.
- Spot-check a few `(question_id, question)` pairs across both files.

### 7.3 A system’s column is missing in the merged outputs
This usually means the notebook did not load that system’s result files (path mismatch) or rejected them (missing required columns).

Actions:
- Verify the configured results directory and filenames.
- Confirm each result CSV contains `question_id` and `rank`.

---

## 8) Relationship to the broader ComplianceGPT evaluation

This notebook is complementary to the main evaluation tables:

- Main evaluation reports summarize overall dataset performance (Recall@K, MRR@10, nDCG@10).
- This notebook focuses on **Error Bank** diagnostics by failure mode (MRR@10-equivalent breakdown).

Use this notebook’s pivot table when you need to explain *which failure types* are improved or regressed by specific retrieval components.

---

## 9) Related project documents

- `WORKFLOW.md` — where this notebook is used in the ablation pipeline.
- `Labeling_Rationale.md` — definitions and examples for `failure_category`.
- `SYSTEMS.md` — system variants and component descriptions.
- `RESULTS.md` — consolidated metrics for the main datasets.
