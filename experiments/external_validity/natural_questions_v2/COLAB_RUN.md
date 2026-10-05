# Run the reviewed natural-question experiment

1. Open `Batch_Natural_Questions_v2.ipynb` in Colab and select A100 GPU.
2. Run all cells. The launcher checks out exact registration commit `71a9a187d0a3fe0d64d71cdefbacdb345cce890d`, checks its public registration before loading models, creates an isolated Python 3.12.14 environment, installs pinned packages and runs 39 offline checks before study inference. It preserves the frozen dependency versions even if the Colab notebook kernel uses Python 3.13.
3. Keep the Drive checkpoints and logs if a cell fails. Launcher logs are retained in the sibling `natural_questions_v2_launcher_logs` directory; experiment checkpoints remain in `natural_questions_v2`. The next attempt must match the registered source and recorded runtime; do not replace questions, labels or outputs.
4. Return `natural_questions_v2_results.zip` and download the fully executed notebook from **File → Download → Download .ipynb**. Preserve every cell output. The executed notebook will be archived in GitHub alongside the result audit.

This launcher is supplied unexecuted. No GPU results are included. Its result package preserves 20 questions and 40 answer-path outputs, source registration, run identity, retrieval contexts, raw generation attempts, automatic outcomes and the blank post-run review form. Qualitative author review remains required. No independent professional correctness is claimed.

The existing optional-media import failure is checked before the study begins. The isolated environment does not inherit Colab's optional vision, audio or TensorFlow packages. PyTorch CUDA wheels are installed from the official index; the process records the actual GPU, CUDA and all package versions.

## Resume a session stopped by the launcher-log collision

The earlier launcher wrote `launcher_steps.jsonl` into the result directory before the runner created `run_config.json`. The frozen runner correctly rejects any unregistered CSV/JSONL there, so it stopped before retrieval and generation. This was a launcher layout error.

Replace only the experiment-running cell with the corresponding cell from the corrected notebook and run it in the existing prepared session. It verifies and moves the legacy launcher-event file into the separate log directory, updates both log paths, and invokes the same frozen runner. Existing result files and its compatibility guard are preserved. Do not remove result files or manufacture a run configuration. After success, continue with the audit and packaging cells; the full launcher log directory is included in the result ZIP. The source checkout remains `71a9a187d0a3fe0d64d71cdefbacdb345cce890d`.
