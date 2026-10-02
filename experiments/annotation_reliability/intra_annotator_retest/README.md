# Intra-annotator test-retest protocol

This folder records the pre-label protocol for a 30-row blinded
intra-annotator test-retest check over the 136-row ComplianceGPT benchmark.
The check estimates the stability of the author's original labels. It is not
independent adjudication, inter-annotator agreement, or external validation.

The pre-label commit intentionally records the algorithm, frozen input hashes,
sample allocation, and cryptographic commitments while withholding the private
seed, blind-ID mapping, original sampled labels, and agreement results. Those
items are revealed only after the completed second-label file is frozen and
hashed.

## Manual design decisions and automated selection

The researcher fixed three design choices before re-labeling:

1. use 30 rows from the 136-row benchmark;
2. stratify only by NIST revision, yielding 8 of 36 Revision 4 rows and 22 of
   100 Revision 5 rows after proportional whole-row allocation; and
3. re-label governing control, expected clause IDs, and required ODP IDs.

The script performs every row-level operation automatically. Within each
revision it computes a SHA-256 rank from the private seed, revision label, and
original row ID; sorts by that digest; and takes exactly the first 8 or 22
rows. It then computes a separately domain-separated SHA-256 rank to establish
display order, assigns `IR-001` through `IR-030`, removes original identifiers
and labels, and validates the output. There is no manual truncation after
viewing the ranking and no outcome-dependent row substitution.

Question text, gold labels, ODP status, system outputs, strict-pass results,
and ErrorBank categories do not enter either ranking function. Exact formulas,
source hashes, and commitments are in [`protocol_v1.json`](protocol_v1.json).

## Washout basis

The original benchmark construction and annotation took place from October
2025 through February 18, 2026. The original labels were not consulted by
the annotator while preparing the blinded packet. That elapsed interval is the
washout period; generating the packet does not restart it or require an
additional waiting period.

The fuller date range is recorded in the dated
[chronology clarification](PROTOCOL_CLARIFICATION_2026-10-02.md). The registered
protocol and all frozen experiment records remain unchanged.

## Private preparation command

The script uses only the Python standard library. Store the private seed
outside the repository and generate outputs into the ignored `private/`
directory:

```bash
python experiments/annotation_reliability/intra_annotator_retest/prepare_blinded_sample.py \
  --rev4-csv data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv \
  --rev5-csv data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv \
  --seed-file /secure/path/private_seed.txt \
  --output-dir experiments/annotation_reliability/intra_annotator_retest/private \
  --expected-sample-commitment a6582b20ea6605395627dd0229981be6841ef76e55af022526ce773f71a686c0
```

The command writes:

- `blinded_relabeling_packet.csv`, containing only blind ID, NIST revision,
  question, and empty response fields;
- `private_blind_id_mapping.json`, which must remain withheld until reveal; and
- `sampling_run_manifest.json`, containing source and output hashes but not the
  seed value.

The formatted XLSX packet is a reader-facing derivative of the same selected
rows. Its frozen blank-file hash is recorded in `COMMITMENTS.sha256`; the XLSX
itself is not committed during the blinded phase.

## Offline tests

Run:

```bash
python experiments/annotation_reliability/intra_annotator_retest/test_prepare_blinded_sample.py
```

The tests verify deterministic 8/22 selection, unique blind IDs and questions,
label independence, absence of forbidden gold fields in the blinded output,
content-sensitive commitments, and the two frozen source-file hashes.

## Reveal sequence

1. Complete all 30 second-label rows without consulting the original labels,
   row mapping, or system outputs.
2. Freeze the completed workbook and record its SHA-256 before comparison.
3. Reveal the seed and blind-ID mapping and reproduce the committed sample.
4. Compare the second labels with the original labels.
5. Report control exact agreement and Cohen's kappa; clause-set and ODP-set
   exact agreement and Jaccard similarity; and a row-level disagreement audit.
6. Commit the reveal material, scoring code, and frozen outputs in a separate
   post-label commit. Incorporate the results into the manuscript separately.

## Post-label reveal

All 30 second-label rows were completed before the original labels, mapping,
or agreement results were revealed. The completed workbook was frozen at
`2026-10-02T12:08:35-04:00` with SHA-256
`7815a13223f356a69ae67ce4f989d2eb01c79c598510cd1c3bf3dd9598f61ca2`.
The `Relabeling completed` cell in the workbook was left blank; the external
freeze timestamp records completion without changing the frozen file.

This was a blinded repeat by the original annotator. The original labels and
system outputs were not available during re-labeling, but this was not an
independent-assessor exercise. The result therefore measures test-retest label
stability, not external correctness.

The [`reveal/`](reveal/) directory contains:

- the frozen completed workbook and a machine-readable CSV export;
- the originally blinded CSV, revealed seed, blind-ID mapping, and sampling
  run manifest;
- the scoring summary, complete row-level comparison, Markdown report, and
  formatted result workbook; and
- `reveal_manifest.json`, which records the freeze, commitments, source
  hashes, and SHA-256 of every revealed artifact.

The warning inside `private_blind_id_mapping.json` is intentionally preserved
byte-for-byte from its pre-reveal generation. The mapping is now public only
because the completed workbook was frozen first.

## Agreement results

| Metric | Result |
| --- | ---: |
| Governing-control exact agreement | 29/30 (96.7%) |
| Governing-control Cohen's kappa | 0.965 |
| Clause-set exact agreement | 16/30 (53.3%) |
| Clause-set mean Jaccard | 0.796 |
| ODP-set exact agreement | 26/30 (86.7%) |
| ODP-set mean Jaccard | 0.887 |
| All three components exact | 16/30 (53.3%) |

Fourteen rows had at least one disagreement. A row-level audit found that five
of the clause-set disagreements involved parent-versus-child citation
granularity. The complete differences are reported in
[`reveal/AGREEMENT_REPORT.md`](reveal/AGREEMENT_REPORT.md) and
[`reveal/agreement_results.csv`](reveal/agreement_results.csv).

## Reproduce the reveal

Run the sampler again with the now-public seed, then run the scorer against the
frozen second labels:

```bash
retest_out="$(mktemp -d)"

python experiments/annotation_reliability/intra_annotator_retest/prepare_blinded_sample.py \
  --rev4-csv data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv \
  --rev5-csv data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv \
  --seed-file experiments/annotation_reliability/intra_annotator_retest/reveal/revealed_seed.txt \
  --output-dir "$retest_out/sample" \
  --expected-sample-commitment a6582b20ea6605395627dd0229981be6841ef76e55af022526ce773f71a686c0

python experiments/annotation_reliability/intra_annotator_retest/score_retest.py \
  --completed-csv experiments/annotation_reliability/intra_annotator_retest/reveal/completed_second_labels.csv \
  --completed-xlsx experiments/annotation_reliability/intra_annotator_retest/reveal/ComplianceGPT_Intra_Annotator_Retest_30_Rows_Completed.xlsx \
  --expected-completed-xlsx-sha256 7815a13223f356a69ae67ce4f989d2eb01c79c598510cd1c3bf3dd9598f61ca2 \
  --mapping-json "$retest_out/sample/private_blind_id_mapping.json" \
  --rev4-csv data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv \
  --rev5-csv data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv \
  --frozen-at 2026-10-02T12:08:35-04:00 \
  --output-dir "$retest_out/scored"
```

Run the offline tests with:

```bash
python experiments/annotation_reliability/intra_annotator_retest/test_prepare_blinded_sample.py
python experiments/annotation_reliability/intra_annotator_retest/test_score_retest.py
```
