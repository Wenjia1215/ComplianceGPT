# rq2_no_selector complete strict-pass results

Strict pass requires C, W, L, U, A, F, and P together: complete gold-clause coverage, valid sources and spans, complete retained-parameter accounting, citation use in the body, complete answer requirements, faithful normative claims, and faithful parameter semantics. Faithful paraphrases can pass. Clarification value domains are outside this endpoint.

The common rule assesses frozen stored answers through source inspection or complete-retention proofs. No independent expert adjudication is available. Uncertain cases remain in the denominator and receive no pass credit. Paired tests are retrospective, exploratory, and unadjusted.

| Revision and condition | Strict pass | Complete clause coverage | Mean answer words | Mean gold-clause precision |
| --- | --- | --- | --- | --- |
| rev4/selector_v3 | 29/36 | 29/36 | 167.17 | 0.5049 |
| rev4/no_selector_v1 | 3/36 | 35/36 | 604.94 | 0.2149 |
| rev5/selector_v3 | 65/100 | 65/100 | 220.67 | 0.5841 |
| rev5/no_selector_v1 | 7/100 | 93/100 | 601.66 | 0.3061 |

See [row-level assessments](../../strict_pass_rows.jsonl) and the [manifest](../../manifest.json). Original contract CSVs retain their historical C-check fields. This separate summary reports the complete endpoint. Answer length is a proxy for review burden; it does not measure professional review time.

The stored diagnostic contracts have empty `ask_list` fields. In Rev. 5, 85 C-passing answers lack the required parameter requests; Rev. 4 has 32 such answers. The strict-pass difference cannot be attributed entirely to the selector. Coverage, length, precision, and the original parameter-set measurements retain their recorded values.

rev5: main-path-only passes 58, no-selector-only passes 0, two-sided exact McNemar p = 6.938893904e-18。

rev4: main-path-only passes 27, no-selector-only passes 1, two-sided exact McNemar p = 2.160668373e-07。
