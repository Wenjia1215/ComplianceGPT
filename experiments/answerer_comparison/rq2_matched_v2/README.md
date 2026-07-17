# RQ2 matched-window rerun (v2)

This directory contains the corrected primary experiment for RQ2. It compares
the ComplianceGPT answer path with the free-form generative answer path while
holding the retrieval result and the model-visible evidence window constant.
The run includes all 100 Revision 5 questions and all 36 Revision 4 questions.

[Open the rerun notebook in Colab](https://colab.research.google.com/github/Wenjia1215/ComplianceGPT_v2/blob/codex/rq2-immutable-window-v2/experiments/answerer_comparison/rq2_matched_v2/RQ2_Matched_Window_Rerun.ipynb)

## Experimental scope

The primary paired comparison is:

| Component | Generative RAG baseline | ComplianceGPT |
|---|---|---|
| Stored S7 retrieval trace | Same | Same |
| Ordered evidence window | Same immutable window | Same immutable window |
| Base model and exact model commit | Same | Same |
| Decoding | Deterministic greedy decoding | Deterministic greedy decoding |
| Answer path | Free-form answer generation | Evidence selection followed by deterministic assembly |
| Gold labels visible during generation | No | No |

This design isolates the effect of the answer path. A conventional
BM25-to-generator system would be a useful supplemental end-to-end baseline,
but it is not a substitute for this paired RQ2 comparison because it changes
retrieval and answer construction at the same time.

## Active inputs

The runner reads only the active repository paths below. No archived directory
is read, moved, or modified.

- `experiments/pipeline_runs/pipeline_rev5_contracts_20260312_150620.csv`
- `experiments/pipeline_runs/pipeline_rev4_contracts_20260312_152654.csv`
- `data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl`
- `data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl`
- `data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv`
- `data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv`
- `data/ODP/rev5/odp_registry_rev5.json`
- `data/ODP/rev4/odp_registry_rev4.json`

The existing experiment outputs remain unchanged. The corrected run writes to
a new versioned output directory.

## Controls enforced by the runner

1. The stored S7 trace is reconstructed from the original contract output. No
   live retrieval call is allowed.
2. Control gating, primary-control ordering, evidence-kind filtering, and the
   24-record cap are implemented once and shared by both answer paths.
3. Each prepared context receives a canonical SHA-256 digest. Each evidence
   window receives an order-sensitive and text-sensitive SHA-256 digest.
4. Each answer path recomputes the window and must match the locked digest
   before generation starts.
5. Both answer paths use the same in-memory model and tokenizer. The Hugging
   Face model commit is resolved once and recorded on every output row.
6. Prepared contexts reject fields whose names begin with `gold`. Gold rows are
   passed only to the post-generation verifier.
7. A checkpoint is written after every question. Resume is refused if the code
   commit, model revision, context hash, or evidence-window hash changes.
8. Paired validation must report zero context, evidence-window, and model
   mismatches before metrics are summarized.
9. The active input files and the generated Revision 4 and Revision 5 context
   files must match the SHA-256 regression values established before the GPU
   run. Any drift stops the run before model loading.

## Colab run

1. Open `RQ2_Matched_Window_Rerun.ipynb` in Colab.
2. Select a T4 GPU or better.
3. Add a Colab secret named `GITHUB_TOKEN` with read access to this repository.
4. Select **Runtime > Run all** and approve the Google Drive mount.

The notebook checkpoints to
`MyDrive/compliancegpt_rq2_matched_v2`. If Colab disconnects, run the same
notebook again; completed questions are validated and skipped. At completion,
the notebook downloads `compliancegpt_rq2_matched_v2.zip`.

The equivalent command in a CUDA environment is:

```bash
python experiments/answerer_comparison/rq2_matched_v2/run_matched_rq2.py \
  --repo-root . \
  --output-dir /path/to/compliancegpt_rq2_matched_v2
```

## Output structure

```text
compliancegpt_rq2_matched_v2/
├── contexts/
│   ├── rev4_prepared_contexts.jsonl
│   └── rev5_prepared_contexts.jsonl
├── contracts/
│   ├── rev4_compliancegpt.csv
│   ├── rev4_generative_baseline.csv
│   ├── rev5_compliancegpt.csv
│   └── rev5_generative_baseline.csv
├── manifests/
├── summaries/
└── run_config.json
```

The result ZIP is the evidence package for the Chapter 5 update. Results must
not be copied into the dissertation until paired validation succeeds.
