# Returned natural-question run and audit

**GPU generation and automatic scoring are complete. Technical identity/scoring audit passed. The separate author review of all 40 final outputs is pending. Independent expert correctness has not been validated.**

This is the separate exploratory external-input study of 20 naturally occurring questions requested in Dr. Sadjadi's September 21 feedback, section 2.4. It does not replace the 136-row benchmark or the 30-row intra-annotator retest. All questions, failed outputs, retries, and outside-scope cases are retained.

## Registered results

| Outcome | ComplianceGPT | Generative baseline |
|---|---:|---:|
| Runtime contract valid | 20/20 | 13/20 |
| All reference clause-ID groups covered | 6/15 | 2/15 |
| All reference groups with complete canonical text | 6/15 | 2/15 |
| Strict contract on fully catalog-answerable questions | 0/3 | 0/3 |
| ODP sensitivity against author reference | 2/2 | 0/2 |
| ODP specificity against author reference | 1/13 | 13/13 |
| Total answer words | 4,739 | 473 |
| Total cited evidence spans | 59 | 34 |
| Total listed ODP keys | 34 | 3 |

The full machine summary includes raw denominators and Wilson 95% intervals. The strict paired test has zero discordant pairs and exact McNemar p = 1.0 on only three eligible questions. This establishes neither superiority nor equivalence. The sensitivity denominator contains only two positive cases. Baseline specificity includes abstentions and errors: it is not an answer-success rate.

The pre-inference author reference classifies three questions as full, 12 as partial and five as outside scope. ODP labels are two required, 13 not required and five not applicable. ComplianceGPT triggers PARAMS_REQUIRED on 12 of the 13 negatives. Additional listed keys remain unadjudicated expansions, distinct from this registered status-based specificity result. Answer length and key counts describe output burden, not measured user effort.

## Execution and retention

The original scientific registration was published at `71a9a187d0a3fe0d64d71cdefbacdb345cce890d`. An interrupted attempt captured five revision-4 retrieval contexts before generation. The explicitly documented authority-check repair was published at `27c437a2176847b6ac82f86b3f1abbb3ba63c1ac`. The repaired registration and scientific inputs were fixed before answer generation. The repair followed the first five retrieval captures; do not describe the repaired executable as frozen before all retrieval. Their repeated contexts are byte-identical, and the original attempt is preserved in the ZIP.

The returned executed notebook is archived unchanged. Its initial setup cells belong to the earlier launcher; the main execution cell downloads the pinned repaired launcher and updates execution identity/output settings. Captured output records the repaired source commit. Do not use the earlier setup cell alone as the run identity.

Actual study runtime: Python 3.12.14, PyTorch 2.6.0+cu124, Transformers 4.51.3, CUDA 12.4, NVIDIA A100-SXM4-40GB. The notebook kernel is a different Python installation. Qwen2.5-7B-Instruct model/tokenizer revision is `a09a35458c702b33eeacc393d103063234e8bc28`; E5 and BGE pins are in the protocol. Frozen executed code explicitly loads BF16 without quantization and checks actual CUDA placement and floating-point dtypes before inference. Model file hashes are archived; the ZIP contains no model weight files.

Both paths use the same original question, locked canonical evidence window and shared loaded answerer. Production S7 retrieval uses top 12 controls without query rewrites; the adaptive window has at most 24 records. Decoding is greedy, one beam and repetition penalty 1.05. The frozen selector budget is 512 new tokens; the baseline budget is 640. Prompts, schemas, budgets, retries and answer construction differ. This compares complete answer paths and does not isolate an architectural component.

There are 40 final outputs and 44 raw generation calls: 20 selector calls and 24 baseline calls. NQ04 and NQ11 each exhausted three baseline attempts. The model invocations succeeded but their emitted status strings were unquoted, invalid JSON, leaving final ERROR outputs. Every attempt is preserved. Input lengths are 604–3,723 tokens and generated continuations are 34–303 tokens. No continuation reaches its registered generation limit.

## What the source-level audit found

- Shared-window omissions explain important limitations: NQ12 loses retrieved SC-10; NQ17 loses retrieved CA-2; NQ18 loses retrieved AC-10; NQ20 loses retrieved AC-11. These observations concern this captured execution, not a new ablation or causal estimate. Other required groups are already absent upstream, including boundary/external-service groups in NQ07, AU-3/AU-12 in NQ09, and AU-11/tailoring rationale in NQ16.
- ComplianceGPT's valid contracts reproduce canonical text, but do not consistently interpret the whole question or explain scope boundaries. The outside-scope cases receive generic catalog text. Runtime validity is not semantic correctness.
- Actual clarification wording has catalog/type mismatches beyond the two input limitations documented before inference. Examples include roles asked for as durations, event types asked for as organizational units, and privileged-account personnel/roles asked for as a frequency. The frozen registry remains unchanged. [CLARIFICATION_AUDIT.json](CLARIFICATION_AUDIT.json) records each affected returned prompt and canonical definition. These are post-run explanatory observations, not a new registered metric.
- Frozen group coverage is ID-specific. NQ14 cites the full SI-2 parent statement, which contains the required SI-2a/SI-2d text, but does not cite those separate child IDs. Its group-score failure must not be described as absence of all substantive SI-2 content. The score is retained exactly as registered.
- Baseline prose sometimes introduces unsupported implementation or authority claims despite valid formatting. NQ12's suggested time norms and broad government-definition claim are not established by its cited clauses. The author must assess these claims in the separate review.

[CONTENT_AUDIT.csv](CONTENT_AUDIT.csv) gives all 40 source-linked observations. They are not completed author ratings. [RETRIEVAL_DIAGNOSTICS.json](RETRIEVAL_DIAGNOSTICS.json) distinguishes upstream, window and final cited-ID omissions, including parent-clause textual overlap.

## Files and verification

- [Batch_Natural_Questions_v2_executed.ipynb](Batch_Natural_Questions_v2_executed.ipynb): exact uploaded executed notebook, including outputs.
- [natural_questions_v2_results.zip](natural_questions_v2_results.zip): exact uploaded ZIP containing all contexts, contracts, raw generation calls, runtime manifests, source snapshot, console/launcher logs, earlier attempt, scoring outputs and complete internal hash manifest.
- [summary.json](summary.json), [per_question_outcomes.jsonl](per_question_outcomes.jsonl): exact registered automatic scoring outputs, extracted for inspection.
- [TECHNICAL_AUDIT.json](TECHNICAL_AUDIT.json): 63 internal archive files verified, registered identities and pairing verified, and four scoring outputs replayed byte-for-byte in a separate copy. No model inference was performed during this audit.
- [post_run_semantic_review.csv](post_run_semantic_review.csv): original blank 40-row author review template. No author or expert judgments have been fabricated.
- [ARTIFACTS_SHA256.json](ARTIFACTS_SHA256.json): checksums of the published result files.

To replay the audit, extract the ZIP into a new directory and use the pinned dependencies/import environment:

```bash
PYTHONPATH=src:. USE_TORCH=1 USE_TF=0 USE_FLAX=0 python experiments/external_validity/natural_questions_v2/audit_returned_run.py \
  --results-dir /path/to/extracted_results \
  --notebook experiments/external_validity/natural_questions_v2/results_v1/Batch_Natural_Questions_v2_executed.ipynb \
  --replay-dir /path/to/new_scoring_replay \
  --report /path/to/technical_audit.json
```

## Remaining author review and dissertation integration

Record `scope_appropriate`, `responsive_to_entire_question`, `unsupported_implementation_or_legal_claim`, reviewer name and relevant notes for each of the 40 question/system pairs. Preserve uncertainties. A positive unsupported-claim judgment flags a problem. These ratings concern the whole question and actual clarification wording; a format pass or verbatim source span cannot substitute for them. Formal completion remains pending until this review is documented.

In the dissertation, explain the purposive one-forum collection and author source/label verification, keep these 20 rows separate, report the adverse outcomes as well as the useful mechanism behavior, and state the small denominators and lack of independent correctness validation. Do not pool or substitute these strict outcomes for historical headline metrics. Dr. Sadjadi's later instruction also remains a writing requirement: the intra-annotator test–retest study bounds the author's labeling consistency, not independent correctness; name an independent expert study as future work. Preserve the Gemini 65-versus-66, p = 1.0 tie framing wherever that comparison appears, including the abstract. It is a different comparison from this study's 0/3-versus-0/3 result.
