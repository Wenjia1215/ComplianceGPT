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

The public remote was checked on 2026-09-24. The preserved branch
`history/pre-public-cleanup-2026-07-29` existed at commit
`1f15049360132271684da01c48506c17cc0861ce`. That branch is historical
provenance, not the recommended execution target.

Current source may contain clearly identified documentation and regression
patches made after the frozen evaluation. Such patches do not retroactively
change stored outputs or their metrics.

## Evaluation map

| Evaluation | Canonical entry point | Recorded results |
|---|---|---|
| S1–S7 governing-control retrieval | `experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb` | `experiments/retriever_ablation/ablation_outputs/` |
| Matched answer construction | `experiments/answerer_comparison/rq2_matched/run_matched_rq2.py` | `experiments/answerer_comparison/rq2_matched/results_v3/` |
| No-selector ablation | `experiments/answerer_comparison/rq2_no_selector/run_no_selector_ablation.py` | `experiments/answerer_comparison/rq2_no_selector/results_v1/` |
| ODP-statement rescue ablation | `experiments/answerer_comparison/rq2_rescue_ablation/run_rescue_ablation.py` | `experiments/answerer_comparison/rq2_rescue_ablation/results_v1/` |
| Runtime Verifier mutation evaluation | `experiments/answerer_comparison/runtime_verifier_mutation/run_verifier_mutations.py` | `experiments/answerer_comparison/runtime_verifier_mutation/results_v1/` |
| Per-identifier runtime provenance | `experiments/answerer_comparison/rq2_identifier_provenance/run_identifier_provenance.py` | `experiments/answerer_comparison/rq2_identifier_provenance/results_v1/` |
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
`2026-09-24-preserve-status-v1`. It has not been evaluated in an end-to-end
`PRESERVE` run.

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
