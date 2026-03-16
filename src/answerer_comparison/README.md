# Answerer Comparison (RQ2)

This folder contains the **RQ2 answerer-vs-answerer comparison** for ComplianceGPT.

The purpose of this comparison is to test the dissertation claim that, **holding retrieval broadly fixed**, the main gain of ComplianceGPT comes from **safe final answer construction**, not merely from reaching the right neighborhood of controls.

In this comparison:

- **ComplianceGPT** uses the current selector-only answerer with deterministic citation-contract assembly.
- **Generative RAG baseline** uses the same retrieval stack but replaces deterministic final assembly with a normal free-form LLM answerer.

The core question is:

> When the retriever is already competitive, does a standard generative answerer still fail in ways that matter for compliance, especially on organization-defined parameters (ODPs)?

The current results say **yes**.

---

## Files in this folder

- `answerer_compare.py`
  - builds committee-facing metric tables
  - builds head-to-head comparison tables
  - builds status disagreement matrices
  - extracts representative failure examples

Related files outside this folder:

- `../generative_answerer/generator.py`
- `../generative_answerer/pipeline.py`
- `../generative_answerer/Batch_Run_Generative_Baseline_Compare.ipynb`

---

## What was compared

### System A: ComplianceGPT

Current answerer path:

- ComplianceGPT retrieval stack
- QUR-enabled retrieval preparation
- selector-only generator
- deterministic citation-contract assembly
- verifier-based evaluation

### System B: Generative RAG baseline

Baseline answerer path:

- same ComplianceGPT retrieval stack
- same retrieval preparation path
- same general model family
- free-form generative final answer
- same evaluation datasets

This is the correct RQ2 baseline because it isolates the answer-construction question.

It does **not** ask whether retrieval matters. That was already addressed by the S1-S7 retrieval ladder.

It asks whether a normal generative answerer remains unsafe even when retrieval is already strong.

---

## Datasets used

Two gold datasets were used.

- **Rev5 gold set**: 100 questions
- **Rev4 gold set**: 36 questions

The current RQ2 comparison was run in the **no-profile** setting. That detail matters for ODP interpretation:

- if an answer depends on unresolved organization-defined parameters,
- and there is no approved profile value to fill them,
- then the correct behavior is to return **`PARAMS_REQUIRED`**, not a complete-looking final answer.

---

## Read this first: what these metrics mean, and what they do NOT mean

### These metrics do **not** mean the answer text is 100% identical to the gold answer text

This comparison is **not** mainly a natural-language exact-match evaluation.

A metric like **Audit-Ready Answer Rate**, it does **not** mean:

- the generated answer sentence is identical to the gold wording,
- the model reproduced the gold answer text word for word,
- or the system got every phrasing detail exactly the same as the gold set.

Instead, this comparison asks whether the system made the **correct compliance decision** and whether the final answer satisfied the project's answer contract.

### What the gold set is used for here

The gold set is used mainly to check things like:

- did the system reach the **right control**?
- did it reach the **right clause(s)**?
- did it recover the **full gold clause set**, when that is required?
- did it produce a final status consistent with the gold expectation, especially for ODP cases?
- did it avoid pretending an unresolved ODP requirement was complete?

So the gold set here is functioning mainly as a **compliance-decision and evidence reference**, not as a single target paragraph that the system must copy exactly.

### What “audit-ready” means in this README

In this README, **audit-ready** means:

> the final answer passed the project's strict contract-validity check for this experiment.

In plain language, that means the answer was acceptable under the current evaluation rules as a safe, contract-valid compliance answer.

It does **not** mean the answer text was literally the same as the gold answer text.

### Why this matters for RQ2

This distinction is important because RQ2 is trying to show that:

- a system can retrieve the right control,
- and even produce a fluent answer,
- but still be **unsafe** if it hides unresolved ODPs or presents incomplete requirements as complete.

That is why this comparison emphasizes:

- audit-ready answer rate,
- ODP correct handling rate,
- ODP false complete rate,
- and right control found rate.

Those metrics are more important here than natural-language similarity.

---

## Main result in one sentence

**The generative baseline often still finds the right control, but it fails at safe final answer construction, especially by producing falsely complete answers on ODP-bearing questions.**

---

## Polished result tables

### Committee-facing summary table

These are the four clearest metrics to show on a slide.

| Framework | System | Audit-Ready Answer Rate | Right Control Found Rate | ODP Correct Handling Rate | ODP False Complete Rate |
|---|---|---:|---:|---:|---:|
| Rev5 | ComplianceGPT | 0.64 | 0.96 | 1.00 | 0.000 |
| Rev5 | Generative RAG baseline | 0.22 | 0.91 | 0.00 | 0.952 |
| Rev4 | ComplianceGPT | 0.750 | 1.00 | 1.00 | 0.000 |
| Rev4 | Generative RAG baseline | 0.222 | 1.00 | 0.00 | 1.000 |

### Interpretation of the summary table

- On **Rev5**, the baseline still finds the right control reasonably often (`0.91`), but its **audit-ready answer rate** drops to `0.22`, and its **ODP false complete rate** rises to `0.952`.
- On **Rev4**, both systems find the right control equally well (`1.00`), yet the baseline still collapses on safe final handling: **ODP correct handling rate** is `0.00`, and **ODP false complete rate** is `1.00`.
- This means the decisive difference is **not simply retrieval**. The decisive difference is **what the system does after retrieval**, when it has to turn evidence into a final compliance answer.

---

## Full current system tables

### Rev5

| System | n Questions | Audit-Ready Answer Rate | Right Control Found Rate | Right Clause Found Rate | Full Gold Clause Coverage Rate | Answer Has Supporting Evidence Rate | Average Supporting Span Count | Strict Verbatim Grounding Rate | Normalized Verbatim Grounding Rate | n ODP Questions | ODP Correct Handling Rate | ODP False Complete Rate | ODP Unresolved Detected Rate | ODP Unresolved Hidden Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ComplianceGPT | 100 | 0.64 | 0.96 | 0.92 | 0.64 | 1.00 | 4.01 | 1.0 | 1.0 | 63 | 1.0 | 0.000000 | 1.000000 | 0.000000 |
| Generative RAG baseline | 100 | 0.22 | 0.91 | 0.77 | 0.48 | 0.95 | 3.39 | 1.0 | 1.0 | 63 | 0.0 | 0.952381 | 0.365079 | 0.634921 |

### Rev4

| System | n Questions | Audit-Ready Answer Rate | Right Control Found Rate | Right Clause Found Rate | Full Gold Clause Coverage Rate | Answer Has Supporting Evidence Rate | Average Supporting Span Count | Strict Verbatim Grounding Rate | Normalized Verbatim Grounding Rate | n ODP Questions | ODP Correct Handling Rate | ODP False Complete Rate | ODP Unresolved Detected Rate | ODP Unresolved Hidden Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ComplianceGPT | 36 | 0.750000 | 1.0 | 0.972222 | 0.750000 | 1.0 | 4.222222 | 1.0 | 1.0 | 19 | 1.0 | 0.0 | 1.000000 | 0.000000 |
| Generative RAG baseline | 36 | 0.222222 | 1.0 | 0.833333 | 0.555556 | 1.0 | 2.722222 | 1.0 | 1.0 | 19 | 0.0 | 1.0 | 0.315789 | 0.684211 |

---

## Head-to-head comparison tables

These metrics compare the two systems directly on the same question sets.

### Head-to-head summary

| Framework | n Compared Questions | ComplianceGPT Strict Win Rate | Generative False Complete vs ComplianceGPT Safe Warning Rate | Generative Missed Right Control vs ComplianceGPT Rate | Same Final Status Rate |
|---|---:|---:|---:|---:|---:|
| Rev5 | 100 | 0.440000 | 0.780000 | 0.05 | 0.170000 |
| Rev4 | 36 | 0.527778 | 0.777778 | 0.00 | 0.222222 |

### Interpretation

- **ComplianceGPT Strict Win Rate**
  - Rev5: `0.44`
  - Rev4: `0.527778`
  - Meaning: on a large fraction of questions, ComplianceGPT passes strict contract validity where the generative baseline does not.

- **Generative False Complete vs ComplianceGPT Safe Warning Rate**
  - Rev5: `0.78`
  - Rev4: `0.777778`
  - Meaning: on roughly **78%** of questions in both datasets, the generative baseline returns `OK` where ComplianceGPT returns `PARAMS_REQUIRED`.
  - This is the most important head-to-head failure pattern.

- **Same Final Status Rate**
  - Rev5: `0.17`
  - Rev4: `0.222222`
  - Meaning: the two systems are not merely phrasing the same answer differently. They are making materially different final compliance decisions.

---

## Status disagreement matrices

### Rev5

| Baseline Status | ComplianceGPT Status | Count |
|---|---|---:|
| OK | OK | 17 |
| OK | PARAMS_REQUIRED | 78 |
| NO_EVIDENCE | PARAMS_REQUIRED | 2 |
| ERROR | PARAMS_REQUIRED | 3 |

### Rev4

| Baseline Status | ComplianceGPT Status | Count |
|---|---|---:|
| OK | OK | 8 |
| OK | PARAMS_REQUIRED | 28 |

### Interpretation

The dominant disagreement pattern is not random.

It is:

- **Generative baseline: `OK`**
- **ComplianceGPT: `PARAMS_REQUIRED`**

That means the baseline most often fails by presenting an underspecified requirement as if it were complete.

---

## Why the ODP result matters so much

This is the strongest part of the current RQ2 result.

For compliance work, a system should **not** present a requirement as fully answerable when the standard still contains unresolved organization-defined parameters.

The main danger is not just “wrong wording.”
The main danger is **false completeness**.

That is exactly the behavior shown here:

- ComplianceGPT consistently surfaces unresolved ODP conditions.
- The generative baseline usually suppresses them and answers as if the requirement were complete.

This makes the comparison much stronger than a generic “RAG vs RAG” comparison. It shows a specific, compliance-relevant failure mode that the dissertation is designed to prevent.

---

## Metric guide

### First, the count columns

#### `n_questions`
Number of questions evaluated for that system on that framework.

#### `n_compared_questions`
Number of paired questions used in the direct head-to-head comparison.

#### `n_odp_questions`
Number of questions in that dataset that are ODP-bearing for the current evaluation setup.

### Primary committee-facing metrics

#### `audit_ready_answer_rate`
Fraction of questions whose final answer passes strict contract validity.

Use this as the main overall answer-quality metric for RQ2.

Important: this does **not** mean the final answer text is 100% identical to the gold answer text. It means the final answer satisfied the project's contract-validity rules for this experiment.

#### `right_control_found_rate`
Fraction of questions where the system reaches the correct gold control.

Use this as the retrieval sanity metric.

#### `odp_correct_handling_rate`
For the current **no-profile** RQ2 setting, this means:

- the question is ODP-bearing, and
- the system correctly returns `PARAMS_REQUIRED` rather than pretending the requirement is complete.

This is a success metric. Higher is better.

#### `odp_false_complete_rate`
For ODP-bearing questions, the fraction where the system returns `OK` even though the requirement is still unresolved.

This is the clearest failure metric for the generative baseline.

### Supporting metrics

#### `right_clause_found_rate`
Fraction of questions where the system reaches the correct gold clause.

#### `full_gold_clause_coverage_rate`
Fraction of questions where the full gold clause set is recovered.

#### `answer_has_supporting_evidence_rate`
Fraction of questions with at least one supporting evidence span.

#### `average_supporting_span_count`
Average number of supporting evidence spans in the final output.

#### `odp_unresolved_detected_rate`
On ODP-bearing questions, fraction where the system explicitly surfaces unresolved ODP structure through either `PARAMS_REQUIRED` or a non-empty ODP-required list.

#### `odp_unresolved_hidden_rate`
On ODP-bearing questions, fraction where the system hides unresolved ODP structure.

#### `strict_verbatim_grounding_rate`
Fraction of questions passing the current strict verbatim grounding check.

This metric is currently reported for completeness, but it is **not** a headline RQ2 metric in this README.

#### `normalized_verbatim_grounding_rate`
Fraction of questions passing the current normalized verbatim grounding check.

This metric is currently reported for completeness, but it is **not** a headline RQ2 metric in this README.

### Head-to-head metrics

#### `compliancegpt_strict_win_rate`
Fraction of compared questions where ComplianceGPT passes strict validity and the generative baseline does not.

This is one of the most important RQ2 metrics.

#### `generative_false_complete_vs_compliancegpt_safe_warning_rate`
Fraction of compared questions where the generative baseline returns `OK` while ComplianceGPT returns `PARAMS_REQUIRED`.

This is one of the most important RQ2 metrics.

#### `generative_missed_right_control_vs_compliancegpt_rate`
Fraction of compared questions where the generative baseline misses the right control while ComplianceGPT finds it.

#### `same_final_status_rate`
Fraction of compared questions where both systems return the same final status.

---

## Important caveat

The current `strict_verbatim_grounding_rate` and `normalized_verbatim_grounding_rate` are both `1.0` for both systems in these runs.

That looks too optimistic for the generative baseline and should **not** be treated as a headline RQ2 claim until that metric path is audited specifically for free-form answers.

For now, the strongest and safest RQ2 claims are:

- **audit-ready answer rate**
- **ODP correct handling rate**
- **ODP false complete rate**
- **right control found rate**
- **status disagreement pattern**

---

## Representative failure pattern

The most representative failure pattern is:

- retriever reaches the correct control neighborhood,
- generative baseline returns `OK`,
- ComplianceGPT returns `PARAMS_REQUIRED`,
- the baseline answer sounds fluent and plausible,
- but it suppresses unresolved ODP structure.

This is exactly the kind of compliance failure that ordinary generative RAG is prone to, and exactly the kind of failure ComplianceGPT is designed to reduce.

---

## How to rerun this comparison

### Batch notebook

Use:

- `../generative_answerer/Batch_Run_Generative_Baseline_Compare.ipynb`

This notebook should:

1. run the generative baseline on Rev5 and Rev4,
2. save baseline contracts and baseline eval CSVs,
3. load the current ComplianceGPT batch outputs,
4. call `answerer_compare.py`,
5. write comparison CSVs and markdown reports.

### Comparison helper

Core entry point:

- `compare_answerers(...)` in `answerer_compare.py`

It returns:

- `system_table`
- `head_to_head`
- `status_matrix`
- `failure_examples`
- `baseline_eval_augmented`
- `compliance_eval_augmented`

If `output_dir` is provided, it also writes those tables to disk and produces a markdown report.

---

## Recommended slide/table version

If space is limited, use only this table:

| Framework | System | Audit-Ready Answer Rate | Right Control Found Rate | ODP Correct Handling Rate | ODP False Complete Rate |
|---|---|---:|---:|---:|---:|
| Rev5 | ComplianceGPT | 0.64 | 0.96 | 1.00 | 0.000 |
| Rev5 | Generative RAG baseline | 0.22 | 0.91 | 0.00 | 0.952 |
| Rev4 | ComplianceGPT | 0.750 | 1.00 | 1.00 | 0.000 |
| Rev4 | Generative RAG baseline | 0.222 | 1.00 | 0.00 | 1.000 |

Suggested spoken summary:

> With retrieval held nearly constant, the generative answerer often still finds the right control, but it fails at safe final answer construction. Its dominant failure mode is false completeness on ODP-bearing questions. ComplianceGPT instead consistently surfaces unresolved parameters and returns the correct safe warning status.

---

## Current take-away

As of the current runs, the RQ2 result is already strong enough to support a clear claim:

> The value of ComplianceGPT is not only that it retrieves relevant controls. The stronger contribution is that it converts retrieved evidence into a safer final compliance decision, especially by avoiding false completion on unresolved ODP-bearing requirements.

This is the main reason the answerer comparison should appear in both the paper and the defense.
