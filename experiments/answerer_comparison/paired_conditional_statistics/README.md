# Paired strict-pass comparisons and sensitivity

ComplianceGPT passes more of the saved questions than Gemini, but neither
overall paired comparison establishes a statistically significant difference.
The request-repaired no-selector replay passes more questions than both systems.
Keep that replay separate from the original no-selector output condition.

This retrospective analysis has identity `paired_conditional_statistics_v1`
and uses `strict-pass-v2`. It preserves all contracts, labels, source text, and
semantic judgments. The 680 answer records reuse 136 questions across five
paths: 100 Revision 5 questions and 36 Revision 4 questions. No model execution,
retrieval, or new semantic review contributes to these results.

## Overall paired comparisons

Pair outputs by revision and question ID. Within each question, the three main
systems received the same ordered evidence window. Their prompts, models, and
answer construction differ, so matching windows does not isolate one component.

Differences use the left system minus the right system, in percentage points.
Intervals use Newcombe's paired method 10. Exact two-sided McNemar tests use
the discordant questions; these retrospective primary tests are unadjusted.

| Revision | Left versus right | n | Left-only | Right-only | Difference (pp) | 95% interval (pp) | Exact p |
|---|---|---:|---:|---:|---:|---|---:|
| Rev. 5 | ComplianceGPT versus Gemini | 100 | 18 | 9 | 9.0 | [-1.2, 18.9] | 0.122078 |
| Rev. 5 | ComplianceGPT versus Qwen 4-bit | 100 | 46 | 2 | 44.0 | [32.5, 53.6] | 8.36309e-12 |
| Rev. 5 | Gemini versus Qwen 4-bit | 100 | 36 | 1 | 35.0 | [24.6, 44.2] | 5.52973e-10 |
| Rev. 4 | ComplianceGPT versus Gemini | 36 | 10 | 3 | 19.4 | [-0.4, 37.4] | 0.092285 |
| Rev. 4 | ComplianceGPT versus Qwen 4-bit | 36 | 24 | 1 | 63.9 | [42.1, 77.0] | 1.54972e-6 |
| Rev. 4 | Gemini versus Qwen 4-bit | 36 | 17 | 1 | 44.4 | [23.6, 60.1] | 0.000144958 |

Both ComplianceGPT/Gemini intervals include zero. These results establish
neither end-to-end superiority nor equivalence. The author defined and labeled
the question sets, and some controls recur across questions. The statistics
summarize these records under question-level reference models; they do not
estimate representative practitioner accuracy or broad model-family performance.

## Comparisons on common retained-ID coverage

Each subset contains questions where both compared outputs retain every required
gold clause ID. This selects questions using system outputs and gives a
conditional diagnostic. It does not identify a causal realization effect.

| Revision | Comparator | Common n | ComplianceGPT passes | Comparator passes | CG-only / other-only | Exact p | Holm p |
|---|---|---:|---:|---:|---|---:|---:|
| Rev. 5 | Gemini | 54 | 54 | 47 | 7 / 0 | 0.015625 | 0.03125 |
| Rev. 5 | Qwen 4-bit | 47 | 47 | 19 | 28 / 0 | 7.45058e-9 | 2.98023e-8 |
| Rev. 4 | Gemini | 25 | 25 | 19 | 6 / 0 | 0.03125 | 0.03125 |
| Rev. 4 | Qwen 4-bit | 16 | 16 | 5 | 11 / 0 | 0.0009765625 | 0.0029296875 |

The supplementary Holm adjustment covers these four conditional comparisons
only. It does not adjust the overall tests or every possible study comparison.
System-specific coverage subsets overlap and have different memberships. Their
loss rates remain descriptive; an independent-subset Fisher test does not
replace this question-paired diagnostic or the overall comparison.

## Sensitivity to an uncertain Gemini judgment

The frozen strict rule gives uncertain judgments no pass credit and keeps every
question in the denominator. Revision 5 Gemini Q67 has uncertain faithfulness
and parameter-semantics judgments, while its other gates pass. Granting both
uncertain gates optimistic credit changes Gemini from 56 to 57 overall passes.
No confirmed failure receives new credit, and subset membership stays fixed.

| Revision | Scenario | Common n | CG-only / Gemini-only | Exact p | Four-comparison Holm p |
|---|---|---:|---|---:|---:|
| Rev. 5 | Frozen judgments | 54 | 7 / 0 | 0.015625 | 0.03125 |
| Rev. 5 | Optimistic Q67 | 54 | 6 / 0 | 0.03125 | 0.0625 |
| Rev. 4 | Frozen judgments | 25 | 6 / 0 | 0.03125 | 0.03125 |
| Rev. 4 | Optimistic Q67 | 25 | 6 / 0 | 0.03125 | 0.0625 |

The Revision 4 outcomes remain unchanged; their adjusted p-value changes because
the diagnostic family changes. The optimistic overall Revision 5 p-value is
0.168638. This sensitivity adds no independent judgment and leaves the overall
ComplianceGPT/Gemini conclusion inconclusive.

## Coverage-conditioned losses and their limits

These denominators use each system's own retained-ID-complete outputs.
Intervals are 95% Wilson score intervals for the loss rate.

| Revision | System | Strict failures / coverage-complete outputs | Loss (%) | 95% interval (%) |
|---|---|---|---:|---|
| Rev. 5 | ComplianceGPT | 0/65 | 0.0 | [0.0, 5.6] |
| Rev. 5 | Gemini | 11/67 | 16.4 | [9.4, 27.1] |
| Rev. 5 | Qwen 4-bit | 32/53 | 60.4 | [46.9, 72.4] |
| Rev. 4 | ComplianceGPT | 0/29 | 0.0 | [0.0, 11.7] |
| Rev. 4 | Gemini | 6/28 | 21.4 | [10.2, 39.5] |
| Rev. 4 | Qwen 4-bit | 12/18 | 66.7 | [43.7, 83.7] |

Zero observed loss does not establish zero future loss. ComplianceGPT's semantic
pass credit relies on complete-retention proofs against the frozen references.
These proofs do not assess clarification value domains, organizational approval,
parameter necessity, or whole-question usefulness.

The row ledger assigns each output to its first failed condition: available
window coverage, retained-ID coverage, reference agreement, provenance or
parameter accounting, then semantic gates. This order gives mutually exclusive
bookkeeping counts, not independent causes. All individual gates remain recorded.

The ComplianceGPT/Gemini difference decomposes into +7, +11, and -9 passes on
Revision 5: shared complete coverage, only ComplianceGPT complete, and only
Gemini complete. Revision 4 contributes +6, +4, and -3. These strata explain
the totals descriptively without replacing the overall paired comparison.

## Original and request-repaired no-selector outputs

| Revision | ComplianceGPT | Original no-selector | Request-repaired no-selector | Repaired-only / CG-only |
|---|---:|---:|---:|---|
| Rev. 5 | 65/100 | 7/100 | 92/100 | 27 / 0 |
| Rev. 4 | 29/36 | 3/36 | 35/36 | 6 / 0 |

The repaired replay changes only `ask_list`; answer bodies, retained IDs,
statuses, and evidence windows remain fixed. Its higher pass count limits claims
that the selector is necessary for high strict pass on these windows. The
no-selector bodies average 601.66 and 604.94 whitespace-separated words,
compared with 220.67 and 167.17 for ComplianceGPT. Length, additional retained
IDs, and request counts are proxies; human usefulness and review time remain
unmeasured. See the [request-repair evidence](../retrospective_repairs/README.md).

## Evidence and historical source identities

| File | Purpose |
|---|---|
| [summary.json](results_v1/summary.json) | Ten group summaries and 20 overall/conditional comparison records across frozen and optimistic scenarios. |
| [question_rows.jsonl](results_v1/question_rows.jsonl) | All 680 answer records, contract hashes, source IDs, gate outcomes, and input-source hashes. |
| [paired_question_rows.jsonl](results_v1/paired_question_rows.jsonl) | Matched outcomes and common-coverage membership for the three main-system pairings. |
| [joint_coverage_strata.json](results_v1/joint_coverage_strata.json) | Question memberships and descriptive coverage decomposition. |
| [no_selector_audit.json](results_v1/no_selector_audit.json) | Original-to-repaired field and strict-pass transitions. |
| [uncertainty_sensitivity.json](results_v1/uncertainty_sensitivity.json) | Q67 identity, uncertain gates, and fixed-subset sensitivity. |
| [run_config.json](results_v1/run_config.json) | Historical input hashes, analysis/scorer hashes, and recorded local source identity. |
| [FILES_SHA256.json](results_v1/FILES_SHA256.json) | Original hashes for the seven frozen result files. |
| [PUBLICATION_INDEX.json](PUBLICATION_INDEX.json) | Public input locations, archive members, and documented English-metadata bindings. |

All eight result files retain their original bytes. File indexes use byte-level
SHA-256; row ledgers use canonical JSON hashes for contracts.
Canonical contract hashing sorts object keys, emits UTF-8 without ASCII escaping,
and uses commas and colons without extra whitespace. The saved run configuration
identifies a local candidate commit and tree, not a public GitHub execution pin.
This directory publishes the saved data; the historical analysis programs are
not included. Reconstruct table counts from the row ledgers and the definitions
above. The publication index binds every historical input to the public source
at `b3603f48ce85ce8acecd11f9d9058e4844e30b03`. Where English explanations and
dependent hash metadata changed, it lists those fields explicitly. Contracts,
review identities, verdicts, scoring gates, and runtime outcomes agree.

The [scoring map](../../../docs/EVALUATION_RESULTS.md) distinguishes the complete
endpoint from legacy C checks. The [repeated-label sensitivity](../../annotation_reliability/repeated_annotation_sensitivity/README.md)
uses a separate 30-question sample and does not replace these benchmark results.
