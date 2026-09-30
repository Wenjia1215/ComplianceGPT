# Independent Batch 5C audit

Audit date: 2026-09-30

## Integrity checks

- The supplied runner ZIP passed CRC testing. Its 25 entries used safe relative
  paths with no absolute path, parent traversal, or backslash path.
- The SHA-256 of the supplied ZIP exactly matched the value printed by the
  executed notebook:
  `039ce427f717b83da6f54a87a67bb0438f6c15e44b49d29838d39bc523c20767`.
- After the documented paid-tier metadata correction, all 18 files registered
  by `manifests/outputs.json` matched their SHA-256 values. The canonical
  file-map hash matched
  `9d3a5abff585bde671faf75be1118d7d336adff531c06f2f1dacf3fbf5fb4e73`.
- The corrected ZIP passed CRC testing and has SHA-256
  `351af9780f0ed7e6714ed3eb81799e8793985ea8b14351f32da9e43ebefa0dfb`.
- The frozen context JSONL retained 36 unique query IDs, 36 distinct context
  hashes, 36 distinct order-sensitive evidence-window hashes, and registered
  SHA-256
  `4f1ca834993a34c22bb4b61fa9a984d32382b5e84e3473656a22af688412d7a6`.
- The frontier, BF16, 4-bit baseline, and ComplianceGPT CSVs contained the same
  36 query IDs in the same frozen order. The apparent `18, 17` ordering is also
  present in the registered contexts and every frozen reference; it is not a
  result corruption.

## Runtime and API checks

- Requested and server-reported model: `gemini-3.5-flash`.
- Python: 3.13.15; Google Gen AI SDK: 2.25.0; device: CPU.
- Settings: thinking `LOW`, temperature `1.0`, maximum output tokens `2048`, no
  tools, and no API-enforced structured-output schema.
- All 36 rows completed with exactly 36 logged API calls and 36 unique response
  IDs. Every question used call index 1; there were no parse retries and no
  orphaned responses.
- Every response status was `completed`, and every candidate finished with
  `FinishReason.STOP`.
- Every raw output SHA-256 matched its response-log digest.
- Logged usage totaled 48,037 prompt tokens, 4,994 candidate tokens, 11,307
  thinking tokens, and 64,338 total tokens.
- Aggregate model latency was 96.59 seconds; median per-call latency was 2.63
  seconds.
- `manifests/run.json` reports `resumed_rows: 0`. Switching accounts therefore
  produced one clean 36-row run rather than combining the earlier partial run
  with later responses.

## Independently checked metrics

| Metric | Gemini frontier | Qwen BF16 | Qwen 4-bit | ComplianceGPT 4-bit |
|---|---:|---:|---:|---:|
| Strict verifier pass | 24/36 (0.667) | 8/36 (0.222) | 8/36 (0.222) | 29/36 (0.806) |
| Full gold-clause coverage | 28/36 (0.778) | 20/36 (0.556) | 18/36 (0.500) | 29/36 (0.806) |
| Runtime contract pass | 33/36 (0.917) | 14/36 (0.389) | 13/36 (0.361) | 36/36 (1.000) |
| Mean gold-clause recall | 0.833 | 0.664 | 0.596 | 0.886 |
| Mean gold-clause precision | 0.615 | 0.575 | 0.488 | 0.505 |
| Mean selected clauses | 3.06 | 2.89 | 3.33 | 4.03 |
| Author-label ODP sensitivity | 18/19 | 0/19 | 0/19 | 19/19 |

## Paired analysis

Against either Qwen baseline, Gemini had 18 frontier-only strict passes and two
Qwen-only strict passes. The exact two-sided McNemar value was
`0.0004024505615234375`.

Against ComplianceGPT, 21 rows passed under both systems and four failed under
both. Gemini alone passed query IDs 4, 16, and 30. ComplianceGPT alone passed
IDs 1, 8, 18, 24, 28, 31, 33, and 36. The discordance was therefore 3 versus 8,
with exact two-sided McNemar `p = 0.2265625`.

The result supports a large improvement from model strength within the
free-form baseline while leaving ComplianceGPT with the highest observed
strict-pass rate and perfect runtime-contract validity. The 36-row paired
comparison does not establish statistically significant superiority over the
Gemini frontier baseline.

## Metadata correction boundary

The original runner archive is retained unchanged. The corrected materialized
result changes only `run_config.json` billing/data-policy provenance and the
dependent `manifests/outputs.json` hashes. The correction is explicitly marked
as operator-reported because the Gemini `generateContent` response does not
return the billing tier. Scientific payloads and metrics are byte-identical to
the original run.
