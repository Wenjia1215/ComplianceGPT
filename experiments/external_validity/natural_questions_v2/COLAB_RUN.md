# Run the reviewed natural-question experiment

1. Open `Batch_Natural_Questions_v2.ipynb` in Colab and select A100 GPU.
2. Run all cells. The launcher checks out exact registration commit `71a9a187d0a3fe0d64d71cdefbacdb345cce890d`, checks its public registration before loading models, installs pinned packages and runs 39 offline checks before study inference.
3. Keep the Drive checkpoints and console log if a cell fails. The next attempt must match the registered source and recorded runtime; do not replace questions, labels or outputs.
4. Return `natural_questions_v2_results.zip` and download the fully executed notebook from **File → Download → Download .ipynb**. Preserve every cell output. The executed notebook will be archived in GitHub alongside the result audit.

This launcher is supplied unexecuted. No GPU results are included. Its result package preserves 20 questions and 40 answer-path outputs, source registration, run identity, retrieval contexts, raw generation attempts, automatic outcomes and the blank post-run review form. Qualitative author review remains required. No independent professional correctness is claimed.

The existing optional-media import failure is checked before the study begins. PyTorch CUDA wheels are installed from the official index; the process records the actual GPU, CUDA and all package versions.
