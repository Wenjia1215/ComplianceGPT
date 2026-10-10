# Retained failure of profile-resolution study v1

Registration commit: `de9e4612e37911c0eb295772dd25286ba19c9f2b`.
Protocol SHA-256: `d89b01098e7aa0514b415b41dd7f380d773bdf32e44b1978186fca879532ad9b`.

The first formal run failed its registered acceptance rules: 792 of 800 cases
satisfied every check. All 800 matched the four condition-oracle fields and
passed runtime verification. All 630 attempted mutations were rejected, and all
144 ASK/PRESERVE core-output comparisons passed. The eight failures were the
eight profile conditions for Rev.5 query 99, each failing `selector_unchanged`.
The original protocol and failed outputs remain unchanged.

The frozen archive's `debug.selector_raw` is the normalized selection contract
after deterministic fallback for Rev.5 queries 9 and 99. It is not the original
raw model output for those two rows. V1 passed that post-fallback contract back
through generator normalization. For query 99, this bypassed the actual fallback
and dropped its debug marker; its source was consequently attributed to the
selector. Query 9 happened to re-enter fallback after enhancement filtering.
Canonical evidence and answers did not change, but the v1 claim that every
historical selection trace was retained was not satisfied.

The separate `rq2_profile_fill_v2` study reconstructs the recorded empty-selection
state for these two rows and executes the pipeline's actual fallback. It cannot
recover the unretained original model text. It checks the stored post-fallback
selection contract, fallback flags/reasons and the runtime fallback origin, in
addition to the existing oracle, window, corpus and regression checks. The
production profile resolver and verifier are unchanged between studies. V2 uses
a new protocol and result identity, published before its formal execution.

The complete failed outputs, including all contracts and attempted mutations,
are in `results_v1/rq2_profile_fill_v1.zip`. Smaller audit files are also published
directly. `SHA256SUMS` describes the archive's extracted contents; its contract
and mutation entries need not be present separately in the Git checkout.
