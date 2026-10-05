# Primary RQ1 constant sensitivity

**Status: formal GPU run completed; all 952 evaluations verified by exact replay and separate statistical checks.**

This study varies the primary notebook's blend weight, fixed rerank-adoption
margin and rerank-skip margin separately by ±20%. Its seven conditions cover
all 136 questions (952 evaluations), use the existing rewrite files, and preserve
the original notebook logic. See [PROTOCOL.md](PROTOCOL.md) and `protocol.json`
for the exact configuration, model/code/input pins, scoring rules and limits.

Scientific execution commit: `a066453a317bba365db707b71745e49fee28811a`.

The finalized notebook checks out this immutable commit. It validates all
scientific source, registered questions and corpus/rewrite hashes before inference.

## Run in Colab

Open `Batch_RQ1_Constant_Sensitivity.ipynb`, select **Runtime → Change runtime
type → A100 GPU**, then **Run all**. The notebook clones the public registered
source, installs the pinned dependencies, runs offline checks and performs the
complete capture and seven-condition replay. No generation API key is needed.
It mounts Drive to retain completed captures and resume an interrupted session.
The actual allocated GPU is recorded in the run manifest.

The launcher removes the optional `timm`, `torchvision` and `torchaudio` packages
together before installing the pinned text-model dependencies. Leaving `timm`
installed after removing `torchvision` causes Transformers 4.51.3 to discover a
broken vision backend during text-model loading. A fresh-process preflight now
checks the optional backends and constructs tiny BERT and XLM-RoBERTa models
through the same AutoModel loading paths before the study starts. The subprocess
environment explicitly selects PyTorch and disables unused TensorFlow imports.
This launcher correction preserves the scientific execution commit, registration,
model pins, package pins and output directory, so compatible captures can resume.

Default output: `MyDrive/ComplianceGPT_runs/rq1_constant_sensitivity_v1`.
Return the generated `rq1_constant_sensitivity_v1.zip` after completion. It
contains all score caches, per-query ranks, gate diagnostics, paired statistics,
historical-baseline comparisons, configuration and checksums. Do not replace
the original S7 CSVs with these new results.

The saved historical results have no complete raw score cache. A fresh model
capture is needed, including cross-encoder scores for originally skipped queries.
After capture, all seven decisions use identical per-query scores. The new
baseline's differences from the saved historical ranks are reported explicitly;
no model is tuned to force agreement.

## Checks and reproduction

```bash
PYTHONPATH=src:. python -m unittest tests.test_rq1_constant_sensitivity -v
PYTHONPATH=src:. python experiments/retriever_ablation/constant_sensitivity/run_sensitivity.py \
  --output-dir /content/drive/MyDrive/ComplianceGPT_runs/rq1_constant_sensitivity_v1
```

Once a complete cache exists, `--replay-cache` regenerates the deterministic
scoring/report files without fresh model inference. A compatible resume requires
the same scientific source, package/runtime settings, input hashes and pinned
model files. The runner rejects changes rather than silently restarting them.
`--prepare` is for a new registration before execution and refuses existing
registration files. Preserve this result identity if a new study is needed.

The interpretation remains exploratory: these comparisons do not remove prior
evaluation-set tuning bias or demonstrate held-out or independent correctness.

## Verified result

The complete verified result is in [results/rq1_constant_sensitivity_v1](results/rq1_constant_sensitivity_v1).
Read [AUDIT.md](results/rq1_constant_sensitivity_v1/AUDIT.md) for the interpretation,
verification evidence, gate tradeoffs, historical drift, limits and reproduction
command. The original result ZIP is retained as two binary parts; the audit
command verifies their hashes and reconstructs the exact original archive.

Revision 5 Success@1 ranges from 88/100 to 90/100 and Success@10 from 99/100 to
100/100. At alpha 0.52, query 23's governing control moves from rank 10 to rank 11.
The fresh baseline differs from two saved historical gold ranks. These findings
are reported explicitly; historical headlines are preserved. Local sensitivity
does not establish parameter invariance, remove benchmark tuning bias or replace
independent expert validation.
