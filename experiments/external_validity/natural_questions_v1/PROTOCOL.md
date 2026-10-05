# Natural-question protocol v1

This is a **pre-inference preparation protocol**, assembled after exploratory source discovery. It is not a claim that sampling rules were registered before question discovery. The machine-readable specification is [protocol.json](protocol.json). Formal registration requires confirmed sources and author labels, then a publicly retrievable commit before any retrieval outcomes or answer generation.

## Questions and provenance

Select 20 original question threads concerning NIST SP 800-53 from r/NISTControls. The planned posted-date window is 2014-01-01 through 2026-10-04. The selected indexed dates are in 2020–2024; collection took place on 2026-10-05 UTC. This convenience selection targets 12 control-interpretation/implementation cases and eight broader scope/workflow cases. Discovery searches and URL dispositions are recorded. Multiple questions within a post remain together. Include one selected question per original thread; do not use replies as separate questions. Selection occurred before any model outcomes.

Retain original captured title/body text, explicit control IDs, source quotations, primary URL, indexed date, capture boundary and wording digest. Indexed formatting is not a raw Reddit export. Direct original-site access returned HTTP 403. Source date, completeness and separation of the author's question from replies require author confirmation. Professional identity and the independence of forum users are unverified. NQ19 explicitly stops at the question author's closing sentence because the indexed block then blends into unmarked reply text.

Before registration, log any capture correction, duplication, unavailable source, exclusion or replacement. Keep an auditable reason and a new candidate/protocol identity. Do not optimize selection or labels using retrieval scores or answerer results. After registration, do not substitute questions, change their wording or drop failed/unanswerable cases. Record deviations and use a new result version when required.

## Reference labels

The author reviews original sources and labels before execution:

- Catalog revision. Explicitly resolve historical revision clues; do not silently reinterpret all questions as Revision 5.
- Whole-question answerability: `full`, `partial`, `outside`, `ambiguous`.
- Governing canonical control IDs and required clause evidence groups. One group per duty; alternatives within a group are interchangeable sources.
- Semantic ODP applicability: `required`, `not_required`, `not_applicable`, `uncertain`, plus explicit required registry IDs or uncertainty.
- Ambiguity, source confirmation, reviewer name and UTC review timestamp.

Draft suggestions and visible parameter helpers are not accepted labels. An ODP token in background text does not alone imply that an answer needs a value. Required ODP labels concern values needed by the supported answer with an empty organizational profile. Outside questions cannot be converted to positive/negative ODP cases. Unknown ODP requirements remain `uncertain` with `null`, not `[]`/negative. No independent expert review is claimed.

## Execution identity

Freeze the source captures, review, accepted labels, registered questions, protocol and source-file hashes. A clean checkout retrieves the registration from its exact public commit before model loading. Record actual Python, packages, GPU name/memory, CUDA, determinism settings, canonical input hashes, model revisions and model-file hashes. Request an A100 runtime. Pin dependencies from `requirements-colab.txt`; verify actual CUDA availability and BF16 support.

Models are Qwen/Qwen2.5-7B-Instruct at `a09a35458c702b33eeacc393d103063234e8bc28`, intfloat/e5-small-v2 at `ffb93f3bd4047442299a41ebb6fa998a38507c52`, and BAAI/bge-reranker-base at `2cfc18c9415c912f9d8155881c133215df768a70`. Explicitly load the shared answerer in BF16 without quantization; the ordinary pipeline's non-quantized loader uses FP16, so a flag alone does not establish the declared precision.

Use the production S7 retriever with its pinned source defaults, top 12 controls and no query rewriting. Retrieve from the author's selected revision. Retrieval and generation do not receive governing control, evidence-group or ODP reference labels. Capture retrieval metadata and rebuild the canonical evidence once. Both paths use the adaptive top-1/top-2/top-3 gate, `prefer_smt_keep_params` and a 24-record maximum window. Record and verify canonical record content and all context/window hashes.

Run the current ComplianceGPT path and generative baseline with that shared model and matched evidence, greedy decoding, no organization profile, and `ASK` resolution policy. This compares two complete answer paths. Their prompts, schemas, token budgets, parsing retries and construction differ. It does not isolate one architectural component. It also does not reproduce the historical RQ1 notebook pipeline.

Checkpoint each retrieval question and each answer. Retain all generation input/output token IDs, decoded output, configuration, retries and failures. Resume only with identical source/runtime/registration and locked evidence. Empty retrieval is a protocol case requiring explicit versioned handling; do not drop it or supply reference-label evidence. No silent model substitutions, decoding changes or reruns selecting the most favorable answer.

## Outcomes and denominators

Report all 20 questions, both paths and each reviewed answerability class. Report unresolved source/scope cases rather than claiming all natural questions are catalog-answerable.

| Outcome | Eligible denominator | Interpretation |
|---|---|---|
| Runtime contract validity | All 20 per path | Current strict runtime schema/evidence/policy validation |
| Clause-ID group coverage | Full/partial rows with required evidence groups | Whether every group has a cited acceptable source ID |
| Complete-clause-text group coverage | Same full/partial subset | Every group has at least one span equal to complete canonical clause text |
| Whole-question strict catalog contract | Full rows with determinate required/not-required ODP labels | Runtime-valid contract, evidence present, complete group coverage, all spans verbatim, OK/PARAMS_REQUIRED status, correct ODP status and all required reference keys listed |
| ODP sensitivity | Author-labeled required rows | Fraction returning PARAMS_REQUIRED |
| ODP specificity | Author-labeled not-required rows | Fraction not returning PARAMS_REQUIRED |
| Burden proxies | All 20 per path | Answer characters/word count, evidence spans, listed clarification keys |
| Scope/responsiveness review | All 40 path/question pairs | Separate author assessment of entire-question responsiveness and unsupported claims |

An extra listed ODP is an unadjudicated expansion unless the author separately judges it. Key recall alone is not precision. Partial questions may meet a clause-coverage diagnostic but never become whole-question successes. Outside/ambiguous questions have no automatic clause accuracy. Uncertain ODP cases do not enter discrimination or strict denominators. Zero eligible rows give `n.a.`, not zero accuracy. The strict criterion is new, conservative and distinct from historical headline metrics.

Report raw numerators and denominators, Wilson 95% intervals for eligible proportions and exact paired McNemar on the strict eligible pairs. Nonsignificance does not prove equivalence. The intervals assume binomial observations; they do not account for purposive selection or shared/correlated forum users. Do not pool with, update or replace the historical 136-row headline results.

## Interpretation and completion

After automatic scoring, complete the separate author scope/responsiveness review, identify unsupported implementation/assessment/legal claims, and explain partial/unresolved cases. Technical runtime validity or verbatim text alone does not establish responsive interpretation. Answer length and clarification counts are workload proxies, not measured effort. No independent professional correctness has been validated; that is future work.

Publish the source/label registration, run identity, executed notebook and console output, all retained contexts/contracts/generation calls, per-question outcomes, summary, hashes and audited deviations. The automatic summary deliberately leaves experiment completion false until the qualitative review and full audit are separately documented. Preparation files alone do not close this study.
