# Environments and execution modes

Choose an environment for the task you want to run. Reading saved results,
scoring stored contracts, replaying deterministic fixtures, and collecting
new model responses have different requirements.

This guide describes source commit
`3427dca90921fad88afa3fc179cb6980fb1d1a42`, checked on 2026-10-10.
Documentation updates after that snapshot do not change its execution code.
Use [REPRODUCIBILITY.md](../REPRODUCIBILITY.md) for result identities and
[the result map](EVALUATION_RESULTS.md) for assessment versions.

## Choose a mode

| Task | Inputs and execution | Environment |
|---|---|---|
| Inspect saved tables, manifests, and row ledgers | Read checked-in files; no experiment runs. | A file reader; Python is optional. |
| Score stored main and supplementary answers | Read frozen contracts, labels, and evidence; write separate assessment files. | The CPU environment below; no model download, GPU, or API key. |
| Run unit checks and profile/revision integration diagnostics | Use stored selectors, synthetic profiles, and deterministic mutations. | The CPU environment below; no live retrieval or model/API inference. |
| Reproduce a registered retrieval or Qwen run | Use its recorded source commit, inputs, model revision, and dependencies. | Its historical GPU/Colab environment; model downloads may be needed. |
| Reproduce a registered Gemini run | Send the registered prompts through the API and retain responses and usage. | Its recorded API environment and an operator-supplied key; no local GPU is needed. |

An offline assessment is a new score of stored answers. It does not collect a
new model response. Likewise, a replay of stored selector outputs does not
rerun retrieval or the selector model.

## Checked CPU environment

The offline checks used Python **3.12.14**, NumPy **2.3.5**, pandas **2.2.3**,
and PyYAML **6.0.3**. NumPy supports imported retrieval/evaluation utilities;
pandas supports the constant-sensitivity unit checks; PyYAML reads profiles.
The environment did not have Torch, Transformers, Sentence Transformers, or
the Google GenAI SDK installed.

To prepare a separate environment with these package versions, use Python
3.12 and run the following commands from the repository root:

```bash
python -m venv /tmp/compliancegpt-offline-venv
source /tmp/compliancegpt-offline-venv/bin/activate
python -m pip install numpy==2.3.5 pandas==2.2.3 PyYAML==6.0.3
```

This is a dependency set for the offline checks, not a replacement for a
historical experiment's requirements. Keep model experiments in separate
environments because their recorded package versions differ.

Run the unit suite from the repository root:

```bash
PYTHONPATH=src:. python -m unittest discover -s tests -v
```

Use fresh directories outside the repository for generated assessments:

```bash
python experiments/answerer_comparison/run_strict_pass.py \
  --output-root /tmp/compliancegpt_main_scores
python experiments/answerer_comparison/run_supplementary_strict_pass.py \
  --output-root /tmp/compliancegpt_supplementary_scores
python experiments/answerer_comparison/revision_hardening_v2/run_revision_replay.py \
  --output-dir /tmp/compliancegpt_revision_scores
python tools/validate_release_candidate.py \
  --output-dir /tmp/compliancegpt_profile_integration
```

Some runners reject existing or nonempty output directories. Select unused
paths before repeating a command. Keep checked-in results, execution archives,
labels, and manifests intact. Compare generated assessments with the recorded
version rather than replacing that evidence.

## Historical dependency records

| Result family | Dependency record | Interpretation |
|---|---|---|
| Matched Qwen evaluation and follow-on Qwen comparisons | [Matched Colab requirements](../experiments/answerer_comparison/rq2_matched/requirements-colab.txt) | Pins the model-loading packages, including Transformers, Accelerate, and bitsandbytes. Torch/CUDA and precision settings belong to the recorded runtime. |
| Secondary retrieval micro-ablations | [Micro-ablation requirements](../experiments/micro_ablations/requirements.txt) | Pins NumPy 1.26.4, pandas 2.2.3, Sentence Transformers 3.1.1, and Torch 2.4.1. These are separate from the primary notebook evaluation. |
| Revision 4 and Revision 5 Gemini comparisons | [API requirements](../experiments/answerer_comparison/rq2_frontier_baseline/requirements-api.txt) | The Google GenAI dependency uses a version range. Consult each run's configuration and API log for the recorded serving identity and execution provenance. |
| Natural-question v2 evaluation | [Natural-question Colab requirements](../experiments/external_validity/natural_questions_v2/requirements-colab.txt) | Pins its Torch, model, retrieval, and data packages. The completed notebook and prior failed attempt remain separate records. |
| Retrieval-constant sensitivity | [Constant-sensitivity Colab requirements](../experiments/retriever_ablation/constant_sensitivity/requirements-colab.txt) | Pins the registered sensitivity environment. Its execution notebook and captured retrieval data support the completed result. |
| Historical verifier notebook environment | [Full environment freeze](../src/compliancegpt/generator/verifier/requirements.lock.txt) | Records a broad Colab environment; it is not a portable project installation list. |

The historical verifier freeze contains
`google-colab @ file:///colabtools/dist/google_colab-1.0.0.tar.gz` and
runtime-specific packages such as `torch==2.9.0+cu126`. The local archive path
belongs to the recorded Colab image. Installing this entire freeze in an
ordinary CPU environment is not the offline setup described above. The freeze
remains unchanged as provenance.

Do not merge these requirement files into one environment. Their differing
NumPy, Torch, Transformers, and Sentence Transformers versions describe
different runs. A new package or model configuration needs a separate run
identity if it produces new experimental outputs.

## Source pins and notebook boundaries

Registered runners verify their source and input hashes. Reproduce a formal
run at the execution commit recorded in its manifest; a current-main checkout
may correctly fail that historical registration. Preserve the hash checks.
Current integration diagnostics test the revised source separately.

Useful completed-study entry points are:

| Study | Execution source | Evidence |
|---|---|---|
| Corrected PRESERVE replay | `17a76e14a2285c5070b8d8da3c7341e5772d303d` | [Eight stored-selector cases](../experiments/answerer_comparison/rq2_preserve_replay/README.md) |
| Profile-fill v2 | `2e269c3d93728fae9acca6eff47fb672902436f5` | [800 registered deterministic cases](../experiments/answerer_comparison/rq2_profile_fill_v2/README.md) |
| Natural-question v2 | `27c437a2176847b6ac82f86b3f1abbb3ba63c1ac` | [Completed model run and author post-run review](../experiments/external_validity/natural_questions_v2/README.md) |
| Retrieval-constant sensitivity | `a066453a317bba365db707b71745e49fee28811a` | [Seven conditions and their execution record](../experiments/retriever_ablation/constant_sensitivity/README.md) |

The [notebook audit](../NOTEBOOK_AUDIT.md) lists all 20 notebooks, their stored
execution counts, and the preserved failed authority check. Colab imports,
Drive mounts, and `/content/drive` paths describe the notebook environment;
they are not ordinary local paths. An execution count alone does not establish
that every registered experiment completed. Use the result manifest and the
completed execution record together.

Supply API and repository credentials through the notebook's documented
Secrets or interactive input path. Credential variable names are references,
not embedded values. The audit records no detected credential value under its
listed pattern checks; it does not claim exhaustive secret detection.

## GitHub Actions boundary

The existing [micro-ablation workflow](../.github/workflows/run-matched-micro-ablations.yml)
runs only through `workflow_dispatch`. It performs retrieval experiments and
uploads their artifacts. It is not an automatic push or pull-request check,
and it does not run the offline unit suite or language audit automatically.
This documentation update does not change the workflow.
