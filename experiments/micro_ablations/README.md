# Matched rewrite diagnostics: S4/S4b and S7/S7a

This directory contains a secondary, gold-informed diagnostic study of two
rewrite choices.  The letter suffixes identify variants of existing systems;
they do not extend the S1--S7 retrieval ladder.

## Questions

- **S4b:** What happens when S4 fuses the original question with only one
  gold-informed selected rewrite instead of all accepted rewrites?
- **S7a:** What happens when S7 keeps its candidate construction unchanged but
  uses that selected rewrite as the cross-encoder query?

The selection procedure applies the canonical S7 query transformation and
rewrite filter, tests each of up to three accepted stored rewrites in the
base hybrid stage, and chooses the one giving the best gold-control rank.  It
uses the gold label and is therefore not available in deployment.  These
variants are diagnostic counterfactuals, not claims of a deployable upper
bound.

## Matched design

`run_micro_ablations.py` runs each variant together with its baseline in the
same process:

- S4 and S4b share BM25 control documents and RRF settings.
- S7 imports query planning, weighted fusion, privilege-scope adjustment, and
  reranking guards from `src/compliancegpt/retriever/retriever_s7.py`.
- S7 and S7a share the complete candidate set; only the cross-encoder query
  changes.
- All four use the same CCS files, stored rewrites, filtering, metrics, and
  evaluation rows.

The matched diagnostic configuration is:

- dense encoder: `intfloat/e5-small-v2`
- cross encoder: `BAAI/bge-reranker-base`
- candidate controls: 50
- RRF constant: 60
- rewrite weight: 0.25
- rewrite Jaccard threshold: 0.15
- S7 rerank blend: 0.65 base / 0.35 cross encoder
- S7 skip margin: 0.10
- S7 adoption margin: 0.15, reduced to 0.10 when the base margin is below 0.08
- privilege-scope match adjustment: 0.08 of the peak fused score
- privilege-scope mismatch adjustment: -0.06 of the peak fused score

Pinned Python dependencies are in `requirements.txt`.  Each run records package
versions, model repository revisions, input SHA-256 hashes, the canonical
retriever source hash, and output hashes in `run_metadata.json`.

## Run

The two revisions can be run independently and then aggregated:

```bash
python -m pip install -r experiments/micro_ablations/requirements.txt
python experiments/micro_ablations/run_micro_ablations.py \
  --revision rev4 --parts-root /tmp/micro-parts
python experiments/micro_ablations/run_micro_ablations.py \
  --revision rev5 --parts-root /tmp/micro-parts
python experiments/micro_ablations/run_micro_ablations.py \
  --aggregate-only --parts-root /tmp/micro-parts
```

The manually triggered GitHub Actions workflow runs the revisions in separate
jobs, aggregates the artifacts, and validates row counts and identifiers.

## Outputs

- `S4_matched_ALL.csv`
- `S4b_rrf_best_ALL.csv`
- `S7_matched_ALL.csv`
- `S7a_rerank_best_ALL.csv`
- `micro_ablation_summary.csv`
- `paired_diagnostics.csv`
- `baseline_validation.csv`
- `run_metadata.json`

## Validated findings

GitHub Actions run `29434558254` completed the Rev. 4 and Rev. 5 jobs and a
separate aggregation check.  Each system has 173 rows: 100 Rev. 5 gold, 36
Rev. 4 gold, 24 Rev. 5 ErrorBank, and 13 Rev. 4 ErrorBank rows.

| Dataset | S4 MRR@10 | S4b MRR@10 | S7 MRR@10 | S7a MRR@10 |
|---|---:|---:|---:|---:|
| Rev. 5 gold | 0.8509 | 0.8110 | 0.9400 | 0.9450 |
| Rev. 4 gold | 0.7880 | 0.7688 | 0.9583 | 0.9583 |
| Rev. 5 ErrorBank | 0.4504 | 0.4125 | 0.7813 | 0.8194 |
| Rev. 4 ErrorBank | 0.4615 | 0.3974 | 0.9231 | 0.8205 |

S4b lowers MRR@10 on all four datasets.  S7a gives small gains on the two
Rev. 5 datasets, ties S7 on the Rev. 4 gold set, and is worse on the Rev. 4
ErrorBank set.  Gold-informed rewrite selection therefore does not provide a
uniform benefit.  `paired_diagnostics.csv` records improve/tie/worsen counts
and exact metric differences for every matched contrast.

`baseline_validation.csv` compares the newly matched S4 and canonical S7 rows
with the frozen main-ablation rows.  This comparison makes source evolution
visible.  Dissertation contrasts between a baseline and its diagnostic
variant use the matched rerun, not results produced under a different
implementation state.

The per-query CSVs retain gate decisions, margins, query transformations, and
ranked controls.  They omit the canonical retriever's verbose candidate debug
array because it duplicates score details that are not used by this study's
metrics or paired comparisons.

`MicroAblation_S4b_S7a.ipynb` is retained only as the original exploratory
interface.  Its execution state has been cleared; canonical results come from
the standalone runner.
