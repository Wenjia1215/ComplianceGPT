# ComplianceGPT

ComplianceGPT is a research prototype for auditable compliance question
answering over revision-scoped regulatory text. A language model selects source
identifiers from a bounded evidence window; deterministic components then
resolve those identifiers against canonical records, apply
organization-defined-parameter (ODP) policy, assemble a citation contract, and
validate its source, span, revision, and status consistency.

The reported evaluation covers NIST SP 800-53 Revision 4 and Revision 5.
ComplianceGPT is not a legal compliance decision engine or a production
compliance product.

**Author:** Wenjia Wang  
**License for original project code and documentation:** Apache License 2.0

## Answer construction

Conventional retrieval-augmented generation often follows:

```text
retrieve evidence -> generate answer -> attach citations
```

ComplianceGPT uses:

```text
retrieve candidates -> select source IDs -> assemble canonical spans -> verify contract
```

The released answer contract records the requested revision, selected and
realized source IDs, canonical evidence spans, unresolved ODPs, final status,
and verifier result.

## Start here

| Goal | Entry point |
|---|---|
| Understand the pipeline | [`src/compliancegpt/pipeline/README_pipeline.md`](src/compliancegpt/pipeline/README_pipeline.md) |
| Run a single-query demonstration | [`src/compliancegpt/pipeline/single_run/Single_Run_Demo.ipynb`](src/compliancegpt/pipeline/single_run/Single_Run_Demo.ipynb) |
| Inspect the citation-contract schema | [`src/compliancegpt/generator/citation_contract_80053.md`](src/compliancegpt/generator/citation_contract_80053.md) |
| Review the S1–S7 retrieval evaluation | [`experiments/retriever_ablation/README.md`](experiments/retriever_ablation/README.md) |
| Review the matched answerer comparison | [`experiments/answerer_comparison/rq2_matched/README.md`](experiments/answerer_comparison/rq2_matched/README.md) |
| Review or reproduce the control-gate width sweep | [`experiments/answerer_comparison/rq2_control_gate_width/README.md`](experiments/answerer_comparison/rq2_control_gate_width/README.md) |
| Review the no-selector ablation | [`experiments/answerer_comparison/rq2_no_selector/README.md`](experiments/answerer_comparison/rq2_no_selector/README.md) |
| Review the ODP-rescue ablation | [`experiments/answerer_comparison/rq2_rescue_ablation/README.md`](experiments/answerer_comparison/rq2_rescue_ablation/README.md) |
| Review Runtime Verifier mutation testing | [`experiments/answerer_comparison/runtime_verifier_mutation/README.md`](experiments/answerer_comparison/runtime_verifier_mutation/README.md) |
| Review per-identifier runtime provenance | [`experiments/answerer_comparison/rq2_identifier_provenance/README.md`](experiments/answerer_comparison/rq2_identifier_provenance/README.md) |
| Review the secondary retrieval diagnostics | [`experiments/micro_ablations/README.md`](experiments/micro_ablations/README.md) |
| Review runtime contract validation | [`experiments/runtime_validation/README.md`](experiments/runtime_validation/README.md) |
| Inspect ErrorBank annotation | [`data/error_bank/Labeling_Rationale.md`](data/error_bank/Labeling_Rationale.md) |
| Identify exact NIST/OSCAL source releases | [`data/DATA_VERSIONS.md`](data/DATA_VERSIONS.md) |
| Verify canonical evaluation inputs | [`EVALUATION_INPUT_CHECKSUMS.md`](EVALUATION_INPUT_CHECKSUMS.md) |
| Distinguish the three S7 result families | [`EVALUATION_CONFIGURATIONS.md`](EVALUATION_CONFIGURATIONS.md) |
| Review evaluation-constant provenance | [`CONSTANTS_PROVENANCE.md`](CONSTANTS_PROVENANCE.md) |
| Review AI-assistance disclosure | [`AI_ASSISTANCE.md`](AI_ASSISTANCE.md) |
| Review notebook audit | [`NOTEBOOK_AUDIT.md`](NOTEBOOK_AUDIT.md) |
| Reproduce reported evaluations | [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) |

## Repository layout

```text
ComplianceGPT/
├── data/
│   ├── ccs/                       # Canonical Clause Store records
│   ├── ODP/                       # ODP registries and example profiles
│   ├── gold_standard_datasets/    # Rev. 4 and Rev. 5 evaluation sets
│   ├── error_bank/                # Diagnostic ErrorBank and labels
│   ├── qur_outputs/               # Recorded query rewrites
│   ├── raw/                       # Identified NIST source inputs
│   └── DATA_VERSIONS.md           # Upstream release/tag/commit record
├── src/
│   ├── compliancegpt/             # Retriever, selector, orchestrator, verifier
│   ├── answerer_comparison/       # Matched evidence-window utilities
│   ├── generative_answerer/       # Free-form comparison answerer
│   └── data_tools/                # Data validation utilities
├── experiments/
│   ├── retriever_ablation/        # S1–S7 evaluation and outputs
│   ├── answerer_comparison/       # Matched evaluation and selector/rescue ablations
│   ├── micro_ablations/           # Secondary gold-informed diagnostics
│   ├── pipeline_runs/             # Recorded contract traces
│   └── runtime_validation/        # Gold-independent contract validation
├── tests/
├── AI_ASSISTANCE.md
├── CONSTANTS_PROVENANCE.md
├── EVALUATION_CONFIGURATIONS.md
├── EVALUATION_INPUT_CHECKSUMS.md
├── LICENSE
├── NOTEBOOK_AUDIT.md
└── REPRODUCIBILITY.md
```

## Output statuses

| Status | Meaning |
|---|---|
| `OK` | Usable evidence was selected and no required parameter remains unresolved. |
| `PARAMS_REQUIRED` | Evidence was found, but organization input is still required. |
| `NO_EVIDENCE` | The available evidence cannot support an answer. |

## Evidence and ODP boundary

The retriever ranks statement and guidance records. ODP/PRM records support
canonicalization, profile validation, ODP policy, and verification; they are
not ordinary cited evidence candidates. See
[`docs/ODP_RETRIEVAL_BOUNDARY.md`](docs/ODP_RETRIEVAL_BOUNDARY.md).

The raw inputs are pinned official NIST OSCAL catalogs. They integrate SP
800-53 control content with SP 800-53A assessment material. Assessment
objective records are retained in the CCS for provenance but are excluded
from the evaluated retrieval corpus. The project's YAML “organization
profile” is not an OSCAL Profile document or a claim of OSCAL profile
resolution conformance.

## Evaluation artifacts

- The S1–S7 evaluation measures governing-control ranking.
- The matched answerer evaluation compares complete answer-construction
  methods under the same ordered evidence window and loaded model instance.
- The registered control-gate sensitivity study holds the frozen retrieval
  traces and 24-record window policy fixed while sweeping fixed top-1, top-2,
  top-3, and top-5 gate widths. The completed A100 run, row-level contracts,
  deterministic context audit, and validation manifests are archived under
  `experiments/answerer_comparison/rq2_control_gate_width/results_v1/`.
- The deterministic no-selector ablation retains every statement and guidance
  record in each frozen matched-run evidence window. It measures the coverage,
  answer-length, evidence-precision, and ODP-scope tradeoff without new model
  inference.
- The deterministic ODP-rescue ablation reconstructs the frozen pre-rescue
  selector state and replays bounded rescue on and off. It measures the rule's
  ODP-blocking, clause-coverage, status-scope, and evidence-burden effects
  without retrieval or model inference.
- The Runtime Verifier mutation evaluation applies five deterministic defect
  operators to the 136 frozen valid ComplianceGPT contracts. It reports
  operator-specific detection rates, triggering predicates, and undetected
  cases without using gold labels.
- The per-identifier provenance replay positively labels every final source ID
  as selector-, fallback-, rescue-, or hierarchy-originated and checks each ID
  against the question-specific frozen shared evidence window. It performs no
  retrieval, model inference, or gold-guided attribution.
- The micro-ablation study is a secondary, gold-informed diagnostic and is not
  a deployable retrieval method.
- Runtime validation checks source resolution, span containment, and visible
  unresolved-state consistency; it does not establish global evidence
  completeness.

Input identities are listed in
[`EVALUATION_INPUT_CHECKSUMS.md`](EVALUATION_INPUT_CHECKSUMS.md). Run-specific
model, code, context, and result identities are recorded alongside each
experiment.

Reported metrics remain tied to the recorded evaluation commits and frozen
outputs. Current source includes a post-evaluation regression fix that makes
`PRESERVE` return `PARAMS_REQUIRED` when placeholders remain; the reported
runs used `ASK`, so they were not regenerated. The frozen E5 path also used
`passage:` for corpus text but omitted the recommended `query:` prefix. See
[`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) and
[`CONSTANTS_PROVENANCE.md`](CONSTANTS_PROVENANCE.md) before comparing a new
run with the dissertation tables.

## Guarantees and limits

Within the evaluated NIST SP 800-53 scope, the implementation is designed to
make source IDs, canonical spans, revision scope, unresolved inputs, and
validation outcomes inspectable. It does not guarantee:

- perfect evidence selection or complete clause recovery;
- semantic or legal correctness;
- auditor approval or certification;
- safe production deployment;
- generalization to every framework, model, or organization profile.

The principal residual risk is evidence-selection error: a contract can be
mechanically grounded in selected records while still omitting required
evidence.

## Authorship and AI assistance

Candidate topics were collected through Web search, and ChatGPT and Gemini
supplied additional candidate-question suggestions. The author selected the
final question set and manually wrote and checked every final answer and
substantive gold annotation. ChatGPT reviewed author-created labels, and
Gemini formatted and grammar-checked author-drafted ErrorBank documentation.
Codex assisted with S1–S7 debugging. The complete disclosure is in
[`AI_ASSISTANCE.md`](AI_ASSISTANCE.md). Qwen2.5 is separately documented as an
experimental model used by the evaluated system.

## License

Copyright 2026 Wenjia Wang.

Unless a file states otherwise, original ComplianceGPT software and project
documentation are licensed under the [Apache License 2.0](LICENSE). Apache-2.0
was selected because it is a permissive research-software license with an
explicit patent grant. Third-party publications, data, model weights, and
other incorporated materials retain their own terms and are not relicensed by
this repository.
