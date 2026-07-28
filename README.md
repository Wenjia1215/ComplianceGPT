# ComplianceGPT

**ComplianceGPT** is a research prototype for auditable compliance question answering. It studies a citation-contract architecture in which a language model helps select evidence, but the final evidence-bearing answer is assembled deterministically from canonical source text and checked by a rule-based verifier.

The current dissertation evaluation focuses on **NIST SP 800-53 Revision 4 and Revision 5**. The project is not a legal compliance decision engine. Its purpose is to make compliance answers more inspectable by preserving source linkage, revision scope, unresolved parameters, and verification status.

---

## Core idea

Most retrieval-augmented generation systems follow this pattern:

```text
retrieve evidence -> generate answer -> attach citations
```

That pattern is useful for many tasks, but it creates risks in compliance settings. A generated answer may paraphrase a requirement too freely, attach citations after the fact, mix revisions, or fill an organization-defined parameter with a plausible but unsupported value.

ComplianceGPT uses a stricter answer path:

```text
retrieve candidates -> select source IDs -> assemble from canonical clauses -> verify contract
```

The model is therefore not responsible for writing the final evidence-bearing answer. Once evidence IDs are selected, the system resolves them against a Canonical Clause Store, extracts verbatim evidence spans, applies explicit organization-defined-parameter logic, and emits a structured answer contract.

---

## Architecture

```text
User question
   |
   v
Query rewriting and retrieval
   |
   v
Candidate clause pool
   |
   v
LLM evidence selector
   |
   v
Contract orchestrator
   |        \
   |         -> Canonical Clause Store
   |         -> ODP registry / organization profile
   v
Rule-based verifier
   |
   v
Answer contract or explicit status
```

Main components:

| Component | Role |
|---|---|
| Canonical Clause Store | Revision-scoped source records extracted from authoritative compliance text. |
| Query Rewriter / Retriever | Recovers candidate controls and clauses under terminology mismatch. |
| LLM Evidence Selector | Selects candidate source IDs from a bounded evidence pool. |
| Contract Orchestrator | Resolves source IDs, extracts verbatim spans, applies ODP policy, and builds the answer contract. |
| Verifier | Checks citation linkage, revision consistency, status consistency, and verbatim evidence grounding. |

The final output is a structured contract, not an unconstrained model-written paragraph.

---

## Output statuses

| Status | Meaning |
|---|---|
| `OK` | Evidence was selected and all required parameters are resolved. |
| `PARAMS_REQUIRED` | Evidence was found, but the answer depends on an unresolved organization-defined parameter. |
| `NO_EVIDENCE` | The system cannot support an answer from the available candidate evidence. |

These statuses are part of the safety boundary. The system should expose missing evidence or missing organizational values instead of producing a complete-looking answer.

---

## Repository map

```text
ComplianceGPT_v2/
  data/
    ccs/                         # Canonical Clause Store files
    ODP/                         # ODP registries and organization profiles
    gold_standard_datasets/       # Human-verified evaluation sets
    error_bank/                   # Diagnostic ErrorBank and labeling notes
    raw/                          # Raw source inputs where retained
    qur_outputs/                  # Query rewrite outputs used by retrieval studies

  src/
    compliancegpt/
      retriever/                  # Retrieval implementation
      QUR_generator/              # Query rewrite utilities
      generator/                  # Citation contract, selector, verifier assets
      pipeline/                   # End-to-end ComplianceGPT pipeline
    data_tools/                   # CCS validation and data utilities
    generative_answerer/          # Baseline answerer components
    answerer_comparison/          # Matched answerer comparison utilities
    3_canonical_examples/         # Canonical motivating examples

  experiments/
    retriever_ablation/           # Retrieval ablation workflow, definitions, and outputs
    answerer_comparison/          # Baseline vs. citation-contract comparison outputs
    pipeline_runs/                # Batch pipeline contracts and reports
    micro_ablations/              # Focused retrieval diagnostics

  img/                            # Architecture and result figures
  ARTIFACTS.md                    # Frozen-input manifest and checksums
  FREEZE_REQUIREMENTS.md          # Evaluation-freeze requirements and acceptance boundary
```

---

## Main entry points

| Goal | Start here |
|---|---|
| Understand the end-to-end answerer | `src/compliancegpt/pipeline/README_pipeline.md` |
| Run a single query | `src/compliancegpt/pipeline/single_run/Single_Run_Demo.ipynb` |
| Check contract behavior | `src/compliancegpt/pipeline/single_run/Acceptance_Tests.ipynb` |
| Run batch pipeline evaluation | `src/compliancegpt/pipeline/batch_run/` |
| Inspect retrieval system definitions | `experiments/retriever_ablation/SYSTEMS.md` |
| Inspect retrieval workflow | `experiments/retriever_ablation/WORKFLOW.md` |
| Inspect retrieval results | `experiments/retriever_ablation/RESULTS.md` |
| Inspect ErrorBank labeling | `data/error_bank/Labeling_Rationale.md` |
| Inspect frozen input provenance | `ARTIFACTS.md` |
| Inspect freeze requirements | `FREEZE_REQUIREMENTS.md` |

All paths are relative to the repository root.

---

## Evaluation assets

The current evaluation package uses:

| Asset | Role |
|---|---|
| Rev5 gold set | Main NIST SP 800-53 Rev5 evaluation set. |
| Rev4 gold set | Main NIST SP 800-53 Rev4 evaluation set. |
| ErrorBank v1 | Diagnostic set for known failure modes and difficult cases. |
| Rev4 / Rev5 CCS files | Canonical source records used for retrieval and answer construction. |
| Rev4 / Rev5 ODP registries | Organization-defined-parameter detection and handling. |

`ARTIFACTS.md` is authoritative for frozen input checksums, including CCS files, gold sets, ErrorBank files, and ODP registries. Code is controlled by Git commit history. Active dissertation result artifacts are managed separately: the matched v3 package checksum is recorded in `experiments/answerer_comparison/rq2_matched_v2/results_v3/README.md`, and the dissertation source supplement includes `artifact_manifests/dissertation_result_manifest_sha256.txt` for the complete active result set. Generated outputs not named by either record are not checksum-managed.

---

## Evaluation dimensions

ComplianceGPT separates evaluation into several dimensions:

| Dimension | Question being tested |
|---|---|
| Retrieval quality | Did the retriever recover the correct control or clause neighborhood? |
| Answer-contract validity | Does the final answer satisfy citation, status, revision, and verbatim-grounding checks? |
| ODP-safe behavior | Does the system preserve unresolved parameters instead of fabricating values? |
| Matched answerer comparison | Does deterministic assembly improve audit-readiness relative to a generative final answer? |
| ErrorBank analysis | How does the system behave on known difficult or diagnostic cases? |

This separation matters because groundedness and completeness are not the same. A contract can be mechanically grounded while still depending on imperfect evidence selection.

---

## Guarantees and limits

Within the stated NIST SP 800-53 Rev4/Rev5 research scope, ComplianceGPT is designed to enforce:

- evidence-bearing answer text derived from canonical clause records;
- explicit linkage between answer content and cited sources;
- revision-scoped citation handling;
- visible handling of unresolved organization-defined parameters;
- deterministic verification of contract structure and verbatim evidence spans.

ComplianceGPT does **not** guarantee:

- perfect evidence selection;
- complete compliance analysis for every operational scenario;
- legal, audit, or certification approval;
- production deployment hardening;
- universal support for all compliance frameworks;
- elimination of all possible upstream retrieval or selection errors.

The main residual risk is evidence-selection error. If the wrong clause is selected, the final answer may still be mechanically grounded but substantively incomplete or misdirected.

---

## Reproducibility notes

This repository is organized as a dissertation and core-paper research artifact. The supported execution environment is Google Colab. Non-Colab execution may require path and dependency adjustments.

Reproducibility is handled through three layers:

1. **Git commit history** locks code, notebooks, and documentation.
2. **`ARTIFACTS.md`** records checksums for frozen input assets.
3. **Experiment folders** retain generated outputs, reports, and raw traces used for analysis.

Exploratory variants that are not part of the active evaluation are retained under archive folders for provenance rather than mixed into the main workflow.

---

## Academic status

ComplianceGPT is under active dissertation development. The current repository supports:

- dissertation proposal refinement;
- core paper drafting;
- evaluation freeze and result provenance;
- follow-on work on evidence-selection robustness, compliance QA, and audit-oriented RAG systems.

The project should be interpreted as a research prototype, not a production compliance product.
