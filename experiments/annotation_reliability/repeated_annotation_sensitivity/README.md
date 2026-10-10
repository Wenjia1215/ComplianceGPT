# Strict-pass sensitivity to repeated author labels

Repeated labels change two ComplianceGPT decisions while keeping its sampled
total at 25/30. Revision 5 increases from 17/22 to 18/22; Revision 4 decreases
from 8/8 to 7/8. Ten generative answers need fresh semantic judgments, so their
revised totals remain bounded rather than receiving an invented pass count.

The retrospective identity is `repeated_annotation_sensitivity_v1`. The analysis
uses the [registered author retest](../intra_annotator_retest/README.md), frozen
answer contracts, and `strict-pass-v2`. Five answer paths reuse 30 questions,
producing 150 records. No new model execution, retrieval, labels, or semantic
review contributes to this analysis.

## Agreement and scope

The original annotator repeated 22 Revision 5 and eight Revision 4 questions.
The recorded chronology places original annotation between October 2025 and
February 18, 2026; the second pass ended on October 2, 2026. The commitments
and revealed files document the protocol but cannot independently establish
how the annotator performed the work.

| Metric | All 30 | Rev. 5, n = 22 | Rev. 4, n = 8 |
|---|---:|---:|---:|
| Governing-control exact agreement | 29/30 | 21/22 | 8/8 |
| Clause-set exact agreement | 16/30 | 12/22 | 4/8 |
| ODP-set exact agreement | 26/30 | 19/22 | 7/8 |
| All three fields exact | 16/30 | 12/22 | 4/8 |
| Control Cohen's kappa | 0.9654 | 0.9525 | 1.0000 |
| Mean clause Jaccard | 0.7955 | 0.8291 | 0.7031 |
| Mean ODP Jaccard | 0.8867 | 0.8909 | 0.8750 |

Five clause disagreements concern parent-versus-child citation granularity;
nine change the annotated requirement scope. This explanation leaves raw
clause agreement at 16/30. The retest measures author repeatability, not
independent label correctness or a held-out evaluation.

## Strict-pass sensitivity on the same frozen answers

Every count uses the same sampled questions before and after label substitution.
Available-window coverage stays at 20/22 for Revision 5 and 8/8 for Revision 4.

| Revision | Answer path | n | Original strict pass | Retest strict pass or bounds | Unreviewed answers |
|---|---|---:|---:|---|---:|
| Rev. 5 | ComplianceGPT | 22 | 17 | 18 | 0 |
| Rev. 5 | Gemini | 22 | 14 | 10–16 | 6 |
| Rev. 5 | Qwen 4-bit | 22 | 6 | 3–5 | 2 |
| Rev. 5 | Original no-selector | 22 | 4 | 4 | 0 |
| Rev. 5 | Request-repaired no-selector | 22 | 20 | 20 | 0 |
| Rev. 4 | ComplianceGPT | 8 | 8 | 7 | 0 |
| Rev. 4 | Gemini | 8 | 5 | 3–5 | 2 |
| Rev. 4 | Qwen 4-bit | 8 | 0 | 0 | 0 |
| Rev. 4 | Original no-selector | 8 | 0 | 0 | 0 |
| Rev. 4 | Request-repaired no-selector | 8 | 8 | 8 | 0 |

Ranges are identification bounds for missing semantic judgments, not confidence
intervals. The lower count includes identified passes. The upper count allows
mechanically eligible unreviewed answers to pass. Confirmed mechanical failures
remain failures under both bounds; unchanged uncertain judgments receive no
strict credit.

## Why an unchanged total hides changed decisions

| Case | Change in repeated reference | ComplianceGPT outcome |
|---|---|---|
| IR-028, Rev. 5 Q84 | SA-10 parent and children become children only. | Fail becomes pass: the retained children satisfy the repeated ID set. |
| IR-029, Rev. 4 Q14 | IA-5 guidance becomes seven statement clauses. | Pass becomes fail: `ia-5_smt.b`, `ia-5_smt.c`, and `ia-5_smt.e` are missing. |

The first change concerns required ID representation; the second changes
substantive scope. An unchanged combined total does not mean unchanged decisions
or show that reference boundaries have no effect.

The five granularity cases are IR-001, IR-003, IR-004, IR-017, and IR-028.
IR-017 removes child IDs while retaining a full parent statement. The other
four remove a parent while retaining its children. The literal-content audit
records these relationships without treating every granularity change as
equivalent meaning.

## Reference mapping and semantic rules

| Repeated-label field | Accepted scoring field | Rule |
|---|---|---|
| Governing control | `control_id` | Canonicalize the ID and replace the original value. |
| Expected clause IDs | `gold_control_path` | Replace the original clause set using lowercased IDs. |
| Required ODP IDs | `odp_required` | Replace the original requirement; convert `NONE` to an empty value. |
| NIST revision | `gold_source_version` and active corpus | Keep the matched original revision. |
| Resolution policy, not re-annotated | `resolution_policy` | Retain the original policy; report the separate ASK diagnostic. |

The retest alias `required_odp_ids` is not an accepted gold field in the
verifier. Appending it beside the original field would leave old requirements
active. The saved analysis explicitly replaces `odp_required` and validates
every repeated clause and parameter ID against its matched source inventory.

For changed references, the analysis recomputes complete-retention proofs.
When a proof and all mechanical gates pass, the existing rule identifies a
strict pass. For unchanged labels, it retains prior semantic judgments. For
changed labels without a new proof, it invalidates prior semantic judgments
and bounds mechanically eligible answers until fresh review. No inherited
semantic judgment is reused after a label change.

The retest did not annotate resolution policy. IR-005 and IR-021 introduce ODPs
where the original policy was blank. Setting ASK in a separate diagnostic
changes none of their ten reference-check outcomes. This diagnostic supplies
no missing human policy annotation. Retention proofs establish literal source
retention under the rule; they do not independently validate labels, minimal
answers, or useful clarification wording.

## Remaining semantic reviews

| Revision | Answer path | Questions |
|---|---|---|
| Rev. 5 | Gemini | Q12, Q36, Q61, Q67, Q71, Q73 |
| Rev. 4 | Gemini | Q3, Q14 |
| Rev. 5 | Qwen 4-bit | Q12, Q61 |

The [ten-record review queue](review_queue/semantic_review_queue.jsonl) contains
frozen answers and mapped references. Fresh judgments are needed only to replace
the stated ranges with single revised generative totals. The bounded analysis
is complete without them. It introduces no new p-value and does not change the
inconclusive overall ComplianceGPT/Gemini comparison on the full benchmark.

## Evidence and historical source identities

| File | Purpose |
|---|---|
| [summary.json](results_v1/summary.json) | Ten revision/path summaries and six paired pass-difference bounds. |
| [question_sensitivity_rows.jsonl](results_v1/question_sensitivity_rows.jsonl) | All 150 original/retest outcomes, mechanical checks, proof methods, and bounds. |
| [label_audit.jsonl](results_v1/label_audit.jsonl) | All 30 reference mappings, disagreements, and literal-content checks. |
| [frozen_contracts.jsonl](results_v1/frozen_contracts.jsonl) | The 150 unchanged contract strings and canonical JSON hashes. |
| [agreement_reproduction.json](results_v1/agreement_reproduction.json) | Agreement counts, Jaccard values, and kappa by revision and overall. |
| [policy_diagnostics.jsonl](results_v1/policy_diagnostics.jsonl) | Fixed-policy and separate ASK checks. |
| [run_config.json](results_v1/run_config.json) | Historical source, input, and analysis-program hashes. |
| [FILES_SHA256.json](results_v1/FILES_SHA256.json) | Original hashes for the seven frozen result files. |
| [PUBLICATION_INDEX.json](PUBLICATION_INDEX.json) | Public input locations, archive members, English-metadata bindings, and review-queue hash. |

All eight result files and the review queue retain their original bytes.
File indexes use byte-level SHA-256. Canonical contract hashing sorts object keys,
emits UTF-8 without ASCII escaping, and uses commas and colons without extra
whitespace. The saved run configuration identifies a local candidate commit
and tree, not a
public GitHub execution pin. This directory publishes saved data; the historical
sensitivity programs are not included. Inspect aggregate counts against the
row ledger using the mapping and bound rules above. The publication index binds
every historical input to the public source at
`b3603f48ce85ce8acecd11f9d9058e4844e30b03`, explicitly listing English
explanation and dependent-hash differences. Contract bytes, review identities,
verdicts, scoring gates, and runtime outcomes agree.

See the [full-benchmark paired analysis](../../answerer_comparison/paired_conditional_statistics/README.md)
and [evaluation result map](../../../docs/EVALUATION_RESULTS.md) for their
separate denominators and conclusions.
