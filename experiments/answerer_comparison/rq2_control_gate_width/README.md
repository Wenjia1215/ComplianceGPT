# RQ2 Control Gate Width Sensitivity

The archived pass endpoint is the legacy contract/gold check (C). Its historical
`strict_pass` fields retain that meaning. See the
[result and scoring map](../../../docs/EVALUATION_RESULTS.md) for the current
complete standard and the boundaries between assessments and execution records.

[Open the Batch 5A notebook in Colab](https://colab.research.google.com/github/Wenjia1215/ComplianceGPT/blob/main/experiments/answerer_comparison/rq2_control_gate_width/Batch_5A_Control_Gate_Width_Sweep.ipynb)

This study implements the advisor-requested fixed-width sweep over the top 1, 2, 3, and 5 ranked controls. It changes one factor only: the number of ranked controls admitted to the shared evidence window. Retrieval traces, accepted query rewrites, document filtering, the primary-first rule, the 24-record cap, selector prompt, pinned selector model, ODP policy, and verifier remain fixed.

The new result identity is `rq2_control_gate_width_v1`. It never edits or replaces the frozen RQ2 v3 result family.

The completed, validated result is recorded under [`results_v1/`](results_v1/). Its canonical archive SHA-256 is `543c2e40879422a5a1462bb6fc56fda2ad76f9b060efbc780ebe2a51bc48a07d`.

The released adaptive gate is included as an unchanged reference. The four experimental settings use fixed widths with adaptive widening disabled. This distinction matters because the released path begins at top 1 but widens to top 2 or top 3 on low-margin queries.

The sweep preserves the released gate's exact unit of counting. Ranked enhancements are normalized to their base control before document filtering, and repeated normalized controls are not silently deduplicated. The output therefore records both requested rank width and effective unique base-control width. This exposes, rather than repairs, any width lost when multiple ranked enhancements map to the same base control.

## Metrics

For each revision and gate width, the completed run reports:

- legacy contract/gold pass (C) under the execution-time citation-contract endpoint;
- full expected-clause coverage and mean clause recall;
- mean gold-clause precision, selected-clause count, additional-clause count, and answer length;
- right-governing-control coverage;
- runtime contract validity;
- `PARAMS_REQUIRED` sensitivity, status precision, specificity, and exact ODP-list agreement against the author labels; and
- paired exact McNemar tests for C-pass differences.

The ODP operating characteristics use current author labels and have not been
independently adjudicated. The full annotation study is future validation, not
a pending condition on this recorded result.

## Deterministic preparation without a GPU

From the repository root:

```bash
python experiments/answerer_comparison/rq2_control_gate_width/run_control_gate_width.py \
  --output-dir /tmp/rq2_control_gate_width_v1 \
  --prepare-only
```

This verifies the frozen archive hash, reconstructs all 544 fixed-width contexts, hashes every context and evidence window, replays the exact non-adaptive runtime gate/window path against every locked manifest, and writes a gold-aware evidence-window opportunity audit. It does not call the selector and is not the completed sensitivity result.

## Full GPU run

Use a CUDA runtime and a persistent output directory so the row-level checkpoints survive a disconnect:

```bash
python experiments/answerer_comparison/rq2_control_gate_width/run_control_gate_width.py \
  --output-dir /content/drive/MyDrive/rq2_control_gate_width_v1
```

The runner pins `Qwen/Qwen2.5-7B-Instruct` at revision `a09a35458c702b33eeacc393d103063234e8bc28`, matching RQ2 v3. It refuses changes to the registered widths, frozen archive, source hashes, model identity, prepared contexts, or experiment-code fingerprint after model checkpoints exist. Re-running the same command resumes at the next unfinished question.

The completed directory contains the fixed-width contexts, row-level selector contracts, manifests, `summary.json`, `SUMMARY.md`, and a ZIP archive. The original adaptive outputs are read directly from the immutable RQ2 v3 archive and are never regenerated or modified.

For Colab, open `Batch_5A_Control_Gate_Width_Sweep.ipynb`, confirm the default
A100 GPU runtime, and choose **Runtime > Run all**. The notebook checks out the
registered runner commit and writes resumable checkpoints to
`MyDrive/rq2_control_gate_width_v1`.

## Recorded finding

Under the archived C endpoint, fixed top 2 matched the released adaptive gate's pass count in both revisions: 65/100 on Rev. 5 and 29/36 on Rev. 4. Top 3 produced the same C-pass and ODP-specificity results with lower clause precision. Top 5 reached 67/100 on Rev. 5 but fell to 28/36 on Rev. 4 and reduced Rev. 5 author-label ODP specificity from 17/37 to 12/37. Fixed top 1 fell to 62/100 and 26/36 without a specificity gain over the adaptive reference.

No stored within-revision C-pass comparison was statistically significant;
all exact two-sided McNemar values were at least 0.25. The tested data show no
benefit from the adaptive gate over a constant top-2 gate, making fixed top 2
the simpler evidence-supported operating point. ODP operating characteristics
use current author labels and have not been independently adjudicated.
