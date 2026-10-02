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
`run_config.json` retained generic free-tier data-policy wording. The
materialized result and `rq2_frontier_baseline_v1_corrected.zip` correct only
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

## Recorded result

| System | Strict pass | Full clause coverage | Runtime contract pass | Mean clause precision | ODP sensitivity* |
|---|---:|---:|---:|---:|---:|
| Gemini 3.5 Flash frontier baseline | 24/36 (0.667) | 28/36 (0.778) | 33/36 (0.917) | 0.615 | 18/19 (0.947) |
| Qwen BF16 generative baseline | 8/36 (0.222) | 20/36 (0.556) | 14/36 (0.389) | 0.575 | 0/19 (0.000) |
| Qwen 4-bit generative baseline | 8/36 (0.222) | 18/36 (0.500) | 13/36 (0.361) | 0.488 | 0/19 (0.000) |
| ComplianceGPT 4-bit | 29/36 (0.806) | 29/36 (0.806) | 36/36 (1.000) | 0.505 | 19/19 (1.000) |

Gemini substantially strengthened the free-form baseline relative to both Qwen
baselines (`p = 0.00040245056` for each paired strict-pass comparison).
ComplianceGPT and Gemini had eight and three exclusive passes, respectively,
but are not statistically distinguishable on strict pass on these 36 rows
(`p = 0.2265625`). The count difference is not interpreted as evidence of a
direction.

*ODP values use current author labels and have not been independently
adjudicated. The immutable runner-generated summary retains its original
pre-scope wording; the controlling interpretation is the limitation stated
here and in the unified Batch 5A–5D comparison.*
