# Evaluation Configuration Boundaries

The dissertation reports three S7-related configurations. They are separate
result families and must not be treated as one interchangeable execution.

| Mechanism | Primary RQ1 | Matched answerer | Secondary diagnostic |
|---|---|---|---|
| Execution basis | Recorded S1-S7 ablation notebook execution | Frozen matched-run trace; no live retrieval during answer construction | Checked S7 source and diagnostic runner |
| Query variants | Original question plus accepted precomputed rewrites | Raw question variants inherited from the frozen trace | Transformed question plus transformed accepted rewrites |
| Instruction stripping and scope expansion | Absent | Absent | Present |
| Privilege-scope score adjustment | Absent | Absent | Present: `+0.08/-0.06` of peak fused score |
| Conditional cross-encoder reranking | Present; skip margin `0.10` | Decision already materialized in the trace | Present; skip margin `0.10` |
| Changed-top adoption gate | Fixed margin `0.15` | Trace reflects `0.15`, reduced to `0.10` under low base confidence | `0.15`, reduced to `0.10` when base margin is below `0.08` |
| Clause-pool role | Constructed after control ranking; RQ1 scores the control rank | Frozen clause pool feeds the shared window builder | Constructed after control ranking; diagnostic scores the control rank |
| Control gate and 24-record selector window | Outside the RQ1 scoring boundary | Applied once and shared by both answer paths | Outside the diagnostic scoring boundary |
| Dissertation result family | Main S1-S7 and ErrorBank tables | RQ2, RQ3, no-selector, rescue, mutation, provenance, and retention analyses | Gold-informed S4b/S7a rewrite diagnostic |

## Interpretation rules

- The primary RQ1 numbers belong to the recorded notebook execution.
- The matched answerer evaluation consumes frozen retrieval traces and does not
  rerun retrieval while constructing either answer path.
- The secondary diagnostic tests the checked query-transformation and
  privilege-scope mechanisms and is not a replacement for the primary RQ1
  table.
- Constants and their provenance classifications are listed in
  [`CONSTANTS_PROVENANCE.md`](CONSTANTS_PROVENANCE.md).
- A changed mechanism or constant requires a new configuration identity and
  new outputs; frozen results are never overwritten.

## Registered follow-on sensitivity study

`rq2_control_gate_width_v1` is a separate follow-on result identity. It reuses
the immutable matched-answerer retrieval traces and sweeps fixed top-1, top-2,
top-3, and top-5 control-gate widths while preserving the 24-record window and
the pinned selector configuration. Its completed end-to-end result is archived
under `experiments/answerer_comparison/rq2_control_gate_width/results_v1/`;
the deterministic prepared-context audit remains a distinct opportunity
analysis rather than an end-to-end result. The released adaptive gate remains
the unchanged reference rather than being relabeled as one of the fixed-width
conditions.

`rq2_bf16_baseline_v1` is a second separate follow-on identity. It uses only
the 36 immutable Rev. 4 RQ2 v3 contexts and reruns the free-form generative
baseline with the same Qwen2.5-7B model revision, prompts, deterministic
decoding, ODP policy, and verifier. Its sole changed factor is model-weight
precision (`4-bit` to `torch.bfloat16`). The frozen 4-bit baseline and
ComplianceGPT contracts remain unchanged paired references. This study tests
quantization sensitivity within one model; it is not a frontier-model
baseline and must not be merged into the original RQ2 v3 result family. Its
complete supplied A100 evidence package and audit record are archived under
`experiments/answerer_comparison/rq2_bf16_baseline/results_v1/`. BF16 left the
baseline's strict-pass count unchanged at 8/36, so the result does not support
4-bit quantization as the explanation for the 29/36 ComplianceGPT result.
