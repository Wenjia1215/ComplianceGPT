# ODP Resolution Policy for Gold-Standard Evaluation Sets

This README defines the meaning and assignment rules for the `resolution_policy` column in the gold-standard Q&A CSV files
(e.g., `nist_sp800-53_rev4_gold-set_36q.csv`, `nist_sp800-53_rev5_gold-set_100q.csv`).

The purpose of `resolution_policy` is to make ODP/PRM handling *testable*:
not only “did the system find the right clause,” but also “did it handle org-defined parameters correctly”.

---

## 1) Core principle (applies to ALL policies)

If a cited clause contains an Organization-Defined Parameter placeholder (ODP/PRM), the system must:

1) **Never invent a value** (no guessing / no substitution without an org profile value).
2) **Preserve the placeholder verbatim** in any quoted evidence (and in any answer text that includes quoted evidence).

Evaluation uses `odp_required` to specify which parameter IDs must be recognized.

---

## 2) Policy values and expected behavior

`resolution_policy` is one of:

### **N/A**
- Use when the question does **not** involve any ODP/PRM.
- Expected behavior: normal citation-grounded answer, status `OK` (assuming evidence exists).
- New or revised datasets should store `N/A` explicitly. The frozen dissertation gold CSVs predate this convention and use blank `resolution_policy` cells when `odp_required` is empty. Evaluators normalize those blank cells as the non-ODP case; the frozen CSVs are not rewritten.

### **FILL_FROM_PROFILE**
- Use when the required values are standard organization-wide settings that reasonably live in an `org_profile`.
  Examples: frequencies, time windows, numeric thresholds used consistently across the org.
- Expected behavior:
  - If all required ODPs exist in the `org_profile`: status `OK`, and the answer includes substituted values.
  - If any required ODP is missing from `org_profile`: status `PARAMS_REQUIRED` and the system asks for missing values.

### **ASK**
- Use when the ODP/PRM values are contextual, list-based, or dependent on system/business specifics.
  Examples: list of auditable events; specific roles/personnel; context-dependent criteria.
- Expected behavior:
  - status `PARAMS_REQUIRED`
  - the system asks the user for the required values (do not guess).
  - placeholder preservation is allowed in quoted evidence, but the answer may paraphrase the need for the value.

### **PRESERVE**
- Use to test **literal placeholder preservation** while still requiring the system to request missing values.
- Expected behavior:
  - status `PARAMS_REQUIRED`
  - the system explicitly requests the required values (ASK behavior)
  - **AND** any placeholder strings appearing in the cited evidence must remain **verbatim** in output
    (no modification of the placeholder ID, punctuation, braces, or numbering).

> In short: PRESERVE is not “OK with placeholders”.
> PRESERVE is “PARAMS_REQUIRED + strict literal placeholder preservation”.

---

## 3) Assignment logic (how to choose a policy)

Use these rules when labeling each ODP-related question:

- Choose **FILL_FROM_PROFILE** when the org can plausibly define the value once in a configuration profile.
- Choose **ASK** when the value is context-specific, varies by unit/system, or is a list that must be supplied.
- Choose **PRESERVE** only when you specifically want to test:
  1) placeholder detection,
  2) placeholder literal preservation, and
  3) ask-back behavior,
  all at the same time.

---

## 4) Canonical format for `odp_required` (IMPORTANT)

To avoid “false failures” caused by formatting drift, **`odp_required` must use the exact parameter IDs
as they appear inside CCS placeholders**.

### What to store in `odp_required`
- Store the **placeholder ID string** from CCS, e.g. the token inside:
  `{{ insert: param, <TOKEN_HERE> }}`

### Examples
- Rev5 examples (often zero-padded, may contain dots for enhancements):
  - `ac-01_odp.01`
  - `ac-02.02_odp.01`
  - `ca-02_odp.02`
- Rev4 examples (prm keys; enhancements may use dots):
  - `at-2_prm_1`
  - `ac-12.1_prm_1`

### List formatting
- If multiple parameters are required, write **one per line** (newline-separated).
- Do not use commas inside `odp_required`.

---

## 5) Canonical format for `gold_control_path`

`gold_control_path` must list **canonical clause IDs that exist in the clause-level CCS**.
- One clause ID per line (newline-separated).
- Clause IDs must match CCS exactly (case-sensitive in strict tools).
- Avoid mixing separators like semicolons, commas, and blank lines.

---

## 6) CSV hygiene requirements

To keep evaluation deterministic across tools:
- Save gold CSVs as **UTF-8**
- Use newline-separated lists in cells (not semicolons)
- Trim whitespace around IDs
- Avoid NaN/blank ambiguity in new or revised datasets:
  - If `odp_required` is empty, set `resolution_policy` to `N/A`.
  - Preserve blank cells in already frozen dissertation CSVs unless a new experimental state is declared; evaluators must normalize them as non-ODP rows.

---

## 7) Changelog

- **2026-07**: Documented the preserved blank `resolution_policy` cells in the frozen dissertation CSVs and the evaluator normalization rule.
- **2026-02**: Redefined `PRESERVE` as **PARAMS_REQUIRED + strict literal placeholder preservation**
  (i.e., preserve + ask), not “OK with placeholders”.
