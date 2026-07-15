# ErrorBank category analysis

`run_error_mode_analysis.py` regenerates the category-level retrieval report
from the labeled ErrorBank and the frozen S1--S7 result files.

## Why the revision is part of the key

The Rev. 4 and Rev. 5 ErrorBank subsets reuse question identifiers.  A row is
therefore identified by `(version, question_id)`, not by `question_id` alone.
The script also checks the question text and gold control after every join.  It
exits without writing a report if a result is missing, duplicated, or attached
to the wrong source row.

## Run

From the repository root:

```bash
python experiments/retriever_ablation/error_analysis/run_error_mode_analysis.py
```

The script requires pandas and reads:

- `data/error_bank/error_bank_v1.csv`
- all Rev. 4 and Rev. 5 ErrorBank outputs under
  `experiments/retriever_ablation/ablation_outputs/system_*/`

It writes:

- `generated_reports/merged_results_data.csv`
- `generated_reports/pivot_table.csv`
- `generated_reports/pivot_table.md`

For one gold control per query, RR@10 is `1/rank` for ranks 1--10 and zero
otherwise.  The category mean is therefore MRR@10.  Category counts are
included in the pivot and must sum to the frozen 37-row ErrorBank.

## Interpretation boundary

ErrorBank was constructed from known BM25 misranking cases.  Its categories
localize behavior within that challenge set; they do not estimate category
prevalence in a broader question population.  The Semantic Gap category has
only two cases, so its system ordering is descriptive rather than inferential.

The checked script and its generated reports are the canonical category
analysis.
