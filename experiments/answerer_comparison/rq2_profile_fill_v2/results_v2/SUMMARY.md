# Profile-resolution study

Result identity: `rq2_profile_fill_v2`.

Formal execution commit: `2e269c3d93728fae9acca6eff47fb672902436f5`.
Registered protocol SHA-256: `9a0b022f7c738865674344946cf3ea4a96a3b9241d9a1dbbc95fa91761de2756`.

Accepted condition cases: **800/800**.

| Condition | Runtime-valid | Oracle agreement | OK | PARAMS_REQUIRED |
|---|---:|---:|---:|---:|
| empty | 100/100 | 100/100 | 17 | 83 |
| complete | 100/100 | 100/100 | 100 | 0 |
| partial | 100/100 | 100/100 | 17 | 83 |
| wrong_revision | 100/100 | 100/100 | 17 | 83 |
| unknown_keys | 100/100 | 100/100 | 17 | 83 |
| unversioned | 100/100 | 100/100 | 17 | 83 |
| placeholder_values | 100/100 | 100/100 | 17 | 83 |
| literal_backslashes | 100/100 | 100/100 | 100 | 0 |

Detected mutations: **630/630**, with 63 positive-control contracts and ten operators.
Unchanged ASK/PRESERVE regressions: **144/144**.
Registered acceptance: **PASS**.

## Interpretation

Canonical evidence, prepared windows and stored selection traces are retained. For the two recorded empty-selection fallbacks (Rev.5 queries 9 and 99), the replay reconstructs an empty selection and executes the real fallback; the original pre-normalization model output was not retained. The full pipeline now emits profile-bound resolution provenance, and runtime verification checks literal construction against the caller-supplied profile and corpus revision.

These are deterministic mechanism outcomes on synthetic profiles, not new historical ASK strict-pass accuracy estimates. They do not validate gold labels, establish evidence completeness, or validate organizational approval, parameter-domain/cardinality rules, or behavior under new model/retrieval outputs. Anonymous assignments remain blocked.

See PROTOCOL.md, protocol.json and registered_cases.jsonl in the parent directory for the published design and all profile inputs. Per-case contracts, attempted mutations and legacy comparisons are retained in the complete result archive. The failed v1 run remains available in the sibling rq2_profile_fill directory.
