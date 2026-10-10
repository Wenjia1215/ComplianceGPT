# Revision hardening and strict-pass-v2

The original checker compared the active corpus revision with the reference row,
but ignored `framework_version` on ASK and PRESERVE contracts. A passing Rev. 5
answer could declare Rev. 4 and still pass. The reverse mutation also passed.
Source-ID normalization could similarly remove a contradictory revision prefix.

`active-revision-v2` adds explicit agreement checks. The current ComplianceGPT
and generative pipelines use this checker for new outputs. Historical verifier
snapshots remain available at their recorded execution commits. The
`strict-pass-v1` scoring source, original labels, and recorded model outputs retain
their bytes. Supplementary review explanations have a documented English edition
with the same verdicts, review IDs, and quoted evidence.

## Rules and identities

| Component | Identity | Scope |
|---|---|---|
| Runtime and reference verifier | `active-revision-v2`; patch `2026-10-09-active-revision-v2` | Require one supported declaration that agrees with the caller's active corpus. Check recognized source and citation revision labels. |
| Complete answer endpoint | `strict-pass-v2` | Require every v1 gate and the added revision gate. |
| Frozen-output score replay | `strict_pass_revision_replay_v2` | Assess 408 main, 988 supplementary, and 136 repaired no-selector records. |
| Revision mutation diagnostic | `runtime_revision_mutations_v2` | Test eight operators on 1,422 runtime-valid normal output records. |
| Semantic component | Inherited `strict-pass-v1` reviews and retention proofs | Preserve each existing verdict and record its origin; add no semantic adjudication. |

The v2 assessment fingerprint includes the declared revision and checked citation
metadata. Each assessment also records its v1 body fingerprint. Source-inspection
rows link to the unchanged v1 review ID and rule version. Retention proofs and
legacy contract failures carry separate provenance labels. This linkage avoids
presenting the revision repair as a new semantic review.

The caller must supply the active revision. A missing, unknown, non-string,
ambiguous, or opposite `framework_version` fails. Supported whole-string aliases
include `rev5`, `Revision 5`, `Rev. 5`, `r5`, and `5`, with equivalent Rev. 4
forms. The checker rejects conflicting recognized labels in source identifiers,
primary/all citation fields, and rendered citation suffixes. It also recognizes
packed NIST filenames such as `NIST.SP.800-53r4.pdf`.

The checker does not treat references to another revision in ordinary answer
prose as metadata declarations. A plain dictionary of clause text cannot prove
its catalog identity; callers must provide that identity and correct corpus
bytes. The replay verifies the pinned corpus hashes before scoring.

## Results

All **1,532 original v1 assessments reproduced**, and every strict-pass decision
remained unchanged under v2. Every added revision gate passed on the unchanged
records. No original contract error, semantic verdict, retention proof,
parameter-accounting result, or runtime validity result changed.

| Revision | ComplianceGPT | Gemini | Qwen baseline | Repaired no-selector replay |
|---|---:|---:|---:|---:|
| Rev. 5 | 65/100 | 56/100 | 21/100 | 92/100 |
| Rev. 4 | 29/36 | 22/36 | 6/36 | 35/36 |

The three main systems retain their original model executions. The repaired
no-selector result belongs to Batch 2's retrospective request replay. It does
not replace the original no-selector result, which remains 7/100 and 3/36.
The row-level [comparison counts](results_v1/comparison_counts.csv) include every
supplementary condition, including gate widths, rescue, and the BF16 baseline.

The legacy checker accepted all **11,376 runtime mutations**; v2 rejected all of
them. Each of 1,422 eligible output records supplied eight attempts: opposite,
missing, unknown, ambiguous, and non-string declarations; opposite source and
packed-file namespaces; and an opposite citation label. Rev. 4 supplied 384
controls, and Rev. 5 supplied 1,038. Both directions therefore have positive
controls. The other 110 records failed runtime validation before mutation and
do not enter this diagnostic denominator.

For each declaration or citation-label operator, 893 previously strict-passing
records retained the v1 semantic surface. V1 continued to credit those metadata
mutations; v2 credited none. Namespace mutations alter source IDs, so their
audit reports runtime results without inventing new semantic judgments.

These attempts reuse questions across conditions and systems. They test revision
handling on selected valid controls and do not estimate global verifier
sensitivity or an independent sample of question-level accuracy. The unchanged
counts show that the original outputs avoided this checker gap; they do not
excuse the original checker or prove correctness on other outputs.

## Reproduce

From the repository root, write a fresh external output directory:

```bash
python3 experiments/answerer_comparison/revision_hardening_v2/run_revision_replay.py \
  --output-dir /tmp/compliancegpt_revision_replay_v2
PYTHONPATH=src:. python3 -m unittest tests.test_revision_validation_v2 -v
```

The runner makes no model, retrieval, or API calls. It verifies frozen input
hashes, context/window identities, and all saved v1 assessment fields before
adding the v2 gate. It refuses to overwrite completed results. Check
`run_config.json` for source and input hashes, `score_deltas.jsonl` for every
decision comparison, `semantic_review_links.jsonl` for review provenance, and
`revision_mutation_audit.jsonl` for each mutation and its error tags.

This is a retrospective repair and diagnostic. Historical formal registrations
remain unchanged and reject the revised runtime. Register new runtime source
separately before collecting new experimental outputs.

## Interpretation limits

V2 preserves the v1 endpoint's other limits. It does not assess clarification
value domains, organizational approval, parameter necessity, nested obligations,
or whole-question usefulness. Source-inspection judgments remain inherited and
lack independent adjudication. Paired comparisons must identify this score
identity and retain the original question denominators.
