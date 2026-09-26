# RQ2 No-Selector Ablation

This experiment answers whether the model selector improves the evaluated system or primarily trades expected-clause coverage for concision.

`run_no_selector_ablation.py` consumes the immutable contexts and ComplianceGPT contracts in the frozen RQ2 v3 archive. For each question it bypasses the selector and retains every statement or guidance record in the recorded evidence window. It performs no retrieval, model inference, fallback, rescue, or hierarchy expansion. The ordinary no-profile `ASK` policy and existing offline verifier are then applied.

The result identity is `rq2_no_selector_v1`. It does not replace or rename any RQ2 v3 artifact.

The report includes:

- offline strict pass;
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
  --output-dir experiments/answerer_comparison/rq2_no_selector/results_v1
```

The script refuses an existing output directory so reruns cannot silently mix with or overwrite an earlier result identity.

