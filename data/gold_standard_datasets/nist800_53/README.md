# ODP Resolution Policy for Gold-Standard Evaluation Sets

This document outlines the purpose and assignment logic for the `resolution_policy` column in the gold-standard Q&A (`.csv`) files.

---

## 1. Purpose of the `resolution_policy` Column

The `resolution_policy` column is essential for evaluating the system’s ability to correctly handle Organization-Defined Parameters (ODPs). It specifies the expected behavior of the answerer when it encounters a question that involves one or more ODPs. This allows us to programmatically test not just whether the system can identify an ODP, but whether it can take the correct, context-appropriate action.

---

## 2. Policy Definitions

The `resolution_policy` column can contain one of four possible values:

- **N/A**  
  Assigned to any question/answer pair that does **not** involve an ODP.

- **FILL_FROM_PROFILE**  
  The expected behavior is for the system to retrieve a predefined value from a sample `org_profile.yaml` file and correctly substitute it into the answer. This tests the system’s ability to use organization-specific configuration.

- **ASK**  
  The expected behavior is for the system to recognize that it lacks the required information and return a `PARAMS_REQUIRED` status, prompting the user for the specific ODP value. This tests the system’s “ask back” capability.

- **PRESERVE**  
  The expected behavior is for the system to leave the ODP placeholder (e.g.,  {{ insert: param, ... }}) in the final answer verbatim. This tests the system’s ability to quote a control exactly as written without modification.

---

## 3. Assignment Logic: How to Choose a Policy

The policy for each ODP-related question is chosen based on the nature of the parameter itself, with the goal of creating a balanced and comprehensive evaluation set.

### Use **FILL_FROM_PROFILE** for standard, organization-wide settings.
- **Rationale:** These are parameters that an organization would likely define once and apply broadly.  
- **Examples:** Frequencies (annually, monthly), time periods (e.g., 90 days, one hour), or common configuration choices.

### Use **ASK** for specific, contextual, or list-based parameters.
- **Rationale:** These are parameters that cannot be easily predefined and often depend on the specifics of a system, an incident, or a business unit.  
- **Examples:** A list of organization-defined auditable events, a list of personnel or roles, or criteria for an action that is not globally defined.

### Use **PRESERVE** for testing literal citation.
- **Rationale:** This is used in a minority of cases to verify that the system can, when instructed, simply repeat the source text without attempting to resolve the ODP.

---

## 4. ODP Key Normalization and Format

For consistent and unambiguous programmatic evaluation, all Organization-Defined Parameter (ODP) and Parameter (`prm`) keys across all gold sets have been standardized to a single canonical format.

---

### Final Format

The final format is **`[control-id]_[type]_[number]`**.

* **Example (Rev. 5):** `ac-2_odp_1`
* **Example (Rev. 4):** `at-2_prm_1`

---

### Normalization Rules

The following rules were applied to the source OSCAL keys to produce the final, clean format:

1.  **Identifier Type:** Both `prm` (from Rev. 4) and `odp` (from Rev. 5) are preserved to maintain source traceability but are treated as the same conceptual category for evaluation.

2.  **Separators:** All original separators (e.g., dots, colons) have been replaced with a single underscore (`_`) to join the parts of the key.

3.  **Numbering:** All parameter numbers have been normalized to remove leading zeros.
    * **Example:** A source key like `sr-03_odp_3` is normalized to `sr-3_odp_3`.

---

By distributing these policies across the ODP-containing questions in our gold sets, we can rigorously test all facets of the system’s ODP-handling logic.


#### Notes:
1. EasyQs are the first version of gold standard datasets.
