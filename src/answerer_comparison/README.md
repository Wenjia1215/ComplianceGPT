# Matched Answerer Utilities

`matched_window_runner.py` implements the shared evidence-window construction
and validation used by the corrected matched answerer evaluation.

The experiment holds the question, requested revision, ordered evidence
window, and loaded model instance fixed for each pair. The answer methods then
diverge:

- the generative baseline writes free-form answer content and citations;
- ComplianceGPT selects source IDs and uses deterministic citation-contract
  assembly.

Gold labels are excluded from context preparation and answer construction.
They enter only during offline scoring.

The canonical runner, environment record, execution instructions, manifests,
and validated results are under:

[`experiments/answerer_comparison/rq2_matched/`](../../experiments/answerer_comparison/rq2_matched/)

This module is not a standalone command-line entry point.
