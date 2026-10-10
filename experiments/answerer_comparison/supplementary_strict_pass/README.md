# Complete strict-pass assessment of supplementary outputs

This assessment applies `strict-pass-v1`, requiring `C AND W AND L AND U AND A
AND F AND P`, to 988 frozen answers. It checks 136 original no-selector, 272
rescue-off/on, 544 fixed-gate-width, and 36 BF16 outputs. It verifies original
C decisions before applying the complete endpoint. Clarification value domains
are outside the scoring rule.

| Condition | Rev. 5 strict pass | Rev. 4 strict pass |
|---|---:|---:|
| Original no-selector | 7/100 | 3/36 |
| Rescue off | 59/100 | 29/36 |
| Rescue on | 65/100 | 29/36 |
| Fixed top-1 | 62/100 | 26/36 |
| Fixed top-2 | 65/100 | 29/36 |
| Fixed top-3 | 65/100 | 29/36 |
| Fixed top-5 | 64/100 | 28/36 |
| Free-form BF16 baseline | Not evaluated | 7/36 |

Original no-selector contracts have empty `ask_list` fields. Among C-passing
outputs, 85 Rev. 5 and 32 Rev. 4 answers therefore fail retained-parameter
accounting. Rev. 5 fixed top-5 answers Q12, Q39, and Q61 cite sources outside
their own frozen windows. These failures do not concern clarification value domains.

Seven BF16 source-inspection records appear in
[the supplementary review ledger](../strict_pass_supplementary_reviews.jsonl).
Identical answers reuse main-comparison judgments. Q17 leaves actor and system
enforcement uncertain, remains in the 36-question denominator, and receives no
pass credit. These are author judgments without independent expert adjudication.
Paired tests are retrospective, exploratory, and unadjusted. A nonsignificant
overall comparison does not establish equivalence.

## Evidence and reproduction

- [All 988 row-level assessments](results_v1/strict_pass_rows.jsonl)
- [Condition counts and paired results](results_v1/summary.json)
- [Input, scoring-source, review, and output hashes](results_v1/manifest.json)
- [BF16 complete-endpoint summary](results_v1/studies/rq2_bf16_baseline/SUMMARY.md)
- [Original no-selector complete-endpoint summary](results_v1/studies/rq2_no_selector/SUMMARY.md)
- [Rescue complete-endpoint summary](results_v1/studies/rq2_rescue_ablation/SUMMARY.md)
- [Fixed-width complete-endpoint summary](results_v1/studies/rq2_control_gate_width/SUMMARY.md)

```bash
python experiments/answerer_comparison/run_supplementary_strict_pass.py \
  --output-root /tmp/compliancegpt_supplementary_scores
```

Use a fresh output directory outside the repository. The runner checks frozen
input hashes, question identities, contexts, windows, canonical source text,
original C decisions, and review usage. It generates a separate assessment
package. Historical execution CSVs, JSON summaries, ZIPs, and split archives
retain their original bytes and endpoint labels.

The [English edition record](LANGUAGE_EDITION.json) identifies the source review
hash and translated fields. Every verdict, review ID, checked source, parameter
identifier, and source excerpt remains the original record. This edition adds
no semantic adjudication. The [strict-v2 replay](../revision_hardening_v2/README.md)
adds explicit revision agreement and preserves every decision in this ledger.
