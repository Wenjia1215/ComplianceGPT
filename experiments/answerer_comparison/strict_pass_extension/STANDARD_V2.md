# Strict-pass extension v2

Status: implemented trial endpoint on `evaluation/strict-pass-extension-20261008`.

Source snapshot: `72979835f1e05bae513468ca4074b4d43497da2c`. Specification date: 2026-10-08.

## Scope

Re-evaluate the saved matched-window outputs for the Qwen2.5-7B 4-bit free-form baseline, ComplianceGPT and Gemini 3.5 Flash: 100 Revision 5 questions and 36 Revision 4 questions per system, 408 outputs in total. Use the same clauses, labels, revisions, outputs and denominators. Do not regenerate answers, revise gold labels, change retrieval, or overwrite historical scores.

The rubric was developed after examining these outputs and concrete failure examples. This is a retrospective exploratory analysis, not a preregistered or independent expert evaluation. The archived free-form prompt allowed concise paraphrases. Exact quotation is therefore a sufficient proof of source retention, never a required writing style or a gate that rejects correct paraphrases.

The new code is an offline evaluation extension. It does not repair or change Runtime Verifier behavior. Original strict-pass columns and archived summaries retain their original meaning.

## Endpoint

`S_v2 = S0 AND W AND L AND U AND A AND F AND P AND C`

All predicates are mandatory. There is no weighted score, compensating credit, system-specific exception, or rescue of an old failure. Each question counts once even if several predicates fail.

| Gate | Required behavior | Assessment |
| --- | --- | --- |
| S0: unchanged legacy strict | Reproduce the existing verifier outcome, including complete expected clause-ID coverage and all implemented version, evidence-span, ODP and status checks. | Existing code, unchanged |
| W: exact provenance and answer presence | Every returned evidence ID is an exact eligible statement/guidance ID in the active CCS and the frozen question window; IDs are unique. A successful positive-evidence answer has a nonempty body and normal status. | Mechanical |
| L: full retained-parameter accounting | The normalized declared parameter set equals the union of named unresolved placeholders in the body and every returned span. IDs exist in the active parameter inventory. Status agrees with that state; clarification IDs equal declared IDs and clarification sources belong to the returned evidence. | Mechanical |
| U: actual citation use | Every cited record contributes a source-supported proposition actually expressed in the body. An ID in the citation list or a canonical span in an auxiliary field is insufficient. Topic words alone are insufficient. Parent/child overlap is permitted; a citation need not contribute a unique proposition. | Source inspection or full-retention proof |
| A: required answer content | Express the question-relevant required actions, objects and material conditions from the pinned required clauses, or preserve an unresolved parameter as part of its source-backed obligation. A deferral to the control's name alone does not answer the question. | Source inspection or full-retention proof |
| F: claim faithfulness | Every material assertion is supported by cited evidence. Preserve technical relationships, actors, actions, objects, normative force, alternatives, exceptions and explicit applicability conditions. Do not move a qualification to a different requirement. | Source inspection or full-retention proof |
| P: parameter meaning | When interpreting a parameter, preserve its canonical role, structured components and logical relationships. Do not replace an agreement selection with policies/procedures, bind a frequency to a recipient, collapse an unselected alternative, or change conditional conjunction to disjunction. A neutral reference to the whole unresolved parameter is allowed. | Source inspection or full-retention proof |
| C: clarification value domain | A clarification's explicit requested value kind must be compatible with the canonical parameter definition. Inspect both metadata and explicit prompt restrictions. Asking for days, a job title, organization units or a numeric threshold cannot substitute for a different parameter domain. | Conservative canonical-domain check |

The supplementary `answer_content_pass` endpoint omits C so that prose errors can be distinguished from shared clarification-template errors. **The final strict-pass score includes C.** Neither column replaces historical S0.

## Legacy configuration preserved

Use `strict_extras=False`, `strict_verbatim=True`, `strict_version=False`, the requested active corpus revision, and `org_profile={}`. Preserve the gold row's existing ASK, PRESERVE or FILL_FROM_PROFILE policy; do not replace all gold policies with ASK. Generation in these archived runs was configured as ASK. The empty profile leads to PARAMS_REQUIRED where bindings are missing.

The existing S0 policies, as actually implemented in the unchanged verifier, are:

| Existing policy | Exact behavior retained |
| --- | --- |
| Status validity | Accept the implemented status vocabulary; ERROR is always a failure. PARAMS_REQUIRED needs an unresolved placeholder and a nonempty parameter list; OK cannot retain an unresolved placeholder. NO_EVIDENCE cannot carry spans or a substantive body. |
| Governing control | Require 100% recall of the gold governing control. |
| Expected clause IDs | Require every gold statement/guidance ID through the existing candidate-ID matching. A parent containing a child obligation does not replace a missing required child ID. |
| Evidence proof | Resolve every returned source in the active corpus and require a nonempty verbatim substring after whitespace normalization. S0 does not require every span to be the full record, and it does not test generated prose entailment. |
| Revision | Compare the supplied active corpus revision with the gold revision. `strict_version=False` remains unchanged; with the active revision supplied, missing revision tokens in IDs are not a failure. |
| Parameter extraction | Compare the declared list with named placeholders extracted from the body; only when no IDs are extracted there, fall back to all spans. This original fallback is preserved in S0; L additionally checks the full union. |
| Gold-required parameters | Require the gold parameters in the declared list. ASK/PRESERVE require PARAMS_REQUIRED; PRESERVE also checks retained placeholders. FILL_FROM_PROFILE uses the original empty profile and requires PARAMS_REQUIRED for missing bindings. |
| Extra evidence/parameters | Keep `strict_extras=False`: extras alone do not fail S0. The new gates still check actual use, meaning and complete accounting. |
| Final decision | Require full control recall and no hard error; warning tags do not fail S0. |

Extra evidence remains permitted. An extra citation fails U if it does not support anything actually stated; it is not automatically a failure merely because it is outside the gold list. A parent quotation does not rescue a missing child ID under S0.

For the added parameter checks, resolve exact canonical inventory IDs first. Accept a legacy alias only when it resolves uniquely. The legacy zero-padding normalizer can conflate a parent ODP with an enhancement ODP; the new union check must keep these distinct canonical identities separate.

## Coverage and paraphrase boundaries

- Derive required content from the question and its required source clauses, using the original expected answer for scope, not as an exact-match string.
- Do not turn an entire long guidance paragraph into mandatory output. Examples, background and exhaustive lists of possible techniques are not automatically required.
- If a question asks only for a principle's name, a correct name can suffice. A question asking for required steps must retain the required actions and material conditions.
- Abstract, concise descriptions can be correct. A generic reference to the whole unresolved parameter is allowed. An affirmative interpretation that narrows a composite parameter or substitutes a different domain is not.
- Do not infer that every enhancement is universally adopted, or automatically reject additional enhancements. Fail a scope change when the answer misstates a control-specific obligation or drops an explicit source limitation; additional source-backed content alone is not a failure.
- Preserve revision-specific wording. Never invent a Revision 5 qualifier while reviewing a Revision 4 source.

## Clarification-domain boundaries

Read the parameter's own canonical definition, not a nearby span or registry heuristic. `free-text` imposes no restrictive value domain and is allowed unless the prompt independently imposes an incompatible restriction. A temporal period can represent a periodic frequency as a recurrence interval. A composite event set plus logging frequency is not a scalar duration; event names and required situations cannot be replaced by a number of days.

For explicit domains supported by the canonical definition, reject incompatible requests. Distinguish personnel/roles, organizations/units, temporal values, numeric limits, selections, events, controls and non-temporal objects/actions/requirements. Numeric selection alternatives can support a numeric request. Unknown canonical domains are not guessed and are not automatically penalized; the source-inspection record remains responsible for material semantic interpretations. Fluency and presentation quality are outside C.

## Semantic audit and sufficient proof

The evaluation code contains no model-specific or question-number-specific failure rule. Source-inspection judgments are separate, versioned inputs in `reviews_v2.jsonl`, keyed by a hash of the answer surface. That surface includes the revision, question, body, evidence, status, declared parameters and clarification requests, while excluding system identity, model metadata, legacy scores and debug traces. Identical surfaces share a judgment.

Each reviewed surface has pass/fail/uncertain decisions for U, A, F and P, a rationale, and source-supported findings for every nonpassing gate. Failure excerpts must occur exactly in the pinned body and active canonical records. Editing an answer invalidates its review fingerprint. Missing, stale, duplicated or unused review records stop final scoring. The source-inspection judgments are not independently adjudicated; removing identity fields from packets does not make this already retrospective audit blinded.

A full-retention certificate is a sufficient proof for the body gates when: every span is the complete exact canonical statement/guidance record, every gold-required ID is present, and the body equals the concatenation of those records after whitespace normalization. This establishes that the selected text, its obligations and parameter references are expressed without alteration. It does **not** establish independent gold validity, evidence minimality, usefulness, fluent presentation, or clarification correctness. C is always evaluated separately. A paraphrase without this certificate can pass all body gates through source inspection.

Uncertain judgments receive no strict-pass credit. Report the possible-pass upper count separately; retain all original questions in the denominator. Do not select criteria or change judgments based on which system wins.

## Outputs and validation

The runner writes a new `results_v2` directory with per-row CSV/JSONL results, a summary, input/code/rubric/review hashes and a readable report. Verify original contract hashes, matched evidence-window identities, all 408 original per-row outcomes, and original aggregate counts before accepting the extension. Recheck input hashes after scoring. Preserve original CSV files, gold files, generation settings and all Runtime Verifier files.

Tests must cover the known partial-union loophole, omitted prose despite canonical auxiliary spans, accepted correct paraphrases, changed-answer/stale-review rejection, uncertainty, incompatible clarification domains, numeric selections, and inability to rescue a legacy missing-ID failure.

## Reporting boundary

Report the new score as a retrospective contract-fidelity result on these saved outputs. Do not claim a general Gemini failure rate, performance on the advisor's later prompt, or an independently confirmed accuracy advantage. Report paired comparisons and uncertainty; a higher point estimate alone does not establish superiority.
