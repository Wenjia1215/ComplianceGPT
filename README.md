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
| Review the secondary retrieval diagnostics | [`experiments/micro_ablations/README.md`](experiments/micro_ablations/README.md) |
| Review runtime contract validation | [`experiments/runtime_validation/README.md`](experiments/runtime_validation/README.md) |
| Inspect ErrorBank annotation | [`data/error_bank/Labeling_Rationale.md`](data/error_bank/Labeling_Rationale.md) |
| Verify canonical evaluation inputs | [`EVALUATION_INPUT_CHECKSUMS.md`](EVALUATION_INPUT_CHECKSUMS.md) |
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
│   └── raw/                       # Identified NIST source inputs
├── src/
│   ├── compliancegpt/             # Retriever, selector, orchestrator, verifier
│   ├── answerer_comparison/       # Matched evidence-window utilities
│   ├── generative_answerer/       # Free-form comparison answerer
│   └── data_tools/                # Data validation utilities
├── experiments/
│   ├── retriever_ablation/        # S1–S7 evaluation and outputs
│   ├── answerer_comparison/       # Corrected matched answerer evaluation
│   ├── micro_ablations/           # Secondary gold-informed diagnostics
│   ├── pipeline_runs/             # Recorded contract traces
│   └── runtime_validation/        # Gold-independent contract validation
├── tests/
├── EVALUATION_INPUT_CHECKSUMS.md
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

## Evaluation artifacts

- The S1–S7 evaluation measures governing-control ranking.
- The matched answerer evaluation compares complete answer-construction
  methods under the same ordered evidence window and loaded model instance.
- The micro-ablation study is a secondary, gold-informed diagnostic and is not
  a deployable retrieval method.
- Runtime validation checks source resolution, span containment, and visible
  unresolved-state consistency; it does not establish global evidence
  completeness.

Input identities are listed in
[`EVALUATION_INPUT_CHECKSUMS.md`](EVALUATION_INPUT_CHECKSUMS.md). Run-specific
model, code, context, and result identities are recorded alongside each
experiment.

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
