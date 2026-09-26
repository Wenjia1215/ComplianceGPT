# runtime_verifier_mutation_v1

## Baseline qualification

All 136/136 frozen ComplianceGPT contracts passed the gold-independent Runtime Verifier before mutation.

## Detection by operator

| Operator | Attempted | Detected | Detection rate | Triggering predicates |
|---|---:|---:|---:|---|
| Valid active-revision ID swap | 136 | 136 | 1.0000 | `SpanNotVerbatim` (136) |
| One-character span alteration | 136 | 136 | 1.0000 | `SpanNotVerbatim` (136) |
| Rev. 4-only ID in Rev. 5 | 100 | 100 | 1.0000 | `UnknownSourceId` (100) |
| Remove one ODP-list entry | 111 | 41 | 0.3694 | `ParamsRequiredButODPListEmpty` (41) |
| Status flip | 136 | 136 | 1.0000 | `OKButUnresolvedODPPlaceholders` (111); `ParamsRequiredButNoPlaceholders` (25); `ParamsRequiredButODPListEmpty` (25) |

## Revision breakdown

| Revision | Operator | Attempted | Detected | Detection rate |
|---|---|---:|---:|---:|
| rev5 | Valid active-revision ID swap | 100 | 100 | 1.0000 |
| rev5 | One-character span alteration | 100 | 100 | 1.0000 |
| rev5 | Rev. 4-only ID in Rev. 5 | 100 | 100 | 1.0000 |
| rev5 | Remove one ODP-list entry | 83 | 26 | 0.3133 |
| rev5 | Status flip | 100 | 100 | 1.0000 |
| rev4 | Valid active-revision ID swap | 36 | 36 | 1.0000 |
| rev4 | One-character span alteration | 36 | 36 | 1.0000 |
| rev4 | Rev. 4-only ID in Rev. 5 | 0 | 0 | — |
| rev4 | Remove one ODP-list entry | 28 | 15 | 0.5357 |
| rev4 | Status flip | 36 | 36 | 1.0000 |

## Undetected mutations

- **Valid active-revision ID swap:** 0 undetected.
- **One-character span alteration:** 0 undetected.
- **Rev. 4-only ID in Rev. 5:** 0 undetected.
- **Remove one ODP-list entry:** 70 undetected.
  - rev5 query 1: `odp_required_list[3]` changed from `ac-02_odp.08` to `<removed>`.
  - rev5 query 4: `odp_required_list[2]` changed from `ac-07_odp.03` to `<removed>`.
  - rev5 query 6: `odp_required_list[4]` changed from `at-2_prm_2` to `<removed>`.
- **Status flip:** 0 undetected.

## Scope

Detection rates apply only to the five deterministic operators and the implemented gold-independent predicates. They do not measure evidence completeness, semantic or legal correctness, or general mutation adequacy.

The pooled rate is retained only as an artifact check; operator-specific rates are the reported results because the operators have different applicability and predicates.
