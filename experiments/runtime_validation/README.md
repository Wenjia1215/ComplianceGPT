# Runtime contract revalidation

This directory contains deterministic, gold-independent revalidation of the
recorded ComplianceGPT and generative-baseline answer artifacts.

The repair identified by `2026-07-12-contract-validity-fix` corrects the
contract-only validator without rerunning retrieval, query rewriting, evidence
selection, or answer generation. The recorded source CSV artifacts remain
unchanged.

Run from the repository root:

```bash
python experiments/runtime_validation/revalidate_contracts.py
```

The script resolves each evidence source ID against the revision-matched Canonical
Clause Store, checks strict span containment, and applies runtime-visible status and
unresolved-placeholder consistency checks. It does not use gold labels and does not
measure global evidence completeness.

Generated CSVs and the JSON summary under `outputs/` record source-artifact and CCS
SHA-256 hashes for provenance.
