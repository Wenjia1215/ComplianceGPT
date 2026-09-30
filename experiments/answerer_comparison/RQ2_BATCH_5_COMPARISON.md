# RQ2 Batch 5A–5C Follow-on Comparison

This record consolidates the three registered Batch 5 follow-on studies that
address the control-gate, quantization, and stronger-baseline questions raised
about RQ2. It does not merge their result identities or replace the frozen RQ2
v3 result. Cross-system comparisons below use only the 36 shared Revision 4
questions and their identical ordered evidence contexts.

## Experimental boundaries

| Batch | Result identity | Changed factor | Scope | Question answered |
|---|---|---|---|---|
| 5A | `rq2_control_gate_width_v1` | Fixed control-gate width: top 1, 2, 3, or 5; adaptive v3 retained as a frozen reference | 100 Rev. 5 and 36 Rev. 4 rows | Does widening the control gate improve end-to-end coverage enough to justify added evidence and ODP exposure? |
| 5B | `rq2_bf16_baseline_v1` | Qwen2.5-7B free-form baseline weights: 4-bit to true BF16 | 36 Rev. 4 rows | Is the original baseline gap principally an artifact of 4-bit quantization? |
| 5C | `rq2_frontier_baseline_v1` | Free-form answer model and serving runtime: Qwen2.5-7B to Gemini 3.5 Flash | 36 Rev. 4 rows | Does the RQ2 gap persist against a materially stronger hosted model? |

Batch 5A is a within-ComplianceGPT operating-point study. Batch 5B is a
within-Qwen precision study. Batch 5C is a stronger-system comparison rather
than a one-factor model-weight experiment. Their conclusions therefore remain
separate even though the shared Rev. 4 rows permit a unified descriptive table.

## Unified Revision 4 outcomes

| System or condition | Strict pass | Full clause coverage | Runtime contract pass | Right governing control |
|---|---:|---:|---:|---:|
| ComplianceGPT, adaptive v3 | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 36/36 (1.000) |
| ComplianceGPT, fixed top 1 | 26/36 (0.722) | 26/36 (0.722) | 36/36 (1.000) | 34/36 (0.944) |
| ComplianceGPT, fixed top 2 | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 36/36 (1.000) |
| ComplianceGPT, fixed top 3 | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 36/36 (1.000) |
| ComplianceGPT, fixed top 5 | 28/36 (0.778) | 28/36 (0.778) | 36/36 (1.000) | 36/36 (1.000) |
| Qwen2.5-7B free-form, 4-bit | 8/36 (0.222) | 18/36 (0.500) | 13/36 (0.361) | 36/36 (1.000) |
| Qwen2.5-7B free-form, BF16 | 8/36 (0.222) | 20/36 (0.556) | 14/36 (0.389) | 36/36 (1.000) |
| Gemini 3.5 Flash free-form | 24/36 (0.667) | 28/36 (0.778) | 33/36 (0.917) | 36/36 (1.000) |

The shared strict-pass endpoint requires full expected-clause coverage,
source/revision/verbatim validity, and ODP/status consistency; additional
evidence is permitted.

## Evidence and ODP operating characteristics

| System or condition | Mean clause precision | Mean clause recall | Mean selected clauses | Mean answer words | ODP sensitivity* | ODP specificity* | ODP status precision* |
|---|---:|---:|---:|---:|---:|---:|---:|
| ComplianceGPT, adaptive v3 | 0.505 | 0.886 | 4.03 | 167.2 | 19/19 (1.000) | 8/17 (0.471) | 19/28 (0.679) |
| ComplianceGPT, fixed top 1 | 0.497 | 0.827 | 3.89 | 143.8 | 19/19 (1.000) | 8/17 (0.471) | 19/28 (0.679) |
| ComplianceGPT, fixed top 2 | 0.511 | 0.867 | 3.86 | 157.4 | 19/19 (1.000) | 8/17 (0.471) | 19/28 (0.679) |
| ComplianceGPT, fixed top 3 | 0.511 | 0.872 | 3.97 | 154.3 | 19/19 (1.000) | 8/17 (0.471) | 19/28 (0.679) |
| ComplianceGPT, fixed top 5 | 0.491 | 0.856 | 4.17 | 163.8 | 19/19 (1.000) | 8/17 (0.471) | 19/28 (0.679) |
| Qwen2.5-7B free-form, 4-bit | 0.488 | 0.596 | 3.33 | 36.8 | 0/19 (0.000) | 17/17 (1.000) | —† |
| Qwen2.5-7B free-form, BF16 | 0.575 | 0.664 | 2.89 | 41.3 | 0/19 (0.000) | 17/17 (1.000) | —† |
| Gemini 3.5 Flash free-form | 0.615 | 0.833 | 3.06 | 44.9 | 18/19 (0.947) | 11/17 (0.647) | 18/24 (0.750) |

*ODP values use author labels and remain provisional until the blinded
independent annotation is returned. †The Qwen baselines never predicted
`PARAMS_REQUIRED`, so positive predictive value is undefined; perfect
specificity must not be read without their zero sensitivity.*

## Strict-pass decomposition on the shared rows

| System | Rows with full clause coverage | Strict passes | Coverage-complete rows rejected by remaining strict predicates |
|---|---:|---:|---:|
| ComplianceGPT, adaptive v3 | 29 | 29 | 0 |
| Qwen2.5-7B free-form, 4-bit | 18 | 8 | 10 |
| Qwen2.5-7B free-form, BF16 | 20 | 8 | 12 |
| Gemini 3.5 Flash free-form | 28 | 24 | 4 |

For ComplianceGPT, gate-width changes affected full evidence coverage while
all contracts remained runtime-valid. Increasing Qwen precision improved
coverage by two rows but did not improve strict pass. Gemini closed most of
the free-form baseline's evidence and contract-conformance gap, although four
coverage-complete rows still failed another strict predicate.

## Paired strict-pass tests

| Paired comparison | Left only | Right only | Exact two-sided McNemar p | Interpretation |
|---|---:|---:|---:|---|
| Rev. 4 fixed top 1 vs fixed top 2 | 1 | 4 | 0.375 | No detected gate-width difference |
| Rev. 4 fixed top 2 vs fixed top 3 | 0 | 0 | 1.000 | Identical strict-pass set |
| Rev. 4 adaptive v3 vs fixed top 5 | 2 | 1 | 1.000 | No detected gate-width difference |
| Qwen BF16 vs Qwen 4-bit | 2 | 2 | 1.000 | No quantization effect on strict pass |
| ComplianceGPT vs Qwen BF16 | 21 | 0 | 0.0000009537 | ComplianceGPT advantage remains after removing 4-bit quantization |
| Gemini vs Qwen 4-bit | 18 | 2 | 0.00040245 | Stronger free-form model materially improves strict pass |
| Gemini vs Qwen BF16 | 18 | 2 | 0.00040245 | Stronger free-form model materially improves strict pass |
| ComplianceGPT vs Gemini | 8 | 3 | 0.2265625 | ComplianceGPT has the higher observed rate, but the paired difference is not significant on 36 rows |

The McNemar results are paired conditional comparisons over the frozen sample;
they are not population-level equivalence or superiority claims.

## Revision 5 gate-width sensitivity

Batch 5B and Batch 5C were registered only for Revision 4. The Revision 5
evidence therefore comes from Batch 5A alone.

| ComplianceGPT gate | Strict pass | Full clause coverage | Runtime pass | Right control | Mean clause precision | Mean clause recall | ODP sensitivity* | ODP specificity* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Adaptive v3 | 65/100 | 65/100 | 100/100 | 97/100 | 0.584 | 0.835 | 63/63 | 17/37 |
| Fixed top 1 | 62/100 | 62/100 | 100/100 | 91/100 | 0.582 | 0.795 | 62/63 | 17/37 |
| Fixed top 2 | 65/100 | 65/100 | 100/100 | 99/100 | 0.572 | 0.832 | 63/63 | 16/37 |
| Fixed top 3 | 65/100 | 65/100 | 100/100 | 99/100 | 0.565 | 0.825 | 63/63 | 16/37 |
| Fixed top 5 | 67/100 | 67/100 | 100/100 | 99/100 | 0.560 | 0.834 | 63/63 | 12/37 |

No stored within-revision gate-width comparison reached `p < 0.05`. Fixed top
2 is the parsimonious fixed-width operating point because it matched the
adaptive strict-pass count on both revisions. Fixed top 5 gained two Revision
5 passes but lost one Revision 4 pass and reduced Revision 5 ODP specificity.
The released adaptive gate therefore remains the defensible default.

## Consolidated findings

1. **Control-gate width is not the main explanation for RQ2 performance.**
   Top 2 recovered the adaptive strict-pass counts, but no tested width was
   significantly better and wider gates exposed an ODP-specificity tradeoff.
2. **Four-bit quantization does not explain the weak Qwen baseline.** True
   BF16 raised full clause coverage from 18/36 to 20/36, while strict pass
   remained 8/36 with a symmetric two-versus-two discordance.
3. **Free-form model strength matters.** Gemini reached 24/36 strict pass and
   significantly outperformed both Qwen baselines. The original comparison
   against a 4-bit 7B model therefore understated what a strong free-form
   answerer can achieve.
4. **The stronger baseline narrows but does not reverse the observed result.**
   ComplianceGPT retained the highest observed strict-pass count, 29/36 versus
   Gemini's 24/36, and perfect runtime-contract validity. The paired test does
   not establish a significant difference between them at this sample size.
5. **The most defensible claim is mechanistic.** ComplianceGPT prevented
   contract/status loss once full evidence was present and made unresolved
   ODPs visible by construction. Gemini showed that a strong model can
   approximate much of that behavior, but not with the same deterministic
   runtime guarantee. Evidence completeness remains upstream and unresolved
   by the citation contract.

## Evidence provenance

The tables above were transcribed from these immutable machine-readable
summaries and independently checked against them:

| Batch | Summary | Summary SHA-256 | Archived result identity |
|---|---|---|---|
| 5A | [`rq2_control_gate_width/results_v1/summary.json`](rq2_control_gate_width/results_v1/summary.json) | `0418612200de5f9550ac576ae216fd6372b8c7ade91d5a7f253da7a582c95358` | Canonical ZIP `543c2e40879422a5a1462bb6fc56fda2ad76f9b060efbc780ebe2a51bc48a07d` |
| 5B | [`rq2_bf16_baseline/results_v1/summary.json`](rq2_bf16_baseline/results_v1/summary.json) | `2b7a251c884f9fa25df9b13539164bb9366e75f27711e7b7a494ab345244c339` | Supplied Drive export `4039e67453d46b12ad214a3759d16e5a4c9f1028353dd6e253fca06f3b57a561` |
| 5C | [`rq2_frontier_baseline/results_v1/summary.json`](rq2_frontier_baseline/results_v1/summary.json) | `97943089d1cce2ee35ad65ba3da814e2e7e4cebc1d5cf44cae48447508dc1efc` | Corrected archive `351af9780f0ed7e6714ed3eb81799e8793985ea8b14351f32da9e43ebefa0dfb`; byte-exact runner archive `039ce427f717b83da6f54a87a67bb0438f6c15e44b49d29838d39bc523c20767` |

The Batch 5C correction records the operator-confirmed Paid Tier 1 provenance
in `run_config.json`; it changes no response, contract, metric, token count, or
other scientific output.
