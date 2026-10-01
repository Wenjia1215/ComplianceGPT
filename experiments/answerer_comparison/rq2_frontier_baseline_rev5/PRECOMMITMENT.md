# Batch 5D — Revision 5 Frontier API Baseline Pre-commitment

Registered at **2026-10-01T19:36:19Z** (**2026-10-01 15:36:19 EDT**), before any
Revision 5 Gemini API response was generated or inspected.

Machine-readable registration: [`precommitment.json`](precommitment.json)

## Commitment

This study will run Gemini 3.5 Flash on all 100 frozen NIST SP 800-53 Revision 5
questions and their immutable ordered evidence windows. The complete result will
be reported whether it supports, weakens, eliminates, or reverses the current
comparison with ComplianceGPT. No row will be removed, relabeled, substituted,
or selectively reported after model outputs are observed.

The study evaluates a hosted frontier free-form answerer against the already
frozen ComplianceGPT outputs. It does not replace ComplianceGPT's selector with
Gemini and does not claim a controlled one-factor model comparison. The matched
experimental factors are the questions, model-visible evidence windows,
free-form prompt and parser, ODP policy, and offline verifier. The answer model
and serving runtime differ by design.

## Registered result identity and completion rule

- Result identity: `rq2_frontier_baseline_rev5_v1`.
- Framework: NIST SP 800-53 Revision 5.
- Sample: all 100 frozen Revision 5 rows; no post-output exclusions.
- Completion rule: all 100 rows must have validated, checkpointed contracts.
- Stopping rule: no early stopping based on interim outcomes.
- Comparison system: the 100 frozen ComplianceGPT contracts in the validated
  RQ2 matched-window v3 archive.
- Stronger model: `gemini-3.5-flash` through the Google Gemini Developer API,
  using Paid Tier 1.
- No Gemini Pro comparison is registered.

## Frozen inputs

The validated archive is
`experiments/answerer_comparison/rq2_matched/results_v3/compliancegpt_rq2_matched_v3.zip`
with SHA-256
`56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328`.

| Input | SHA-256 |
|---|---|
| Revision 5 prepared contexts | `b47e58c17ce6d0aca1d8519941f52c3c21e393d9187fcf113de7bfec68cfc473` |
| Revision 5 frozen ComplianceGPT contracts | `9440fd02c25e30b4b3fe39890fadb3ec3e120dfd8af9e82ea23fab6f87167cc9` |
| Revision 5 frozen Qwen generative contracts | `85a3e52b75b283a3fda6c50ae59d8dde4e59748ada7d58c5b88ae8c5c8f2cb63` |
| Revision 5 gold set | `f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5` |
| Revision 5 canonical clause store | `71057ba79c54b8c1f0d171198a6ccb60b4c8818acbd2062e7f7c74ee11242e08` |
| Revision 5 ODP registry | `3cd31393ed97df6292a45b749bca5359c802397d68ee6dcb41081b075fd32545` |

Gold labels remain excluded from every API request and are used only for the
offline evaluation after answer construction.

## Frozen model call and answer protocol

The Revision 5 run will inherit the exact free-form system prompt, context
serialization, user prompt, JSON extraction, fail-closed normalization, ASK
policy, and maximum of two parse retries used for Batch 5C. The registered
prompt SHA-256 is
`91ba0d840befd5517fbec7595f640333bcb8df8e63301e80552dad841744fdef`.

The API configuration is fixed as follows:

| Field | Registered value |
|---|---|
| Provider/API | Google Gemini Developer API `generateContent` |
| Model | `gemini-3.5-flash` stable model ID |
| Thinking level | `LOW` |
| Temperature | `1.0` |
| Maximum output tokens | `2048` |
| Maximum parse retries | `2` |
| SDK retry attempts | `5` |
| SDK timeout | `180` seconds |
| Tools | disabled |
| API-enforced structured output | disabled |
| Retrieval | none; frozen contexts only |

Every response ID, raw output, server-reported model version, latency, token
usage, parse retry, and orphaned call will be retained. A server-reported model
version change within the output directory will stop the run. Completed rows
will be validated and skipped after a resumable restart.

## Registered analyses

### Primary endpoint

The primary endpoint is the existing offline strict pass on each of the 100
paired rows. Strict pass requires full expected-clause coverage,
source/revision/verbatim validity, and ODP/status consistency; extra evidence is
permitted. Gemini and the frozen ComplianceGPT contracts will be compared with
a **two-sided exact McNemar test**. The report will include both marginal
counts/rates, both discordant counts, and the exact p-value. A nonsignificant
result will be described as statistically indistinguishable, without using the
point estimate as evidence of direction.

### Registered secondary endpoints

All secondary endpoints will be reported regardless of direction:

1. Full expected-clause coverage count and rate.
2. Coverage-complete strict failures and realization loss, defined as
   `coverage-complete but strict-failing rows / coverage-complete rows`.
3. Runtime structural contract pass count and rate.
4. Mean gold-clause precision, recall, selected-clause count, and answer word
   count.
5. ODP status sensitivity, specificity, and precision, reported together,
   using author labels; exact ODP-set agreement will also be reported.
6. Two-sided Fisher's exact test for the registered realization-loss table,
   alongside its descriptive counts and denominators.
7. Ninety-five-percent Wilson intervals for reported binomial rates.

ODP results based on author labels will be identified as such and will not be
presented as independently adjudicated. The sensitivity result will never be
reported without specificity and the corresponding false-positive burden.

## Deviations, failures, and corrections

Rate-limit interruptions may wait and resume without changing the protocol.
Provider or authentication failures will be retained as operational logs and
will not be converted into scored scientific rows.

If a genuine implementation defect is discovered, the original outputs and
logs will be preserved, the defect and correction will be documented, and all
affected rows will be rerun under one uniform correction. Any change to an
input, model, prompt, parser, generation setting, metric definition, exclusion
rule, or hypothesis after registration requires a clearly labeled protocol
deviation and, when scientifically material, a new result identity. Results
will not be edited manually.

## Interpretation boundary

The strict-pass comparison tests agreement with the implemented author-labeled
rules on this frozen benchmark; it does not establish legal sufficiency or
auditor approval. The primary dissertation claim does not depend on proving
higher strict-pass accuracy. The registered mechanistic comparison concerns
realization loss and the difference between empirically observed free-form
behavior and contract-enforced, runtime-verifiable behavior.
