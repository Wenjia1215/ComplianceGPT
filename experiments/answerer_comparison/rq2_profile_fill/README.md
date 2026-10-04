# Frozen-input profile-resolution study

This directory contains the registered design and execution artifacts for
`rq2_profile_fill_v1`. See [PROTOCOL.md](PROTOCOL.md) for the fixed conditions,
acceptance rules, original feedback reference, and interpretation limits.

## Reproduce the registered study

From a clean checkout of the execution commit recorded in `results_v1/run_config.json`:

```bash
PYTHONPATH=src:. python -m unittest tests.test_profile_resolution -v
PYTHONPATH=src:. python experiments/answerer_comparison/rq2_profile_fill/run_profile_fill.py \
  --output-dir /tmp/compliancegpt_profile_fill_reproduction
```

The destination must be empty or absent. The runner validates source and
registration hashes and refuses a dirty checkout. It reuses frozen selectors
and prepared evidence; GPU execution, API credentials and new inference are
not required. Compare summary counts, per-case acceptance, mutation outcomes,
and legacy regressions. Execution timestamps/checkout identities can differ.
Do not overwrite `results_v1` or re-register the completed study.

The `--prepare` option is only for preparing a new registration before its
first formal execution. It refuses existing registration files. A changed
design or implementation requires a new result identity.

## Versioned profile contract

Profiles used for substitution explicitly declare their corpus revision:

```json
{
  "framework_version": "rev5",
  "odp_values": {
    "ac-01_odp.03": "synthetic::example::responsible-role"
  }
}
```

The value above is an illustrative synthetic input. Supply configured values
using the actual keyed placeholders. The older unversioned YAML examples do
not authorize substitutions through this versioned path. Blank, missing,
unsupported and placeholder-bearing values remain unresolved. Anonymous
assignment markers also remain unresolved.

The pipeline preserves `evidence_spans` as canonical source quotations. Its
FILL contract adds `resolution_policy` and a `profile_resolution` record with
the profile hash/revision, each value's profile path and source IDs, and the
remaining obligations. The caller independently supplies the corpus, revision,
profile, and expected policy to the Runtime Verifier:

```python
valid, errors = verify_contract_validity(
    contract,
    corpus=canonical_corpus,
    org_profile=profile,
    corpus_version="rev5",
    expected_resolution_policy="FILL_FROM_PROFILE",
)
```

The expected policy comes from caller configuration, not a field trusted from
the returned contract. This detects removal of both profile-related fields.
Verification checks canonical source spans and independently reconstructs
literal substitutions; a contract record cannot authorize its own values.
The fingerprint identifies configured inputs; it is not an approval signature.

The existing ASK/PRESERVE policy identity is retained. The opt-in profile
resolver and verifier have a separate patch identity,
`2026-10-04-profile-resolution-v1`. Source hashes and the registered execution
commit identify the complete implementation used by this study.
