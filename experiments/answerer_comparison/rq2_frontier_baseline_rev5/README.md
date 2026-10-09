# Batch 5D — Revision 5 Frontier API Baseline

[Open the Batch 5D notebook in Colab](https://colab.research.google.com/github/Wenjia1215/ComplianceGPT/blob/main/experiments/answerer_comparison/rq2_frontier_baseline_rev5/Batch_5D_Rev5_Frontier_API_Baseline.ipynb)

Batch 5D extends the completed Revision 4 frontier comparison to the primary
100-row NIST SP 800-53 Revision 5 benchmark. The protocol was registered in
[`PRECOMMITMENT.md`](PRECOMMITMENT.md) and
[`precommitment.json`](precommitment.json) before any Revision 5 Gemini output
was generated or inspected.

The result identity is `rq2_frontier_baseline_rev5_v1`. It is separate from the
36-row Batch 5C result and never edits or replaces the frozen RQ2 v3 outputs.

## Registered boundary

- Questions: all 100 frozen Revision 5 rows; no post-output exclusions.
- Contexts: the immutable ordered evidence windows from RQ2 matched-window v3.
- API model: stable model ID `gemini-3.5-flash`, Gemini Developer API Paid Tier 1.
- Prompt/parser: the exact frozen free-form prompt, context serialization, JSON
  parser, fail-closed normalization, and two parse retries used in Batch 5C.
- Prompt SHA-256:
  `91ba0d840befd5517fbec7595f640333bcb8df8e63301e80552dad841744fdef`.
- Settings: thinking level `LOW`, temperature `1.0`, maximum output tokens
  `2048`, no tools, and no API-enforced structured-output schema.
- Retrieval: none. The runner consumes the frozen prepared contexts.
- Gold policy: gold labels never enter an API request and are used only by the
  offline verifier.
- Completion rule: 100 validated, checkpointed rows; no outcome-based early
  stopping.
- Excluded study: Gemini Pro is not part of the registered comparison.

The evaluation uses the [complete strict-pass standard](../../../src/answerer_comparison/README.md)
on the saved three-system outputs, with two-sided exact McNemar tests. Supporting outputs
include clause coverage, coverage-complete realization loss, a two-sided Fisher
exact test, runtime structural pass, Wilson intervals, ODP sensitivity,
specificity and precision, clause precision/recall, and answer length.

## Offline tests

The tests use fake API responses or frozen local artifacts. They make no Gemini
request:

```bash
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python -m unittest \
  tests.test_frontier_api_answerer \
  tests.test_rq2_frontier_baseline \
  tests.test_rq2_frontier_baseline_rev5 -v
```

## Deterministic preparation without an API key

```bash
python experiments/answerer_comparison/rq2_frontier_baseline_rev5/run_frontier_baseline_rev5.py \
  --output-dir /tmp/rq2_frontier_baseline_rev5_v1 \
  --prepare-only
```

This verifies the pre-commitment, source archive, all Revision 5 inputs, all 100
model-visible contexts, and the frozen reference outputs. It writes a gold-free
prepared-context audit and does not read `GEMINI_API_KEY`.

## Full API run

Use the linked Colab notebook with an A100 GPU runtime. The notebook metadata
requests an A100 by default; confirm **Runtime → Change runtime type → A100
GPU** before starting. Store `GEMINI_API_KEY` in Colab Secrets and enable
notebook access. The key is read only into process memory and is never printed
or archived.

The notebook pins source commit
`b7e10b0993147378ade09853265ac8af1214a729`, runs the offline tests and
preflight before the API stage, and uses the persistent Drive directory
`/content/drive/MyDrive/rq2_frontier_baseline_rev5_v1`.

Every API response and every completed row is checkpointed. After a disconnect,
reconnect and use **Runtime → Run all**; validated rows are skipped. A transient
per-minute 429 waits and resumes. Authentication errors, daily-quota failures,
model-version changes, and other non-per-minute failures stop for inspection.

## Completed result

The pre-committed run completed all 100 rows with one API call per row, no
parse retries, no orphaned calls, and the server-reported model
`gemini-3.5-flash` on every response. The result package is archived under
[`results_v1/`](results_v1/), and the linked notebook is the executed Colab
record with all nine code-cell execution counts and outputs retained.

| System | Strict pass | Full clause coverage | Runtime contract pass | Realization loss |
|---|---:|---:|---:|---:|
| ComplianceGPT | 65/100 | 65/100 | 100/100 | 0/65 |
| Gemini 3.5 Flash | 56/100 | 67/100 | 99/100 | 11/67 |
| Qwen2.5-7B 4-bit | 21/100 | 53/100 | 42/100 | 32/53 |

ComplianceGPT has the highest observed strict-pass rate. Its paired comparison
with Gemini has 47 both passing, 18 ComplianceGPT-only, nine Gemini-only, and
26 neither passing (exact two-sided McNemar `p = 0.122078`). This exploratory
comparison does not establish a statistically significant end-to-end difference.
Coverage-complete realization loss is 0/65 for ComplianceGPT and 11/67 for
Gemini; the coverage-complete subsets differ by system. Semantic judgments
are not independently adjudicated.

Reproduce the saved-output evaluation with
`python experiments/answerer_comparison/run_strict_pass.py`.

The complete package contains:

- `contracts/rev5_generative_frontier_api.csv`;
- `api/responses.jsonl` with response IDs, raw outputs, server model, latency,
  finish metadata, and token usage;
- frozen Revision 5 ComplianceGPT and Qwen reference contracts;
- source, generation, API runtime, response, run, and output manifests;
- `summary.json`, `SUMMARY.md`, and `strict_pass_rows.{csv,jsonl}` with final strict-pass decisions and supporting metrics; and
- the sibling archive `rq2_frontier_baseline_rev5_v1.zip`.

ODP operating characteristics use the current author labels and are reported
with that limitation; they are not described as independently adjudicated.

See [`results_v1/AUDIT.md`](results_v1/AUDIT.md) for the post-run integrity and
metric recomputation, and
[`../RQ2_BATCH_5_COMPARISON.md`](../RQ2_BATCH_5_COMPARISON.md) for the unified
Batch 5A–5D interpretation.
