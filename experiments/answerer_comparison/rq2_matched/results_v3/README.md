# RQ2 matched-window v3 results

Audit status: **PASS**

This directory records the validated result package for the corrected RQ2
matched-window experiment. The complete evidence package is
`compliancegpt_rq2_matched_v3.zip`.

## Provenance

- Runner commit: `be862bcadfa61b474d795303e01ce9394909fdcc`
- Model and tokenizer: `Qwen/Qwen2.5-7B-Instruct`
- Exact model and tokenizer revision:
  `a09a35458c702b33eeacc393d103063234e8bc28`
- Device: `NVIDIA A100-SXM4-40GB`
- Four-bit loading: enabled
- Resumed model-output rows: 0 for every run
- Archive SHA-256:
  `56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328`

The run reconstructed each prepared context from the frozen stored S7 trace.
It made no live retrieval call. One ordered evidence window was prepared per
question and supplied unchanged to both answer paths. Gold rows entered only
after answer construction, through the offline verifier.

## Validation

- 100 Revision 5 and 36 Revision 4 questions are present for each system.
- Prepared-context IDs and output IDs are unique and complete.
- Every context digest and every order-sensitive, text-sensitive window digest
  recomputes from the stored content.
- Paired validation reports zero context, evidence-window, model, and tokenizer
  mismatches.
- Every output span is canonical text from a source identifier in that
  question's locked window.
- Every baseline citation that survived the generator's locked-window check is
  preserved in the final contract, including enhancement citations.
- The raw-output audit found no window-valid baseline citation removed during
  normalization or final construction.
- The shipped paired summaries match an independent recomputation from the
  contract CSV files and gold rows.
- The recorded experiment-code hashes match the files at the runner commit.

## RQ2 results

| Revision | System | Questions | Offline strict pass | Rate |
|---|---|---:|---:|---:|
| Revision 5 | ComplianceGPT | 100 | 65 | 0.6500 |
| Revision 5 | Generative baseline | 100 | 25 | 0.2500 |
| Revision 4 | ComplianceGPT | 36 | 29 | 0.8056 |
| Revision 4 | Generative baseline | 36 | 8 | 0.2222 |

For Revision 5, the discordant counts are 42 ComplianceGPT-only passes and two
baseline-only passes. The two-sided exact McNemar value is
`1.1266365618212149e-10`. For Revision 4, the corresponding counts are 22 and
one, with `p = 5.7220458984375e-06`.

These values measure agreement with the implemented gold-based rules under the
fixed questions, evidence windows, model revision, and outputs. They do not
establish legal sufficiency, auditor approval, or complete semantic correctness.

## RQ3 no-profile results

| Revision | System | ODP rows | `PARAMS_REQUIRED` | `OK` | Exact ODP set |
|---|---|---:|---:|---:|---:|
| Revision 5 | ComplianceGPT | 63 | 63 | 0 | 55 |
| Revision 5 | Generative baseline | 63 | 0 | 61 | 21 |
| Revision 4 | ComplianceGPT | 19 | 19 | 0 | 12 |
| Revision 4 | Generative baseline | 19 | 0 | 19 | 6 |

`Exact ODP set` in the generated summaries means set equality only. The
dissertation's stricter ODP-list metric additionally requires
`PARAMS_REQUIRED`. Under that composite definition, ComplianceGPT scores
55/63 and 12/19, while the baseline scores 0/63 and 0/19. This distinction is
kept explicit in the dissertation tables.

The no-profile result supports visible refusal to declare completion when
organizational inputs remain unresolved. It does not inspect every generated
sentence for an invented value and does not evaluate profile filling.
