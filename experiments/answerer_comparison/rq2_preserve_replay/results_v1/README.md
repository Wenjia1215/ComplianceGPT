# RQ2 PRESERVE End-to-End Replay

Result identity: `rq2_preserve_replay_v1`  
PRESERVE policy artifact: `v1.1` (`2026-10-03-preserve-status-v1.1`)

The replay processed all eight gold rows whose registered resolution policy is
`PRESERVE`: six Revision 5 rows and two Revision 4 rows. It reused the frozen
prepared contexts and exact selector outputs from matched-window v3, then ran
the corrected deterministic pipeline through evidence filling, PRESERVE policy,
contract construction, Runtime Verifier, and offline verifier. It used no live
retrieval and no new model inference.

| Acceptance measure | Result |
|---|---:|
| Applicable rows completed | 8/8 |
| Rows with visible unresolved markers | 8/8 |
| Visible-marker rows returning `PARAMS_REQUIRED` | 8/8 |
| Rows preserving literal placeholder text | 8/8 |
| Rows with empty `ask_list` under PRESERVE | 8/8 |
| Runtime-valid contracts | 8/8 |
| Frozen selector outputs unchanged | 8/8 |
| Final identifiers contained in frozen windows | 8/8 |
| Offline strict-verifier passes | 5/8 |

Registered acceptance result: **PASS**.

## Interpretation boundary

This is a frozen-selector, prepared-context end-to-end replay of the corrected
deterministic PRESERVE path. It directly evaluates the branch that previously
retained placeholders while returning `OK`; it is not a new retrieval study or
a new stochastic model run. The original matched RQ2 and RQ3 results remain
unchanged because those reported runs used `ASK`.
