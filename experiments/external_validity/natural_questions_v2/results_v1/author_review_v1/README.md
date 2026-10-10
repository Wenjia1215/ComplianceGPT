# Completed author post-run review

All 40 final question/system pairs were reviewed by **Wenjia Wang**. This
publication translates the 40 explanatory notes into English. All 120
yes/no/uncertain judgments, reviewer names, runtime statuses, pair identities,
and frozen question references retain their recorded values. The import checks the actual
judgment cells, all pair identities and order, recorded runtime statuses, and
the 20 frozen question references against the registered inputs. It does not
rely on cached workbook completion formulas.

[LANGUAGE_EDITION.json](LANGUAGE_EDITION.json) records the original and English
workbook hashes, all changed note cells, and the original source commit. The
[original workbook](https://github.com/Wenjia1215/ComplianceGPT/blob/9116c4f9bf12042878d37935a036139f70529fd1/experiments/external_validity/natural_questions_v2/results_v1/author_review_v1/ComplianceGPT_Natural_Questions_Post_Run_Reviewed_Wenjia_Wang.xlsx)
remains available at that immutable historical source. The English edition
preserves formulas, validation lists, pane positions, and sheet names. It adds
no author judgment or independent review.

| Judgment | ComplianceGPT: yes / no / uncertain | Baseline: yes / no / uncertain |
|---|---:|---:|
| Within scope of available authority | 5 / 15 / 0 | 9 / 8 / 3 |
| Responsive to the entire original question | 1 / 19 / 0 | 5 / 15 / 0 |
| Unsupported implementation or legal claim | 0 / 20 / 0 | 6 / 14 / 0 |

Each row uses all 20 questions per system. The three uncertain judgments are
baseline scope assessments for NQ09, NQ16 and NQ19. They remain uncertain;
neither system's denominator is reduced. The author identified the baseline
unsupported-claim cases as NQ01, NQ02, NQ03, NQ05, NQ12 and NQ14.
Responsiveness is a separate dimension: several responsive baseline answers
also contain unsupported claims. A negative unsupported-claim judgment does
not establish that an empty or incomplete response is correct or useful.

This is a single-author, unblinded, descriptive post-run review. The author had
access to the companion audit observations. It is neither independent expert
validation nor a blind outcome assessment, and it supplies no population
accuracy estimate, composite correctness score, or new significance test.

The technical run, registered automatic scoring, and required author review
are now complete. Independent correctness remains unvalidated. The original
ZIP, contracts, automatic `summary.json`, and original blank
`post_run_semantic_review.csv` are unchanged. Their historical pending-review
flags describe the state when automatic scoring finished. This separate
completion record documents the later author review without rewriting that
history.

## Audit erratum

In NQ03, `cp-7_prm_1` has stored `data_type=duration`, while the canonical
definition is information-system operations. The displayed prompt itself does
not explicitly request a duration. The author correctly identified this
distinction. The post-run clarification audit description is corrected; the
original contract and scores remain unchanged. Other clarification defects
remain documented as qualitative observations, not a new registered metric.

## Reproduce the import

From the repository root, use Python's standard library and a new output folder:

```bash
python experiments/external_validity/natural_questions_v2/import_author_review.py \
  --workbook experiments/external_validity/natural_questions_v2/results_v1/author_review_v1/ComplianceGPT_Natural_Questions_Post_Run_Reviewed_Wenjia_Wang_English.xlsx \
  --output-dir /tmp/natural_questions_author_review
```

The exported CSV preserves the author's judgment values and name and carries
the translated notes. The JSON summary retains all uncertainties and identifies
the English workbook hash.
