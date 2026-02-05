**Author:** Wen
**Purpose of this note:** Tech details for future recall

# ComplianceGPT Answerer Engine (provably extractive mode)

> **_NOTE:_**  This md is the logic of specific engineering choices (The "Why") of our generator.

`generator.py` is intentionally used as an **evidence selector**:

1. Retriever returns `docs=[{id,text,score}, ...]` from the clause-level CCS.
2. Generator (LLM) selects the minimal set of `source_id` values.
3. Pipeline fills `span_text` verbatim from CCS and constructs `answer_text` deterministically.
4. Pipeline applies ODP policy (ASK vs FILL_FROM_PROFILE) and sets final `status`/`odp_required_list`.
5. Verifier consumes the pipeline’s final contract and checks citation correctness + verbatim evidence.

Key reason:
- Prevents hallucinated “verbatim” spans while keeping the selection step flexible.

Public API (generator.py):
- `ComplianceGenerator.generate(query, docs, profile=None) -> dict` (selector contract)
- `normalize_contract(raw) -> dict`
- `load_org_profile(path) -> dict`

Definitive contract definitions: see `citation_contract_80053.md`.
