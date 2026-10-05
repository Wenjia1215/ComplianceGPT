# Separate natural-question study

**Status: preparation only. Source confirmation and author label review are pending. No retrieval outcomes or answer generations have been produced for these questions.**

This version prepares 20 naturally occurring question candidates from original r/NISTControls posts. Their captured wording, URLs, indexed posted dates and capture boundaries are retained. The experiment will report these rows separately from the historical 136-row benchmark.

The selection is a purposive, one-forum convenience sample. It is not random or exhaustive. Twelve candidates concern control interpretation/implementation, and eight concern broader scope/workflow. Direct Reddit access returned HTTP 403; the captures are indexed original post blocks. Confirm each original post, date and completeness before registration. Poster professional identities are unverified. Original control IDs and control quotations remain in the questions.

## Review before inference

Use the accompanying author review workbook, or edit [review_labels.template.csv](review_labels.template.csv). The workbook has four sheets:

- **Review:** yellow editable decisions, with draft revision, scope and clause suggestions.
- **Questions:** original captured questions, primary URLs, source notes and visible-parameter helpers.
- **Authority:** canonical statement, guidance and parameter records supporting the draft suggestions.
- **Guide:** field definitions and instructions.

For all 20 rows, confirm the source and review the revision, answerability, governing controls and required evidence groups. Decide semantic ODP applicability and the required registry keys. Record your name and UTC review time. Draft suggestions are not accepted author labels. Visible parameter IDs are helpers; their presence does not establish that the question needs those values.

Use `full`, `partial`, `outside` or `ambiguous` for answerability. Keep `required`, `not_required`, `not_applicable` and `uncertain` ODP judgments separate. Use `[]` for an explicit empty JSON list and `null` for uncertain required ODP IDs. An evidence group represents one required duty; members within a group are acceptable alternative sources. Separate groups must all be covered. The validator checks catalog identities and consistency, but cannot establish semantic correctness of a human judgment.

If a source capture is incomplete, unavailable or dated incorrectly, mark `source_problem` and describe it. Do not paraphrase it or mark it confirmed. Recover the original capture, document the correction and version the candidate set before freezing. Exclusion or replacement must be explained before any model outcome is observed. The current compiler requires 20 reviewed, confirmed rows and will not silently drop a problem row.

Reviewing these labels establishes **author reference judgments**, not independent expert correctness. An independent professional study remains separate future work.

## Files

| File | Purpose |
|---|---|
| [QUESTIONS.md](QUESTIONS.md) | Readable original question blocks with provenance |
| `candidate_questions.jsonl` | Frozen preparation captures and explicitly provisional suggestions |
| `discovery_ledger.jsonl` | Discovered Reddit URLs and selection/disposition reasons |
| `authority_records.jsonl` | Canonical reference records with catalog/text identities |
| `protocol.json`, [PROTOCOL.md](PROTOCOL.md) | Separate versioned design and metric definitions |
| `review_and_freeze.py` | Validate reviewed CSV/XLSX and create the pre-inference registration |
| `run_natural_questions.py` | Registered CUDA execution, immutable contexts and generation checkpoints |
| `score_results.py` | Offline author-reference coverage/contract scoring and semantic-review template |
| `requirements-colab.txt` | Pinned Python dependencies |

## Sequence

1. Return the completed source/label review. No model runs are needed for this step.
2. Validate the review and freeze the questions, labels, protocol and executable hashes.
3. Publish that registration in a commit. The GPU runner requires a clean checkout and retrieves the exact public registration from the checkout commit before loading a model.
4. Prepare a Colab notebook pinned to that reviewed commit. Run on a BF16-capable CUDA device, preferably A100. Preserve its cell outputs, console log and result files.
5. Audit all 20 paired rows and their source/model/context identities. Review responsiveness and unsupported claims using the generated post-run review sheet. Report the outcomes, unresolved cases and limitations separately.

The registration commands, from the repository root, are:

```bash
python experiments/external_validity/natural_questions_v1/review_and_freeze.py --check-candidates
python experiments/external_validity/natural_questions_v1/review_and_freeze.py --review /path/to/completed_review.xlsx
```

The second command intentionally refuses the unreviewed workbook/template. After publishing the reviewed registration, preflight and execution are:

```bash
python experiments/external_validity/natural_questions_v1/run_natural_questions.py --output-dir /path/to/new_result_folder --preflight-only
python experiments/external_validity/natural_questions_v1/run_natural_questions.py --output-dir /path/to/new_result_folder
```

Do not run against a preparation commit. No accepted labels or registration are included yet. Changing wording, labels, inputs or executable code after registration requires a new version. Resume requires identical registered source, actual software/device configuration and locked evidence files. Failed generation calls are retained. Empty retrieval stops the run for explicit versioned treatment instead of discarding the row.

## Configuration and interpretation

Both answer paths share the same pinned Qwen2.5-7B-Instruct model in explicitly verified BF16, the same original question and the same locked evidence window. Retrieval uses the current production S7 implementation with pinned E5/BGE models, default retrieval constants, top 12 controls and no query rewriting. This is a new configuration identity; it does not recreate the historical notebook-based RQ1 study. Prompts, construction, token budgets and retries differ between the two complete answer paths, so the comparison is not an isolated schema intervention.

Partial/outside/ambiguous questions remain in the all-20 description. Only questions judged fully answerable with determinate ODP applicability enter the conservative whole-question catalog-contract denominator. Required clause groups must have complete canonical text retained verbatim, all spans must pass containment, the contract must pass the runtime verifier, and ODP status/key recall must match the author reference. This criterion does not establish semantic responsiveness or independent correctness, and is distinct from historical headline metrics. See [PROTOCOL.md](PROTOCOL.md) for denominators and limits.

## Preparation validation

`python -m unittest tests.test_natural_questions -q` passes 28 synthetic tests. They cover source/author review requirements, wording and identity changes, clause/ODP consistency, uncertainty handling, strict coverage denominators, alternative sources, conservative full-text coverage, statistics, canonical checkpoint evidence and retention of failed generations. Synthetic fixtures are not study labels or results.

The five existing shared-evidence-window tests also pass in the pinned CPU import environment. The candidate/source-input hashes pass their preparation check. The runner stops before model loading when human review/registration is missing. The supplied workbook preserves the exact captured question strings and leaves review decisions pending. Formal end-to-end CUDA execution has not been performed. The study remains incomplete until reviewed registration, execution, result audit and post-run qualitative review.
