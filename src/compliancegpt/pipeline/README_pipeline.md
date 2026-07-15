# ComplianceGPT Pipeline

This folder contains the **answerer pipeline** for ComplianceGPT: the notebooks used to run single-query demos, acceptance checks, and full gold-set batch evaluation, plus the canonical `pipeline.py` implementation and score tables used by the pipeline evaluation flow.

This README documents:
- what this folder is for,
- what each file and subfolder does,
- the current intended workflow,
- how to run single-query and batch-query evaluation,
- what outputs are produced,
- how to interpret the main fields and metrics.

---

## 1. Purpose of this folder

The `pipeline/` directory is the operational entrypoint for the ComplianceGPT answerer.

At a high level, the pipeline takes a user question and produces a **provably extractive answer contract** rather than an unconstrained free-form answer. The pipeline:

1. takes a natural-language query,
2. optionally uses query rewrites,
3. retrieves candidate clause evidence from the clause-level CCS,
4. uses the generator in **selector-only** mode,
5. fills evidence spans deterministically from canonical source text,
6. applies ODP policy handling,
7. returns a structured final answer contract,
8. optionally runs verifier-based evaluation against a gold row.

This folder is the place to:
- run a single freeform demo query,
- run acceptance/regression tests,
- run full Rev5 and Rev4 batch evaluations,
- save pipeline outputs and evaluation reports.

This folder is **not** the place for retriever ablation experiments or matched
retrieval diagnostics. Those live under `experiments/`.

---

## 2. Current folder structure

Current intended structure:

```text
pipeline/
├── batch_run/
│   ├── rev4/
│   │   └── Batch_Run_rev4.ipynb
│   └── rev5/
│       └── Batch_Run.ipynb
├── pipeline_score/
│   ├── eval_rev4.csv
│   └── eval_rev5.csv
├── pipeline.py
├── README.md
└── single_run/
    ├── Acceptance_Tests.ipynb
    └── Single_Run_Demo.ipynb
```

Associated output directory outside this folder:

```text
experiments/
└── pipeline_runs/
    ├── pipeline_rev4_contracts_<timestamp>.csv
    ├── pipeline_rev5_contracts_<timestamp>.csv
    └── reports/
        ├── eval_rev4_<timestamp>.csv
        ├── eval_rev4_<timestamp>.md
        ├── eval_rev5_<timestamp>.csv
        └── eval_rev5_<timestamp>.md
```

This split is intentional:
- `pipeline/` contains code and notebooks used to run the answerer,
- `experiments/pipeline_runs/` contains generated run artifacts.

---

## 3. File-by-file guide

### 3.1 `pipeline.py`

This is the canonical end-to-end answerer pipeline implementation.

Current role of `pipeline.py`:
- instantiate the retriever,
- optionally instantiate the QUR component,
- run retrieval,
- call the generator in selector-only mode,
- fill final evidence spans from canonical CCS text,
- assemble `answer_text` deterministically,
- apply ODP policy,
- normalize and flatten the final contract,
- optionally run verifier-based evaluation.

This file is the central control plane for answer construction.

### 3.2 `single_run/Single_Run_Demo.ipynb`

This is the **single freeform query demo notebook**.

Use it when you want to:
- ask one query interactively,
- inspect the final answer contract,
- inspect rewrites used in retrieval,
- inspect top retrieval metadata,
- sanity-check current pipeline behavior without running batch evaluation.

This notebook is for **demo and quick inspection**, not for formal benchmarking.

### 3.3 `single_run/Acceptance_Tests.ipynb`

This is the **regression and invariants notebook**.

Use it when you change pipeline behavior and want to confirm that the answerer still satisfies the core contract semantics.

It checks the main behavior classes:
- `PARAMS_REQUIRED` path,
- `NO_EVIDENCE`-style path,
- `OK`-style path,
- contract schema invariants,
- basic status consistency.

This notebook is the first stop after modifying `pipeline.py` or `generator.py`.

### 3.4 `batch_run/rev5/Batch_Run.ipynb`

This is the **full batch evaluation notebook for Rev5**.

Use it to:
- run the pipeline across the Rev5 gold set,
- optionally use precomputed QUR rewrites,
- save one row per query contract output,
- compute evaluation summaries,
- save markdown and CSV reports.

### 3.5 `batch_run/rev4/Batch_Run_rev4.ipynb`

This is the **full batch evaluation notebook for Rev4**.

Its role is the same as the Rev5 notebook, but configured for the Rev4 gold set.

### 3.6 `pipeline_score/`

This folder stores score tables used as part of the pipeline evaluation flow.

Files currently present:
- `eval_rev4.csv`
- `eval_rev5.csv`

Treat this folder as lightweight score artifacts that belong to the pipeline evaluation layer, not as the authoritative run archive. The authoritative run outputs live in `experiments/pipeline_runs/`.

---

## 4. Current intended workflow

The current recommended workflow is:

1. **single freeform demo**
   - use `single_run/Single_Run_Demo.ipynb`
2. **acceptance / regression checks**
   - use `single_run/Acceptance_Tests.ipynb`
3. **full gold-set evaluation**
   - use `batch_run/rev5/Batch_Run.ipynb`
   - use `batch_run/rev4/Batch_Run_rev4.ipynb`
4. **inspect saved outputs**
   - contract-level CSV in `experiments/pipeline_runs/`
   - summary reports in `experiments/pipeline_runs/reports/`

This means:
- demo notebook = interactive,
- acceptance notebook = guardrail,
- batch notebooks = official evaluation entrypoints.

---

## 5. Current answerer design assumptions

This pipeline assumes the current ComplianceGPT answerer architecture:

- **retriever** builds a candidate clause pool,
- **QUR** may provide rewrites, but is part of the retrieval preparation path,
- **generator** is **selector-only**,
- **pipeline** owns deterministic answer assembly,
- **pipeline** owns final ODP policy behavior,
- **verifier** checks contract validity and gold-aligned evaluation behavior.

In other words, the language model is not treated as the final author of the user-facing compliance answer. It is used for bounded evidence selection, while final answer synthesis is controlled by deterministic orchestration.

---

## 6. Single-run notebooks

## 6.1 `Single_Run_Demo.ipynb`

### Purpose
Run one query end-to-end and print a readable summary.

### Typical use cases
- demonstrate the answerer to a human reviewer,
- inspect one ODP-heavy query,
- inspect retrieval behavior,
- sanity-check the current baseline after code changes.

### Expected behavior
The notebook should:
- initialize the pipeline,
- run one query through `pipe.answer(...)`,
- print a compact final contract summary,
- print rewrites used,
- print top retrieval metadata.

### Important note
The notebook should read current debug fields from:
- `debug["query_plan"]["rewrites"]`
- `debug["retrieval_meta"]`

Older field names such as `debug["rewrites"]` and `debug["retriever_meta"]` are stale and should not be used.

### Typical `pipe.answer(...)` usage in demo mode
- `use_generator=True`
- `run_verify=False`
- `top_k` usually set to `12` or similar

### What the summary output means
Typical printed fields:

- `status`:
  - final contract status,
  - usually one of `OK`, `NO_EVIDENCE`, `PARAMS_REQUIRED`, or `ERROR`
- `odp_required_list`:
  - unresolved ODP identifiers required to finalize the answer
- `evidence_spans_len`:
  - number of final evidence spans in the assembled contract
- `primary_citation`:
  - the single clause identifier used as the primary displayed citation
- `answer_preview`:
  - preview of the assembled deterministic answer text
- `QUR Rewrites Used`:
  - the actual rewrites passed into retrieval
- `Retriever Meta (Top)`:
  - compact retrieval diagnostics such as `num_variants`, `final_top1`, `selected_controls`, `n_docs`

### When to use this notebook
Use this notebook when you care about **one query** and want readability over evaluation detail.

---

## 6.2 `Acceptance_Tests.ipynb`

### Purpose
Run fast regression checks on the current answerer.

### Why this notebook matters
If `pipeline.py` or `generator.py` changes, this notebook should be run before full batch. It protects against accidental breakage of:
- required contract fields,
- status semantics,
- ODP-required behavior,
- schema stability.

### Current test style
The notebook builds the pipeline, loads a gold set, and runs a few targeted checks:
- one `PARAMS_REQUIRED`-like test,
- one nonsense or weak-match query,
- one `OK`-like test,
- optional mini-batch smoke tests.

### Typical settings
Current default pattern:
- `FRAMEWORK_VERSION = "rev5"` or `"rev4"`
- `USE_GENERATOR = True`
- `USE_ORG_PROFILE = False`
- `VERIFY_STRICT_EXTRAS = False`
- `VERIFY_STRICT_VERBATIM = True`
- `VERIFY_STRICT_VERSION = False`
- `TOP_K = 12`

### Why `use_qur=False` here
Acceptance tests are intended to be as deterministic as practical, so the build step typically keeps `use_qur=False`.

### What it validates
At minimum, the notebook should validate that the returned contract contains:
- `answer_text`
- `evidence_spans`
- `status`
- `odp_required_list`
- `primary_citation`
- `all_citations`
- `answer_text_with_citation`
- `contract_mode`

And that:
- `contract_mode == "provably_extractive"`
- `NO_EVIDENCE` has no evidence spans,
- `OK` and `PARAMS_REQUIRED` have at least one evidence span.

### Mini-batch use
This notebook is also the best place to run a **small smoke-test batch** before full batch, for example:
- `gold_df.head(5)`
- a small mixed set of ODP-heavy rows

Use it when you want to confirm that a recent code change did not break the answerer before running the full dataset.

---

## 7. Batch notebooks

## 7.1 Overview

The batch notebooks are the official notebooks for full gold-set evaluation.

They:
- load the correct gold dataset,
- optionally load precomputed QUR rewrites,
- build the pipeline,
- run `pipe.answer(...)` row by row,
- save contract-level outputs,
- compute summary evaluation tables,
- save evaluation reports.

### Rev5 notebook
- path: `batch_run/rev5/Batch_Run.ipynb`
- default `FRAMEWORK_VERSION = "rev5"`

### Rev4 notebook
- path: `batch_run/rev4/Batch_Run_rev4.ipynb`
- default `FRAMEWORK_VERSION = "rev4"`

---

## 7.2 Recommended batch settings

Current stable settings used in the recent baseline runs:

- `USE_QUR_PRECOMPUTED = True`
- `USE_QUR_LIVE = False`
- `USE_ORG_PROFILE = False`
- `VERIFY_STRICT_EXTRAS = False`
- `VERIFY_STRICT_VERBATIM = True`
- `VERIFY_STRICT_VERSION = False`
- `TOP_K = 12`
- `MAX_ROWS = None`

### Important pipeline construction note
The pipeline should be built with:

```python
ComplianceGPTPipeline(..., doc_filter_mode="prefer_smt_keep_params", ...)
```
Note: `prefer_smt_keep_params` is a legacy mode name. In the frozen pipeline, it does not pass standalone ODP/PRM records into the generator. It prioritizes statement records while retaining guidance records, and ODP placeholders are preserved when they appear inside selected clause text.

This matters because batch behavior should match the validated single-run and acceptance-tested routine.

### Why precomputed QUR is preferred in batch
Use precomputed QUR rewrites for batch runs whenever available because:
- it is faster,
- it is more reproducible,
- it avoids introducing runtime variation from live rewrite generation.

---

## 7.3 What the batch notebooks save

Each full run saves two kinds of outputs.

### A. Contract-level CSV
Saved to:

```text
experiments/pipeline_runs/pipeline_<rev>_contracts_<timestamp>.csv
```

Example:
- `pipeline_rev5_contracts_20260312_150620.csv`
- `pipeline_rev4_contracts_20260312_152654.csv`

This CSV contains one row per evaluated query, with fields such as:
- `query_id`
- `framework_version`
- `question`
- `gold_control_id`
- `gold_source_version`
- `gold_resolution_policy`
- `gold_control_path`
- `status`
- `verifier_pass`
- `verifier_errors`
- `primary_citation`
- `all_citations`
- `odp_required_list`
- `selected_source_ids`
- `contract_json`

### B. Evaluation reports
Saved to:

```text
experiments/pipeline_runs/reports/
```

Files produced per run:
- `eval_<rev>_<timestamp>.csv`
- `eval_<rev>_<timestamp>.md`

The markdown report is the easiest artifact to inspect first.

---

## 8. Understanding batch outputs

## 8.1 Contract CSV

This is the raw batch output of the answerer, one row per question.

Important fields:

### `status`
Final contract status.

Typical values:
- `OK`
- `NO_EVIDENCE`
- `PARAMS_REQUIRED`
- `ERROR`

### `verifier_pass`
Boolean that indicates whether the answer contract passed the configured verifier check for that row.

### `verifier_errors`
Pipe-delimited error tags when verification fails.

Typical examples seen in current evaluations:
- `LowControlRecall`
- `MissedDocIds`
- `MissedControlCitations`
- `ODPRequiredListNotEqualGold`
- `PreserveMissingPlaceholder`

### `primary_citation`
The main single citation shown for the answer. Useful for fast inspection, but not a substitute for full citation analysis.

### `all_citations`
All clause identifiers included in the final answer contract.

### `odp_required_list`
All unresolved ODP identifiers surfaced by the final contract.

### `selected_source_ids`
The final source IDs selected for answer assembly.

### `contract_json`
Full serialized contract for audit/debug use. This is the most detailed per-row artifact.

---

## 8.2 Evaluation CSV / Markdown report

The evaluation report aggregates row-level contract outputs into multi-metric summaries.

The markdown report currently contains sections such as:
- `Overall`
- `By status`
- `By gold resolution policy`
- `Top verifier error tags`
- `Strict pass rate vs. gold clause count` (when available)

### Key overall metrics

#### `strict_verifier_pass_rate`
Fraction of rows whose final answer contract passes the configured verifier.

This is the strictest main score.

#### `control_hit_rate`
Fraction of rows where the pipeline hits at least one correct gold control.

This is a very important measure because it shows whether control-level grounding is working even when exact clause matching is imperfect.

#### `control_full_recall_rate`
Fraction of rows where all required gold controls are recovered.

#### `doc_hit_rate`
Fraction of rows where at least one correct gold document/clause path is recovered.

#### `doc_full_recall_rate`
Fraction of rows where the full gold document/clause set is recovered.

#### `avg_evidence_span_count`
Average number of evidence spans per row.

#### `has_evidence_spans_rate`
Fraction of rows that contain at least one evidence span.

#### `avg_verbatim_strict_pass_rate`
Average strict extractive-verbatim score across rows.

#### `avg_verbatim_normalized_pass_rate`
Average normalized extractive-verbatim score across rows.

---

## 9. How to use this folder in practice

## 9.1 Single freeform question

Use:
- `single_run/Single_Run_Demo.ipynb`

Recommended when:
- presenting the system,
- debugging one query,
- checking QUR rewrites,
- checking retrieval diagnostics,
- checking whether ODP behavior looks correct on a specific question.

## 9.2 Regression after code changes

Use:
- `single_run/Acceptance_Tests.ipynb`

Recommended when:
- `pipeline.py` changes,
- `generator.py` changes,
- you changed answer assembly,
- you changed ODP policy behavior,
- you changed schema fields expected by notebooks.

## 9.3 Full evaluation for official numbers

Use:
- `batch_run/rev5/Batch_Run.ipynb`
- `batch_run/rev4/Batch_Run_rev4.ipynb`

Recommended when:
- you want updated official results,
- you want report files for paper/slides/advisor updates,
- you want full gold-set metrics.

---

## 10. Current stable baseline (record)

The current stable answerer baseline is the version that:
- uses the selector-only generator,
- uses the pipeline-owned ODP policy,
- includes the ODP statement rescue guardrail in `pipeline.py`,
- uses `doc_filter_mode="prefer_smt_keep_params"` in validated runs,
- has updated single-run debug display paths,
- passed acceptance checks,
- completed full Rev5 and Rev4 batch runs.

Recent full-run results associated with this stabilized answerer are:

### Rev5
- strict verifier pass rate: `0.64`
- control hit rate: `0.96`
- document hit rate: `0.92`
- evidence-span coverage: `1.0`

### Rev4
- strict verifier pass rate: `0.75`
- control hit rate: `1.00`
- document hit rate: `0.9722`
- evidence-span coverage: `1.0`

These results indicate that the current answerer is stable enough to serve as the current ComplianceGPT baseline for writing and presentation, while remaining errors are mostly concentrated in clause-granularity and ODP-list exactness rather than routine-level architectural failure.

---

## 11. Relationship to other experiment folders

This pipeline folder should be distinguished from the following experiment areas under `experiments/`:

### `experiments/retriever_ablation/`
This contains retriever-only system comparisons such as S1–S7, error analysis, benchmark notebooks, and retriever result reports.

### `experiments/micro_ablations/`
This contains the matched S4/S4b and S7/S7a rewrite diagnostic. The standalone
runner is authoritative; the notebook is retained only as an exploratory
interface.

### `experiments/pipeline_runs/`
This contains official pipeline run outputs and evaluation reports.

Practical rule:
- if you are running the end-to-end answerer, use `pipeline/`
- if you are studying retriever variants, use `experiments/retriever_ablation/`
- if you are reproducing the matched rewrite diagnostic, use the standalone
  runner in `experiments/micro_ablations/`
- if you are inspecting saved pipeline artifacts, use `experiments/pipeline_runs/`

---

## 12. Maintenance rules

Recommended maintenance rules for this folder:

1. Keep only one demo notebook in `single_run/`.
2. Keep only one acceptance/regression notebook in `single_run/`.
3. Keep Rev5 and Rev4 batch notebooks separate to reduce accidental config drift.
4. Save outputs to `experiments/pipeline_runs/`, not inside `pipeline/`.
5. Update this README whenever:
   - the notebook set changes,
   - contract fields change,
   - output directory conventions change,
   - batch result interpretation changes.

---

## 13. Quick start

### Single query demo
1. Open `single_run/Single_Run_Demo.ipynb`
2. Set the query text
3. Build the pipeline
4. Run the demo cell
5. Inspect:
   - status
   - ODP list
   - evidence count
   - primary citation
   - rewrites used
   - retrieval meta

### Acceptance check
1. Open `single_run/Acceptance_Tests.ipynb`
2. Set framework version and verifier knobs
3. Build pipeline
4. Run the acceptance cells
5. Confirm the summary completes successfully

### Rev5 full batch
1. Open `batch_run/rev5/Batch_Run.ipynb`
2. Confirm user config
3. Confirm `doc_filter_mode="prefer_smt_keep_params"` in pipeline construction
4. Run full notebook
5. Inspect saved files in `experiments/pipeline_runs/`

### Rev4 full batch
1. Open `batch_run/rev4/Batch_Run_rev4.ipynb`
2. Confirm user config
3. Confirm `doc_filter_mode="prefer_smt_keep_params"` in pipeline construction
4. Run full notebook
5. Inspect saved files in `experiments/pipeline_runs/`

---

## 14. Final note

This folder should now be treated as the **official operational surface** of the ComplianceGPT answerer. The goal is not to maximize notebook count, but to keep a small, stable, understandable interface:
- one demo notebook,
- one acceptance notebook,
- one Rev5 batch notebook,
- one Rev4 batch notebook,
- one canonical `pipeline.py`.

That structure is sufficient for demo, regression checking, and formal evaluation.
