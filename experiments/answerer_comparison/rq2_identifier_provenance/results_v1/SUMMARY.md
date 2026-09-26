# RQ2 Per-Identifier Runtime Provenance

Result identity: `rq2_identifier_provenance_v1`

The run deterministically reconstructs all frozen ComplianceGPT contracts and emits one positive origin for every final source identifier. It performs no retrieval, model inference, or gold-guided construction.

## REV5

All 100 contracts have complete provenance, match their frozen core contracts, and pass the gold-independent Runtime Verifier.

| Origin | Identifier occurrences | Contracts | In shared window | Rate |
|---|---:|---:|---:|---:|
| `selector` | 391 | 98 | 391/391 | 1.0000 |
| `fallback` | 2 | 2 | 2/2 | 1.0000 |
| `rescue` | 44 | 22 | 44/44 | 1.0000 |
| `hierarchy` | 0 | 0 | 0/0 | not applicable |

Overall containment: 437/437 final identifier occurrences; 100/100 contracts have every final identifier in the frozen shared window.

## REV4

All 36 contracts have complete provenance, match their frozen core contracts, and pass the gold-independent Runtime Verifier.

| Origin | Identifier occurrences | Contracts | In shared window | Rate |
|---|---:|---:|---:|---:|
| `selector` | 139 | 36 | 139/139 | 1.0000 |
| `fallback` | 0 | 0 | 0/0 | not applicable |
| `rescue` | 6 | 2 | 6/6 | 1.0000 |
| `hierarchy` | 0 | 0 | 0/0 | not applicable |

Overall containment: 145/145 final identifier occurrences; 36/36 contracts have every final identifier in the frozen shared window.

## Combined

All 136 contracts have complete provenance, match their frozen core contracts, and pass the gold-independent Runtime Verifier.

| Origin | Identifier occurrences | Contracts | In shared window | Rate |
|---|---:|---:|---:|---:|
| `selector` | 530 | 134 | 530/530 | 1.0000 |
| `fallback` | 2 | 2 | 2/2 | 1.0000 |
| `rescue` | 50 | 24 | 50/50 | 1.0000 |
| `hierarchy` | 0 | 0 | 0/0 | not applicable |

Overall containment: 582/582 final identifier occurrences; 136/136 contracts have every final identifier in the frozen shared window.

## Interpretation boundary

The observed run contains no hierarchy additions because hierarchy closure was disabled in the frozen RQ2 configuration. This is a direct zero count, not evidence about enabled hierarchy-closure behavior. The rescue containment result is direct per-identifier runtime evidence: every rescue-added identifier is enumerated in the contract provenance field and checked against that question's frozen evidence window.
