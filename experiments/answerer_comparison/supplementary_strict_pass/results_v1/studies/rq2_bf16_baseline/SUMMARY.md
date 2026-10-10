# rq2_bf16_baseline complete strict-pass results

Strict pass requires C, W, L, U, A, F, and P together: complete gold-clause coverage, valid sources and spans, complete retained-parameter accounting, citation use in the body, complete answer requirements, faithful normative claims, and faithful parameter semantics. Faithful paraphrases can pass. Clarification value domains are outside this endpoint.

The common rule assesses frozen stored answers through source inspection or complete-retention proofs. No independent expert adjudication is available. Uncertain cases remain in the denominator and receive no pass credit. Paired tests are retrospective, exploratory, and unadjusted.

| Revision and condition | Strict pass | Complete clause coverage | Mean answer words | Mean gold-clause precision |
| --- | --- | --- | --- | --- |
| compliancegpt_4bit | 29/36 | 29/36 | 167.17 | 0.5049 |
| generative_baseline_4bit | 6/36 | 18/36 | 36.81 | 0.4880 |
| generative_baseline_bf16 | 7/36 | 20/36 | 41.28 | 0.5754 |

See [row-level assessments](../../strict_pass_rows.jsonl) and the [manifest](../../manifest.json). Original contract CSVs retain their historical C-check fields. This separate summary reports the complete endpoint. Answer length is a proxy for review burden; it does not measure professional review time.

BF16 Q17 leaves uncertain whether the information system must enforce the restriction or the organization alone must act. It receives no strict-pass credit and remains in the 36-question denominator. This is an author judgment without independent expert adjudication.

bf16_baseline_vs_4bit_compliancegpt: left-only passes 0, right-only passes 22, two-sided exact McNemar p = 4.768371582e-07。

bf16_vs_4bit_baseline: left-only passes 4, right-only passes 3, two-sided exact McNemar p = 1。
