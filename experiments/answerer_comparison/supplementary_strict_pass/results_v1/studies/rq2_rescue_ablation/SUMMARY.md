# rq2_rescue_ablation complete strict-pass results

Strict pass requires C, W, L, U, A, F, and P together: complete gold-clause coverage, valid sources and spans, complete retained-parameter accounting, citation use in the body, complete answer requirements, faithful normative claims, and faithful parameter semantics. Faithful paraphrases can pass. Clarification value domains are outside this endpoint.

The common rule assesses frozen stored answers through source inspection or complete-retention proofs. No independent expert adjudication is available. Uncertain cases remain in the denominator and receive no pass credit. Paired tests are retrospective, exploratory, and unadjusted.

| Revision and condition | Strict pass | Complete clause coverage | Mean answer words | Mean gold-clause precision |
| --- | --- | --- | --- | --- |
| rev4/rescue_off | 29/36 | 29/36 | 157.83 | 0.5132 |
| rev4/rescue_on | 29/36 | 29/36 | 167.17 | 0.5049 |
| rev5/rescue_off | 59/100 | 59/100 | 207.98 | 0.6217 |
| rev5/rescue_on | 65/100 | 65/100 | 220.67 | 0.5841 |

See [row-level assessments](../../strict_pass_rows.jsonl) and the [manifest](../../manifest.json). Original contract CSVs retain their historical C-check fields. This separate summary reports the complete endpoint. Answer length is a proxy for review burden; it does not measure professional review time.

Under the common rule, frozen Rev. 5 rescue-off and rescue-on outputs pass 59/100 and 65/100, respectively. Both Rev. 4 conditions pass 29/36. Other measurements match the original archive.
