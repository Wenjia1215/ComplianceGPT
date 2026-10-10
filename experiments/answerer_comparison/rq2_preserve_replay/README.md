# RQ2 PRESERVE Replay

This experiment evaluates the corrected `PRESERVE` branch on every frozen RQ2
gold row whose registered resolution policy is `PRESERVE`: six Revision 5 rows
and two Revision 4 rows.

It reuses the immutable prepared contexts and the exact selector outputs from
the matched-window v3 archive. It then executes the current deterministic
pipeline from evidence filling through ODP policy, contract construction,
Runtime Verifier, and offline verifier. It performs no live retrieval and no
new model inference.

The pre-registered protocol and acceptance rules are in
[`PRECOMMITMENT.md`](PRECOMMITMENT.md) and
[`precommitment.json`](precommitment.json).

The formal result records execution commit
`17a76e14a2285c5070b8d8da3c7341e5772d303d`. Use that source snapshot to
reproduce the registered run; its source-hash checks remain active. The current
[profile integration diagnostic](../../runtime_validation/release_integration_v2/README.md)
checks the revised runtime separately.

Run the non-outcome preflight from the repository root of the recorded snapshot:

```bash
PYTHONPATH=src python experiments/answerer_comparison/rq2_preserve_replay/run_preserve_replay.py \
  --preflight
```

Run the formal replay into a fresh directory outside the repository:

```bash
PYTHONPATH=src python experiments/answerer_comparison/rq2_preserve_replay/run_preserve_replay.py \
  --output-dir /tmp/compliancegpt_preserve_replay_v1
```

The runner refuses to mix with or overwrite a nonempty result directory.
Choose an unused path for each reproduction and preserve the published
`results_v1/` evidence.

## Frozen result

Result identity: `rq2_preserve_replay_v1`

| Measure | Result |
|---|---:|
| Registered rows completed | 8/8 |
| Visible-marker rows returning `PARAMS_REQUIRED` | 8/8 |
| Literal placeholder preservation | 8/8 |
| Empty `ask_list` under `PRESERVE` | 8/8 |
| Runtime-valid contracts | 8/8 |
| Frozen selectors unchanged | 8/8 |
| Final IDs inside frozen windows | 8/8 |
| Historical offline contract/gold check (C) | 5/8 |

The registered runtime acceptance result is **PASS**. The historical C check
passes 5/6 Revision 5 rows and 0/2 Revision 4 rows. The three failures retain
the frozen selector choices and contain missing gold-clause signals; two also
contain missing gold-ODP signals. These are coverage limitations, not failures
of the corrected `PRESERVE` status transition.
The archived field name does not make 5/8 a complete seven-gate strict-pass
result; see the [scoring identities](../../../REPRODUCIBILITY.md#scoring-identities).

Frozen result archive:

```text
results_v1/rq2_preserve_replay_v1.zip
SHA-256 580a7917678ea00b8529774108ecb293221b77b058ea7a215aea0f0d2d7b6339
```
