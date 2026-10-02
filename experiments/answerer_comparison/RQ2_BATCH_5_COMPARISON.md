# RQ2 Batch 5A–5D Follow-on Comparison

This record consolidates the four registered Batch 5 follow-on studies that
address the control-gate, quantization, and stronger-baseline questions raised
about RQ2. It keeps every result identity separate and does not replace the
frozen RQ2 v3 result. Batch 5C provides the 36-row Revision 4 frontier
comparison; the pre-committed Batch 5D study extends that comparison to the
primary 100-row Revision 5 benchmark.

The strict-pass result is intentionally stated without a direction claim:
**ComplianceGPT and Gemini 3.5 Flash are statistically indistinguishable on
strict pass on both revisions. The claimed distinction is not accuracy; it is
construction-enforced realization and runtime verifiability.**

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

## Headline result: coverage-complete realization loss

Realization loss asks a narrower question than end-to-end strict pass: once all
required evidence is present, how often is the answer still rejected because
of a citation, source, status, or contract failure?

### Revision 4 (36 matched rows)

| System | Coverage-complete | Strict pass | Lost | Realization loss |
|---|---:|---:|---:|---:|
| ComplianceGPT | 29 | 29 | 0 | 0/29 (0.0%) |
| Gemini 3.5 Flash | 28 | 24 | 4 | 4/28 (14.3%) |
| Qwen2.5-7B BF16 | 20 | 8 | 12 | 12/20 (60.0%) |
| Qwen2.5-7B 4-bit | 18 | 8 | 10 | 10/18 (55.6%) |

For ComplianceGPT versus Gemini, the two-sided Fisher exact p-value is
`0.0518341`. This is close to, but does not cross, the pre-specified `0.05`
threshold.

### Revision 5 (100 matched rows)

| System | Coverage-complete | Strict pass | Lost | Realization loss |
|---|---:|---:|---:|---:|
| ComplianceGPT | 65 | 65 | 0 | 0/65 (0.0%; 95% Wilson CI 0.0%–5.6%) |
| Gemini 3.5 Flash | 67 | 66 | 1 | 1/67 (1.5%; 95% Wilson CI 0.3%–8.0%) |
| Qwen2.5-7B 4-bit | 53 | 25 | 28 | 28/53 (52.8%; 95% Wilson CI 39.7%–65.6%) |

For ComplianceGPT versus Gemini, the registered two-sided Fisher exact p-value
is `1.0`. The larger study therefore does not establish an empirical
realization-loss-rate difference between them.

ComplianceGPT's observed zero loss is predicted by construction: deterministic
assembly and the Runtime Verifier make a coverage-complete contract a strict
pass. The zero counts confirm that the implementation matches that
specification on both benchmarks; they are not presented as an estimated
zero-risk rate. Gemini's 1/67 result is excellent empirical performance under
this model and prompt, but the free-form protocol does not guarantee it in
advance or expose a model-independent verifier for it. That guarantee and
verifiability distinction—not an accuracy-superiority claim—is the durable
mechanistic result.

## End-to-end outcomes

### Revision 4

| System or condition | Strict pass | Full clause coverage | Runtime contract pass | Right governing control |
|---|---:|---:|---:|---:|
| ComplianceGPT, adaptive v3 | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 36/36 (1.000) |
| ComplianceGPT, fixed top 1 | 26/36 (0.722) | 26/36 (0.722) | 36/36 (1.000) | 34/36 (0.944) |
| ComplianceGPT, fixed top 2 | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 36/36 (1.000) |
| ComplianceGPT, fixed top 3 | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 36/36 (1.000) |
| ComplianceGPT, fixed top 5 | 28/36 (0.778) | 28/36 (0.778) | 36/36 (1.000) | 36/36 (1.000) |
| Gemini 3.5 Flash free-form | 24/36 (0.667) | 28/36 (0.778) | 33/36 (0.917) | 36/36 (1.000) |
| Qwen2.5-7B free-form, BF16 | 8/36 (0.222) | 20/36 (0.556) | 14/36 (0.389) | 36/36 (1.000) |
| Qwen2.5-7B free-form, 4-bit | 8/36 (0.222) | 18/36 (0.500) | 13/36 (0.361) | 36/36 (1.000) |

### Revision 5

| System | Strict pass | Full clause coverage | Runtime contract pass | Right governing control |
|---|---:|---:|---:|---:|
| ComplianceGPT, adaptive v3 | 65/100 (0.650) | 65/100 (0.650) | 100/100 (1.000) | 97/100 (0.970) |
| Gemini 3.5 Flash free-form | 66/100 (0.660) | 67/100 (0.670) | 99/100 (0.990) | 97/100 (0.970) |
| Qwen2.5-7B free-form, 4-bit | 25/100 (0.250) | 53/100 (0.530) | 42/100 (0.420) | 93/100 (0.930) |

The shared strict-pass endpoint requires full expected-clause coverage,
source/revision/verbatim validity, and ODP/status consistency; additional
evidence is permitted.

## Paired strict-pass tests

| Revision and paired comparison | Left only | Right only | Exact two-sided McNemar p | Interpretation |
|---|---:|---:|---:|---|
| Rev. 4, ComplianceGPT vs Gemini | 8 | 3 | 0.2265625 | Not statistically distinguishable |
| Rev. 5, ComplianceGPT vs Gemini | 11 | 12 | 1.000 | Not statistically distinguishable |
| Rev. 4, Gemini vs Qwen 4-bit | 18 | 2 | 0.00040245 | Gemini materially improves strict pass |
| Rev. 4, Gemini vs Qwen BF16 | 18 | 2 | 0.00040245 | Gemini materially improves strict pass |
| Rev. 5, Gemini vs Qwen 4-bit | 42 | 1 | 0.0000000000100044 | Gemini materially improves strict pass |
| Rev. 4, Qwen BF16 vs Qwen 4-bit | 2 | 2 | 1.000 | No detected quantization effect |
| Rev. 4, fixed top 2 vs fixed top 3 | 0 | 0 | 1.000 | Identical strict-pass set |

The McNemar results are paired conditional comparisons over the frozen
samples. They are not population-level equivalence claims. In particular,
`p = 0.2265625` on Revision 4 does not mean “better but unproven,” and the
near-equal Revision 5 discordance supplies no direction claim either.

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
has fewer false alarms and higher status precision, while missing 7/63
positive rows. Qwen's perfect specificity is not useful without its zero
sensitivity.

The behavior observed in a free-form model is a property of that model,
version, prompt, and serving runtime. The ComplianceGPT contract enforces the
`PARAMS_REQUIRED` safety behavior for any selector and the Runtime Verifier can
check it without gold labels. The operating-characteristic values above use
current author labels and have not been independently adjudicated; the planned
annotation study is reported as future validation rather than a pending
condition on these results.

## Evidence and verbosity tradeoff

| Revision | System | Mean clause precision | Mean clause recall | Mean answer words |
|---|---|---:|---:|---:|
| Rev. 4 | ComplianceGPT | 0.505 | 0.886 | 167.2 |
| Rev. 4 | Gemini 3.5 Flash | 0.615 | 0.833 | 44.9 |
| Rev. 5 | ComplianceGPT | 0.584 | 0.835 | 220.7 |
| Rev. 5 | Gemini 3.5 Flash | 0.696 | 0.775 | 60.2 |

Across both revisions, ComplianceGPT buys higher clause recall and guaranteed
citation/status fidelity at a clear cost in precision and length. Gemini is
substantially more concise and precise. For the target audit setting, retaining
governing text with resolvable citations is the chosen failure mode, but this
is an engineering tradeoff rather than a universal advantage.

## Gate simplification finding

Fixed top 2 matched the adaptive gate's strict-pass count on both revisions:
29/36 on Revision 4 and 65/100 on Revision 5. Fixed top 3 also matched those
counts, and the Revision 4 top-2 versus top-3 pass sets were identical. Top 1
was worse (26/36 and 62/100) and reduced governing-control accuracy. Top 5 was
unstable across revisions and reduced Revision 5 ODP specificity.

The tested data therefore show no benefit from the adaptive gate over a
constant top-2 gate. Fixed top 2 is the simpler evidence-supported operating
point; retaining the adaptive implementation path is an engineering option,
not an empirically supported performance claim.

## Consolidated findings

1. **ComplianceGPT and Gemini are not distinguishable on strict pass.** The
   paired results are 8:3 on Revision 4 (`p = 0.2266`) and 11:12 on Revision 5
   (`p = 1.0`). Neither supports an accuracy-superiority or direction claim.
2. **The main result is mechanistic.** A 7B open-weight selector plus
   deterministic assembly matches a hosted frontier model on strict pass while
   guaranteeing runtime-checkable citation, status, and realization properties
   that the evaluated free-form protocol only approximates empirically.
3. **Gemini establishes a strong free-form baseline.** It decisively
   outperforms both Qwen baselines and nearly eliminates realization loss on
   Revision 5. The original Qwen comparison understated strong free-form model
   performance.
4. **Contract-enforced ODP safety has a measurable operating cost.** It retains
   100% sensitivity under the author labels but has lower specificity and
   precision than Gemini on both revisions.
5. **Four-bit quantization does not explain the weak Qwen result.** BF16
   improves Revision 4 coverage from 18/36 to 20/36 but leaves strict pass at
   8/36.
6. **The control gate can be simplified.** Fixed top 2 reproduces the adaptive
   strict-pass count on both revisions, so the adaptive mechanism has not earned
   its added complexity in these experiments.

## Evidence provenance

The tables above were transcribed from immutable machine-readable summaries
and independently checked against row-level contracts and manifests:

| Batch | Summary | Summary SHA-256 | Archived result identity |
|---|---|---|---|
| 5A | [`rq2_control_gate_width/results_v1/summary.json`](rq2_control_gate_width/results_v1/summary.json) | `0418612200de5f9550ac576ae216fd6372b8c7ade91d5a7f253da7a582c95358` | Canonical ZIP `543c2e40879422a5a1462bb6fc56fda2ad76f9b060efbc780ebe2a51bc48a07d` |
| 5B | [`rq2_bf16_baseline/results_v1/summary.json`](rq2_bf16_baseline/results_v1/summary.json) | `2b7a251c884f9fa25df9b13539164bb9366e75f27711e7b7a494ab345244c339` | Supplied Drive export `4039e67453d46b12ad214a3759d16e5a4c9f1028353dd6e253fca06f3b57a561` |
| 5C | [`rq2_frontier_baseline/results_v1/summary.json`](rq2_frontier_baseline/results_v1/summary.json) | `97943089d1cce2ee35ad65ba3da814e2e7e4cebc1d5cf44cae48447508dc1efc` | Corrected archive `351af9780f0ed7e6714ed3eb81799e8793985ea8b14351f32da9e43ebefa0dfb`; byte-exact runner archive `039ce427f717b83da6f54a87a67bb0438f6c15e44b49d29838d39bc523c20767` |
| 5D | [`rq2_frontier_baseline_rev5/results_v1/summary.json`](rq2_frontier_baseline_rev5/results_v1/summary.json) | `3c4c813bd73835f39e24432c42bf8c2e003e680ee284ce99e5466741634f5024` | Byte-exact runner archive `9f088b2ccb410fdd6df8980d693529320fec351e9a01e7400cd7d48fc55dddef` |

The completed Batch 5D notebook is retained with its execution counts and
outputs. Its SHA-256 is
`2e96e47c83f4d02e04b992a81d76cb3c8e670cffbc876d3329437637a1247fcc`.
The Batch 5C metadata correction records operator-confirmed Paid Tier 1
provenance and changes no response, contract, metric, token count, or other
scientific output.
