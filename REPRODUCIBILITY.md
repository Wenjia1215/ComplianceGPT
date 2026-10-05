# Reproducing ComplianceGPT Evaluations

This repository retains the source, canonical inputs, recorded outputs, and
run-specific provenance for the evaluations reported for ComplianceGPT. The
workflows use Google Colab or a CUDA-capable Python environment and may download
third-party model weights.

## Repository identity and historical boundary

The dissertation's frozen inputs and reported output artifacts are tied to
the public evaluation baseline:

```text
repository: https://github.com/Wenjia1215/ComplianceGPT
branch:     main
commit:     da0ea7d5e964a67b193e1e59ba4d933760f3ba79
```

The preserved public branch `history/pre-public-cleanup-2026-07-29` resolves to
`1f15049c70b29fb29d2785765dcf45dc1123ceff`, verified directly against its public
Git reference during the completed-review publication. This corrects the earlier
unavailable commit pointer. That branch is historical provenance, not the
recommended execution target. Historical local execution identities and public
publication identities are distinguished in experiment-specific records.

Current source may contain clearly identified documentation and regression
patches made after the frozen evaluation. Such patches do not retroactively
change stored outputs or their metrics.

## Evaluation map

| Evaluation | Canonical entry point | Recorded results |
|---|---|---|
| S1–S7 governing-control retrieval | `experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb` | `experiments/retriever_ablation/ablation_outputs/` |
| Matched answer construction | `experiments/answerer_comparison/rq2_matched/run_matched_rq2.py` | `experiments/answerer_comparison/rq2_matched/results_v3/` |
| Control-gate width sensitivity | `experiments/answerer_comparison/rq2_control_gate_width/run_control_gate_width.py` | `experiments/answerer_comparison/rq2_control_gate_width/results_v1/` |
| Rev. 4 BF16 generative baseline | `experiments/answerer_comparison/rq2_bf16_baseline/run_bf16_baseline.py` | `experiments/answerer_comparison/rq2_bf16_baseline/results_v1/` |
| Rev. 4 frontier API baseline | `experiments/answerer_comparison/rq2_frontier_baseline/run_frontier_baseline.py` | `experiments/answerer_comparison/rq2_frontier_baseline/results_v1/` |
| No-selector ablation | `experiments/answerer_comparison/rq2_no_selector/run_no_selector_ablation.py` | `experiments/answerer_comparison/rq2_no_selector/results_v1/` |
| ODP-statement rescue ablation | `experiments/answerer_comparison/rq2_rescue_ablation/run_rescue_ablation.py` | `experiments/answerer_comparison/rq2_rescue_ablation/results_v1/` |
| Runtime Verifier mutation evaluation | `experiments/answerer_comparison/runtime_verifier_mutation/run_verifier_mutations.py` | `experiments/answerer_comparison/runtime_verifier_mutation/results_v1/` |
| Per-identifier runtime provenance | `experiments/answerer_comparison/rq2_identifier_provenance/run_identifier_provenance.py` | `experiments/answerer_comparison/rq2_identifier_provenance/results_v1/` |
| Synthetic profile resolution | `experiments/answerer_comparison/rq2_profile_fill_v2/run_profile_fill.py` | `experiments/answerer_comparison/rq2_profile_fill_v2/results_v2/` |
| Primary RQ1 constant sensitivity | `experiments/retriever_ablation/constant_sensitivity/run_sensitivity.py` | `experiments/retriever_ablation/constant_sensitivity/results/rq1_constant_sensitivity_v1/` |
| Natural-question complete answer paths | `experiments/external_validity/natural_questions_v2/run_natural_questions.py` | `experiments/external_validity/natural_questions_v2/results_v1/` |
| Completed natural-question author review | `experiments/external_validity/natural_questions_v2/import_author_review.py` | `experiments/external_validity/natural_questions_v2/results_v1/author_review_v1/` |
| Secondary rewrite diagnostics | `experiments/micro_ablations/run_micro_ablations.py` | `experiments/micro_ablations/` |
| Runtime contract validation | `experiments/runtime_validation/revalidate_contracts.py` | `experiments/runtime_validation/outputs/` |
| Single-query demonstration | `src/compliancegpt/pipeline/single_run/Single_Run_Demo.ipynb` | generated during execution |

The S1–S7 retrieval results, corrected matched answerer results, no-selector
ablation, ODP-statement rescue ablation, Runtime Verifier mutation evaluation,
per-identifier provenance replay, secondary diagnostics, and runtime validation
are distinct result families. Do not substitute one for another.
Their mechanism-by-mechanism boundary is recorded in
[`EVALUATION_CONFIGURATIONS.md`](EVALUATION_CONFIGURATIONS.md), and the
provenance and limitation of every material fixed constant is recorded in
[`CONSTANTS_PROVENANCE.md`](CONSTANTS_PROVENANCE.md).

## Canonical inputs

The NIST source files, Canonical Clause Store files, gold datasets, ErrorBank,
ODP registries, and example organization profiles used by the reported
evaluations are identified in
[`EVALUATION_INPUT_CHECKSUMS.md`](EVALUATION_INPUT_CHECKSUMS.md).
The exact upstream NIST OSCAL tag, resolved commit, source URLs, embedded
metadata, and SP 800-53/SP 800-53A relationship are recorded in
[`data/DATA_VERSIONS.md`](data/DATA_VERSIONS.md).

Verify all listed inputs from the repository root:

```bash
python - <<'PY'
import hashlib
import pathlib
import re

manifest = pathlib.Path("EVALUATION_INPUT_CHECKSUMS.md").read_text()
rows = re.findall(r"\| `([^`]+)` \| `([0-9a-f]{64})` \|", manifest)
for path_text, expected in rows:
    path = pathlib.Path(path_text)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"checksum mismatch: {path}")
print(f"verified {len(rows)} evaluation inputs")
PY
```

## S1–S7 retrieval evaluation

Open
[`AblationStudy_S1_7.ipynb`](experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb)
in Colab and follow
[`experiments/retriever_ablation/WORKFLOW.md`](experiments/retriever_ablation/WORKFLOW.md).
The stored outputs identify the notebook-local implementation used for the
reported retrieval results. Current-source diagnostics are reported separately
under `experiments/micro_ablations/`.

## Matched answerer evaluation

Install the recorded Colab dependencies and run:

```bash
python -m pip install -r experiments/answerer_comparison/rq2_matched/requirements-colab.txt
python experiments/answerer_comparison/rq2_matched/run_matched_rq2.py \
  --repo-root . \
  --output-dir /path/to/compliancegpt_rq2_matched_v3
```

The validated evidence package is
`experiments/answerer_comparison/rq2_matched/results_v3/compliancegpt_rq2_matched_v3.zip`.
Its SHA-256 is:

```text
56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328
```

The result record identifies:

- runner commit `be862bcadfa61b474d795303e01ce9394909fdcc`;
- model `Qwen/Qwen2.5-7B-Instruct`;
- model and tokenizer revision
  `a09a35458c702b33eeacc393d103063234e8bc28`;
- deterministic settings, code hashes, input hashes, context hashes, and
  output hashes.

See
[`experiments/answerer_comparison/rq2_matched/results_v3/README.md`](experiments/answerer_comparison/rq2_matched/results_v3/README.md)
for the validation boundary and reported results.

## Control-gate width sensitivity

The registered follow-on study reuses the immutable RQ2 v3 retrieval traces
and changes only the fixed control-gate width. The four widths are top 1, 2,
3, and 5; adaptive widening is disabled for those four experimental settings,
and the released adaptive v3 result remains an unchanged reference.

Prepare and audit all 544 gold-free contexts without loading a model:

```bash
python experiments/answerer_comparison/rq2_control_gate_width/run_control_gate_width.py \
  --output-dir /path/to/rq2_control_gate_width_v1 \
  --prepare-only
```

Run the complete selector sweep on a persistent CUDA runtime:

```bash
python experiments/answerer_comparison/rq2_control_gate_width/run_control_gate_width.py \
  --output-dir /path/to/rq2_control_gate_width_v1
```

The full run uses the same pinned Qwen revision and 4-bit setting as RQ2 v3,
checkpoints every question, and resumes only when all source, code, context,
and model identities match. The preparation audit measures evidence-window
opportunity only; it is not an end-to-end selector result.

The completed A100 result, including all 544 fixed-width contexts and 544
row-level selector contracts, is recorded under
[`experiments/answerer_comparison/rq2_control_gate_width/results_v1/`](experiments/answerer_comparison/rq2_control_gate_width/results_v1/).
The canonical result archive SHA-256 is:

```text
543c2e40879422a5a1462bb6fc56fda2ad76f9b060efbc780ebe2a51bc48a07d
```

Fixed top 2 matched the adaptive reference's strict-pass count on both
revisions. The stored within-revision exact McNemar comparisons found no
significant strict-pass difference at the 0.05 level. ODP sensitivity,
specificity, and status precision use current author labels and have not been
independently adjudicated. The full independent annotation study is scoped as
future validation rather than a pending condition on these recorded results.

## Rev. 4 BF16 generative baseline

Batch 5B isolates the quantization setting for the free-form RQ2 baseline. It
reuses the 36 immutable Rev. 4 contexts from RQ2 v3 and the exact source tree
recorded at commit `be862bcadfa61b474d795303e01ce9394909fdcc`. The only
experimental change is loading the same pinned Qwen2.5-7B revision in
`torch.bfloat16` instead of 4-bit.

Verify the registered inputs without a GPU:

```bash
python experiments/answerer_comparison/rq2_bf16_baseline/run_bf16_baseline.py \
  --output-dir /path/to/rq2_bf16_baseline_v1 \
  --prepare-only
```

Run the 36-row experiment on an A100 (preferred) or another CUDA GPU with
native BF16 and sufficient memory:

```bash
python -m pip install -r experiments/answerer_comparison/rq2_matched/requirements-colab.txt
python experiments/answerer_comparison/rq2_bf16_baseline/run_bf16_baseline.py \
  --output-dir /path/to/rq2_bf16_baseline_v1
```

T4 is intentionally rejected because it lacks native BF16 support. The runner
verifies all floating parameter dtypes and the absence of a quantizer,
checkpoints each question, and compares the completed BF16 output with the
unchanged frozen 4-bit baseline and ComplianceGPT references. This is a
within-model quantization-sensitivity study, not a frontier-model comparison.
Open
[`Batch_5B_Rev4_BF16_Baseline.ipynb`](experiments/answerer_comparison/rq2_bf16_baseline/Batch_5B_Rev4_BF16_Baseline.ipynb)
for the Drive-first Colab workflow.

The complete supplied A100 evidence package and independent audit are archived under
[`experiments/answerer_comparison/rq2_bf16_baseline/results_v1/`](experiments/answerer_comparison/rq2_bf16_baseline/results_v1/).
The exact supplied Google Drive export has SHA-256:

```text
4039e67453d46b12ad214a3759d16e5a4c9f1028353dd6e253fca06f3b57a561
```

The executed notebook records 36/36 completed rows, a BF16-only parameter
inventory, and no attached quantizer. BF16 and the frozen 4-bit baseline each
passed 8/36 strict contracts; their two-versus-two discordance gives an exact
two-sided McNemar value of `1.0`. Frozen 4-bit ComplianceGPT passed 29/36 and
had 21 exclusive passes against BF16 (`p = 9.5367432e-07`).

## Rev. 4 frontier API baseline

Batch 5C runs the same 36 immutable Revision 4 questions, ordered contexts,
free-form prompt, parser, ODP policy, and offline verifier against the stable
Gemini API model `gemini-3.5-flash`. The model and serving runtime change, so
this is a stronger-system comparison rather than a one-factor precision study.

The completed Paid Tier 1 result is archived under
[`experiments/answerer_comparison/rq2_frontier_baseline/results_v1/`](experiments/answerer_comparison/rq2_frontier_baseline/results_v1/).
It contains 36 unique completed API responses, no parse retries, and no
orphaned calls. Gemini passed 24/36 strict contracts, compared with 8/36 for
each Qwen baseline and 29/36 for frozen ComplianceGPT. The exact paired
McNemar values were `0.00040245` against either Qwen baseline and `0.2265625`
against ComplianceGPT.

The byte-exact runner archive has SHA-256
`039ce427f717b83da6f54a87a67bb0438f6c15e44b49d29838d39bc523c20767`.
The public corrected archive changes only paid-tier provenance in
`run_config.json` and the dependent output-manifest hashes; its SHA-256 is
`351af9780f0ed7e6714ed3eb81799e8793985ea8b14351f32da9e43ebefa0dfb`.

## Rev. 5 frontier API baseline

The pre-committed Batch 5D study applies the same stable
`gemini-3.5-flash` protocol to all 100 frozen Revision 5 contexts. The complete
result, executed A100 notebook, raw API log, contracts, manifests, archive, and
independent audit are retained under
[`experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/`](experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/).

The run completed with 100 unique API responses, one call per row, no parse
retries, and no orphaned calls. ComplianceGPT and Gemini passed 65/100 and
66/100 strict contracts. Their paired discordance was 11 versus 12 with exact
two-sided McNemar `p = 1.0`; no accuracy direction is claimed. Coverage-complete
realization loss was 0/65 for ComplianceGPT and 1/67 for Gemini, with Fisher
exact `p = 1.0`. The observed zero for ComplianceGPT confirms the deterministic
construction on this benchmark; it is not presented as an estimated zero-risk
rate.

The byte-exact result archive SHA-256 is
`9f088b2ccb410fdd6df8980d693529320fec351e9a01e7400cd7d48fc55dddef`.
The original executed-notebook bytes remain addressable at public commit
`e00f9cdf77b1ad45a42df0a0bddd338de744266f` with SHA-256
`2e96e47c83f4d02e04b992a81d76cb3c8e670cffbc876d3329437637a1247fcc`.
Repository-only Colab/tool metadata was later removed without changing cell
sources, execution counts, outputs, attachments, or notebook format. The
sanitized distributed notebook at public commit
`487f207edc578930cd66a53ff524e12d8edfbec3` has SHA-256
`d4cafb9d32ddf1e51516bb1b08eb6d1037cc99e05ed5e0ef9894fbb358a751af`;
the semantic projection of both versions has SHA-256
`a84858d01a08076445c9597902e95a15151d7ebd14e50d4ae43321ee53f1bee0`.

The consolidated Batch 5A–5D comparison is
[`experiments/answerer_comparison/RQ2_BATCH_5_COMPARISON.md`](experiments/answerer_comparison/RQ2_BATCH_5_COMPARISON.md).

## No-selector ablation

The no-selector ablation reuses the immutable contexts and ComplianceGPT
contracts in the validated RQ2 v3 package. It retains every statement and
guidance record in each frozen bounded evidence window, performs no model
inference or new retrieval, and applies the ordinary no-profile `ASK` policy
before evaluation. Run it from the repository root:

```bash
python experiments/answerer_comparison/rq2_no_selector/run_no_selector_ablation.py \
  --output-dir /path/to/rq2_no_selector_v1
```

The script refuses an existing output directory. The recorded result identity
is `rq2_no_selector_v1`; its checked-in summary, per-row comparison, run
configuration, and result archive are under
[`experiments/answerer_comparison/rq2_no_selector/results_v1/`](experiments/answerer_comparison/rq2_no_selector/results_v1/).
The SHA-256 of `experiments/answerer_comparison/rq2_no_selector/results_v1.zip`
is:

```text
470d75f469ee6c823c22fc0695da368ada85295ecc3ec4f5a2cf536ef5ba816e
```

This post hoc experiment measures the coverage-versus-review-burden tradeoff
and does not replace the frozen RQ2 v3 result family.

## ODP-statement rescue ablation

The rescue ablation consumes the same immutable RQ2 v3 package. It reconstructs
the recorded selector or fallback state immediately before bounded
ODP-statement rescue and creates paired rescue-off and rescue-on contracts. The
replay performs no retrieval or model inference, and it refuses to report an
effect unless every rescue-on core contract matches the corresponding frozen
ComplianceGPT contract. Run it from the repository root:

```bash
python experiments/answerer_comparison/rq2_rescue_ablation/run_rescue_ablation.py \
  --output-dir /path/to/rq2_rescue_ablation_v1
```

The recorded result identity is `rq2_rescue_ablation_v1`; its checked-in
summary, paired row data, four contract CSVs, run configuration, and archive
are under
[`experiments/answerer_comparison/rq2_rescue_ablation/results_v1/`](experiments/answerer_comparison/rq2_rescue_ablation/results_v1/).
The SHA-256 of
`experiments/answerer_comparison/rq2_rescue_ablation/results_v1.zip` is:

```text
a2bc5a122dfe391f605276eb896d7ae036bf42b8f8330019556dec97db5e8ea4
```

The replay measures the implemented rescue rule on fixed selector outputs. Its
status changes on author-labeled non-ODP rows are descriptive review-scope
expansion, not a false-positive rate or specificity estimate.

## Runtime Verifier mutation evaluation

The mutation evaluation consumes the 136 valid ComplianceGPT contracts in the
immutable RQ2 v3 archive and first requires every original contract to pass the
gold-independent Runtime Verifier. It then changes one runtime-visible field at
a time through five deterministic operators: a valid active-revision source-ID
swap, a one-character span alteration, a Rev. 4-only ID inserted into a Rev. 5
contract, removal of one ODP-list entry, and an `OK`/`PARAMS_REQUIRED` status
flip. Run it from the repository root:

```bash
python experiments/answerer_comparison/runtime_verifier_mutation/run_verifier_mutations.py \
  --output-dir /path/to/runtime_verifier_mutation_v1
```

The recorded result identity is `runtime_verifier_mutation_v1`. The checked-in
baseline qualification, complete 136 × 5 applicability matrix, 619 mutated
contracts, operator summaries, run configuration, and sibling archive are
under
[`experiments/answerer_comparison/runtime_verifier_mutation/results_v1/`](experiments/answerer_comparison/runtime_verifier_mutation/results_v1/).
The SHA-256 of
`experiments/answerer_comparison/runtime_verifier_mutation/results_v1.zip` is:

```text
8bbb98b0f40299a5d46cf0106262c3d3437eb0ffcbbb0111c2d3ab1172f86366
```

Detection rates are reported per operator. They establish behavior only for
the defined mutations and implemented structural predicates; they do not
measure evidence completeness, semantic correctness, or legal sufficiency.

## Per-identifier runtime provenance

The provenance replay consumes the immutable RQ2 v3 contracts and prepared
evidence windows. It reconstructs each frozen selector or fallback state,
executes the implemented bounded rescue rule, and refuses the row unless the
reconstructed core contract equals the frozen contract. It then emits one
positive origin for every final source identifier: `selector`, `fallback`,
`rescue`, or `hierarchy`.

Run it from the repository root:

```bash
PYTHONPATH=src python experiments/answerer_comparison/rq2_identifier_provenance/run_identifier_provenance.py \
  --output-dir /path/to/rq2_identifier_provenance_v1
```

The recorded result identity is `rq2_identifier_provenance_v1`. The checked-in
full contracts, occurrence-level provenance, contract-level audit table,
summary, run configuration, and sibling archive are under
[`experiments/answerer_comparison/rq2_identifier_provenance/results_v1/`](experiments/answerer_comparison/rq2_identifier_provenance/results_v1/).
The SHA-256 of
`experiments/answerer_comparison/rq2_identifier_provenance/results_v1.zip` is:

```text
357d5af80874ef1cfe14ea3cb05a11592ee916b8fd222e4c05df54bf8d2ec38d
```

All 582 final identifier occurrences across the 136 contracts are positively
attributed and occur in their question-specific frozen shared evidence window.
This includes 50/50 rescue-added occurrences across 24 contracts and 2/2
fallback occurrences. Hierarchy closure was disabled in the frozen run, so the
observed hierarchy-addition count is zero; this does not evaluate enabled
hierarchy behavior. The replay uses no gold labels to construct provenance or
test evidence-window containment.

## Secondary retrieval diagnostics

Install the dedicated dependencies and follow
[`experiments/micro_ablations/README.md`](experiments/micro_ablations/README.md):

```bash
python -m pip install -r experiments/micro_ablations/requirements.txt
python experiments/micro_ablations/run_micro_ablations.py \
  --revision rev4 \
  --parts-root /tmp/micro-parts
python experiments/micro_ablations/run_micro_ablations.py \
  --revision rev5 \
  --parts-root /tmp/micro-parts
python experiments/micro_ablations/run_micro_ablations.py \
  --aggregate-only \
  --parts-root /tmp/micro-parts
```

These variants use gold labels to select rewrites and are diagnostic
counterfactuals, not deployable retrieval methods.

## Runtime validation

The runtime validator is deterministic and gold-independent:

```bash
python experiments/runtime_validation/revalidate_contracts.py
```

It checks source resolution, span containment, and visible unresolved-state
consistency. It does not measure global evidence completeness.

## Post-evaluation corrections and compatibility conditions

The current repository corrects the runtime `PRESERVE` branch so unresolved
placeholders remain literal and the final status is `PARAMS_REQUIRED`. The
frozen runtime version could return `OK` in that unevaluated branch. The
reported matched runs used `ASK`; therefore this correction does not change
the dissertation results. The regression is covered by
`tests/test_odp_policy.py` and identified in source as
policy artifact v1.1, `2026-10-03-preserve-status-v1.1`.

The pre-committed `rq2_preserve_replay_v1` study executes the corrected path on
all eight gold rows labeled `PRESERVE` (six Revision 5 and two Revision 4). It
reuses the exact matched-window v3 prepared contexts and selector outputs, then
runs evidence filling, `PRESERVE` policy, contract construction, the Runtime
Verifier, and the offline verifier. It performs no live retrieval and no new
model inference. All 8/8 rows retain visible literal placeholders, return
`PARAMS_REQUIRED`, expose a nonempty required-parameter list, have an empty
`ask_list`, preserve the frozen selector and evidence-window identities, and
pass runtime contract validation. The offline strict scorer passes 5/8 rows:
5/6 on Revision 5 and 0/2 on Revision 4. The three strict failures retain the
registered selector outputs and reflect missing gold clauses; two also omit
gold ODP identifiers outside the retained spans. They are evidence-selection
or coverage failures, not regressions in the corrected state transition.

The protocol, row-level audit, contracts, hashes, and frozen result are under
`experiments/answerer_comparison/rq2_preserve_replay/`. The result archive is
`results_v1/rq2_preserve_replay_v1.zip`, SHA-256
`580a7917678ea00b8529774108ecb293221b77b058ea7a215aea0f0d2d7b6339`.

The frozen `intfloat/e5-small-v2` path used `passage:` for indexed corpus text
but encoded transformed queries without the model-recommended `query:` prefix.
Do not add the prefix and present the resulting output as an exact
reproduction. A corrected-prefix experiment requires a new configuration and
result identity.

Retrieval-setting provenance is recorded in
[`CONSTANTS_PROVENANCE.md`](CONSTANTS_PROVENANCE.md). In particular, BM25
`k1=1.5` and `b=0.75` match common package defaults and RRF `k=60` is
literature-traceable; other weights and thresholds are fixed project choices.
A complete tuning log was not preserved, and a separate development set was
not maintained. Reported results therefore characterize the frozen
configuration on these benchmarks.

AI assistance used in benchmark preparation, annotation review, documentation,
debugging, and manuscript/repository revision is disclosed in
[`AI_ASSISTANCE.md`](AI_ASSISTANCE.md). Qwen2.5 use inside the experimental
system is recorded separately in run manifests and experiment documentation.

## Reproducibility boundary

- Some workflows require Google Colab, GPU resources, and third-party model
  downloads.
- The repository records the evaluated artifacts; it does not claim bitwise
  reproducibility across every hardware and software environment.
- Historical experiment hashes identify files at their recorded Git commits.
  Current source may evolve without changing previously published results.
- The benchmark labels were authored by one researcher and were not
  independently adjudicated. Metrics are agreement with those fixed research
  annotations, not legal correctness.
- Passing the implemented verifier or offline scorer does not establish
  semantic correctness, legal sufficiency, or auditor approval.

## Supplementary study and manuscript-audit boundaries

The profile replay, primary-retriever sensitivity and natural-question study
are separate registered result families. Their protocols, execution identities
and original failures are retained in their respective directories. None
replaces the original benchmark labels or historical headline tables.

The natural-question GPU run and automatic scoring were completed before the
author supplied the separate 40-row qualitative review. The original automatic
summary and blank review template remain unchanged; completion is recorded in
`results_v1/author_review_v1/summary.json`. This is unblinded author review with
three scope uncertainties, not independent expert correctness validation. The
exact submitted workbook and judgment notes are retained. The published executed
notebook still includes its original execution output.

To audit a current extracted Overleaf source package against these public
artifacts, use a full checkout of the publication branch and Python's standard
library:

```bash
python tools/audit_manuscript_consistency.py /path/to/extracted_overleaf \
  --json-out /tmp/manuscript_audit.json \
  --markdown-out /tmp/manuscript_audit.md
```

The tool checks supplementary tables when the source contains their identity
section, in addition to the original benchmark and artifact checks. It verifies
public PRESERVE commit trees and recorded execution-source hashes. The earlier
local execution commit is historical metadata and is not a required public Git
object. Compilation and visual inspection remain separate checks; artifact
consistency cannot establish annotation or professional correctness.
