---

# ComplianceGPT Freeze Requirements Document

**Date:** April 2026
**Scope:** Dissertation and core-paper freeze for ComplianceGPT, limited to **S1–S7** and **NIST SP 800-53 Rev4/Rev5**.
**Purpose:** Define the exact technical, empirical, and documentation artifacts that must be fixed, recorded, and treated as authoritative for the April 24 evaluation freeze.

## 1. Freeze Objective

The purpose of this freeze is not to declare the project “finished.” It is to establish a stable, defensible academic artifact. After the freeze, the supported code path, evaluation assets, baseline definitions, runtime environment, and final figures/tables must be treated as fixed unless there is a compelling reason to reopen them. This is aligned with the supervisor’s instruction to freeze datasets, baselines, metrics, ErrorBank categories, annotation procedure, and final tables/figures, while avoiding further scope expansion.

## 2. Frozen Research Scope

The frozen research scope is limited to the ComplianceGPT architecture evaluated on **NIST SP 800-53 Revision 4 and Revision 5**. The active ablation scope is **S1 through S7 only**. Exploratory retrieval variants beyond S7 are outside the dissertation freeze and must be archived, excluded from active documentation, or explicitly labeled as out of scope. The frozen evaluation scope consists of retrieval ablation, matched answerer comparison, ODP-safe behavior analysis, and ErrorBank-based failure analysis. This matches the current proposal framing and the committee plan to reuse existing assets rather than introduce a large new dataset.

## 3. Supported Execution Scope

The frozen and officially supported execution environment is **Google Colab**. Non-Colab execution is not ruled out, but it is outside the supported reproducibility scope and may require manual path edits and local dependency alignment. The freeze documentation must record the exact Colab runtime assumptions, including Python version, GPU/runtime class if relevant, and any environment-specific constraints. This execution boundary must be stated explicitly in the README and freeze note.

## 4. Frozen Runtime Environment

The frozen environment must include one authoritative dependency file with exact version pins for all packages used in the definitive frozen runs. Version ranges such as `>=` are not acceptable in the freeze file. The environment record must include Python version and the exact versions of the major runtime libraries used by the retriever, generator, reranker, and verifier. The confirmed FAISS pin for the frozen Colab run is:

```text
faiss-cpu==1.13.2
```

The environment record must be tied to the actual frozen rerun used to generate the final figures and tables.

## 5. Canonical Code Paths

The freeze package must define one authoritative execution path for each major evaluation component. There must be one canonical entrypoint for S1–S7 retrieval ablation, one canonical entrypoint for matched answerer comparison, one canonical entrypoint for batch pipeline evaluation, one canonical entrypoint for canonical examples, and one canonical validation path for CCS and ODP artifacts. All other notebooks and scripts must be marked as supporting utilities, exploratory artifacts, or archived legacy materials. A committee member should not have to guess which notebook is “the real one.”

## 6. Project Layout and Path Assumptions

The freeze documentation must record the expected project layout in Colab, including repo root, data root, output locations, and any required manual path edits for unsupported non-Colab use. Hard-coded path assumptions that remain in active notebooks or pipeline code must be acknowledged in the freeze note. No active notebook in the frozen repo should reference obsolete roots such as legacy project folders or superseded output locations.

## 7. Frozen Data Assets

The freeze must identify the exact authoritative data assets used in the evaluation. This includes the Rev4 and Rev5 Canonical Clause Store files, the Rev4 and Rev5 ODP registries, the Rev5 gold set of 100 questions, the Rev4 gold set of 36 questions, and ErrorBank v1 with 24 Rev5 cases and 13 Rev4 cases. Each frozen asset must have a fixed filename, fixed folder location, fixed count, and a note confirming its validation status. Ambiguous naming such as `latest`, `new`, or multiple competing “final” versions is not acceptable in active freeze assets. The proposal already frames these as the empirical foundation of the dissertation and they must now be operationally fixed.

## 8. Frozen Annotation Procedure

The ErrorBank categories alone are not sufficient. The freeze must record the annotation procedure used to assign them. This includes category definitions, decision order, who labeled the cases, whether labeling was single-annotator or multi-annotator, whether any labels were revised after initial assignment, and whether any mixed or adversarial subsets were derived from the original categories. The supervisor explicitly requested that the annotation procedure be frozen, not just the taxonomy.

## 9. Frozen Baseline Definition

The matched comparison baseline must be fixed in a way that a reviewer can inspect and reproduce conceptually. The freeze record must specify the exact generative baseline model name, prompt mode, candidate evidence pool, retrieval conditions, decoding settings, post-processing behavior, retry policy, and whether the baseline saw the same candidate set as ComplianceGPT. The proposal states that RQ2 holds the S7 retrieval backbone and candidate evidence pool constant; the freeze must record exactly how that was implemented. 

## 10. Frozen Retrieval Configuration

The S1–S7 retriever definitions must be recorded in one authoritative location. This includes BM25 parameters, dense model name, rewrite source/model, rewrite filtering rule, RRF settings, reranker model name, reranker thresholds or gating logic, top-k cutoffs, clause extraction behavior, and any inclusion or exclusion rules for guidance or discussion text. The proposal already describes S7 as the cumulative frozen retriever design; the freeze requirements document must convert that narrative into an operational configuration record.

## 11. Frozen Output Contract Schema

The citation contract must be treated as a concrete, documented output schema. The freeze must record the required fields, optional fields, valid status values, meaning of each field, citation fields, evidence span structure, ODP-related fields, and verifier output fields. At minimum, the final schema must define the expected structure for `answer_text`, `evidence_spans`, `status`, citation fields, and verifier pass/fail outputs. If the schema changes across notebooks or scripts, the freeze is not real.

## 12. Claim-Boundary Freeze

The freeze package must include one fixed claim-boundary memo and one guarantee / non-guarantee table. These must define, in stable language, what “mechanically verifiable” means, the distinction between “grounded” and “complete,” the guarantees by construction, and the residual evidence-selection risk that remains outside the guarantee. The committee specifically requested that these boundaries be fixed and not continue to drift.

## 13. Frozen Canonical Examples

The three canonical examples must be fixed as official assets and reused consistently across the paper, dissertation, slides, and job-market materials. These are: organization-defined parameters and value fabrication, informal-to-formal language mismatch, and post-hoc citation versus clause-first deterministic answer construction. For each example, the freeze must record the exact query wording, the exact baseline behavior being illustrated, the exact ComplianceGPT behavior, and the exact figure or table used to present it. The committee explicitly requested these three polished examples.

## 14. Frozen Final Tables and Figures

The freeze must designate a finite, authoritative set of final tables and figures. At minimum, this includes the retrieval ablation table, matched answerer comparison table, ODP handling table, ErrorBank taxonomy table, related-work positioning matrix, architecture figure, S7 retriever figure, and the three canonical example figures/tables. Each figure/table must have a source notebook or script, output filename, and fixed caption draft. The supervisor’s April 24 milestone explicitly requires final tables and figures.

## 15. Result Provenance

Every final table and headline result must be traceable to a specific run artifact. The freeze must record, for each final result table, the source CSV/JSON/MD artifact, generation date, generating notebook or script, whether any rows were excluded after the run, and whether any result was copied manually or produced automatically. This applies especially to the key proposal numbers for Audit-Ready Answer Rate and ODP Correct Handling. The proposal already reports those numbers; the freeze must now tie them to exact source artifacts.

## 16. Raw Output Trace Freeze

In addition to parsed tables and contracts, the freeze must retain the raw output traces from final comparison runs. This includes raw generative baseline answers, raw selector outputs, raw assembled contracts, and raw verifier outputs. This requirement exists to prevent ambiguity about whether parsing or post-processing concealed an error. If a reviewer questions a canonical example or a comparison table, the raw trace should be available as the underlying record.

## 17. Frozen Stochastic Settings

All controllable stochastic settings used in the frozen runs must be recorded. This includes random seeds, decoding parameters such as temperature and top-p, retry behavior, and any tie-breaking behavior in ranking or reranking. The purpose is not to overclaim perfect bitwise determinism, but to freeze all controllable sources of stochastic variation in the supported workflow.

## 18. Hardware and Runtime Provenance

The definitive frozen rerun must record the hardware/runtime context in which it was produced. This includes Colab runtime class, Python version, GPU type if used, and major runtime constraints such as RAM limitations. Cost accounting is optional unless explicitly claimed in the paper, but hardware/runtime provenance is mandatory.

## 19. Related-Work Positioning Matrix

The freeze package must include the final positioning matrix comparing ComplianceGPT with NotebookLM, Perplexity, and citation-aware research systems across retrieval, answer construction, citation mechanism, ODP handling, hallucination risk, and related dimensions. This was explicitly requested by the supervisor as part of the April 24 milestone.

## 20. Archive Boundary

The freeze package must distinguish active assets from archived assets. Exploratory retrieval materials beyond S7, obsolete notebooks, stale path notebooks, superseded outputs, and OS cruft such as `.DS_Store`, `__MACOSX`, and nonessential `.git` packaging artifacts must be removed from the active freeze package or clearly archived. A frozen dissertation artifact is not a dump of the entire development history.

## 21. Smoke Test Requirement

The freeze must include one canonical end-to-end smoke test that loads the frozen assets, runs one query, produces one contract, runs the verifier, and prints the resulting status and citation(s). The smoke test must record the query, expected status, and expected primary citation or qualitative expected behavior. This is the minimum operational proof that the frozen system still runs end to end.

## 22. Supplementary Mapping

The freeze should record which subset of frozen assets will be promoted into the paper/dissertation supplementary package. This is not the core freeze blocker, but it should be planned now so that the paper submission package can be assembled quickly. At minimum, the supplementary mapping should identify the canonical examples, one smoke test path, final tables/figures, and the key frozen data/config files used to support the paper’s claims.

## 23. Third-Party Asset Notes

The freeze should record the source and usage constraints of major third-party assets used in the supported workflow, including NIST source materials, major models, and core libraries. This does not need to become a full legal audit, but the freeze package should not leave the provenance of major dependencies ambiguous.

## 24. Explicit Exclusions

The freeze note must explicitly state what is not included in the supported freeze scope. This should include retrieval variants beyond S7, new benchmark campaigns, non-NIST frameworks, auditor-usefulness studies, production deployment hardening, full legal compliance determination, and official non-Colab reproducibility claims.

## 25. Freeze Acceptance Condition

The code and evaluation are considered frozen only when all of the following are true: the supported environment is documented, the dependency file is pinned, the active scope is S1–S7 only, the canonical code paths are designated, the authoritative data assets are named and validated, the annotation procedure is recorded, the baseline and retrieval configurations are fixed, the contract schema is documented, the claim-boundary memo is fixed, the canonical examples are fixed, the final tables/figures are designated, result provenance is recorded, raw output traces are retained, stochastic settings are recorded, archive boundaries are enforced, and the smoke test succeeds.

---
