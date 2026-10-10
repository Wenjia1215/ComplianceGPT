# Reviewed natural-question study v2

**Status: author source/label review and registered GPU execution completed. Returned identities and automatic scoring passed the technical audit. All 40 final outputs and the executed notebook are archived in [results_v1](results_v1/README.md). Separate author post-run semantic review remains pending.**

This version retains 20 original r/NISTControls threads, separately from the 136-row historical benchmark and the 30-row intra-annotator retest. It supersedes preparation v1 for execution after author review restored omitted original text in NQ03, NQ12 and NQ16. The previous preparation remains unchanged. See [SOURCE_CORRECTIONS.json](SOURCE_CORRECTIONS.json).

## Collection

Public original posts were discovered using keyword web searches restricted to r/NISTControls, including `800-53`, `Rev5`, `implementation`, `evidence`, `logging`, `assessment`, `AC-2`, and `organization-defined`. Additional title/identifier searches recovered indexed original-post blocks. The discovery ledger records 83 distinct discovered Reddit URLs and their dispositions; it is an exploratory discovery record, not a census of the subreddit. Stack Exchange exploration supplied no selected questions.

The selection is a purposive convenience sample: 12 control interpretation/implementation posts and eight broader scope/workflow posts. One original question block was selected from each of 20 distinct threads posted in 2020–2024. Original titles, body wording, control identifiers, control quotations and multiple subquestions within a post are retained. Replies are not separate questions. Initial automated captures came from the search index because direct Reddit access returned HTTP 403; the author subsequently checked every original source and confirmed the reviewed captures. Poster professional identities and independence are unverified.

## Reference labels and denominators

The author reviewed revision, answerability, governing controls, required evidence groups, semantic ODP applicability and required parameter IDs before inference. These are author reference judgments, not independent expert correctness. The accepted review is [author_review.csv](author_review.csv); normalized frozen labels are [registered_labels.jsonl](registered_labels.jsonl). The model-visible input is [registered_questions.jsonl](registered_questions.jsonl), which contains no reference control, clause or ODP labels.

Three questions are fully answerable from the catalog, 12 partially answerable, and five outside its scope. Two need actual ODP values, 13 do not, and five are not applicable. Report all 20, with clause-coverage diagnostics on eligible full/partial cases, conservative whole-question catalog-contract outcomes on only the three full cases, and ODP sensitivity on only two positive cases. Sample-wide semantic accuracy and representative practitioner performance are not established.

See [PROTOCOL.md](PROTOCOL.md) and [protocol.json](protocol.json) for the matched evidence, pinned models, recording, scoring and limitations. Registry display metadata is retained as a documented input limitation, not silently corrected after registration.

## Execute

The [preserved authority-check attempt](prior_attempt/README.md) retains the former main launcher and failure trace separately from the completed run.

The original inputs and execution registration were published at `71a9a187d0a3fe0d64d71cdefbacdb345cce890d` before retrieval. See [EXECUTION_REPAIR.json](EXECUTION_REPAIR.json) for the subsequent, explicitly recorded authority-check correction: canonical control IDs and retriever control IDs use different case/enhancement notation. The validator now compares those identities using the already frozen production normalizer, while source IDs, clause text and evidence kinds remain exact. No question, label, catalog, model, retrieval setting, window rule or metric changed.

The repaired execution completed under the public registration at `27c437a2176847b6ac82f86b3f1abbb3ba63c1ac`. Its archive preserves the original five-context attempt separately and records fresh retrieval of all 20 questions before either answer path began. The Colab launcher used A100, retained per-question checkpoints and logs, and produced the executed notebook and result package. Reproduce this historical run at that execution commit: the integrated runtime has different source hashes and deliberately fails the old registration check.

```bash
python experiments/external_validity/natural_questions_v2/run_natural_questions.py --output-dir /path/to/new_results --preflight-only
python experiments/external_validity/natural_questions_v2/run_natural_questions.py --output-dir /path/to/new_results
```

Both answer paths share Qwen2.5-7B-Instruct in explicitly checked BF16 and the same original question/evidence. Use production S7 retrieval, pinned E5/BGE models, no query rewrites, an empty organization profile and ASK policy. Prompts, construction, token budgets and retries differ between complete answer paths; this is not an isolated component intervention.

CUDA execution and the technical identity/result audit are documented in [results_v1](results_v1/README.md). The [author post-run review](results_v1/author_review_v1/README.md) is complete for all 40 question/path pairs. Automatic scoring retains its historical `experiment_complete=false` flag; the separate review record documents later completion. Partial/outside cases cannot become whole-question successes. Full-text containment and runtime validity do not establish responsive interpretation. Independent expert correctness remains unvalidated.
