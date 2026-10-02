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

The original benchmark labels were created in 2025 and were not consulted by
the annotator while preparing the blinded packet. That elapsed interval is the
washout period; generating the packet does not restart it or require an
additional waiting period.

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
6. Commit the reveal material, scoring code, frozen outputs, and dissertation
   update in a separate post-label commit.
