# Evaluation results and scoring identities

Use this page to distinguish complete answer assessment from the historical
contract/gold check. All counts below refer to saved outputs; they do not come
from new model inference.

## Complete strict pass

The currently published rule is
[`strict-pass-v1`](../src/answerer_comparison/README.md):

`S = C AND W AND L AND U AND A AND F AND P`

C checks the contract and gold conditions. The remaining gates require exact
window provenance, complete retained-parameter accounting, actual citation use,
required body content, faithful claims, and preserved parameter meaning.
Every gate is mandatory, and uncertain judgments remain in the denominator
without pass credit. Source-inspection judgments are retrospective and are not
independently adjudicated.

The legacy `verifier_pass` and `offline_strict_pass` fields record C alone in
the original execution artifacts. Their names predate the complete standard.
Do not interpret those fields as the final seven-gate decision.

## Three-system matched comparison

All three systems use the same questions, ordered evidence windows, gold labels,
and complete scoring standard within each revision.

| Revision | System | Complete strict pass | Legacy contract/gold pass (C) | Full required-clause coverage | Runtime contract pass |
|---|---|---:|---:|---:|---:|
| Rev. 5 | ComplianceGPT | 65/100 | 65/100 | 65/100 | 100/100 |
| Rev. 5 | Gemini 3.5 Flash | 56/100 | 66/100 | 67/100 | 99/100 |
| Rev. 5 | Qwen2.5-7B, free-form 4-bit | 21/100 | 25/100 | 53/100 | 42/100 |
| Rev. 4 | ComplianceGPT | 29/36 | 29/36 | 29/36 | 36/36 |
| Rev. 4 | Gemini 3.5 Flash | 22/36 | 24/36 | 28/36 | 33/36 |
| Rev. 4 | Qwen2.5-7B, free-form 4-bit | 6/36 | 8/36 | 18/36 | 13/36 |

Canonical complete assessments:

- [Revision 5 summary and row-level results](../experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/README.md)
- [Revision 4 summary and row-level results](../experiments/answerer_comparison/rq2_frontier_baseline/results_v1/README.md)
- [Three detailed comparison cases](../experiments/answerer_comparison/STRICT_PASS_EXAMPLES.md)

The exploratory exact paired McNemar p-values for ComplianceGPT versus Gemini
are 0.122078 on Revision 5 and 0.092285 on Revision 4. The observed differences
do not establish statistically significant end-to-end superiority or
population equivalence. Conditional realization-loss comparisons over
different coverage-complete subsets answer a separate descriptive question.

## Original no-selector diagnostic

| Revision | Original no-selector complete strict pass | Legacy contract/gold pass (C) | Full required-clause coverage | Mean answer words |
|---|---:|---:|---:|---:|
| Rev. 5 | 7/100 | 92/100 | 93/100 | 601.7 |
| Rev. 4 | 3/36 | 35/36 | 35/36 | 604.9 |

The original contracts contain empty clarification-request lists. Among the
legacy C passes, 85 Revision 5 outputs and 32 Revision 4 outputs fail complete
retained-parameter accounting. These counts describe the original diagnostic
implementation; they do not isolate the selector's effect. A request-repaired
replay is a different output condition, even if its answer bodies are unchanged.

See the [versioned assessment and reproduction command](../experiments/answerer_comparison/rq2_no_selector/strict_pass_v1/README.md)
for row-level decisions and hashes. Original contract CSVs and archives retain
their historical values.

## Historical execution records

The matched RQ2 v3 archive, original frontier audit reports, and archived gate-width
and BF16 summaries retain the execution-time contract/gold endpoint. For
example, the archived BF16 and 4-bit Revision 4 baselines each have 8/36 C passes.
That statement concerns the legacy endpoint; it is not a complete strict-pass
comparison.

Keep an execution archive separate from a later assessment of its saved answers.
A comparison must identify the revision, answer condition, scoring rule,
denominator, and source artifacts. Runtime validity, clause coverage, C pass,
and complete strict pass are distinct outcomes.

The published v1 scorer retains the original `strict_version=False` contract
checker configuration. Explicit revision-label hardening is a separate versioned
change and must not be attributed to this implementation.
