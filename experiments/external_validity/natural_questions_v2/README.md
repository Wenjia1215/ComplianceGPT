# Reviewed natural-question study v2

**Status: author source/label review completed and inputs frozen. A user-reported GPU attempt captured five revision-4 contexts, then stopped at the authority check before answer generation. The registered execution repair uses a separate result directory; no answerer results are included here.**

This version retains 20 original r/NISTControls threads, separately from the 136-row historical benchmark and the 30-row intra-annotator retest. It supersedes preparation v1 for execution after author review restored omitted original text in NQ03, NQ12 and NQ16. The previous preparation remains unchanged. See [SOURCE_CORRECTIONS.json](SOURCE_CORRECTIONS.json).

## Collection

Public original posts were discovered using keyword web searches restricted to r/NISTControls, including `800-53`, `Rev5`, `implementation`, `evidence`, `logging`, `assessment`, `AC-2`, and `organization-defined`. Additional title/identifier searches recovered indexed original-post blocks. The discovery ledger records 83 distinct discovered Reddit URLs and their dispositions; it is an exploratory discovery record, not a census of the subreddit. Stack Exchange exploration supplied no selected questions.

The selection is a purposive convenience sample: 12 control interpretation/implementation posts and eight broader scope/workflow posts. One original question block was selected from each of 20 distinct threads posted in 2020–2024. Original titles, body wording, control identifiers, control quotations and multiple subquestions within a post are retained. Replies are not separate questions. Initial automated captures came from the search index because direct Reddit access returned HTTP 403; the author subsequently checked every original source and confirmed the reviewed captures. Poster professional identities and independence are unverified.

## Reference labels and denominators

The author reviewed revision, answerability, governing controls, required evidence groups, semantic ODP applicability and required parameter IDs before inference. These are author reference judgments, not independent expert correctness. The accepted review is [author_review.csv](author_review.csv); normalized frozen labels are [registered_labels.jsonl](registered_labels.jsonl). The model-visible input is [registered_questions.jsonl](registered_questions.jsonl), which contains no reference control, clause or ODP labels.

Three questions are fully answerable from the catalog, 12 partially answerable, and five outside its scope. Two need actual ODP values, 13 do not, and five are not applicable. Report all 20, with clause-coverage diagnostics on eligible full/partial cases, conservative whole-question catalog-contract outcomes on only the three full cases, and ODP sensitivity on only two positive cases. Sample-wide semantic accuracy and representative practitioner performance are not established.

See [PROTOCOL.md](PROTOCOL.md) and [protocol.json](protocol.json) for the matched evidence, pinned models, recording, scoring and limitations. Registry display metadata is retained as a documented input limitation, not silently corrected after registration.

## Execute

The original inputs and execution registration were published at `71a9a187d0a3fe0d64d71cdefbacdb345cce890d` before retrieval. See [EXECUTION_REPAIR.json](EXECUTION_REPAIR.json) for the subsequent, explicitly recorded authority-check correction: canonical control IDs and retriever control IDs use different case/enhancement notation. The validator now compares those identities using the already frozen production normalizer, while source IDs, clause text and evidence kinds remain exact. No question, label, catalog, model, retrieval setting, window rule or metric changed.

Publish the revised executable registration before resuming. A clean checkout must retrieve its exact registration from the checkout commit. The Colab launcher pins that public commit, asks for A100, writes per-question checkpoints and console logs to Drive, and retains the executed notebook and result package. Preserve the original `natural_questions_v2` attempt and use `natural_questions_v2_authority_fix` for the repaired execution. Do not transfer its old run configuration into the new run. Retrieve all 20 questions under the repaired registration before either answer path begins, retaining the earlier five-context attempt for provenance.

```bash
python experiments/external_validity/natural_questions_v2/run_natural_questions.py --output-dir /path/to/new_results --preflight-only
python experiments/external_validity/natural_questions_v2/run_natural_questions.py --output-dir /path/to/new_results
```

Both answer paths share Qwen2.5-7B-Instruct in explicitly checked BF16 and the same original question/evidence. Use production S7 retrieval, pinned E5/BGE models, no query rewrites, an empty organization profile and ASK policy. Prompts, construction, token budgets and retries differ between complete answer paths; this is not an isolated component intervention.

Completion still requires CUDA execution, identity/result audit and the separate author post-run review of all 40 question/path pairs. Automatic scoring leaves `experiment_complete` false. Partial/outside cases cannot become whole-question successes. Full-text containment and runtime validity do not establish responsive interpretation. Independent expert correctness remains future work.
