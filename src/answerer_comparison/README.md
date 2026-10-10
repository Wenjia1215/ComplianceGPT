# Matched Answerer Utilities

`matched_window_runner.py` implements the shared evidence-window construction
and validation used by the corrected matched answerer evaluation.

The experiment holds the question, requested revision, ordered evidence
window, and loaded model instance fixed for each pair. The answer methods then
diverge:

- the generative baseline writes free-form answer content and citations;
- ComplianceGPT selects source IDs and uses deterministic citation-contract
  assembly.

Gold labels are excluded from context preparation and answer construction.
They enter only during offline scoring.

The canonical runner, environment record, execution instructions, manifests,
and validated results are under:

[`experiments/answerer_comparison/rq2_matched/`](../../experiments/answerer_comparison/rq2_matched/)

This module is not a standalone command-line entry point.

## Strict pass

Rule version: `strict-pass-v1`. This standard applies to the saved matched-window
three-system comparison: Qwen2.5-7B 4-bit free-form, ComplianceGPT, and Gemini
3.5 Flash, with 100 Revision 5 and 36 Revision 4 questions per system.

`strict_pass_v2.py` retains the v1 gates and adds explicit active-revision
agreement. See the [versioned replay](../../experiments/answerer_comparison/revision_hardening_v2/README.md)
for rules, fingerprints, inherited review provenance, and unchanged stored
decisions. V1 remains the historical assessment identity.

`S = C AND W AND L AND U AND A AND F AND P`

Every condition is mandatory. All systems use the same standard, questions,
ordered evidence windows and gold labels. Clarification value-domain correctness
is outside the standard; parameter identity, accounting and meaning remain
mandatory. No output is removed from the denominator.

## Strict-pass conditions

| Gate | Requirement | Evaluation |
| --- | --- | --- |
| C | Meet all contract and gold conditions below. | Contract checker |
| W: provenance and answer presence | Every returned source is an exact active-CCS statement/guidance ID in the frozen question window; IDs are unique and the normal answer is nonempty. | Mechanical |
| L: retained-parameter accounting | The declared parameter set equals the union of unresolved named placeholders in the body and all returned spans. Canonical identities are distinct, status agrees with unresolved obligations, clarification IDs equal declared IDs, prompts are nonempty and their source IDs belong to the returned evidence. | Mechanical |
| U: actual citation use | Each cited record contributes a source-supported proposition actually expressed in the body. A listed ID or canonical auxiliary span alone is insufficient. Overlapping citations can support the same proposition; uniqueness is not required. | Source inspection or complete-retention proof |
| A: required answer content | Express the question-relevant actions, objects and material conditions from the original required clauses, or preserve the unresolved parameter within its source-backed obligation. Deferral to a control name is insufficient. | Source inspection or complete-retention proof |
| F: claim faithfulness | Preserve the cited source's actors, actions, objects, technical relations, normative force, alternatives, exceptions and explicit applicability conditions. Do not move a qualification to another requirement. | Source inspection or complete-retention proof |
| P: parameter meaning | Preserve a parameter's canonical role, components and logical relationships when interpreting it. Do not substitute a recipient for a frequency, expand agreement selections to policies/procedures, or silently select an unresolved branch. A neutral whole-parameter reference is allowed. | Source inspection or complete-retention proof |

## Contract and gold conditions

The contract checker uses `strict_extras=False`, `strict_verbatim=True`, `strict_version=False`, the active revision and `org_profile={}`. The gold row's original resolution policy is retained; generation was configured as ASK, but gold policies are not all ASK.

| Existing policy | Retained behavior |
| --- | --- |
| Status | ERROR fails. PARAMS_REQUIRED needs an unresolved placeholder and a nonempty parameter list; OK cannot retain unresolved placeholders. NO_EVIDENCE cannot carry spans or a substantive body. |
| Governing control | Require complete gold governing-control recall. |
| Required clause IDs | Require every gold statement/guidance ID through the existing candidate-ID matching. A parent containing a child's text does not replace a missing required child ID. |
| Evidence proof | Resolve each returned source and require a nonempty verbatim substring after whitespace normalization. This proof checks spans, not prose entailment. |
| Revision | Compare the supplied active corpus revision with the gold revision. Keep the original `strict_version=False` configuration. |
| Parameter extraction | C uses body-extracted placeholders, falling back to spans only when the body yields none. L checks the complete retained union. |
| Gold parameters | Require the original required parameters. ASK/PRESERVE require PARAMS_REQUIRED; PRESERVE also checks retained placeholders. FILL_FROM_PROFILE uses the unchanged empty profile and requires PARAMS_REQUIRED for missing bindings. |
| Extras | Extra sources and parameters alone do not fail C. Other conditions check actual use, meaning and complete accounting. |
| Contract-check decision | Full control recall and no hard error are required; warning tags do not fail C. |

Exact canonical parameter identities take precedence over aliases. An existing alias is accepted only when unique; parent and enhancement parameters that collide under the original normalization are not merged.

## Coverage and paraphrase boundaries

- Required content follows the question, original required clauses and expected-answer scope, rather than an exact expected-answer string.
- Correct concise paraphrases can pass. A principle-name question can be answered with the correct name.
- A long guidance record is not automatically a mandatory exhaustive list. Examples and background need not all be copied.
- Extra cited enhancements are permitted when their claims are source-backed and actually used. Additional evidence alone is not a failure.
- Explicit scope restrictions and logical relationships must be preserved when the corresponding assertion is made. Never import a Revision 5 qualifier into a Revision 4 judgment.

## Assessment and reproduction

Mechanical predicates use the saved contracts and revision-specific CCS.
Citation use, body coverage, claim faithfulness and parameter meaning use
versioned source-inspection records. Exact full canonical spans containing all
required IDs, together with a body equal to their concatenation after whitespace
normalization, provide a sufficient complete-retention proof. This proof is not
a required writing style: faithful, complete paraphrases can pass through source
inspection. It does not establish label independence, evidence minimality or
auditor approval.

Review fingerprints cover the question/revision, body, evidence, status,
parameter and clarification records. Model identity, recorded checker outcomes
and debug metadata are excluded. Identical surfaces share judgments. Missing,
stale, duplicate or unused reviews stop the canonical evaluation. Nonpassing
semantic judgments require exact answer/source excerpts and a rationale.
Uncertain judgments receive no strict credit and remain in the denominator;
Rev5 Gemini Q67 is one such judgment.

The 122 distinct source-inspection records cover 123 output occurrences. The
assessment is retrospective and is not independently adjudicated. Paired tests
are exploratory and unadjusted; nominal Wilson intervals describe these fixed
samples. A higher observed pass rate does not establish general model superiority.

```bash
python experiments/answerer_comparison/run_strict_pass.py
```

This is the offline scoring entry point. It verifies the six saved contract
files, both CCS files and both gold files, matches the question windows, and
reproduces all 408 recorded contract-check decisions. It writes the final
`summary.json`, `SUMMARY.md` and `strict_pass_rows.{csv,jsonl}` directly into the
existing Revision 4/5 frontier result directories and refreshes their materialized
output manifests. Each row has one final `strict_pass` decision. Raw contract
CSVs, model outputs, generation settings, execution archives and the Runtime
Verifier remain unchanged.

For a reproducible copy without writing the repository result directories:

```bash
python experiments/answerer_comparison/run_strict_pass.py --output-root /tmp/compliancegpt_strict_pass
```

- [Revision 5 results](../../experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/SUMMARY.md)
- [Revision 4 results](../../experiments/answerer_comparison/rq2_frontier_baseline/results_v1/SUMMARY.md)
- [Source-inspection records](../../experiments/answerer_comparison/strict_pass_reviews.jsonl)
- [Three detailed examples](../../experiments/answerer_comparison/STRICT_PASS_EXAMPLES.md)
