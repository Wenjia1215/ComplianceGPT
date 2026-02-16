# Unified Pipeline Entrypoints (Colab + Drive)

This repo provides three unified Colab notebooks under `src/compliancegpt/pipeline/`:

1. `ComplianceGPT_Run_Single_Unified.ipynb`
   - Runs one query (freeform or from the gold set by `id`).
   - Produces the Final Answer Contract (provably-extractive) and verifier summary.

2. `ComplianceGPT_Run_Batch_Unified.ipynb`
   - Runs the pipeline over the Rev5 (100Q) or Rev4 (36Q) gold set.
   - Optionally uses precomputed QUR rewrites from `data/qur_outputs/`.
   - Saves a CSV of full contracts to `experiments/pipeline_runs/` by default.

3. `ComplianceGPT_Pipeline_Acceptance_Tests_Unified.ipynb`
   - A small regression gate for contract schema and key status invariants.
   - Intended to be run after pipeline changes (not for every experiment).

## Recommended workflow

- Day-to-day development: run `ComplianceGPT_Run_Single_Unified.ipynb`.
- Experiments/evaluation: run `ComplianceGPT_Run_Batch_Unified.ipynb`.
- Regression before committing pipeline changes: run `ComplianceGPT_Pipeline_Acceptance_Tests_Unified.ipynb`.

## Assumptions

- Colab runtime already has required Python packages installed.
- Your repo is stored at: `/content/drive/MyDrive/ComplianceGPT_v2`
- CCS JSONL and gold sets are present in the paths defined in the notebooks.

### Pipeline
ODP Handling Objective (MVP)

The pipeline MUST be audit-safe with respect to Organization-Defined Parameters (ODPs):

1) No hallucinated parameter values.
   - If a required ODP value is not available, the pipeline MUST NOT fabricate it.
   - Instead, it MUST return status=PARAMS_REQUIRED and populate odp_required_list.

2) Policy-driven behavior (per question-level resolution_policy when available):
   - ASK: preserve the canonical placeholder in answer_text and request the parameter (via odp_required_list).
   - PRESERVE: preserve the placeholder verbatim (no filling) and still surface odp_required_list.
   - FILL_FROM_PROFILE: substitute values ONLY from org_profile, and only into answer_text (never into evidence spans).

3) Evidence integrity:
   - Evidence spans must remain verbatim excerpts from the CCS source text.
   - Parameter substitution MUST NOT alter evidence spans.

4) Version explicitness:
   - The pipeline accepts an explicit framework_version (rev4 vs rev5) to select the correct CCS catalog and parameter ID scheme.
   - This is acceptable for research evaluation and reproducibility.
