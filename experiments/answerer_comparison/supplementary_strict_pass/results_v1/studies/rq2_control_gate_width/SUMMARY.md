# rq2_control_gate_width complete strict-pass results

Strict pass requires C, W, L, U, A, F, and P together: complete gold-clause coverage, valid sources and spans, complete retained-parameter accounting, citation use in the body, complete answer requirements, faithful normative claims, and faithful parameter semantics. Faithful paraphrases can pass. Clarification value domains are outside this endpoint.

The common rule assesses frozen stored answers through source inspection or complete-retention proofs. No independent expert adjudication is available. Uncertain cases remain in the denominator and receive no pass credit. Paired tests are retrospective, exploratory, and unadjusted.

| Revision and condition | Strict pass | Complete clause coverage | Mean answer words | Mean gold-clause precision |
| --- | --- | --- | --- | --- |
| rev4_adaptive_v3 | 29/36 | 29/36 | 167.17 | 0.5049 |
| rev4_top1 | 26/36 | 26/36 | 143.81 | 0.4970 |
| rev4_top2 | 29/36 | 29/36 | 157.44 | 0.5110 |
| rev4_top3 | 29/36 | 29/36 | 154.31 | 0.5114 |
| rev4_top5 | 28/36 | 28/36 | 163.83 | 0.4912 |
| rev5_adaptive_v3 | 65/100 | 65/100 | 220.67 | 0.5841 |
| rev5_top1 | 62/100 | 62/100 | 204.62 | 0.5823 |
| rev5_top2 | 65/100 | 65/100 | 229.51 | 0.5717 |
| rev5_top3 | 65/100 | 65/100 | 227.27 | 0.5654 |
| rev5_top5 | 64/100 | 67/100 | 223.40 | 0.5602 |

See [row-level assessments](../../strict_pass_rows.jsonl) and the [manifest](../../manifest.json). Original contract CSVs retain their historical C-check fields. This separate summary reports the complete endpoint. Answer length is a proxy for review burden; it does not measure professional review time.

Rev. 5 fixed top-5 answers Q12, Q39, and Q61 cite valid CCS sources outside their own frozen windows and fail W. Complete coverage remains 67/100, while strict pass is 64/100. Other fixed-width conditions have equal strict-pass and complete-coverage counts.
