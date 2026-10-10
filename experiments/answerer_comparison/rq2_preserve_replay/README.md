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

Run the non-outcome preflight from the repository root:

```bash
PYTHONPATH=src python experiments/answerer_comparison/rq2_preserve_replay/run_preserve_replay.py \
  --preflight
```

Run the formal replay once into a new result directory:

```bash
PYTHONPATH=src python experiments/answerer_comparison/rq2_preserve_replay/run_preserve_replay.py \
  --output-dir experiments/answerer_comparison/rq2_preserve_replay/results_v1
```

The runner refuses to mix with or overwrite a nonempty result directory.

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
| Offline strict-verifier pass | 5/8 |

The registered runtime acceptance result is **PASS**. Offline strict scoring
passes 5/6 Revision 5 rows and 0/2 Revision 4 rows. The three failures retain
the frozen selector choices and contain missing gold-clause signals; two also
contain missing gold-ODP signals. These are coverage limitations, not failures
of the corrected `PRESERVE` status transition.

Frozen result archive:

```text
results_v1/rq2_preserve_replay_v1.zip
SHA-256 580a7917678ea00b8529774108ecb293221b77b058ea7a215aea0f0d2d7b6339
```
