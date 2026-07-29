# Reproducing ComplianceGPT Evaluations

This repository retains the source, canonical inputs, recorded outputs, and
run-specific provenance for the evaluations reported for ComplianceGPT. The
workflows use Google Colab or a CUDA-capable Python environment and may download
third-party model weights.

## Evaluation map

| Evaluation | Canonical entry point | Recorded results |
|---|---|---|
| S1–S7 governing-control retrieval | `experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb` | `experiments/retriever_ablation/ablation_outputs/` |
| Matched answer construction | `experiments/answerer_comparison/rq2_matched/run_matched_rq2.py` | `experiments/answerer_comparison/rq2_matched/results_v3/` |
| Secondary rewrite diagnostics | `experiments/micro_ablations/run_micro_ablations.py` | `experiments/micro_ablations/` |
| Runtime contract validation | `experiments/runtime_validation/revalidate_contracts.py` | `experiments/runtime_validation/outputs/` |
| Single-query demonstration | `src/compliancegpt/pipeline/single_run/Single_Run_Demo.ipynb` | generated during execution |

The S1–S7 retrieval results, corrected matched answerer results, secondary
diagnostics, and runtime validation are distinct result families. Do not
substitute one for another.

## Canonical inputs

The NIST source files, Canonical Clause Store files, gold datasets, ErrorBank,
ODP registries, and example organization profiles used by the reported
evaluations are identified in
[`EVALUATION_INPUT_CHECKSUMS.md`](EVALUATION_INPUT_CHECKSUMS.md).

Verify all listed inputs from the repository root:

```bash
python - <<'PY'
import hashlib
import pathlib
import re

manifest = pathlib.Path("EVALUATION_INPUT_CHECKSUMS.md").read_text()
rows = re.findall(r"\| `([^`]+)` \| `([0-9a-f]{64})` \|", manifest)
for path_text, expected in rows:
    path = pathlib.Path(path_text)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f"checksum mismatch: {path}")
print(f"verified {len(rows)} evaluation inputs")
PY
```

## S1–S7 retrieval evaluation

Open
[`AblationStudy_S1_7.ipynb`](experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb)
in Colab and follow
[`experiments/retriever_ablation/WORKFLOW.md`](experiments/retriever_ablation/WORKFLOW.md).
The stored outputs identify the notebook-local implementation used for the
reported retrieval results. Current-source diagnostics are reported separately
under `experiments/micro_ablations/`.

## Matched answerer evaluation

Install the recorded Colab dependencies and run:

```bash
python -m pip install -r experiments/answerer_comparison/rq2_matched/requirements-colab.txt
python experiments/answerer_comparison/rq2_matched/run_matched_rq2.py \
  --repo-root . \
  --output-dir /path/to/compliancegpt_rq2_matched_v3
```

The validated evidence package is
`experiments/answerer_comparison/rq2_matched/results_v3/compliancegpt_rq2_matched_v3.zip`.
Its SHA-256 is:

```text
56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328
```

The result record identifies:

- runner commit `be862bcadfa61b474d795303e01ce9394909fdcc`;
- model `Qwen/Qwen2.5-7B-Instruct`;
- model and tokenizer revision
  `a09a35458c702b33eeacc393d103063234e8bc28`;
- deterministic settings, code hashes, input hashes, context hashes, and
  output hashes.

See
[`experiments/answerer_comparison/rq2_matched/results_v3/README.md`](experiments/answerer_comparison/rq2_matched/results_v3/README.md)
for the validation boundary and reported results.

## Secondary retrieval diagnostics

Install the dedicated dependencies and follow
[`experiments/micro_ablations/README.md`](experiments/micro_ablations/README.md):

```bash
python -m pip install -r experiments/micro_ablations/requirements.txt
python experiments/micro_ablations/run_micro_ablations.py \
  --revision rev4 \
  --parts-root /tmp/micro-parts
python experiments/micro_ablations/run_micro_ablations.py \
  --revision rev5 \
  --parts-root /tmp/micro-parts
python experiments/micro_ablations/run_micro_ablations.py \
  --aggregate-only \
  --parts-root /tmp/micro-parts
```

These variants use gold labels to select rewrites and are diagnostic
counterfactuals, not deployable retrieval methods.

## Runtime validation

The runtime validator is deterministic and gold-independent:

```bash
python experiments/runtime_validation/revalidate_contracts.py
```

It checks source resolution, span containment, and visible unresolved-state
consistency. It does not measure global evidence completeness.

## Reproducibility boundary

- Some workflows require Google Colab, GPU resources, and third-party model
  downloads.
- The repository records the evaluated artifacts; it does not claim bitwise
  reproducibility across every hardware and software environment.
- Historical experiment hashes identify files at their recorded Git commits.
  Current source may evolve without changing previously published results.
- Passing the implemented verifier or offline scorer does not establish
  semantic correctness, legal sufficiency, or auditor approval.
