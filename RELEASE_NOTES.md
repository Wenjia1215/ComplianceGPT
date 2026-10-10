# Runtime integration and versioned assessment

This release integrates profile resolution, explicit request-registry selection,
and active-revision validation. It also publishes complete strict-pass
assessments of the recorded supplementary outputs. See the
[result map](docs/EVALUATION_RESULTS.md) for scoring identities and final counts.

## Source and evidence identities

| Component | Source or identity | Publication |
|---|---|---|
| Main matched outputs and semantic reviews | `72979835f1e05bae513468ca4074b4d43497da2c`; assessment base `c4188bfb459210d16c8c43f7819df35ba4a6ee07` | Preserve 408 recorded main assessments and frozen model outputs. |
| Profile resolution and completed supplementary studies | `9116c4f9bf12042878d37935a036139f70529fd1` | Restore versioned protocols, failures, completed outputs, and execution archives. |
| Repaired request metadata | `odp_registry_source_repair_v2` | Publish 13 Rev. 5 and three Rev. 4 entry repairs as an explicit opt-in registry. |
| Complete supplementary assessment | `strict-pass-v1` | Publish 988 row-level assessments and separate derived summaries. |
| Active-revision validation | `active-revision-v2`; `strict-pass-v2` | Add revision agreement to runtime validation and the complete endpoint. |
| Integration diagnostic | `release_candidate_profile_integration_v2` | Check revised source against frozen profile fixtures without amending their registration. |

The completed studies include PRESERVE replay, profile-fill v1 and v2,
natural-question v1 and v2 materials, and retrieval-constant sensitivity. The
failed profile-fill v1 remains beside its repaired v2 result. Original execution
archives retain their historical bytes. The author-review workbook has a
documented [English edition](experiments/external_validity/natural_questions_v2/results_v1/author_review_v1/README.md)
that translates explanatory notes while preserving all judgments.

## Runtime behavior

Default corpus and registry paths resolve from the repository root. Explicit
paths remain supported. Callers can inject a generator for stored-selector
replays and use `FILL_FROM_PROFILE` to substitute eligible profile values while
retaining canonical evidence spans and a reconstruction record.

The profile-aware base verifier comes from the recorded profile implementation.
The v2 wrapper adds explicit revision checks. ASK and PRESERVE outputs reproduce
their historical outcomes, and the strict-v1 scoring source retains its bytes.
Historical execution manifests identify the original verifier snapshots.

The default request registry remains `legacy`. Select repaired metadata explicitly:

```python
from compliancegpt.pipeline.odp_registry import load_registry_selection

registry, identity = load_registry_selection(
    "rev5", registry_version="odp_registry_source_repair_v2"
)
```

For a new pipeline, pass
`odp_registry_version="odp_registry_source_repair_v2"`. Each returned contract
records the registry identity, revision, SHA-256, selection mode, and loading
status. The loader rejects unknown versions, conflicting repaired and custom
paths, changed repaired-registry hashes, and mismatched repaired-entry revisions.

Registry metadata describes request labels, prompts, types, examples, and
cardinality. It does not establish organizational approval, supplied-value
validity, parameter necessity, or nested obligations.

Both current answer pipelines record `revision_validation_rule="active-revision-v2"`
and pass their active corpus revision to the checker. Missing, ambiguous,
unknown, non-string, and opposite declarations fail the added gate. Recognized
source and citation revision labels must agree with that corpus. Callers remain
responsible for supplying the correct corpus identity and bytes.

## Verified results

The integration passed 172 unit tests. All 408 main strict-v1 rows reproduced
byte for byte. All 988 supplementary decisions reproduced; their English
explanations retain original review IDs, verdicts, and quoted evidence.
Derived complete-endpoint summaries live under
`experiments/answerer_comparison/supplementary_strict_pass/results_v1/studies/`.
Historical CSVs and execution summaries continue to report their original C checks.

The [revision replay](experiments/answerer_comparison/revision_hardening_v2/README.md)
assesses those 1,396 records plus 136 request-repaired no-selector records.
Every added revision gate passes on the unchanged records. All 1,532 strict
decisions and runtime outcomes remain unchanged. V2 rejected all 11,376 revision
mutations on 1,422 eligible runtime-valid records. Those repeated conditions
test revision handling; they do not estimate independent question-level accuracy
or global verifier sensitivity.

The [profile integration diagnostic](experiments/runtime_validation/release_integration_v2/README.md)
passed 800 frozen cases, detected 630 mutations, and preserved 136 ASK and eight
PRESERVE comparisons. It checks condition oracles, canonical spans, contexts,
windows, selector traces, fallback behavior, and registry provenance. Rev. 5
queries 9 and 99 reconstruct the recorded empty-selection state because raw
selector text was not retained. These checks use synthetic profiles and stored traces.

## Offline verification

Run from the repository root and choose fresh external output directories:

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -v
python tools/validate_release_candidate.py --output-dir /tmp/compliancegpt_profile_integration
python experiments/answerer_comparison/run_strict_pass.py --output-root /tmp/compliancegpt_main_scores
python experiments/answerer_comparison/run_supplementary_strict_pass.py --output-root /tmp/compliancegpt_supplementary_scores
python experiments/answerer_comparison/revision_hardening_v2/run_revision_replay.py --output-dir /tmp/compliancegpt_revision_scores
```

These commands use stored inputs and make no model or API calls. Their manifests
record input and code hashes. Historical formal runners enforce their original
code hashes: reproduce those runs at the execution commits in their manifests.
Register revised code separately before collecting new experimental outputs.
