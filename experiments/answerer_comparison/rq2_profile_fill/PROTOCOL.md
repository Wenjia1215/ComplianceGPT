# Registered profile-resolution study v1

Result identity: `rq2_profile_fill_v1`.

This study addresses Dr. Sadjadi's original dissertation feedback, section 2.5:
evaluate synthetic profile filling on the 63 Revision 5 ODP rows. It uses all
100 frozen Revision 5 questions, comprising 63 author-labeled ODP-positive rows
and 37 author-negative controls. There is no new retrieval or model inference.
The existing author labels and historical ASK results are not changed.

## Input and execution boundary

Use the registered matched-window v3 archive, its exact prepared contexts and
selector outputs, and the pinned CCS/gold files. The current deterministic
pipeline is executed from evidence assembly through profile resolution and
runtime verification. Profiles affect the realization condition only; selector
outputs are frozen. The new versioned profile record preserves canonical spans,
identifies every configured value by its profile path and source IDs, and binds
the record to the supplied profile fingerprint and external corpus revision.
The caller supplies the profile and corpus; the contract cannot establish its
own approved values. Synthetic inputs do not demonstrate approval governance.

Before the formal study, publish the implementation, tests, this protocol,
`protocol.json`, and `registered_cases.jsonl` in Git. Registration includes all
case identities, profile inputs, source hashes, code hashes and acceptance rules.
Formal execution must validate the registration and use a clean checkout. The
result commit follows the registration commit. Do not overwrite frozen output.
Focused fixture tests and the earlier one-span defect diagnostic are preflight
checks, not the formal benchmark study.

## Eight fixed profile conditions

For each row, identify keyed placeholders in the canonical spans already present
in its frozen v3 contract. This is a transparent conditional mechanism study,
not a profile collected from a real organization or a test of model adaptation.

1. `empty`: a Rev.5 profile with no parameter values.
2. `complete`: a Rev.5 profile supplies every keyed placeholder visible in the
   frozen retained evidence using `synthetic::rev5::<parameter-id>` values.
3. `partial`: the complete profile with the last lexicographically sorted visible
   key omitted. A single-key case therefore receives no value; no-key cases are
   unchanged. Anonymous assignment markers are never filled.
4. `wrong_revision`: the same complete values declare Rev.4, including overlapping
   identifiers; no substitution is permitted.
5. `unknown_keys`: a Rev.5 profile supplies only a key absent from the retained
   evidence. It must not affect the answer.
6. `unversioned`: the complete values have no framework revision. They must not
   be substituted by the versioned profile path.
7. `placeholder_values`: every supplied value is itself an unresolved placeholder.
   None may be treated as a resolved value.
8. `literal_backslashes`: every visible key receives a literal backslash-bearing
   value, exercising substitution without regex replacement interpretation.

The formal matrix has 800 contracts: 504 on ODP-positive rows and 296 on the
author-negative controls. Every row/condition remains in the results. A full
keyed profile does not imply `OK` if an anonymous assignment remains unresolved.

## Oracle and measures

The condition-specific oracle starts with the independently retained v3 canonical
answer/spans and registered profile inputs. It predicts literal substitutions,
remaining keyed obligations and anonymous-assignment sentinel, and expected
status. It does not reuse the production resolution function or the newly
generated profile record. Compare exact answer text, required-key set, status,
canonical spans, selector hash, evidence-window identity and direct runtime verdict.
Verify every binding's source and profile provenance. Report per-condition counts
and split counts by author-label stratum; these are mechanism checks, not new
strict-pass accuracy estimates against the historical ASK labeling.

Test ten fixed mutations of complete-profile ODP-positive contracts: append
unsupported answer prose; forge an answer value and matching record value; remove
a binding; alter the corpus revision in the record; alter its profile hash; alter
a canonical span; substitute an unknown source ID; remove both profile record
and policy declaration; replace the external profile; and add an unknown binding.
Use externally selected FILL mode, corpus and revision for verification. Report
detection by operator and errors. Report positive controls alongside rejection
counts; no mutation outcome is filtered after execution.

## Legacy regressions and acceptance

Replay ASK on all 136 frozen Rev.4/Rev.5 rows with frozen selector outputs, checking
the core answer, spans, status, required list, citations, and original offline
outcomes. Replay the eight previously applicable corrected PRESERVE rows and
compare their core contracts to the frozen v1.1 replay. Preserve the existing
PRESERVE policy identity; the profile resolver/verifier has a separate version.

Acceptance requires all 800 case-oracle checks and runtime checks, unchanged
selectors/canonical evidence/windows, all 136 ASK and eight PRESERVE comparisons,
and detection of all ten registered mutation types. Persist failures and all
per-case outputs before declaring acceptance. Do not change the protocol after
outcomes; a revised implementation or study needs a new result identity.

## Interpretation limits

This evaluates deterministic profile realization and runtime checking on frozen
retained evidence. It does not validate the author gold labels, prove that the
selected evidence is complete, evaluate real organizational approvals or values,
or establish behavior with new retrieval/model outputs. Revision isolation is
conditional on the externally supplied revision and corpus. Parameter typing,
domain/cardinality validation, approval signatures, and profile lifecycle
governance remain future work. Anonymous assignments remain blocked.
