# Profile-resolution study v2

**Formal result: PASS.** All 800 registered cases passed, including resolution
of all visible keyed placeholders in 63/63 ODP-positive rows under complete
profiles. All 630 registered mutations were
detected, and all 144 ASK/PRESERVE regression comparisons passed. See
[results_v2/SUMMARY.md](results_v2/SUMMARY.md) for the condition counts and limits.
The formal execution used public commit
`2e269c3d93728fae9acca6eff47fb672902436f5`.

See [PARAMETER_SCOPE.md](PARAMETER_SCOPE.md) for the separate post-hoc coverage
diagnostic: two frozen answers each omit one author-gold parameter, and 20 of
the 37 author-negative rows contain visible keyed placeholders. These limits
must accompany interpretation of the condition results.

This study follows the retained failed v1 run. Read [PROTOCOL.md](PROTOCOL.md)
for the registration, two recorded fallback reconstructions, eight fixed profile
conditions, mutation operators and interpretation limits. The implementation
checks a caller-supplied, versioned synthetic profile against unchanged canonical
evidence. It does not establish independent label correctness or parameter approval.

## Reproduce

Use a clean checkout of the public execution commit in `results_v2/run_config.json`:

```bash
PYTHONPATH=src:. python -m unittest tests.test_profile_resolution tests.test_profile_fill_replay -v
PYTHONPATH=src:. python experiments/answerer_comparison/rq2_profile_fill_v2/run_profile_fill.py \
  --output-dir /tmp/compliancegpt_profile_fill_v2_reproduction
```

The output directory must be empty or absent. No GPU, model inference, new
retrieval or paid API calls are required. Compare acceptance checks, condition
counts, mutation outcomes and legacy comparisons; execution timestamps and
checkout identities can differ. Do not overwrite a completed output directory
or rerun `--prepare` on the published registration.

## Artifacts

`protocol.json` pins the code, original archive/corpus inputs and complete
`registered_cases.jsonl` profile matrix. `results_v2/SUMMARY.md` gives the results;
`summary.json` and the direct audit files give machine-readable acceptance data.
`rq2_profile_fill_v2.zip` preserves all raw contracts, attempted mutations and
other result files. Extract it before checking `SHA256SUMS`; two large raw JSONL
files are retained inside the ZIP rather than separately in Git. Check the ZIP
itself against `ARCHIVE_SHA256SUMS`. The failed v1 registration and full result
archive remain available in `../rq2_profile_fill`.

The resolver's patch identity remains `2026-10-04-profile-resolution-v1`; v2
identifies this study's corrected replay, not a changed production resolver.
