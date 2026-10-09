# Answer-content strict pass

Rule version: `answer-content-strict-pass-v1`.

This is the Answer-content extension applied to the saved matched-window outputs: 100 Revision 5 and 36 Revision 4 questions for the Qwen2.5-7B 4-bit free-form baseline, ComplianceGPT and Gemini 3.5 Flash. There are 408 outputs. The frozen input snapshot is `72979835f1e05bae513468ca4074b4d43497da2c`.

The current extended strict-pass endpoint is:

`S_answer = S0 AND W AND L AND U AND A AND F AND P`

Every gate is mandatory. There are no weights, system-specific exceptions or rescues of legacy failures. Clarification value-domain correctness is outside this endpoint. Parameter-ID and list accounting remain part of L, as in the Answer-content extension.

## Added gates

| Gate | Requirement | Evaluation |
| --- | --- | --- |
| S0 | Preserve every original strict-pass condition and outcome. | Unchanged offline verifier |
| W: provenance and answer presence | Every returned source is an exact active-CCS statement/guidance ID in the frozen question window; IDs are unique and the normal answer is nonempty. | Mechanical |
| L: retained-parameter accounting | The declared parameter set equals the union of unresolved named placeholders in the body and all returned spans. Canonical identities are distinct, status agrees with unresolved obligations, clarification IDs equal declared IDs, prompts are nonempty and their source IDs belong to the returned evidence. | Mechanical |
| U: actual citation use | Each cited record contributes a source-supported proposition actually expressed in the body. A listed ID or canonical auxiliary span alone is insufficient. Overlapping citations can support the same proposition; uniqueness is not required. | Source inspection or complete-retention proof |
| A: required answer content | Express the question-relevant actions, objects and material conditions from the original required clauses, or preserve the unresolved parameter within its source-backed obligation. Deferral to a control name is insufficient. | Source inspection or complete-retention proof |
| F: claim faithfulness | Preserve the cited source's actors, actions, objects, technical relations, normative force, alternatives, exceptions and explicit applicability conditions. Do not move a qualification to another requirement. | Source inspection or complete-retention proof |
| P: parameter meaning | Preserve a parameter's canonical role, components and logical relationships when interpreting it. Do not substitute a recipient for a frequency, expand agreement selections to policies/procedures, or silently select an unresolved branch. A neutral whole-parameter reference is allowed. | Source inspection or complete-retention proof |

## Original policies retained

The unchanged verifier uses `strict_extras=False`, `strict_verbatim=True`, `strict_version=False`, the active revision and `org_profile={}`. The gold row's original resolution policy is retained; generation was configured as ASK, but gold policies are not all ASK.

| Existing policy | Retained behavior |
| --- | --- |
| Status | ERROR fails. PARAMS_REQUIRED needs an unresolved placeholder and a nonempty parameter list; OK cannot retain unresolved placeholders. NO_EVIDENCE cannot carry spans or a substantive body. |
| Governing control | Require complete gold governing-control recall. |
| Required clause IDs | Require every gold statement/guidance ID through the existing candidate-ID matching. A parent containing a child's text does not replace a missing required child ID. |
| Evidence proof | Resolve each returned source and require a nonempty verbatim substring after whitespace normalization. This proof checks spans, not prose entailment. |
| Revision | Compare the supplied active corpus revision with the gold revision. Keep the original `strict_version=False` configuration. |
| Parameter extraction | S0 uses body-extracted placeholders, falling back to spans only when the body yields none. L additionally checks the complete union without changing S0. |
| Gold parameters | Require the original required parameters. ASK/PRESERVE require PARAMS_REQUIRED; PRESERVE also checks retained placeholders. FILL_FROM_PROFILE uses the unchanged empty profile and requires PARAMS_REQUIRED for missing bindings. |
| Extras | Extra sources and parameters alone do not fail S0. Added gates still check actual use, meaning and complete accounting. |
| Final legacy decision | Full control recall and no hard error are required; warning tags do not fail S0. |

Exact canonical parameter identities take precedence over aliases. A legacy alias is accepted only when unique; parent and enhancement parameters that collide under old normalization are not merged.

## Coverage and paraphrase boundaries

- Required content follows the question, original required clauses and expected-answer scope, rather than an exact expected-answer string.
- Correct concise paraphrases can pass. A principle-name question can be answered with the correct name.
- A long guidance record is not automatically a mandatory exhaustive list. Examples and background need not all be copied.
- Extra cited enhancements are permitted when their claims are source-backed and actually used. Additional evidence alone is not a failure.
- Explicit scope restrictions and logical relationships must be preserved when the corresponding assertion is made. Never import a Revision 5 qualifier into a Revision 4 judgment.

## Source inspection and sufficient proof

The evaluator contains no model-specific or question-number-specific failure rule. `reviews.jsonl` has 122 distinct nonliteral eligible surfaces, representing 123 row occurrences. The U/A/F/P judgments and exact excerpts are unchanged from the trial's Answer-content audit, under this endpoint's own rule version.

Review fingerprints include the pinned body, evidence, revision/question, status, declared parameters and clarification records, excluding model identity, legacy scores and debug metadata. Identical surfaces share judgments. Failure or uncertain findings need exact pinned answer/source excerpts; missing, stale, duplicate or unused reviews stop scoring.

A complete-retention certificate is sufficient proof when all returned spans equal full canonical records, every required ID is returned, and the body equals their concatenation after whitespace normalization. It proves expression without alteration; it does not prove independent gold correctness, evidence minimality or usefulness. A paraphrase can pass through source inspection without this certificate.

Uncertain cases receive no strict credit and remain in the denominator. The possible-pass count is reported separately. Rev5 Gemini Q67 remains uncertain; it is not relabeled to change the ranking.

This rubric was developed after these outputs were available. The audit is retrospective and the judgments are not independently adjudicated. Removing metadata does not make the review blinded. Paired tests and Wilson intervals are descriptive, with no adjustment for multiple comparisons; they do not establish general model superiority.

## Results and reproduction

The final scores are in [results_v1/SUMMARY.md](results_v1/SUMMARY.md). [EXAMPLES.md](EXAMPLES.md) gives three detailed, source-backed comparisons. Historical contract files, score columns and Runtime Verifier behavior are unchanged.

```bash
PYTHONPATH=src python -m unittest tests.test_answer_content_strict_pass compliancegpt.generator.verifier.test_contract_validity
python experiments/answerer_comparison/answer_content_strict_pass/run_evaluation.py --output-dir /tmp/compliancegpt_answer_content
```

The runner verifies six contract hashes, both CCS hashes, both gold hashes, matched windows and all 408 original outcomes before accepting results. It rechecks input hashes after scoring, writes a manifest and preserves all questions in the denominator. No inference service is needed. Evaluation outputs are separate from the archived runs.

To prepare the source-inspection packet without producing semantic scores:

```bash
python experiments/answerer_comparison/answer_content_strict_pass/run_evaluation.py --prepare --output-dir /tmp/compliancegpt_answer_content_reviews
```
