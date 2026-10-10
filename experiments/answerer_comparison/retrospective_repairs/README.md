# Retrospective request repairs

These archives preserve new diagnostic replays separately from the original
registered outputs. Each package contains its runner, row-level evidence,
manifests, validation checks, and interpretation limits.

| Archive | Result identity | Main finding |
|---|---|---|
| [ComplianceGPT_Batch_02_No_Selector_Replay.zip](ComplianceGPT_Batch_02_No_Selector_Replay.zip) | `rq2_no_selector_requests_v1` | Constructing requests changes the no-selector strict-v1 count from 7/100 to 92/100 on Rev. 5 and from 3/36 to 35/36 on Rev. 4. Only `ask_list` changes. |
| [ComplianceGPT_Batch_03_Clarification_Repair.zip](ComplianceGPT_Batch_03_Clarification_Repair.zip) | `clarification_registry_repair_v2` | Sixteen source-backed registry repairs change 40 requests across 17 replayed contracts. Historical strict-v1 gates and decisions remain unchanged. |

The batch numbers belong to these historical archive identities. The two replays
change different conditions and must keep separate result labels.

## Original and request-repaired no-selector comparison

All counts use the same 100 Revision 5 or 36 Revision 4 questions and the
complete seven-gate endpoint. The later revision-hardening replay preserves
these decisions under strict-v2.

| Revision | Answer condition | Complete strict pass | Legacy C pass | Full required-clause coverage | Runtime pass |
|---|---|---:|---:|---:|---:|
| Rev. 5 | ComplianceGPT | 65/100 | 65/100 | 65/100 | 100/100 |
| Rev. 5 | Original no-selector | 7/100 | 92/100 | 93/100 | 100/100 |
| Rev. 5 | Request-repaired no-selector | 92/100 | 92/100 | 93/100 | 100/100 |
| Rev. 4 | ComplianceGPT | 29/36 | 29/36 | 29/36 | 36/36 |
| Rev. 4 | Original no-selector | 3/36 | 35/36 | 35/36 | 36/36 |
| Rev. 4 | Request-repaired no-selector | 35/36 | 35/36 | 35/36 | 36/36 |

The original no-selector contracts have empty request lists. Among their C
passes, 85 Revision 5 and 32 Revision 4 records fail complete parameter
accounting. The replay constructs requests with the original registry and
changes only `ask_list`. Bodies, retained source IDs, declared ODP lists,
statuses, contexts, and evidence-window hashes remain unchanged.

The repaired condition contains every ComplianceGPT pass plus 27 Revision 5
and six Revision 4 passes. Revision 5 Q77 still fails reference agreement
because its declared ODP list omits `ra-03_odp.02`. The replay does not repair
that separate field or constitute a new model execution.

| Revision | Answer condition | Mean body words | Mean additional non-gold source IDs | Mean request records |
|---|---|---:|---:|---:|
| Rev. 5 | ComplianceGPT | 220.67 | 1.75 | 1.97 |
| Rev. 5 | Request-repaired no-selector | 601.66 | 8.85 | 4.25 |
| Rev. 4 | ComplianceGPT | 167.17 | 2.08 | 1.36 |
| Rev. 4 | Request-repaired no-selector | 604.94 | 11.78 | 4.83 |

Words use whitespace splitting. Additional non-gold IDs are retained sources
outside the required reference set, not proven irrelevant text. These proxies
describe evidence scope and output size; they do not establish unnecessary
requests, assessor workload, review-time savings, or whole-question usefulness.
The higher repaired pass counts limit claims that the selector is necessary
for high strict pass on these frozen windows.

## Inspect the saved evidence

The no-selector archive contains `results_v1/contract_changes.jsonl`, both
repaired contract CSVs, `strict_pass_rows.jsonl`, `per_question_comparison.csv`,
`remaining_failures.jsonl`, `summary.json`, `validation.json`, and `manifest.json`.
These records document the field boundary, all 136 repaired decisions, and
unchanged input/body hashes. The registry-repair archive separately contains
the 16-entry patch, request changes, selected-case ledger, benchmark assessments,
and its own manifest. The [paired analysis](../paired_conditional_statistics/README.md)
publishes readable group summaries and original-to-repaired audit records.

Archive SHA-256 values:

```text
e1c0c200b72eb33cc7d465c93f20b438d5cb98b465f36d1e55db5a9dae2be4b6  ComplianceGPT_Batch_02_No_Selector_Replay.zip
7ebfe9aa854e1d9d46f8a1fca5ec0a01081c312ef86436ebb0cb283c8c54e01f  ComplianceGPT_Batch_03_Clarification_Repair.zip
```

The no-selector request replay uses the original registry and retains its known prompt errors. Its
reference agreement does not establish that each request asks for the right
information. The registry repair documents selected clarification cases and preserves their
source definitions; those cases do not estimate a registry-wide error rate.

The repaired registry is available at `data/ODP/registry_v2/` with identity
`odp_registry_source_repair_v2`. Its loader verifies manifest hashes and repaired
entry revisions when callers select that version explicitly. Original registries
remain in `data/ODP/rev4/` and `data/ODP/rev5/`.

See the root [release notes](../../../RELEASE_NOTES.md) for registry selection,
integration evidence, and the published revision-hardening rule.
