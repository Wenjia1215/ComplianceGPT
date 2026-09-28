# Validated RQ2 Control Gate Width Results

This directory records the completed `rq2_control_gate_width_v1` result family. The run used the registered fixed widths 1, 2, 3, and 5 with adaptive widening disabled, while retaining the released adaptive v3 outputs as an unchanged reference.

The canonical archive is `rq2_control_gate_width_v1.zip`:

```text
SHA-256: 543c2e40879422a5a1462bb6fc56fda2ad76f9b060efbc780ebe2a51bc48a07d
```

The archive contains the 544 prepared fixed-width contexts, 544 corresponding selector contracts, the preflight audit, run manifests, configuration, and completed summaries. The manually exported upload used to recover the Drive directory had SHA-256 `59edf6cc852e66de35a57bc0609bbe4c552afa915d8b75b84d10f5028b1fda74`; its wrapper directory was removed when the canonical archive was created.

## Validation record

Independent post-run validation recomputed and checked:

- all eight prepared-context and contract-file hashes;
- all 544 context hashes and order-sensitive evidence-window manifests;
- one-to-one query, context, evidence-window, and contract linkage;
- 544 pre-inference runtime-window replays with adaptive widening disabled;
- all 544 model rows against the pinned Qwen model and tokenizer revision;
- all configuration summaries and paired exact McNemar results from row-level outputs;
- 680 preflight rows, comprising the adaptive reference plus four fixed widths over both revisions; and
- the A100 runtime identity, frozen source archive, experiment-code fingerprint, and registered runner commit.

All checks passed. The run used an NVIDIA A100-SXM4-40GB, `Qwen/Qwen2.5-7B-Instruct` at revision `a09a35458c702b33eeacc393d103063234e8bc28`, and runner commit `372632f81ed4ceeb18021690d03ad0874d988092`.

## Main result

| Revision | Adaptive v3 | Top 1 | Top 2 | Top 3 | Top 5 |
|---|---:|---:|---:|---:|---:|
| Rev. 5 strict pass | 65/100 | 62/100 | 65/100 | 65/100 | 67/100 |
| Rev. 4 strict pass | 29/36 | 26/36 | 29/36 | 29/36 | 28/36 |
| Rev. 5 ODP specificity* | 17/37 | 17/37 | 16/37 | 16/37 | 12/37 |
| Rev. 4 ODP specificity* | 8/17 | 8/17 | 8/17 | 8/17 | 8/17 |

Strict pass and full expected-clause coverage were numerically identical in every condition because every generated row passed the runtime contract. No stored within-revision strict-pass comparison was statistically significant; all exact two-sided McNemar values were at least 0.25.

The released adaptive gate remains the most defensible default. Fixed top 2 matched its strict-pass count in both revisions and is the parsimonious fixed-width operating point. Top 3 added no strict-pass or ODP-specificity benefit over top 2. Top 5 gained two Rev. 5 strict passes but lost one Rev. 4 pass and reduced Rev. 5 ODP specificity from 17/37 to 12/37. Fixed top 1 lost coverage without improving specificity over the adaptive reference.

Rank width follows the released implementation: ranked enhancements are normalized to their base control before evidence filtering, so repeated candidates can yield fewer unique admitted base controls than the requested width. The prepared-context audit records that effective width explicitly.

*ODP operating characteristics use the author labels and remain provisional until blinded independent annotation is returned.*

See `SUMMARY.md` for the complete per-revision table, `PREPARED_CONTEXTS.md` for the evidence-window opportunity audit, and `summary.json` for machine-readable distributions and paired tests.
