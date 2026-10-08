# Strict-pass extension v2: completed frozen-output audit

This is a retrospective exploratory re-evaluation. Historical scores, labels, model outputs and Runtime Verifier behavior remain unchanged. No generation or API calls were made. Semantic source-inspection judgments have not received independent expert adjudication.

The final extension requires every old strict-pass condition plus exact provenance, complete retained-parameter/clarification accounting, actual citation use, required answer content, supported claims, preserved parameter meaning, and compatible clarification value domains. Correct paraphrases are accepted.

| Revision | System | Legacy strict | Answer-content extension | Full extension, including clarification domains |
| --- | --- | ---: | ---: | ---: |
| rev5 | baseline | 25/100 (25.0%) | 21/100 (21.0%) | 21/100 (21.0%) |
| rev5 | compliancegpt | 65/100 (65.0%) | 65/100 (65.0%) | 51/100 (51.0%) |
| rev5 | gemini | 66/100 (66.0%) | 56/100 (56.0%) | 48/100 (48.0%) |
| rev4 | baseline | 8/36 (22.2%) | 6/36 (16.7%) | 6/36 (16.7%) |
| rev4 | compliancegpt | 29/36 (80.6%) | 29/36 (80.6%) | 25/36 (69.4%) |
| rev4 | gemini | 24/36 (66.7%) | 22/36 (61.1%) | 17/36 (47.2%) |

The full extension is the new strict-pass endpoint in this trial. The answer-content column separates realization errors from shared clarification-template errors; it is not substituted for the full score.

rev5/gemini: strict credited count 48; possible count if all uncertain cases pass 49. Uncertain cases remain in the denominator.

rev5: ComplianceGPT-only passes 12; Gemini-only passes 9; exact two-sided McNemar p = 0.663624.

rev4: ComplianceGPT-only passes 9; Gemini-only passes 1; exact two-sided McNemar p = 0.0214844.

## New failures

Each ID below previously passed the unchanged legacy endpoint. Overlapping failure categories count once.

- rev5/baseline: Q31, Q35, Q57, Q76
- rev5/compliancegpt: Q1, Q4, Q10, Q11, Q27, Q29, Q32, Q36, Q45, Q47, Q52, Q66, Q69, Q88
- rev5/gemini: Q1, Q11, Q17, Q20, Q22, Q24, Q29, Q35, Q47, Q67, Q69, Q83, Q86, Q87, Q88, Q90, Q92, Q100
  Uncertain semantic cases receive no strict credit: 67
- rev4/baseline: Q15, Q33
- rev4/compliancegpt: Q5, Q10, Q19, Q27
- rev4/gemini: Q4, Q5, Q7, Q10, Q16, Q19, Q27

## Reproduction

```bash
python experiments/answerer_comparison/strict_pass_extension/run_strict_pass_extension.py --output-dir /tmp/compliancegpt_strict_v2
```

The script verifies all six frozen contract hashes, both canonical-source hashes, both gold hashes, matched per-question windows, all 408 legacy outcomes, review fingerprints and exact source excerpts. Missing/stale reviews stop scoring. No uncertain case is silently dropped from the denominator.

The semantic ledger is `../reviews_v2.jsonl`; every failure cites the pinned answer and canonical evidence. Full source-retention certificates account for unchanged canonical assembly, but exact copying is not a requirement for other answers.

## Interpretation boundary

These counts concern the archived matched-window Qwen 4-bit and Gemini 3.5 Flash outputs. They do not measure the advisor's later prompt, another Gemini model, or an independently validated holdout task. The criteria were developed after examining these outputs. A changed ranking does not establish general model superiority, and a highest point estimate need not imply a statistically significant difference.
