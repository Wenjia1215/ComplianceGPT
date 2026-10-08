# Proposed answer-level strict-pass extension

Status: exploratory proposal; not adopted as the dissertation's primary endpoint.

Prepared: 2026-10-08. Source snapshot: `72979835f1e05bae513468ca4074b4d43497da2c`.

Branch: `evaluation/strict-pass-extension-20261008`.

## Scope and research question

This proposal changes evaluation requirements only. It does not change generation, retrieval, model settings, prompts, normalization, Runtime Verifier code, labels, frozen outputs, historical result files, or the existing strict-pass endpoint.

The additional question is: when an answer has acceptable evidence IDs and an acceptable contract, does the answer actually delivered to the reader preserve the required obligations and their meaning?

Criteria apply to the Qwen2.5-7B free-form baseline, ComplianceGPT, and the Gemini 3.5 Flash free-form baseline identically. The three-system trial uses the frozen 4-bit Qwen baseline on both revisions. It does not combine Rev. 4 BF16 results with Rev. 5 4-bit results. The archived Gemini runs used matched evidence windows and a free-form prompt, without tools or schema-constrained decoding; findings do not cover other Gemini models, the current consumer product, or the advisor's later demonstration prompt.

The proposal was developed after the archived outputs and earlier results were available. These are retrospective, exploratory analyses, not preregistered confirmatory findings. No criterion, weight, exclusion, threshold, or labeling change is justified by the identity of the winning system.

## Preserve the primary endpoint

Let S0(q,s) be the original offline strict-pass result for question q and system s, evaluated with the frozen comparison configuration.

The existing endpoint requires full expected-clause ID coverage, governing-control agreement, source/revision and verbatim evidence-span validity, and the implemented ODP/status checks. Extra evidence is permitted. Historical counts remain:

| Revision | Qwen baseline | ComplianceGPT | Gemini |
| --- | ---: | ---: | ---: |
| Rev. 5 | 25/100 | 65/100 | 66/100 |
| Rev. 4 | 8/36 | 29/36 | 24/36 |

The Rev. 5 ComplianceGPT–Gemini exact McNemar p-value remains 1.000; the Rev. 4 p-value remains 0.2265625. Neither establishes an accuracy advantage. Nonsignificance is not a proof of equivalence.

Preserve the original per-row outcomes and definitions. Report every extension beside S0, never by replacing a historical S0 value.

## What the existing evaluator does not establish

In `src/generative_answerer/pipeline.py`, the comparison system looks up selected source IDs and attaches their canonical text as `evidence_spans`. This shared wrapper supplies canonical proof records for the generative systems.

In `src/compliancegpt/generator/verifier/verifier.py`, the existing verifier checks those spans, IDs, version, and ODP/status properties. It does not perform semantic entailment or complete obligation coverage checks on the generated `answer_text`.

Consequently, a citation ID can be present and its attached proof can be verbatim even when the answer prose omits, weakens, or misinterprets that clause. Canonical-span validity is not a direct test of the model's generated prose.

## Proposed extension

Define the full proposed endpoint as:

`S_answer = S0 AND W AND L AND A AND F AND P`

There are no weights or compensating partial credits. Every condition is required. A failure cannot be rescued by superior performance elsewhere, and adding conjuncts cannot increase a system's S0 count.

| Predicate | Requirement | Evaluation route |
| --- | --- | --- |
| W: exact provenance | Every returned evidence-span ID is an exact member of the active-revision CCS and the frozen model-visible evidence window. No new fuzzy identity matching is introduced. | Mechanical |
| L: complete retained-obligation accounting | In the registered ASK condition, the normalized ODP list equals the union of named unresolved parameter IDs present in the answer text and all returned evidence spans. Nonempty unresolved obligations require PARAMS_REQUIRED; a normal answer without them requires OK. The ask-list parameter-ID set must equal the declared ODP set. | Mechanical |
| A: answer-level obligation coverage | Every question-required obligation represented by the existing gold clauses is actually expressed in the delivered answer, or explicitly identified as blocked by a particular unresolved parameter. Merely placing the clause ID in a citation list or attaching a hidden proof record does not satisfy coverage. | Clause-to-answer review |
| F: answer-level faithfulness | Each material claim is supported by the cited active-revision evidence. Preserve actor, action, object, mandatory or permissive force, alternatives, exceptions, triggers, timing, and applicability. Do not add unsupported implementation or compliance conclusions. | Claim-to-source review |
| P: parameter-role fidelity | A named parameter retains its actual role and relationship to the relevant obligation. Do not merge independent parameters, change a parameter's type or meaning, or supply an unapproved value. Apply this check to explanation and clarification prompts as well as the normative answer. | Parameter-to-obligation review |

Correct paraphrases can satisfy A, F, and P. Full verbatim reproduction, a particular JSON field layout, the existence of a verifier log, or a particular implementation architecture is not required for these semantic conditions.

Question-relative required obligations and retained-evidence obligations are different. L measures consistency of the evidence actually returned; it does not prove that all question-relevant evidence was retained or that every requested parameter is necessary for the question. Over-asking must remain visible in the separate ODP specificity and precision results.

This first trial concerns the archived ASK condition only. FILL_FROM_PROFILE behavior, approved-profile authority, sentinel handling outside the frozen named-parameter cases, and cross-condition consistency require a separately specified extension and are not scored here.

## Semantic review procedure

Before reviewing all outputs:

1. Freeze this rubric and version the proposed evaluation annotation table separately from the existing gold set. Do not overwrite gold.
2. Derive atomic, question-relevant obligations from the existing gold clauses and the pinned sources. Long guidance records are not automatically lists of mandatory requirements. Distinguish required actions from examples and explanatory background.
3. Present the same answer surface for every system: answer body, displayed citations, status, and clarification requests. Retain source records for review, but do not substitute canonical metadata for an omitted answer.
4. Hide system identity and legacy scores, randomize presentation, and review each obligation, claim, and parameter role using pass / fail / uncertain plus source-supported reasons.
5. Record disagreements and uncertainty. Without independent review, describe the scores as author or exploratory judgments, not independent correctness.
6. Report uncertain rows explicitly. Give a conservative pass lower bound and a possible-pass upper bound; do not silently exclude them from denominators.
7. Report S0, the mechanical extension, each new predicate, and the full answer-level endpoint separately. Preserve failures and error/abstention rows.
8. Register a new, untouched validation set and the same answer requirements for all systems before treating any ranking as confirmatory. If prompts or output requirements change, rerun all systems and label that comparison as a new task.

A blocked answer must still state the source-backed obligation and identify what is missing. Merely reporting PARAMS_REQUIRED does not satisfy A. Conversely, a readable paraphrase does not fail F simply because it differs lexically from the source.

## Completed mechanical trial

The six contract CSV files, both gold CSV files, and both CCS files match their archived SHA-256 identities. The original offline verifier was independently reapplied to all 408 outputs with ASK, strict_extras=False, strict_verbatim=True, and strict_version=True, reproducing all stored outcomes with zero disagreements.

For this positive-evidence benchmark, errors and abstentions receive no successful normal-answer credit. W and L were computed for normal nonempty-evidence answers; none of their new failures occurred on an S0-passing row. Ask-list ID-set agreement held on all ComplianceGPT and Gemini records and on 29/36 Rev. 4 and 67/100 Rev. 5 Qwen records. Every ask-list disagreement occurred on a row already failing the core ODP-accounting predicate, so adding that condition did not change L or the strict-pass counts.

| Revision / endpoint | Qwen baseline | ComplianceGPT | Gemini |
| --- | ---: | ---: | ---: |
| Rev. 5: original S0 | 25/100 | 65/100 | 66/100 |
| Rev. 5: S0 AND W AND L | 25/100 | 65/100 | 66/100 |
| Rev. 4: original S0 | 8/36 | 29/36 | 24/36 |
| Rev. 4: S0 AND W AND L | 8/36 | 29/36 | 24/36 |

Standalone normal-answer diagnostics:

| Revision / property | Qwen baseline | ComplianceGPT | Gemini |
| --- | ---: | ---: | ---: |
| Rev. 5: W | 98/100 | 100/100 | 99/100 |
| Rev. 5: L | 38/100 | 100/100 | 95/100 |
| Rev. 4: W | 36/36 | 36/36 | 36/36 |
| Rev. 4: L | 13/36 | 36/36 | 30/36 |

Gemini's Rev. 5 L failures comprise four inconsistent normal answers (Q6, Q28, Q77, Q81) and one NO_EVIDENCE output (Q34). The abstention is not described as an ODP contradiction. All six Rev. 4 L failures are normal-answer inconsistencies (Q18, Q21, Q24, Q28, Q33, Q36). These are retained-evidence accounting observations, not independently adjudicated question-level errors.

The full S_answer endpoint has not been scored. No numerical full semantic pass rate or winning system is asserted.

## Concrete examples motivating answer-level review

These were identified during retrospective source inspection. They illustrate candidate rubric decisions; they are not a substitute for a blinded complete evaluation.

### Rev. 5 Q24: a cited obligation omitted from the prose

Question: How should configuration settings be established, approved, and monitored?

Gemini passes S0 and returns `cm-6_smt.b` among its evidence IDs. That canonical clause requires implementation of the configuration settings. Gemini's answer discusses establishment, deviations, and monitoring but does not express the implementation obligation.

This motivates A: evidence-list coverage and delivered-answer coverage are different. The question-relative necessity of each atomic obligation must be checked under the frozen rubric rather than inferred solely from an ID.

ComplianceGPT's answer contains the implementation text through its retained parent statement, but its legacy result is still a failure because its selected ID list omits the required child ID. S_answer must preserve that failure; this proposal does not retroactively rescue ComplianceGPT.

### Rev. 4 Q7: a citation and deferral instead of the required explanation

Question: What are the requirements regarding assessment of security controls and frequency?

Gemini passes S0 and cites `ca-2_smt.b`. Its prose says the requirements are defined in CA-2 and that timing and recipients depend on organizational parameters. It does not explain that assessments determine whether controls are implemented correctly, operating as intended, and producing the intended security outcome.

ComplianceGPT retains that obligation verbatim in its answer. This motivates answer-level coverage while allowing Gemini or Qwen to satisfy the same requirement with a correct paraphrase.

### Rev. 4 Q10: a parameter's meaning changes in generated prose

Gemini passes S0. Its answer describes the basis for configuration-setting deviations as an organization-defined “organizational monitoring and assessment path.” The pinned `cm-6_prm_3` record labels the parameter as organization-defined operational requirements.

This motivates P and F: a valid source-ID list and attached canonical clause cannot establish the correctness of a parameter gloss in the prose. A complete review must apply the same scrutiny to all systems' parameter descriptions.

### ComplianceGPT must face the same checks

For Rev. 5 Q1, ComplianceGPT's clarification request for `ac-02_odp.05` labels it as a duration and suggests 30/60/90 days, although the corresponding canonical clause uses the parameter for additional personnel or roles to be notified. Gemini's shared wrapper produces the same clarification in that row. P must evaluate this shared behavior as well; canonical answer construction does not establish semantic correctness of every clarification prompt.

The existing Runtime Verifier mutation study also failed to detect 70 nonempty partial ODP-list deletions. A new evaluation requirement does not repair that runtime limitation.

## Additional source-retention diagnostic

A separate mechanical diagnostic asks whether every gold-required canonical clause's full text appears as a contiguous substring of the answer body after whitespace normalization. Preserve source capitalization, punctuation, and parameter markers. Do not count the auxiliary evidence_spans field as the answer body.

The combined diagnostic below is S0 AND literal answer-body coverage. Every diagnostic-passing archived row also passed W and L.

| Revision | Qwen baseline | ComplianceGPT | Gemini |
| --- | ---: | ---: | ---: |
| Rev. 5 | 1/100 | 65/100 | 0/100 |
| Rev. 4 | 1/36 | 29/36 | 0/36 |

This is an exact-source-retention property, not a semantic accuracy score. The frozen generative prompt explicitly requested concise free-form answers. A correct paraphrase can fail this diagnostic because it changes case, punctuation, wording, or placeholder representation. It therefore cannot be used to claim that Gemini had zero correct answers or that ComplianceGPT won a fair general-QA comparison.

If exact regulatory quotations are the desired new task, give all systems that requirement prospectively and evaluate all systems on the same newly registered protocol. Do not relabel this retrospective diagnostic as a preregistered quote-task comparison.

## What the evidence currently supports

ComplianceGPT's supported strengths are canonical answer construction, full named-ODP accounting on its retained evidence in these frozen outputs, and separation of evidence-selection failures from implemented realization-contract failures.

The current comparison supports neither universal accuracy superiority nor a claim that Gemini cannot implement these properties with additional code. Google documents schema-compliant but semantically incorrect output handling and recommends application validation. Structured output alone is not answer-level entailment, while an appropriately engineered Gemini-based application could also add deterministic construction and checks.

Preserve Gemini's observed advantages in shorter answers, clause precision, and ODP specificity/status precision. Preserve ComplianceGPT's missed evidence, extra parameter requests, and its verifier's partial-list mutation blind spot.

## Pinned evidence

- [Rev. 5 archived summary](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/SUMMARY.md)
- [Rev. 4 archived summary](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/experiments/answerer_comparison/rq2_frontier_baseline/results_v1/SUMMARY.md)
- [Generative prompt](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/src/generative_answerer/generator.py)
- [Shared canonical-span materialization](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/src/generative_answerer/pipeline.py)
- [Existing verifier](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/src/compliancegpt/generator/verifier/verifier.py)
- [Mutation results](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/experiments/answerer_comparison/runtime_verifier_mutation/results_v1/SUMMARY.md)
- [Google structured-output documentation](https://ai.google.dev/gemini-api/docs/structured-output)

Archived output identities:

| Revision | System | SHA-256 |
| --- | --- | --- |
| Rev. 5 | ComplianceGPT | `9440fd02c25e30b4b3fe39890fadb3ec3e120dfd8af9e82ea23fab6f87167cc9` |
| Rev. 5 | Gemini | `8380b370d061dc772e25b353b353b06023540c6c5f6613839c4f36bedccae06e` |
| Rev. 5 | Qwen baseline | `85a3e52b75b283a3fda6c50ae59d8dde4e59748ada7d58c5b88ae8c5c8f2cb63` |
| Rev. 4 | ComplianceGPT | `cb8d49cdff4b1ebcd68f0010b4fbecafd457352cb9e963856b03ef1a0aae50f9` |
| Rev. 4 | Gemini | `14f5c33146a06ada055057e221bfc226282d11e2930281603a7b6c6e491876b7` |
| Rev. 4 | Qwen baseline | `cf891ddd0710125e5d37b43913166f0e7cef50426605133d87915229a90f53b5` |
