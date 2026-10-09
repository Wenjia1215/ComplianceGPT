# Batch 5D validated result

This directory records the complete evidence package for the finished
`rq2_frontier_baseline_rev5_v1` run. The experiment used the stable Gemini
Developer API model `gemini-3.5-flash` on all 100 frozen Revision 5 contexts.
It was pre-committed before outputs were generated, and the server-reported
model matched the requested model for every response.

The executed notebook at the parent level and the byte-exact runner archive in
this directory form the raw execution record. Their SHA-256 values are:

```text
2e96e47c83f4d02e04b992a81d76cb3c8e670cffbc876d3329437637a1247fcc  Batch_5D_Rev5_Frontier_API_Baseline.ipynb
9f088b2ccb410fdd6df8980d693529320fec351e9a01e7400cd7d48fc55dddef  rq2_frontier_baseline_rev5_v1.zip
```

## Strict-pass results

[`SUMMARY.md`](SUMMARY.md) and [`summary.json`](summary.json) are the canonical
three-system results under the [complete strict-pass standard](../../../../src/answerer_comparison/README.md).
[`strict_pass_rows.csv`](strict_pass_rows.csv) and [`strict_pass_rows.jsonl`](strict_pass_rows.jsonl)
record the final decision and its component predicates for every saved output.

- Baseline: 21/100 (21.0%).
- ComplianceGPT: 65/100 (65.0%).
- Gemini: 56/100 (56.0%).

The original ZIP archives, their embedded output manifests, and `AUDIT.md`
retain the execution record. The materialized `manifests/outputs.json` describes
the current files; `manifests/strict_pass.json` pins evaluation inputs, code,
review records and results. Raw contracts and responses are unchanged. Semantic
judgments are not independently adjudicated.

ODP sensitivity and specificity under the current author labels were 63/63 and
17/37 for ComplianceGPT, 56/63 and 31/37 for Gemini, and 0/63 and 37/37 for
Qwen. These labels have not been independently adjudicated. Sensitivity and
specificity are reported together so the cost of ComplianceGPT's
high-sensitivity operating point remains visible.

See [`AUDIT.md`](AUDIT.md) for the independent post-run checks,
[`SUMMARY.md`](SUMMARY.md) for the runner-generated summary, and
[`ARCHIVE_SHA256SUMS`](ARCHIVE_SHA256SUMS) for the top-level artifact hashes.
