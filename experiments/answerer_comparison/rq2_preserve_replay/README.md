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
