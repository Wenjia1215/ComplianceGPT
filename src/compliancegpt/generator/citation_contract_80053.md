# ComplianceGPT Citation Contract (NIST SP 800-53)

> **_NOTE:_**  This md is Technical Specification of our generator.


**Scope:** Answerer (Generator) → Pipeline → Verifier

This project uses a *provably extractive* Answerer mode: the LLM does **evidence selection only**, and the pipeline deterministically fills verbatim evidence text from the canonical clause-level CCS.

This document defines **two related JSON contracts**:

1) **Generator Output (Selector Contract)** — produced by the LLM generator
2) **Final Answer Contract** — produced by the pipeline after deterministic filling (this is what the Verifier consumes)

---

## 1. Objective

The goal is to ensure every answer is **auditable, verifiable, and strictly grounded** in the configured compliance corpus.

Key design choice (Defense Grade):
- The LLM is not trusted to copy “verbatim” spans.
- The pipeline fills `span_text` from the canonical corpus (CCS) using the selected `source_id` values.

---

## 2. Generator Output (Selector Contract)

The Generator must return a single valid JSON object with this structure:

```json
{
  "answer_text": "",
  "evidence_spans": [
    {"source_id": "<string>", "span_text": ""}
  ],
  "status": "OK" | "NO_EVIDENCE" | "PARAMS_REQUIRED" | "ERROR",
  "odp_required_list": ["<string>"]
}
```

### Rules (Selector Contract)

- **`answer_text`**
  - Must be an empty string in provably-extractive mode.

- **`evidence_spans`**
  - Select a minimal but complete set of `source_id` values needed to answer the query.
  - Evidence spans must reference clause-level items only: `smt` (statement) and `gdn` (guidance).
  - `span_text` must be an empty string for every span.

- **`status`**
  - `OK`: evidence spans selected.
  - `NO_EVIDENCE`: no spans selected (`evidence_spans=[]`).
  - `PARAMS_REQUIRED`: reserved for pipeline output (ODP policy enforcement is deterministic).
  - `ERROR`: parsing/format failure (should be rare; pipeline may fallback).

- **`odp_required_list`**
  - Must be an empty list (`[]`) in provably-extractive mode.
  - ODP/PRM requirements are derived deterministically by the pipeline from filled evidence text and CCS parameter inventory.

- **Evidence eligibility constraints**
  - Only clause evidence kinds are eligible: `smt` (statement) and `gdn` (guidance).
  - Parameter/objective nodes (`odp`, `prm`, `obj`) are not eligible as evidence spans.
  - Prefer specific subclauses over parent clauses when available (e.g., `ac-02_smt.a` over `ac-02_smt`).

> Note: the pipeline is the source of truth for ODP policy enforcement and the final `PARAMS_REQUIRED` status.

---

## 3. Final Answer Contract (Pipeline Output)

After retrieval + generator selection, the pipeline returns the final, verifier-ready contract:

```json
{
  "answer_text": "<string>",
  "evidence_spans": [
    {"source_id": "<string>", "span_text": "<verbatim from CCS>"}
  ],
  "status": "OK" | "NO_EVIDENCE" | "PARAMS_REQUIRED" | "ERROR",
  "odp_required_list": ["<string>"],
  "primary_citation": "<string>",
  "all_citations": "<string>",
  "answer_text_with_citation": "<string>",
  "contract_mode": "provably_extractive"
}
```

### Rules (Final Answer Contract)

- **`answer_text`**
  - Constructed deterministically from canonical evidence (default: concatenation of filled `span_text`).
  - Must not introduce claims not supported by the filled spans.

- **`evidence_spans[].span_text`**
  - Must be copied verbatim from the canonical clause-level CCS for the matched `source_id`.

- **`source_id` format**
  - Recommended to use the canonical CCS ID (e.g., `ac-2_smt.a`, `pl-11_gdn`, etc.).
  - Fully-qualified formats are allowed (the verifier attempts reasonable resolution), but the last segment must still map to a CCS key.

- **ODP behavior**
  - If filled evidence contains unresolved placeholders (e.g., `{{ insert: param, ac-02_odp.05 }}`), the pipeline must set `status="PARAMS_REQUIRED"` and populate `odp_required_list`.
  - If ODP resolution policy is `FILL_FROM_PROFILE` and values exist, the pipeline may substitute in `answer_text` while keeping evidence spans verbatim.

---

## 4. Verifier Consumption

The Verifier consumes the **Final Answer Contract**, and checks:
- status mutual consistency
- citation correctness (control-level + doc-id level)
- ODP handling correctness
- verbatim containment of each `span_text` in the official CCS text for `source_id`

---

## 5. Minimal Examples

### Example A — OK (Selector Contract)

```json
{
  "answer_text": "",
  "evidence_spans": [{"source_id": "ac-1_smt.a", "span_text": ""}],
  "status": "OK",
  "odp_required_list": []
}
```

### Example B — OK (Final Answer Contract)

```json
{
  "answer_text": "<pipeline-filled text from CCS>",
  "evidence_spans": [{"source_id": "ac-1_smt.a", "span_text": "<verbatim from CCS>"}],
  "status": "OK",
  "odp_required_list": [],
  "primary_citation": "ac-1_smt.a",
  "all_citations": "ac-1_smt.a",
  "answer_text_with_citation": "<answer> (CITE: ac-1_smt.a)",
  "contract_mode": "provably_extractive"
}
```

### Example C — PARAMS_REQUIRED

```json
{
  "answer_text": "<filled evidence with unresolved ODP placeholder>",
  "evidence_spans": [{"source_id": "ac-3_smt.x", "span_text": "<verbatim with {{ insert: param, ac-02_odp.05 }}>"}],
  "status": "PARAMS_REQUIRED",
  "odp_required_list": ["ac-02_odp.05"],
  "contract_mode": "provably_extractive"
}
```
