# RQ2 Batch 5A–5D Follow-on Comparison

This record consolidates the four registered Batch 5 follow-on studies that
address the control-gate, quantization, and stronger-baseline questions raised
about RQ2. It keeps every result identity separate and does not replace the
frozen RQ2 v3 result. Batch 5C provides the 36-row Revision 4 frontier
comparison; the pre-committed Batch 5D study extends that comparison to the
primary 100-row Revision 5 benchmark.

The three-system tables use the [complete strict-pass standard](../../src/answerer_comparison/README.md)
and saved matched-window outputs. **Among these three main systems, ComplianceGPT
has the highest observed strict-pass rate on both revisions. Its paired differences from Gemini are not
statistically significant at 0.05.** Semantic judgments are not independently
adjudicated, and the comparisons are exploratory. Batch 5A gate-width and
Batch 5B precision results remain separate archived studies.

Use the [result and scoring map](../../docs/EVALUATION_RESULTS.md) to distinguish
the complete endpoint from the legacy contract/gold check (C). Original execution
audits and archives retain C, including fields historically named `strict_pass`.

The later [paired analysis](paired_conditional_statistics/README.md) adds
intervals, common-coverage diagnostics, and uncertainty sensitivity. The
[request-repaired no-selector replay](retrospective_repairs/README.md) passes
92/100 and 35/36, exceeding all three main systems. It remains a separate
retrospective output condition. The [repeated-label sensitivity](../annotation_reliability/repeated_annotation_sensitivity/README.md)
also has its own sampled denominator and does not replace this comparison.

## Experimental boundaries

| Batch | Result identity | Changed factor | Scope | Question answered |
|---|---|---|---|---|
| 5A | `rq2_control_gate_width_v1` | ComplianceGPT control-gate width: fixed top 1, 2, 3, or 5; adaptive v3 retained as a frozen reference | 100 Rev. 5 and 36 Rev. 4 rows | Does widening the control gate improve end-to-end coverage enough to justify added evidence and ODP exposure? |
| 5B | `rq2_bf16_baseline_v1` | Qwen2.5-7B free-form baseline weights: 4-bit to true BF16 | 36 Rev. 4 rows | Is the original baseline gap principally an artifact of 4-bit quantization? |
| 5C | `rq2_frontier_baseline_v1` | Free-form answer model and serving runtime: Qwen2.5-7B to Gemini 3.5 Flash | 36 Rev. 4 rows | Does the RQ2 gap persist against a materially stronger hosted model? |
| 5D | `rq2_frontier_baseline_rev5_v1` | Same registered frontier protocol as Batch 5C, applied to the primary benchmark | 100 Rev. 5 rows | On the larger, harder benchmark, are ComplianceGPT and Gemini distinguishable, and does realization loss remain observable? |

Batch 5A is a within-ComplianceGPT operating-point study. Batch 5B is a
within-Qwen precision study. Batches 5C and 5D are stronger-system comparisons,
not one-factor weight experiments. Their conclusions remain separate even
where their matched inputs permit unified descriptive tables.

## Descriptive coverage-conditioned loss

Coverage-conditioned loss asks a narrower question than end-to-end strict pass:
once every required gold clause ID is retained, how often is the answer rejected because
of a citation, source, status, contract, or answer-content failure?

### Revision 4 (36 matched rows)

| System | Coverage-complete | Strict pass | Lost | Realization loss |
|---|---:|---:|---:|---:|
| ComplianceGPT | 29 | 29 | 0 | 0/29 (0.0%; 95% Wilson CI 0.0%–11.7%) |
| Gemini 3.5 Flash | 28 | 22 | 6 | 6/28 (21.4%; 95% Wilson CI 10.2%–39.5%) |
| Qwen2.5-7B 4-bit | 18 | 6 | 12 | 12/18 (66.7%; 95% Wilson CI 43.7%–83.7%) |

The coverage-complete subsets differ by system and overlap in question
membership. Their loss rates are descriptive. The later paired analysis uses
the same 25 questions for both systems in its common-coverage diagnostic;
the overall paired comparison keeps all 36 questions.

### Revision 5 (100 matched rows)

| System | Coverage-complete | Strict pass | Lost | Realization loss |
|---|---:|---:|---:|---:|
| ComplianceGPT | 65 | 65 | 0 | 0/65 (0.0%; 95% Wilson CI 0.0%–5.6%) |
| Gemini 3.5 Flash | 67 | 56 | 11 | 11/67 (16.4%; 95% Wilson CI 9.4%–27.1%) |
| Qwen2.5-7B 4-bit | 53 | 21 | 32 | 32/53 (60.4%; 95% Wilson CI 46.9%–72.4%) |

The paired common-coverage diagnostic uses the same 54 questions for both
systems, while the overall comparison retains all 100. Independent-subset
Fisher tests in historical reports do not account for overlapping question
membership and do not supply the inferential comparison on this page.

On these saved outputs, ComplianceGPT expresses the selected canonical text
without alteration and has zero observed coverage-complete realization loss.
The complete-retention proof certifies its body-content predicates; the
Runtime Verifier checks the machine-verifiable contract conditions. Gold
correctness and relevance remain evaluation assumptions. Gemini has 11/67
coverage-complete rejections. The finite counts do not establish zero future
risk or general model superiority.

## End-to-end outcomes

### Revision 4

| System or condition | Strict pass | Full clause coverage | Runtime contract pass | Right governing control |
|---|---:|---:|---:|---:|
| ComplianceGPT, adaptive v3 | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 36/36 (1.000) |
| Gemini 3.5 Flash free-form | 22/36 (0.611) | 28/36 (0.778) | 33/36 (0.917) | 36/36 (1.000) |
| Qwen2.5-7B free-form, 4-bit | 6/36 (0.167) | 18/36 (0.500) | 13/36 (0.361) | 36/36 (1.000) |

### Revision 5

| System | Strict pass | Full clause coverage | Runtime contract pass | Right governing control |
|---|---:|---:|---:|---:|
| ComplianceGPT, adaptive v3 | 65/100 (0.650) | 65/100 (0.650) | 100/100 (1.000) | 97/100 (0.970) |
| Gemini 3.5 Flash free-form | 56/100 (0.560) | 67/100 (0.670) | 99/100 (0.990) | 97/100 (0.970) |
| Qwen2.5-7B free-form, 4-bit | 21/100 (0.210) | 53/100 (0.530) | 42/100 (0.420) | 93/100 (0.930) |

The strict-pass endpoint requires contract/gold conformance, exact provenance,
complete parameter accounting, actual citation use, required body content,
claim faithfulness and parameter meaning. Extra evidence and correct
paraphrases are permitted. Clarification value domains are not scored.

## Paired strict-pass tests

| Revision and paired comparison | Left only | Right only | Exact two-sided McNemar p |
|---|---:|---:|---:|
| rev4, ComplianceGPT vs Gemini | 10 | 3 | 0.0922851562 |
| rev4, ComplianceGPT vs Qwen 4-bit | 24 | 1 | 1.54972076e-06 |
| rev4, Gemini vs Qwen 4-bit | 17 | 1 | 0.000144958496 |
| rev5, ComplianceGPT vs Gemini | 18 | 9 | 0.122078121 |
| rev5, ComplianceGPT vs Qwen 4-bit | 46 | 2 | 8.363088e-12 |
| rev5, Gemini vs Qwen 4-bit | 36 | 1 | 5.52972779e-10 |

These are exploratory, unadjusted paired comparisons over the saved questions.
ComplianceGPT has higher observed pass rates than Gemini, but the two paired
p-values exceed 0.05. Neither a nonsignificant test nor these fixed benchmark
samples establish population equivalence or general superiority.

The 95% paired difference intervals are [-1.2, 18.9] percentage points on
Revision 5 and [-0.4, 37.4] on Revision 4. Both include zero. See the
[full paired table and row-level evidence](paired_conditional_statistics/README.md).

### Common-coverage and uncertain-judgment diagnostics

ComplianceGPT passes all 54 and 25 common-coverage Gemini questions; Gemini
passes 47 and 19. Exact p-values are 0.015625 and 0.03125. A supplementary
Holm adjustment across four ComplianceGPT/Gemini and ComplianceGPT/Qwen
conditional comparisons gives 0.03125 for both Gemini contrasts.

Granting optimistic credit to the two uncertain semantic gates on Revision 5
Gemini Q67 changes its common-coverage pass count to 48/54. Both Gemini
contrasts then have Holm p = 0.0625, although Revision 4 outcomes stay fixed.
These selected, retrospective diagnostics do not establish a causal effect
or replace the inconclusive overall Gemini comparisons.

## ODP operating point

### Revision 4

| System | ODP sensitivity | ODP specificity | ODP status precision |
|---|---:|---:|---:|
| ComplianceGPT | 19/19 (1.000) | 8/17 (0.471) | 19/28 (0.679) |
| Gemini 3.5 Flash | 18/19 (0.947) | 11/17 (0.647) | 18/24 (0.750) |
| Qwen2.5-7B, either precision | 0/19 (0.000) | 17/17 (1.000) | Undefined |

### Revision 5

| System | ODP sensitivity | ODP specificity | ODP status precision | Exact positive-row ODP set |
|---|---:|---:|---:|---:|
| ComplianceGPT | 63/63 (1.000) | 17/37 (0.459) | 63/83 (0.759) | 55/63 (0.873) |
| Gemini 3.5 Flash | 56/63 (0.889) | 31/37 (0.838) | 56/62 (0.903) | 46/63 (0.730) |
| Qwen2.5-7B 4-bit | 0/63 (0.000) | 37/37 (1.000) | Undefined | 21/63 (0.333) |

Sensitivity and specificity must be reported together. ComplianceGPT selects a
high-sensitivity operating point: it detects every author-labeled ODP-positive
row, but it marks 20/37 Revision 5 negative rows as `PARAMS_REQUIRED`. Gemini
marks fewer author-labeled negative rows and has higher status precision, while missing 7/63
positive rows. Qwen's perfect specificity is not useful without its zero
sensitivity.

The behavior observed in a free-form model is a property of that model,
version, prompt, and serving runtime. The ComplianceGPT contract enforces the
`PARAMS_REQUIRED` safety behavior for any selector and the Runtime Verifier can
check it without gold labels. The operating-characteristic values above use
current author labels and have not been independently adjudicated. The completed
30-row author retest measures repeatability, with 16/30 exact clause-set
agreement. Its [score-sensitivity analysis](../annotation_reliability/repeated_annotation_sensitivity/README.md)
keeps these original benchmark outcomes and reports revised sampled bounds.

## Evidence and verbosity tradeoff

| Revision | System | Mean clause precision | Mean clause recall | Mean answer words |
|---|---|---:|---:|---:|
| Rev. 4 | ComplianceGPT | 0.505 | 0.886 | 167.2 |
| Rev. 4 | Gemini 3.5 Flash | 0.615 | 0.833 | 44.9 |
| Rev. 5 | ComplianceGPT | 0.584 | 0.835 | 220.7 |
| Rev. 5 | Gemini 3.5 Flash | 0.696 | 0.775 | 60.2 |

Across both revisions, ComplianceGPT retains canonical source text and has higher
clause recall at a clear cost in precision and length. Gemini is
substantially more concise and precise. For the target audit setting, retaining
governing text with resolvable citations is the chosen failure mode, but this
is an engineering tradeoff rather than a universal advantage.

## Archived gate-width finding under the legacy C endpoint

In the archived Batch 5A evaluation, fixed top 2 matched the adaptive gate's
reported contract/gold pass count on both revisions:
29/36 on Revision 4 and 65/100 on Revision 5. Fixed top 3 also matched those
counts, and the Revision 4 top-2 versus top-3 pass sets were identical. Top 1
was worse (26/36 and 62/100) and reduced governing-control accuracy. Top 5 was
unstable across revisions and reduced Revision 5 ODP specificity.

The tested data therefore show no benefit from the adaptive gate over a
constant top-2 gate. Fixed top 2 is the simpler evidence-supported operating
point; retaining the adaptive implementation path is an engineering option,
not an empirically supported performance claim.

## Consolidated findings

1. **ComplianceGPT leads the three main systems numerically.** The paired
   discordance against Gemini is 10:3 on Revision 4 (`p = 0.0923`) and 18:9
   on Revision 5 (`p = 0.1221`). These comparisons do not establish a
   statistically significant end-to-end difference.
2. **Canonical retention preserves expressed obligations and source meaning.**
   The evaluated ComplianceGPT bodies satisfy the complete-retention proof;
   their zero observed conditional loss remains subject to gold and corpus
   assumptions. Runtime checks and source-inspection judgments are distinct.
3. **Gemini is a stronger free-form baseline than Qwen.** Its strict-pass
   rates are higher, but coverage-complete realization loss remains 6/28 on
   Revision 4 and 11/67 on Revision 5.
4. **Contract-enforced ODP safety has a measurable operating cost.** It retains
   100% sensitivity under the author labels but has lower specificity and
   precision than Gemini on both revisions.
5. **The archived precision study isolates quantization.** BF16
   improves Revision 4 coverage from 18/36 to 20/36 but leaves the legacy
   contract/gold pass count at 8/36. This comparison concerns C.
6. **The archived gate-width study supports a simpler gate.** Fixed top 2
   reproduces the adaptive pass count in that study, so the adaptive mechanism has not earned
   its added complexity in these experiments.
7. **Request-repaired no-selector passes more questions.** Its 92/100 and
   35/36 counts include every ComplianceGPT pass while returning longer bodies
   and more request records. These proxies do not establish human review cost.
8. **An unchanged retest total hides changed decisions.** ComplianceGPT gains
   Revision 5 Q84 and loses Revision 4 Q14, keeping 25/30 combined passes.
   Generative retest totals remain bounded where new semantic reviews are absent.

## Evidence provenance

The three-system tables are derived from the current machine-readable summaries
and row-level assessments. The original execution ZIPs remain byte-exact; their
embedded summaries and manifests retain the historical execution record:

| Batch | Summary | Summary SHA-256 | Archived result identity |
|---|---|---|---|
| 5A | [`rq2_control_gate_width/results_v1/summary.json`](rq2_control_gate_width/results_v1/summary.json) | `0418612200de5f9550ac576ae216fd6372b8c7ade91d5a7f253da7a582c95358` | Canonical ZIP `543c2e40879422a5a1462bb6fc56fda2ad76f9b060efbc780ebe2a51bc48a07d` |
| 5B | [`rq2_bf16_baseline/results_v1/summary.json`](rq2_bf16_baseline/results_v1/summary.json) | `2b7a251c884f9fa25df9b13539164bb9366e75f27711e7b7a494ab345244c339` | Supplied Drive export `4039e67453d46b12ad214a3759d16e5a4c9f1028353dd6e253fca06f3b57a561` |
| 5C | [`rq2_frontier_baseline/results_v1/summary.json`](rq2_frontier_baseline/results_v1/summary.json) | `cebee13040bda0e40b99f75f9c8b4e960f25da8729f476badf30760df1e04e3a` | Corrected archive `351af9780f0ed7e6714ed3eb81799e8793985ea8b14351f32da9e43ebefa0dfb`; byte-exact runner archive `039ce427f717b83da6f54a87a67bb0438f6c15e44b49d29838d39bc523c20767` |
| 5D | [`rq2_frontier_baseline_rev5/results_v1/summary.json`](rq2_frontier_baseline_rev5/results_v1/summary.json) | `bf5c8baefd2a88e7a6a340b87b76d589b681b990754daa0411539b518edc177d` | Byte-exact runner archive `9f088b2ccb410fdd6df8980d693529320fec351e9a01e7400cd7d48fc55dddef` |

The completed Batch 5D notebook is retained with its execution counts and
outputs. Its SHA-256 is
`2e96e47c83f4d02e04b992a81d76cb3c8e670cffbc876d3329437637a1247fcc`.
The Batch 5C metadata correction records operator-confirmed Paid Tier 1
provenance and changes no response, contract, metric, token count, or other
scientific output.
