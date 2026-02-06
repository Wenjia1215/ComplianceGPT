# ComplianceGPT — Answerer v0 (Retriever + Generator + Pipeline + Verifier)

This folder implements a **provably-extractive** ComplianceGPT answerer for **NIST SP 800-53** using a **clause-level Canonical Clause Store (CCS)**.

**Core design principle (Defense-grade auditability):**
- The LLM is trusted for **evidence selection only** (which clause IDs are needed).
- The pipeline is trusted for **verbatim evidence filling**, **ODP handling**, and **final contract construction**.

**Definitive contract spec:** `citation_contract_80053.md`

---

## Components (current)

- `retriever_s7.py`
  - Loads the clause-level CCS JSONL (rev4/rev5 as configured).
  - Retrieves candidate clauses (S7 retrieval stack).

- `generator.py`
  - LLM **evidence selector**.
  - Produces the **Selector Contract** (IDs only; empty `span_text` + empty `answer_text`).

- `pipeline.py`
  - Orchestrates retrieval → selection → deterministic filling.
  - Produces the **Final Answer Contract** (verifier-ready).

- `verifier.py`
  - Validates the **Final Answer Contract** against the CCS and (optionally) gold labels.

---

## Generator contract (what `generator.py` does / does not do)

### Does
- Selects the minimal set of `source_id` values needed to answer the query.
- Outputs JSON matching the **Selector Contract**:
  - `answer_text` must be `""`
  - `evidence_spans[].span_text` must be `""`
  - `status` ∈ `OK | NO_EVIDENCE | PARAMS_REQUIRED | ERROR`
  - `odp_required_list` should be empty unless `status="PARAMS_REQUIRED"`

> Note: the pipeline is the **source of truth** for final ODP handling and may recompute `odp_required_list`
> from canonical CCS text after deterministic filling.

### Does NOT
- Copy verbatim evidence spans.
- Construct the final answer text.
- Substitute ODP values from an organization profile.

Those responsibilities belong to **pipeline.py**.

---

## Pipeline behavior

### 1) Evidence handling (strict)
- The pipeline fills `evidence_spans[].span_text` **verbatim from the canonical CCS** for each selected `source_id`.
- If the generator returns `status="NO_EVIDENCE"` (and selects no spans), the pipeline **must not inject fallback evidence**.
  - Final contract stays `status="NO_EVIDENCE"` and `evidence_spans=[]`.
- If the generator output is malformed or `status="ERROR"`, the pipeline may run a controlled fallback using the retriever’s top hit
  (and should mark that via a flag/metadata if you track it).

### 2) Answer text (provably-extractive)
- `answer_text` is constructed deterministically from canonical evidence
  (default: concatenation of filled `span_text` in selected order).
- The pipeline must not introduce claims not supported by the filled spans.

### 3) ODP handling (unresolved placeholders)
If filled evidence contains unresolved ODP placeholders such as:

`{{ insert: param, <odp_id> }}`

then the pipeline must:
- set `status="PARAMS_REQUIRED"`
- populate `odp_required_list` with the required ODP IDs

If an ODP policy is `FILL_FROM_PROFILE` and values exist, the pipeline may substitute values **in `answer_text` only**
while keeping `evidence_spans[].span_text` verbatim.

---

## Gold-set `resolution_policy`

Gold sets may include `resolution_policy` to define evaluation expectations for ODP behavior:

- `N/A` — no ODP involved
- `ASK` — contextual ODPs; expected `status="PARAMS_REQUIRED"`
- `FILL_FROM_PROFILE` — expected `OK` if values exist in profile, else `PARAMS_REQUIRED`
- `PRESERVE` — expected `PARAMS_REQUIRED` **and** literal placeholder preservation in output evidence/answer text

**Definition of `PRESERVE`:**
> `PRESERVE` is not “OK with placeholders.”  
> It is “PARAMS_REQUIRED + strict literal placeholder preservation (plus ask-back via `odp_required_list`).”

The verifier enforces this by checking that each required ODP token appears in the output in the canonical placeholder form:
`{{ insert: param, <token> }}`

---

## Status meanings (quick)

- `OK`
  - Evidence selected and **no unresolved ODP placeholders remain**, or ODPs are resolvable from profile (and handled accordingly).
- `PARAMS_REQUIRED`
  - Evidence selected, but unresolved ODP placeholders require user/org inputs.
- `NO_EVIDENCE`
  - No evidence selected. Output must have `evidence_spans=[]`.
- `ERROR`
  - Contract parse/format failure. Pipeline may fallback, but should keep this outcome measurable (verifier treats it as valid-but-failed).

For the full schema and rules, see `citation_contract_80053.md`.

---

## Running (Colab / local)

Typical end-to-end path:
1) Load CCS (rev4 or rev5)
2) Retrieve candidate clauses (`retriever_s7.py`)
3) Select minimal evidence IDs (`generator.py`)
4) Deterministically fill & construct final contract (`pipeline.py`)
5) Verify contract (`verifier.py`)

Common causes of errors:
- CCS ID mismatch (`ac_2_smt` vs `ac-2_smt`) — normalize to canonical CCS IDs.
- Mixed separators in gold-set cells — use newline-separated lists.
- Non-UTF8 CSV encoding — save gold sets as UTF-8 to avoid decode failures.
