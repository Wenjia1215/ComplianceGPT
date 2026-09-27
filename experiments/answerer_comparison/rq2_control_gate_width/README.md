# RQ2 Control Gate Width Sensitivity

[Open the Batch 5A notebook in Colab](https://colab.research.google.com/github/Wenjia1215/ComplianceGPT/blob/main/experiments/answerer_comparison/rq2_control_gate_width/Batch_5A_Control_Gate_Width_Sweep.ipynb)

This study implements the advisor-requested fixed-width sweep over the top 1, 2, 3, and 5 ranked controls. It changes one factor only: the number of ranked controls admitted to the shared evidence window. Retrieval traces, accepted query rewrites, document filtering, the primary-first rule, the 24-record cap, selector prompt, pinned selector model, ODP policy, and verifier remain fixed.

The new result identity is `rq2_control_gate_width_v1`. It never edits or replaces the frozen RQ2 v3 result family.

The released adaptive gate is included as an unchanged reference. The four experimental settings use fixed widths with adaptive widening disabled. This distinction matters because the released path begins at top 1 but widens to top 2 or top 3 on low-margin queries.

The sweep preserves the released gate's exact unit of counting. Ranked enhancements are normalized to their base control before document filtering, and repeated normalized controls are not silently deduplicated. The output therefore records both requested rank width and effective unique base-control width. This exposes, rather than repairs, any width lost when multiple ranked enhancements map to the same base control.

## Metrics

For each revision and gate width, the completed run reports:

- offline strict pass under the existing gold-based citation-contract endpoint;
- full expected-clause coverage and mean clause recall;
- mean gold-clause precision, selected-clause count, additional-clause count, and answer length;
- right-governing-control coverage;
- runtime contract validity;
- `PARAMS_REQUIRED` sensitivity, status precision, specificity, and exact ODP-list agreement against the author labels; and
- paired exact McNemar tests for strict-pass differences.

The ODP operating characteristics against the author labels are provisional. They must not be described as independently adjudicated specificity until the blinded practitioner annotation is returned.

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

For Colab, open `Batch_5A_Control_Gate_Width_Sweep.ipynb`, select an A100 GPU when available (T4 or L4 is also supported), and choose **Runtime > Run all**. The notebook checks out the registered runner commit and writes resumable checkpoints to `MyDrive/rq2_control_gate_width_v1`.
