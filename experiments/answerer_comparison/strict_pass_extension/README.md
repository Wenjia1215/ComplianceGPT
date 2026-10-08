# Strict-pass extension trial

The implemented evaluation is [STANDARD_V2.md](STANDARD_V2.md). The completed counts are in [results_v2/SUMMARY.md](results_v2/SUMMARY.md), and the source-backed interpretation is in [REVIEW_EVIDENCE.md](REVIEW_EVIDENCE.md).

The original strict-pass verifier, gold labels, evidence windows and saved answers remain unchanged. Evaluation runs only on `evaluation/strict-pass-extension-20261008`; no generation, retrieval or prompt changes are included. [PROPOSED_STANDARD.md](PROPOSED_STANDARD.md) is the superseded v1 proposal.

The extension adds mandatory checks for exact provenance, complete parameter/clarification accounting, actual citation use, required body content, supported claims, preserved parameter meaning and compatible clarification value domains. The same conditions apply to all three systems. Correct paraphrases can pass. Old failures cannot be rescued.

## Reproduce

From the repository root, using Python 3.10 or later:

```bash
PYTHONPATH=src python -m unittest tests.test_strict_pass_extension compliancegpt.generator.verifier.test_contract_validity
python experiments/answerer_comparison/strict_pass_extension/run_strict_pass_extension.py --output-dir /tmp/compliancegpt_strict_v2
```

The first command exercises 21 extension tests and five unchanged verifier regression tests. The second verifies all ten pinned input files and all 408 historical outcomes, applies the versioned review ledger, and writes a separate result directory. It needs no model dependencies or inference service.

To rebuild the identity-free source-inspection packet without producing semantic scores:

```bash
python experiments/answerer_comparison/strict_pass_extension/run_strict_pass_extension.py --prepare --output-dir /tmp/compliancegpt_review_packet
```

## Audit files

| File | Contents |
| --- | --- |
| `reviews_v2.jsonl` | 122 distinct nonliteral eligible answer surfaces, representing 123 row occurrences; U/A/F/P decisions, case-specific rationales and exact source-backed findings |
| `results_v2/per_row_results.csv` | All 408 outcomes, unchanged S0, every added gate, review method and failure evidence |
| `results_v2/per_row_results.jsonl` | The same per-row data with structured source excerpts and clarification errors |
| `results_v2/summary.json` | Counts, rates, nominal Wilson intervals, possible-pass bounds and paired exact comparisons |
| `results_v2/manifest.json` | Source snapshot, ten input hashes, code/rubric/review hashes and result hashes |

All 94 eligible ComplianceGPT bodies retain complete canonical records and the required source IDs; their body gates have a sufficient source-retention certificate. This certificate does not exempt their clarification requests from inspection. Nonliteral bodies pass through source inspection rather than a literal-match requirement.

This is a retrospective exploratory audit. Source-inspection judgments have not received independent expert adjudication. The identity-free packet removes metadata, but this review was informed by the archived outputs and is not claimed to be blinded. Statistical comparisons are descriptive and unadjusted for multiple comparisons; no confirmatory or general-model ranking is established.
