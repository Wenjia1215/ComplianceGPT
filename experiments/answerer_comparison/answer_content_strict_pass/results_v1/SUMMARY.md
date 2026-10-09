# Answer-content strict-pass results

The strict-pass endpoint in this evaluation is Answer-content extension. Every legacy strict condition remains mandatory. This is a retrospective audit of saved outputs; models and labels were not changed or regenerated. Source-inspection judgments are not independently adjudicated.

| Revision | System | Legacy strict pass | Answer-content strict pass | Nominal 95% Wilson interval |
| --- | --- | ---: | ---: | ---: |
| rev5 | baseline | 25/100 (25.0%) | 21/100 (21.0%) | [0.142, 0.300] |
| rev5 | compliancegpt | 65/100 (65.0%) | 65/100 (65.0%) | [0.553, 0.736] |
| rev5 | gemini | 66/100 (66.0%) | 56/100 (56.0%) | [0.462, 0.653] |
| rev4 | baseline | 8/36 (22.2%) | 6/36 (16.7%) | [0.079, 0.319] |
| rev4 | compliancegpt | 29/36 (80.6%) | 29/36 (80.6%) | [0.650, 0.902] |
| rev4 | gemini | 24/36 (66.7%) | 22/36 (61.1%) | [0.449, 0.752] |

## Added requirements

Exact source/window identity and full retained-parameter accounting are checked mechanically. Actual citation use, required body content, claim faithfulness and parameter meaning are assessed by versioned source inspection or a complete canonical-retention proof. Correct paraphrases can pass. Clarification value domains are not scored.

## Count reconciliation

| Revision / system | Legacy passes | Added failures or uncertain cases | Final passes |
| --- | ---: | ---: | ---: |
| rev5/baseline | 25 | 4 | 21 |
| rev5/compliancegpt | 65 | 0 | 65 |
| rev5/gemini | 66 | 10 | 56 |
| rev4/baseline | 8 | 2 | 6 |
| rev4/compliancegpt | 29 | 0 | 29 |
| rev4/gemini | 24 | 2 | 22 |

New nonpassing IDs among previous passes:

- rev5/baseline: Q31, Q35, Q57, Q76
- rev5/compliancegpt: none
- rev5/gemini: Q17, Q20, Q22, Q24, Q35, Q67, Q86, Q87, Q90, Q100
- rev4/baseline: Q15, Q33
- rev4/compliancegpt: none
- rev4/gemini: Q7, Q10

rev5/gemini: Q67 receives no strict credit. If all uncertain cases pass, the possible count is 57/100. No row is dropped from the denominator.

## Paired comparison

rev5: ComplianceGPT-only passes 18; Gemini-only passes 9; exact two-sided McNemar p = 0.122078.

rev4: ComplianceGPT-only passes 10; Gemini-only passes 3; exact two-sided McNemar p = 0.0922852.

These are unadjusted exploratory comparisons. A higher point estimate does not establish general or independently confirmed model superiority.

## Reproduce

```bash
python experiments/answerer_comparison/answer_content_strict_pass/run_evaluation.py --output-dir /tmp/compliancegpt_answer_content
```

All ten input hashes, matched windows, all 408 historical outcomes, review fingerprints and exact failure excerpts are verified. Missing or stale reviews stop scoring.

See [the full standard](../README.md), [the review ledger](../reviews.jsonl), and [three detailed examples](../EXAMPLES.md).
