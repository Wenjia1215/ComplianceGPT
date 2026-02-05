# ComplianceGPT Answerer: Generator (Evidence Selector)

ComplianceGPT uses a **provably extractive** Answerer mode.

> **_NOTE:_**  This md is Implementation Guide (The "How") of our pipeline.

## Role

The Generator selects **evidence IDs only**.

- The LLM must **not** copy verbatim evidence text.
- The pipeline deterministically fills `evidence_spans[].span_text` from the canonical clause-level CCS.
- The pipeline constructs `answer_text` from the filled spans and applies ODP policy.

## Selector Contract (Generator output)

```json
{
  "answer_text": "",
  "evidence_spans": [{"source_id": "<id>", "span_text": ""}],
  "status": "OK" | "NO_EVIDENCE" | "PARAMS_REQUIRED" | "ERROR",
  "odp_required_list": ["<odp_id>"]
}
```

- `span_text` must be empty (the pipeline fills it).
- If no evidence is selected, set `status="NO_EVIDENCE"` and `evidence_spans=[]`.
- If selected evidence contains unresolved ODP placeholders, set `status="PARAMS_REQUIRED"` and populate `odp_required_list`.

## Final Answer Contract

The pipeline outputs the verifier-ready contract (filled `span_text`, constructed `answer_text`). See `citation_contract_80053.md` for the definitive schema.

## API

`ComplianceGenerator.generate(query: str, docs: list[dict], profile: dict | None) -> dict`
