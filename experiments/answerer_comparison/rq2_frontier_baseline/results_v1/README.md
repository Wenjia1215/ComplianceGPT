# Batch 5C validated result

This directory records the complete evidence package for the finished
`rq2_frontier_baseline_v1` run. The experiment used the stable Gemini Developer
API model `gemini-3.5-flash` on all 36 frozen Revision 4 contexts. The
server-reported model matched the requested model for every response.

The executed notebook and the original runner archive form the raw execution
record. The notebook reported the original archive SHA-256 as:

```text
039ce427f717b83da6f54a87a67bb0438f6c15e44b49d29838d39bc523c20767
```

That exact archive is retained as
`rq2_frontier_baseline_v1_runner_original.zip`.

## Post-run metadata correction

The successful run used Gemini API Paid Tier 1, but the original
`run_config.json` retained generic free-tier data-policy wording. The archived
`rq2_frontier_baseline_v1_corrected.zip` corrects only
that provenance metadata. They add the operator-reported billing tier, state
that `generateContent` does not return the billing tier, and record the
original archive hash. No question, context, response, contract, verifier
result, metric, API log, prompt, generation setting, or model identifier was
changed.

After that correction, all 18 payload hashes were regenerated. Their canonical
file-map hash is:

```text
9d3a5abff585bde671faf75be1118d7d336adff531c06f2f1dacf3fbf5fb4e73
```

The corrected archive SHA-256 is:

```text
351af9780f0ed7e6714ed3eb81799e8793985ea8b14351f32da9e43ebefa0dfb
```

See [`AUDIT.md`](AUDIT.md) for the independent integrity and result checks and
[`SUMMARY.md`](SUMMARY.md) for the runner-generated summary.

## Strict-pass results

[`SUMMARY.md`](SUMMARY.md) and [`summary.json`](summary.json) are the canonical
three-system results under the [complete strict-pass standard](../../../../src/answerer_comparison/README.md).
[`strict_pass_rows.csv`](strict_pass_rows.csv) and [`strict_pass_rows.jsonl`](strict_pass_rows.jsonl)
record the final decision and its component predicates for every saved output.

- Baseline: 6/36 (16.7%).
- ComplianceGPT: 29/36 (80.6%).
- Gemini: 22/36 (61.1%).

The original ZIP archives, their embedded output manifests, and `AUDIT.md`
retain the execution record. The materialized `manifests/outputs.json` describes
the current files; `manifests/strict_pass.json` pins evaluation inputs, code,
review records and results. Raw contracts and responses are unchanged. Semantic
judgments are not independently adjudicated.
