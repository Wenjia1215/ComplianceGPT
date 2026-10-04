# Profile-resolution study v2

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
