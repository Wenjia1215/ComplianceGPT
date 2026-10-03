# RQ2 PRESERVE Replay — Pre-commitment

Registered at **2026-10-03T22:05:20Z**, before any formal replay contract was
generated or inspected.

Machine-readable registration: [`precommitment.json`](precommitment.json)

## Question and result identity

This study tests whether the corrected runtime `PRESERVE` path keeps unresolved
ODP placeholders literal while returning the blocking status
`PARAMS_REQUIRED`. The registered result identity is
`rq2_preserve_replay_v1`.

The version bump is deliberately narrow: `PRESERVE` policy artifact `v1.1`,
identified in source as `2026-10-03-preserve-status-v1.1`. It is not a claim
that the entire repository is a packaged v1.1 software release.

The defective frozen runtime is commit
`be862bcadfa61b474d795303e01ce9394909fdcc`. In that version, the branch kept
visible placeholders but returned `OK`. The original matched RQ2 runs used
`ASK`, so this replay does not replace or silently rewrite those reported
outputs.

## Sample and completion rule

The sample is every frozen gold row whose registered `resolution_policy` is
`PRESERVE`; there are no discretionary exclusions:

| Revision | Query IDs | Rows |
|---|---|---:|
| Rev. 5 | 1, 11, 20, 30, 69, 93 | 6 |
| Rev. 4 | 21, 30 | 2 |
| Total | — | 8 |

All eight rows must complete. There is no outcome-based stopping, row removal,
manual contract editing, relabeling, or substitution.

## Frozen replay design

The run reuses the immutable prepared contexts and exact selector outputs from
the validated matched-window v3 archive. For each applicable row, it executes
the corrected current pipeline from evidence filling through ODP policy,
canonicalization, citation-contract construction, Runtime Verifier, and the
offline verifier.

- Live retrieval: forbidden.
- New model inference: forbidden.
- Selector output: exact stored `debug.selector_raw` value.
- Resolution policy: fixed globally to `PRESERVE`.
- Organization profile: empty.
- Evidence window: exact frozen ordered window; its hash must match.
- Gold labels: used only to identify the registered sample and after
  construction by the offline verifier.

This is a frozen-selector, prepared-context end-to-end replay of the corrected
deterministic path. It is not a new retrieval or stochastic model experiment.

## Frozen inputs

Matched-window v3 archive SHA-256:
`56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328`.

| Input | SHA-256 |
|---|---|
| Rev. 5 prepared contexts | `b47e58c17ce6d0aca1d8519941f52c3c21e393d9187fcf113de7bfec68cfc473` |
| Rev. 4 prepared contexts | `4f1ca834993a34c22bb4b61fa9a984d32382b5e84e3473656a22af688412d7a6` |
| Rev. 5 frozen ComplianceGPT contracts | `9440fd02c25e30b4b3fe39890fadb3ec3e120dfd8af9e82ea23fab6f87167cc9` |
| Rev. 4 frozen ComplianceGPT contracts | `cb8d49cdff4b1ebcd68f0010b4fbecafd457352cb9e963856b03ef1a0aae50f9` |
| Rev. 5 gold set | `f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5` |
| Rev. 4 gold set | `80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2` |
| Rev. 5 CCS | `71057ba79c54b8c1f0d171198a6ccb60b4c8818acbd2062e7f7c74ee11242e08` |
| Rev. 4 CCS | `500bb5d1f265080752710c2f0ae84b8044b67a1e2118cd5e166353b6fc3ab726` |

The registered code-manifest SHA-256 is
`255c1576fe83a85796ee17795a106813698b0c2a7c4a2c7b91f758804b5ff31e`.

## Registered acceptance rules

The replay passes only if all of the following are true:

1. Exactly eight registered rows complete: six Rev. 5 and two Rev. 4.
2. Every row actually contains at least one visible unresolved ODP marker.
3. Every such row returns `PARAMS_REQUIRED`; no visible-marker row returns
   `OK`.
4. Every row retains the literal placeholder text found in its final evidence
   spans and emits a nonempty `odp_required_list`.
5. Every row has an empty `ask_list`, because `PRESERVE` retains rather than
   interactively asks for the values.
6. Every contract passes the gold-independent Runtime Verifier.
7. Every exact selector output is unchanged from matched-window v3.
8. Every final source identifier remains in that row's frozen evidence window.

The offline strict-verifier result will be reported for all eight rows but is
not the acceptance endpoint: it additionally measures author-labeled content
coverage, whereas this study's registered endpoint is the corrected runtime
state transition and contract consistency.

## Deviations and failures

If the formal run fails, the partial output and failure will be preserved. A
code, input, sample, or acceptance-rule change after formal outputs exist
requires a documented deviation and a new result identity; the existing
result will not be overwritten.
