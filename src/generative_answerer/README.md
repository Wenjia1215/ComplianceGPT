# Baseline Generative Answerer (RQ2)

This package implements the **baseline generative RAG** answer path used in the
corrected matched answerer evaluation.

Goal:
- keep the same retrieval stack as ComplianceGPT,
- keep the same model family,
- change only the **final answer construction** step.

That means the comparison is:

- **ComplianceGPT answerer** = selector-only model + deterministic verbatim assembly
- **Baseline generative answerer** = same retrieved evidence + free-form LLM answer

## Main classes

- `BaselineGenerativeAnswerer`
  - prompts the model to return JSON with:
    - `status`
    - `answer_text`
    - `cited_source_ids`
    - `odp_required_list`
  - normalizes outputs in a fail-closed way when status/citations/ODP fields are inconsistent
- `BaselineGenerativeRAGPipeline`
  - subclasses the existing ComplianceGPT pipeline
  - reuses retriever, QUR, CCS loading, model loading, and verifier integration
  - swaps the final answerer from deterministic assembly to free-form generation
  - labels returned contracts with `contract_mode = "generative_rag_baseline"`

## Why this is the correct RQ2 baseline

This baseline isolates the research question about **answer construction**.

It does **not** change:
- retriever
- corpus
- QUR mode
- framework version
- verification dataset

It changes only:
- deterministic citation-contract assembly -> free-form generative answer synthesis

## Intended use

This package is for:
- single-query demonstrations
- the matched answerer experiment under
  `experiments/answerer_comparison/rq2_matched/`

It is **not** the main production answerer.
