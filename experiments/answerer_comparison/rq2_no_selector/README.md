# RQ2 No-Selector Ablation
The separate [Original no-selector complete-endpoint summary](../supplementary_strict_pass/results_v1/studies/rq2_no_selector/SUMMARY.md) applies all seven strict-pass gates to the stored answers. Historical execution summaries retain the C-check endpoint.


This experiment answers whether the model selector improves the evaluated system or primarily trades expected-clause coverage for concision.

`run_no_selector_ablation.py` consumes the immutable contexts and ComplianceGPT contracts in the frozen RQ2 v3 archive. For each question it bypasses the selector and retains every statement or guidance record in the recorded evidence window. It performs no retrieval, model inference, fallback, rescue, or hierarchy expansion. The ordinary no-profile `ASK` policy and existing offline verifier are then applied.

The result identity is `rq2_no_selector_v1`. It does not replace or rename any RQ2 v3 artifact.

The original execution uses the legacy contract/gold check (C). Its historical
`offline_strict_pass` field gives 92/100 on Revision 5 and 35/36 on Revision 4.
The complete seven-gate standard gives 7/100 and 3/36 for the same original
contracts. See the [versioned assessment](strict_pass_v1/README.md) for
row-level decisions, hashes, and an offline reproduction command. The original
contracts contain empty clarification-request lists; a repaired request replay
is a separate intervention and must retain its own result identity.

The [request-repair comparison](../retrospective_repairs/README.md) places the
original 7/100 and 3/36 results beside the repaired 92/100 and 35/36 results.
Only `ask_list` changes between these conditions. The [paired statistical
analysis](../paired_conditional_statistics/README.md) records their relation to
ComplianceGPT without treating the original request-list defect as an isolated
selector effect. Answer length and extra evidence remain scope proxies, not
measured human review cost.

The report includes:

- legacy contract/gold pass (C);
- full expected-clause coverage;
- governing-control and any-clause hits;
- selected-clause and additional-evidence counts;
- gold-clause precision;
- answer and citation length;
- exact ODP-list agreement; and
- status expansion on author-labeled non-ODP rows.

Status expansion is descriptive. It is not reported as a false-positive rate or specificity estimate without independent adjudication.

Run from the repository root:

```bash
python experiments/answerer_comparison/rq2_no_selector/run_no_selector_ablation.py \
  --output-dir /tmp/compliancegpt_no_selector_replay
```

The script refuses an existing output directory so reruns cannot silently mix with or overwrite an earlier result identity.

