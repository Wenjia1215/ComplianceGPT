# Profile integration validation

This retrospective diagnostic checks the integrated runtime against frozen
`rq2_profile_fill_v2` fixtures. It makes no new model, retrieval, or API calls
and does not amend the historical study registration.

| Check | Verified result |
|---|---:|
| Frozen profile condition cases | 800/800 accepted |
| Profile mutations | 630/630 detected |
| Historical ASK comparisons | 136/136 preserved |
| Historical PRESERVE comparisons | 8/8 preserved |

The diagnostic checks answer and status oracles, unresolved keys, profile
bindings, canonical spans, frozen contexts and windows, selector traces,
fallback behavior, runtime validity, and registry identity. Historical case
outcomes and mutation error tags match. For Rev. 5 Q9 and Q99, it reconstructs
the recorded empty-selection fallback because raw selector text was not retained.

```bash
python tools/validate_release_candidate.py \
  --output-dir /tmp/compliancegpt_profile_integration
```

Use a fresh directory outside the repository. Inspect
[summary.json](results_v1/summary.json),
[validation_config.json](results_v1/validation_config.json), and
[FILES_SHA256.json](results_v1/FILES_SHA256.json) for acceptance checks, source
and fixture identities, and publication hashes. The code hashes differ from
the original registration because this diagnostic checks revised source.

The conditions use synthetic profiles and stored normalized selectors. The
checks do not establish organizational approval, value-domain validity,
parameter necessity, or a strict-pass accuracy estimate. Historical formal
runners continue to enforce their recorded source hashes.
