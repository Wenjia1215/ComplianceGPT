# RQ2 ODP-Statement Rescue Ablation

This deterministic replay measures what bounded ODP-statement rescue changed in the frozen selector-based ComplianceGPT path.

`run_rescue_ablation.py` consumes the immutable prepared contexts and ComplianceGPT contracts in the validated RQ2 v3 archive. It reconstructs the pre-rescue spans from the stored normalized selector contract, reapplies the evaluated enhancement gate on non-fallback rows, reuses the two recorded top-window fallback contracts, and produces two contracts for each question:

- `rescue_off`: deterministic assembly from the recovered pre-rescue spans;
- `rescue_on`: the same spans after applying the implemented four-record ODP-statement rescue rule.

Before reporting an effect, the runner requires every replayed `rescue_on` contract to reproduce the frozen contract's core evidence, answer, status, ODP, citation, and scorer outcomes. It performs no live retrieval, model inference, prompt retry, new selector call, hierarchy expansion, or gold-aware rescue.

The result identity is `rq2_rescue_ablation_v1`. It does not replace or rename the frozen RQ2 v3 artifacts or the no-selector result family.

The replay matches all 136 frozen rescue-on core contracts. On Rev. 5, rescue activates on 22/100 rows and adds 44 identifier occurrences. It changes eight gold ODP rows from `OK` to `PARAMS_REQUIRED`, eliminating the eight false-complete cases present with rescue off; six of those rows also gain strict pass and full gold-clause coverage. Exact ODP-list agreement rises from 47/63 to 55/63. On Rev. 4, rescue activates on 2/36 rows but changes none of the measured ODP or coverage outcomes.

Rescue also expands `PARAMS_REQUIRED` on author-labeled non-ODP rows from 6/37 to 20/37 on Rev. 5 and from 7/17 to 9/17 on Rev. 4, while increasing evidence and answer length. Those expansions quantify review scope; they are not labeled false positives or used to estimate specificity without independent adjudication.

Run from the repository root:

```bash
python experiments/answerer_comparison/rq2_rescue_ablation/run_rescue_ablation.py \
  --output-dir /path/to/rq2_rescue_ablation_v1
```

The script refuses an existing output directory. The checked-in result directory is `results_v1/`; the SHA-256 of `results_v1.zip` is `a2bc5a122dfe391f605276eb896d7ae036bf42b8f8330019556dec97db5e8ea4`.
