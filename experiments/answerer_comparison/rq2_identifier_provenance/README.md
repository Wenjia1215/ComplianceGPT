# RQ2 Per-Identifier Runtime Provenance

This experiment repairs the positive runtime-provenance gap identified in the dissertation review. It emits one provenance record for every source identifier in each frozen ComplianceGPT contract:

- `selector`
- `fallback`
- `rescue`
- `hierarchy`

The runner consumes the frozen RQ2 v3 contracts and prepared evidence windows. It performs no retrieval, model inference, or gold-guided attribution. Every replayed core contract must match the corresponding frozen contract before its provenance is accepted.

Run from the repository root:

```bash
PYTHONPATH=src python experiments/answerer_comparison/rq2_identifier_provenance/run_identifier_provenance.py \
  --output-dir experiments/answerer_comparison/rq2_identifier_provenance/results_v1
```

The output contains full contracts with the new `provenance` field, one row per final identifier, one row per contract, a machine-readable summary, a readable summary, and a frozen run manifest. Existing RQ2, no-selector, rescue-ablation, and mutation archives are not modified.

## Frozen result

Result identity: `rq2_identifier_provenance_v1`

| Revision | Selector | Fallback | Rescue | Hierarchy | All final IDs in shared window |
|---|---:|---:|---:|---:|---:|
| Rev. 5 | 391 | 2 | 44 | 0 | 437/437 |
| Rev. 4 | 139 | 0 | 6 | 0 | 145/145 |
| Combined | 530 | 2 | 50 | 0 | 582/582 |

All 136 reconstructed core contracts match their frozen RQ2 v3 contracts and pass the gold-independent Runtime Verifier. The 50 rescue-added occurrences are directly enumerated across 24 contracts, and all 50 occur in the corresponding frozen shared evidence windows.

Hierarchy closure was disabled in the frozen RQ2 configuration. The zero hierarchy count is therefore a direct statement about this run, not an evaluation of enabled hierarchy behavior.

Archive SHA-256:

```text
357d5af80874ef1cfe14ea3cb05a11592ee916b8fd222e4c05df54bf8d2ec38d
```
