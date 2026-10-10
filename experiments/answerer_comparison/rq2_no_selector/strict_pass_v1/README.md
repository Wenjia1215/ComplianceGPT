# Original no-selector contracts: complete strict pass

Result identity: `rq2_no_selector_strict_pass_v1`.

This retrospective assessment applies the published seven-gate
[`strict-pass-v1`](../../../../src/answerer_comparison/README.md) standard to the
unchanged `rq2_no_selector_v1` contracts. It uses the original questions, gold
labels, canonical sources, and frozen matched evidence windows.

| Revision | Questions | Legacy contract/gold pass (C) | Complete strict pass | C passes failing retained-parameter accounting |
|---|---:|---:|---:|---:|
| Revision 5 | 100 | 92 | 7 | 85 |
| Revision 4 | 36 | 35 | 3 | 32 |

The original diagnostic contracts contain empty `ask_list` records. A contract
can therefore meet the legacy gold-based conditions while failing the complete
requirement to account for and request every retained unresolved parameter.
These failures do not show that the selector improves evidence selection.
The original coverage, answer-length, and precision measurements still describe
the stored answers.

This condition retains the original request records. A request-repaired replay
is a separate intervention and requires its own contracts and result identity.

The [summary](results_v1/summary.json) records input and scoring-code hashes.
The [row-level assessments](results_v1/strict_pass_rows.jsonl) expose every gate
decision, and the [file manifest](results_v1/FILES_SHA256.json) verifies the
assessment outputs. The original contract CSV files and execution ZIP remain
unchanged. Eligible bodies satisfy the existing complete-retention proof;
this assessment adds no human semantic judgments or independent adjudication.

Reproduce from the repository root without a GPU or API key:

```bash
python tools/audit_no_selector_strict_pass.py \
  --output-dir /tmp/compliancegpt_no_selector_strict_pass_v1
```

Use a fresh output directory. The script rejects changed input hashes, duplicate
question IDs, differing matched contexts, and disagreements with the recorded
legacy contract decisions.
