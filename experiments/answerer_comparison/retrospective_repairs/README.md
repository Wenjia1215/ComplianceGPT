# Retrospective request repairs

These archives preserve new diagnostic replays separately from the original
registered outputs. Each package contains its runner, row-level evidence,
manifests, validation checks, and interpretation limits.

| Archive | Result identity | Main finding |
|---|---|---|
| `ComplianceGPT_Batch_02_No_Selector_Replay.zip` | `rq2_no_selector_requests_v1` | Constructing requests changes the no-selector strict-v1 count from 7/100 to 92/100 on Rev. 5 and from 3/36 to 35/36 on Rev. 4. Only `ask_list` changes. |
| `ComplianceGPT_Batch_03_Clarification_Repair.zip` | `clarification_registry_repair_v2` | Sixteen source-backed registry repairs change 40 requests across 17 replayed contracts. Historical strict-v1 gates and decisions remain unchanged. |

Archive SHA-256 values:

```text
e1c0c200b72eb33cc7d465c93f20b438d5cb98b465f36d1e55db5a9dae2be4b6  ComplianceGPT_Batch_02_No_Selector_Replay.zip
7ebfe9aa854e1d9d46f8a1fca5ec0a01081c312ef86436ebb0cb283c8c54e01f  ComplianceGPT_Batch_03_Clarification_Repair.zip
```

Batch 2 uses the original registry and retains its known prompt errors. Its
reference agreement does not establish that each request asks for the right
information. Batch 3 documents selected clarification cases and preserves their
source definitions; those cases do not estimate a registry-wide error rate.

The repaired registry is available at `data/ODP/registry_v2/` with identity
`odp_registry_source_repair_v2`. Its loader verifies manifest hashes and repaired
entry revisions when callers select that version explicitly. Original registries
remain in `data/ODP/rev4/` and `data/ODP/rev5/`.

See the root [release notes](../../../RELEASE_NOTES.md) for registry selection,
integration evidence, and the published revision-hardening rule.
