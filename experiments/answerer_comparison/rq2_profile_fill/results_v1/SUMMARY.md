# Profile-resolution study

Result identity: `rq2_profile_fill_v1`.

Formal execution commit: `de9e4612e37911c0eb295772dd25286ba19c9f2b`.
Registered protocol SHA-256: `d89b01098e7aa0514b415b41dd7f380d773bdf32e44b1978186fca879532ad9b`.

Accepted condition cases: **792/800**.

| Condition | Runtime-valid | Oracle agreement | OK | PARAMS_REQUIRED |
|---|---:|---:|---:|---:|
| empty | 100/100 | 99/100 | 17 | 83 |
| complete | 100/100 | 99/100 | 100 | 0 |
| partial | 100/100 | 99/100 | 17 | 83 |
| wrong_revision | 100/100 | 99/100 | 17 | 83 |
| unknown_keys | 100/100 | 99/100 | 17 | 83 |
| unversioned | 100/100 | 99/100 | 17 | 83 |
| placeholder_values | 100/100 | 99/100 | 17 | 83 |
| literal_backslashes | 100/100 | 99/100 | 100 | 0 |

Detected mutations: **630/630**, with 63 positive-control contracts and ten operators.
Unchanged ASK/PRESERVE regressions: **144/144**.
Registered acceptance: **FAIL**.

## Interpretation

Canonical evidence, prepared windows and frozen selector outputs are retained. The full pipeline now emits profile-bound resolution provenance, and runtime verification checks literal construction against the caller-supplied profile and corpus revision.

These are deterministic mechanism outcomes on synthetic profiles, not new historical ASK strict-pass accuracy estimates. They do not validate gold labels, establish evidence completeness, or validate organizational approval, parameter-domain/cardinality rules, or behavior under new model/retrieval outputs. Anonymous assignments remain blocked.

See PROTOCOL.md, protocol.json and registered_cases.jsonl in the parent directory for the published design and all profile inputs. Per-case contracts, attempted mutations and legacy comparisons are retained here.
