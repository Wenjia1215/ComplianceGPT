# Independent Batch 5D audit

## Disposition

**PASS.** The supplied executed notebook and result archive are complete,
internally consistent, and reproduce the registered Batch 5D endpoints from
the row-level evidence. No result row, model output, summary value, or
scientific configuration was edited during repository archiving.

## Input identities

| Artifact | SHA-256 |
|---|---|
| Executed `Batch_5D_Rev5_Frontier_API_Baseline.ipynb` | `2e96e47c83f4d02e04b992a81d76cb3c8e670cffbc876d3329437637a1247fcc` |
| Supplied `rq2_frontier_baseline_rev5_v1.zip` | `9f088b2ccb410fdd6df8980d693529320fec351e9a01e7400cd7d48fc55dddef` |
| `summary.json` | `3c4c813bd73835f39e24432c42bf8c2e003e680ee284ce99e5466741634f5024` |
| `SUMMARY.md` | `6d1048a7294caf158011af13309b628139b28ab0b361543ab861fbc4060cbf38` |
| API response log | `542cea5d834b39e2189ff2b763041f62e2abc35d9d41ee72e0be71bd6ae63c4f` |
| Gemini contract CSV | `8380b370d061dc772e25b353b353b06023540c6c5f6613839c4f36bedccae06e` |

## Execution record

- The notebook has 13 cells, including nine code cells executed in order from
  1 through 9, eleven stored output blocks, and no error output.
- The notebook metadata requests an A100 GPU, and the runtime output identifies
  `NVIDIA A100-SXM4-40GB`.
- Source commit
  `b7e10b0993147378ade09853265ac8af1214a729` and `google-genai 2.26.0`
  were recorded before execution.
- Seventeen offline tests passed, and the preflight verified all 100 frozen
  Revision 5 contexts without making an API request.
- The production stage completed all 100 rows. The log contains 100 unique
  response IDs, one call for each query, zero parse retries, and zero orphaned
  calls. Every server model string is `gemini-3.5-flash`.
- Logged usage totals are 132,723 prompt tokens, 16,813 candidate tokens,
  39,832 thought tokens, and 189,368 total tokens.
- The archive contains no `runner_failure_tail.log` and no credential-like
  value. The notebook reports only the non-secret key family.

## Integrity and recomputation

The audit performed 495 independent checks across the extracted package:

- every output-manifest file hash and the canonical file-map hash;
- pre-commitment, frozen source archive, and model-visible input identities;
- generation settings, ordered context hashes, and exclusion of gold labels
  from model-visible inputs;
- one-to-one correspondence among API responses, completed rows, and
  contracts;
- exact query IDs and equality of the frozen matched inputs; and
- independent row-level recomputation of strict pass, full clause coverage,
  runtime pass, right control, ODP metrics, evidence precision/recall,
  realization loss, exact McNemar tests, and Fisher exact comparison.

All 495 checks passed. The recomputed headline values are:

| Endpoint | ComplianceGPT | Gemini 3.5 Flash | Qwen2.5-7B 4-bit |
|---|---:|---:|---:|
| Strict pass | 65/100 | 66/100 | 25/100 |
| Full clause coverage | 65/100 | 67/100 | 53/100 |
| Runtime contract pass | 100/100 | 99/100 | 42/100 |
| Realization loss | 0/65 | 1/67 | 28/53 |

The ComplianceGPT-versus-Gemini paired table is 54 both, 11
ComplianceGPT-only, 12 Gemini-only, and 23 neither; exact two-sided McNemar
`p = 1.0`. The registered realization-loss Fisher exact value is also `1.0`.

## Interpretation boundary

The audit supports no accuracy-superiority claim between ComplianceGPT and
Gemini. It confirms that ComplianceGPT's deterministic assembly and Runtime
Verifier produced zero realization loss whenever evidence coverage was
complete, as predicted by construction. Gemini nearly matched this behavior
empirically, but the evaluated free-form protocol does not make it a portable
or model-independent guarantee.

ODP operating characteristics use current author labels and have not been
independently adjudicated. The audit verifies their computation; it does not
establish label validity or legal sufficiency.
