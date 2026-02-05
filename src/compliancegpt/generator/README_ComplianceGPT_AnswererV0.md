# ComplianceGPT — Answerer v0 (Pipeline + Generator + Retriever)

This folder implements a **provably extractive** ComplianceGPT Answerer for **NIST SP 800-53** clause-level CCS.

Design principle:
- The LLM is trusted for **evidence selection only**.
- The pipeline is trusted for **verbatim evidence filling**, **ODP handling**, and **final contract construction**.

Definitive contract spec: `citation_contract_80053.md`.

---

## Directory map (current)

- `retriever/retriever_s7.py`
  - Loads the clause-level CCS JSONL (rev4/rev5 as configured).
  - Retrieves candidate clauses with BM25 + dense + rerank (S7).

- `generator/generator.py`
  - **Evidence selector** (LLM).
  - Returns the **Selector Contract** (IDs only; empty `span_text` and empty `answer_text`).

- `pipeline/pipeline.py`
  - Orchestrates retrieval → selection → deterministic filling.
  - Produces the **Final Answer Contract** (verifier-ready).

- `generator/verifier/verifier.py`
  - Consumes the pipeline’s final contract (checked separately).

---

## What `generator.py` does (and does NOT do)

### Does
- Selects the minimal set of `source_id` values needed to answer the query.
- Outputs JSON that matches the **Selector Contract**:
  - `answer_text` must be `""`
  - `evidence_spans[].span_text` must be `""`
  - `odp_required_list` is extracted from selected docs’ text (`{{ insert: param, ... }}`)

### Does NOT
- Substitute ODP values from an organization profile.
- Construct the final answer text.
- Copy verbatim evidence spans.

Those responsibilities belong to **pipeline.py**.

---

## What `pipeline.py` does

- Loads and sanity-checks the CCS (expects clause-level ids like `ac-7_smt...`, `ac-7_gdn...`).
- Calls the retriever to get candidate docs.
- Calls the generator to get selected `source_id` values.
- Deterministically fills:
  - `evidence_spans[].span_text` (verbatim from CCS by `source_id`)
  - `answer_text` (from filled spans)
  - `status` + `odp_required_list` (ODP policy / placeholders)

---

## Running (Colab)

Use these notebooks:
- `pipeline/run_single.ipynb` — single query end-to-end
- `pipeline/run_batch.ipynb` — batch evaluation

**Common causes of errors:**
- Import paths: `pipeline.py` modifies `sys.path` assuming sibling folders (`generator/`, `retriever/`, etc.). If you relocate folders, update those path blocks in `pipeline.py`.
- CCS format mismatch: the pipeline sanity check expects `_smt`/`_gdn` clause ids. Ensure your CCS JSONL includes `clause_id` (preferred) or `id` that contains the kind suffix.

---

## Tests

- `generator/generator_v0_testbench.py`
  - Deterministic unit tests for generator schema + invariants (no LLM required).
  - Optional LLM integration smoke test.

---

## Status meanings (quick)

- `OK`: evidence selected and no unresolved ODP placeholders in selected evidence.
- `PARAMS_REQUIRED`: selected evidence contains unresolved ODP placeholders (pipeline should ask for values or fill from profile depending on policy).
- `NO_EVIDENCE`: no evidence selected.
- `ERROR`: contract parse failure (pipeline may fallback).

For the full schema and rules, see `citation_contract_80053.md`.
