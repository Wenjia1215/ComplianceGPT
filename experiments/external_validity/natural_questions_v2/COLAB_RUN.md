# Run the reviewed natural-question experiment

1. Open `Batch_Natural_Questions_v2.ipynb` in Colab and select A100 GPU.
2. Run all cells. The launcher checks out repaired registration commit `27c437a2176847b6ac82f86b3f1abbb3ba63c1ac`, checks its public registration before loading models, creates an isolated Python 3.12.14 environment, installs pinned packages and runs 53 offline checks before study inference. It preserves the frozen dependency versions even if the Colab notebook kernel uses Python 3.13.
3. Keep the Drive checkpoints and logs if a cell fails. Launcher logs are retained in the sibling `natural_questions_v2_authority_fix_launcher_logs` directory; repaired experiment checkpoints are in `natural_questions_v2_authority_fix`. The original `natural_questions_v2` attempt and its logs remain preserved. The next attempt must match the registered source and recorded runtime; do not replace questions, labels or outputs.
4. Return the result ZIP and download the fully executed notebook from **File → Download → Download .ipynb**. Preserve every cell output. The executed notebook will be archived in GitHub alongside the result audit.

This launcher is supplied unexecuted. No GPU results are included. Its result package preserves 20 questions and 40 answer-path outputs, source registration, run identity, retrieval contexts, raw generation attempts, automatic outcomes and the blank post-run review form. Qualitative author review remains required. No independent professional correctness is claimed.

The existing optional-media import failure is checked before the study begins. The isolated environment does not inherit Colab's optional vision, audio or TensorFlow packages. PyTorch CUDA wheels are installed from the official index; the process records the actual GPU, CUDA and all package versions.

## Resume a session stopped by the launcher-log collision

The earlier launcher wrote `launcher_steps.jsonl` into the result directory before the runner created `run_config.json`. The frozen runner correctly rejects any unregistered CSV/JSONL there, so it stopped before retrieval and generation. This was a launcher layout error.

Replace only the experiment-running cell with the corresponding cell from the corrected notebook and run it in the existing prepared session. It verifies and moves legacy launcher events into the separate log directory. Existing result files and the runner's compatibility guard are preserved. Do not remove result files or manufacture a run configuration.

## Recover the canonical-control authority failure

The original authority validator compared raw CCS control-ID strings with the retriever's existing normalized representation. It stopped after five revision-4 contexts, before loading the answerer. [EXECUTION_REPAIR.json](EXECUTION_REPAIR.json) records this code correction and the unchanged scientific inputs/settings. The repaired executable registration is public at `27c437a2176847b6ac82f86b3f1abbb3ba63c1ac`; it was recorded after the interrupted retrieval and before repaired execution or any answer generation.

In the existing prepared session, replace only the experiment-running cell with cell 6 (zero-based) from this corrected notebook. It checks the original registration and absence of generation artifacts, preserves the old results, checks out the clean repaired registration, runs public preflight and all 53 offline checks, and retrieves all 20 questions into a separate result directory. Dependencies and the mounted Drive remain usable. After success, continue with the audit and packaging cells; the package includes current logs and a byte-preserved copy of the earlier attempt and its logs. The new run configuration is created by the registered runner; the previous one is never edited.
