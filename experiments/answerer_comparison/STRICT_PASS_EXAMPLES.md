# Three detailed strict-pass examples

The three examples below come from the original frozen Rev5 run results, with no changes to their answer bodies. Baseline is the Qwen2.5-7B 4-bit free-form path; Gemini is the archived Gemini 3.5 Flash path; ComplianceGPT uses the 4-bit selector configuration. For each question, all three paths receive the same context and ordered evidence window.

This document uses the [complete strict-pass criterion](../../src/answerer_comparison/README.md): `S = C AND W AND L AND U AND A AND F AND P`. Every condition must hold. The criterion does not assess the value-domain types requested by clarification questions. Accurate paraphrases can pass.

| Example | Question | ComplianceGPT | Gemini | Baseline |
| --- | --- | --- | --- | --- |
| 1 | Rev5 Q35: Non-organizational user authentication | Pass | Fail | Fail |
| 2 | Rev5 Q76: Security categorization and approval | Pass | Pass | Fail |
| 3 | Rev5 Q24: Configuration settings | Fail | Fail | Fail |

The gates cover contract and gold-reference conditions (C), source and window eligibility (W), and the complete parameter list and status (L). The body gates cover actual citation use (U), required content (A), claim faithfulness (F), and parameter meaning (P). "Not scored" means a contract condition has already failed, so the semantic gates need no further assessment. It does not mean that the condition passed.

## Example 1: ComplianceGPT passes; Gemini and Baseline fail

**Question: Rev5 Q35**

> How should organizations handle identification and authentication of non-organizational users accessing federal systems?

**Original gold-required citation:** `ia-8_gdn`.

**Canonical source text: `ia-8_smt`**

```text
Uniquely identify and authenticate non-organizational users or processes acting on behalf of non-organizational users.
```

**Canonical source text: `ia-8.2_gdn`**

```text
Acceptance of only NIST-compliant external authenticators applies to organizational systems that are accessible to the public (e.g., public-facing websites).
```

IA-8 requires identification and authentication of non-organizational users. IA-8(2) guidance limits the requirement to accept only NIST-compliant external authenticators to organizational systems accessible to the public. An answer may cite IA-8(2) as additional evidence, but any added claim must preserve this applicability condition.

### Original answers and contract fields for the three paths

**ComplianceGPT**

Status: `OK`. Declared parameters: empty set.

Returned citation IDs: `ia-8_smt`, `ia-8_gdn`.

```text
Uniquely identify and authenticate non-organizational users or processes acting on behalf of non-organizational users.

Non-organizational users include system users other than organizational users explicitly covered by [IA-2](#ia-2) . Non-organizational users are uniquely identified and authenticated for accesses other than those explicitly identified and documented in [AC-14](#ac-14) . Identification and authentication of non-organizational users accessing federal systems may be required to protect federal, proprietary, or privacy-related information (with exceptions noted for national security systems). Organizations consider many factors—including security, privacy, scalability, and practicality—when balancing the need to ensure ease of use for access to federal information and systems with the need to protect and adequately mitigate risk.
```

**Gemini**

Status: `OK`. Declared parameters: empty set.

Returned citation IDs: `ia-8_smt`, `ia-8_gdn`, `ia-8.2_smt`, `ia-8.2_gdn`.

```text
Organizations must uniquely identify and authenticate non-organizational users (or processes acting on their behalf) for accesses other than those explicitly identified and documented in AC-14. Identification and authentication of these users may be required to protect federal, proprietary, or privacy-related information. When balancing ease of use with risk mitigation, organizations must consider factors such as security, privacy, scalability, and practicality. Additionally, organizations must accept only external authenticators that are NIST-compliant (and compliant with SP 800-63B for public-facing systems) and document and maintain a list of these accepted external authenticators.
```

**Baseline**

Status: `OK`. Declared parameters: empty set.

Returned citation IDs: `ia-8_gdn`, `ia-8.2_gdn`, `ia-8.2_smt`, `ia-8.2_smt.a`, `ia-8.2_smt.b`.

```text
Non-organizational users should be uniquely identified and authenticated. This includes accepting only NIST-compliant external authenticators and maintaining a list of accepted external authenticators.
```

### Gate-by-gate assessment

| System | C | W | L | U | A | F | P | Final strict pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ComplianceGPT | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| Gemini | Pass | Pass | Pass | Pass | Pass | Fail | Pass | Fail |
| Baseline | Pass | Pass | Pass | Pass | Pass | Fail | Pass | Fail |

### Assessment rationale

**ComplianceGPT - Pass.** It returns `ia-8_smt` and the gold-required `ia-8_gdn`, with the complete canonical text of both records in its body. It expresses the base authentication obligation, the AC-14 exception, and the relevant security and privacy considerations. It does not add a claim that all non-organizational user authentication must accept only NIST-compliant external authenticators. It passes by answering the required scope and avoiding that distorted additional claim, rather than by adding the public-access qualifier.

**Gemini - Fail: F is not satisfied.** The body says `must accept only external authenticators that are NIST-compliant` and places `for public-facing systems` in the parenthetical explanation of SP 800-63B. The source attaches the public-access qualifier to the obligation to accept only NIST-compliant external authenticators. Moving the qualifier to a different compliance description changes the scope of the original requirement.

**Baseline - Fail: F is not satisfied.** `This includes accepting only NIST-compliant external authenticators` likewise extends the requirement to non-organizational user authentication without preserving the public-access qualifier.

**Both contract fields and body content must satisfy the requirements.** All three paths cover the gold-required citation, and their attached evidence spans can be verified against the source. Citation evidence and faithful body claims remain separate requirements. The failure concerns a distorted claim; citing an additional enhancement does not itself cause failure.

## Example 2: ComplianceGPT and Gemini pass; Baseline fails

**Question: Rev5 Q76**

> What steps are required to categorize a system and its information, and who must approve the decision?

**Original gold-required citations:** `ra-2_smt.a`, `ra-2_smt.b`, `ra-2_smt.c`.

**Canonical source text: `ra-2_smt.a`**

```text
Categorize the system and information it processes, stores, and transmits;
```

**Canonical source text: `ra-2_smt.b`**

```text
Document the security categorization results, including supporting rationale, in the security plan for the system; and
```

**Canonical source text: `ra-2_smt.c`**

```text
Verify that the authorizing official or authorizing official designated representative reviews and approves the security categorization decision.
```

RA-2 requires categorizing the system and the information it processes, stores, and transmits, then documenting the results and supporting rationale in the security plan. The authorizing official or designated representative must review and approve the decision. Here, `including supporting rationale` specifies required documentation content rather than an optional background example.

### Original answers and contract fields for the three paths

**ComplianceGPT**

Status: `OK`. Declared parameters: empty set.

Returned citation IDs: `ra-2_smt.a`, `ra-2_smt.b`, `ra-2_smt.c`.

```text
Categorize the system and information it processes, stores, and transmits;

Document the security categorization results, including supporting rationale, in the security plan for the system; and

Verify that the authorizing official or authorizing official designated representative reviews and approves the security categorization decision.
```

**Gemini**

Status: `OK`. Declared parameters: empty set.

Returned citation IDs: `ra-2_smt`, `ra-2_smt.a`, `ra-2_smt.b`, `ra-2_smt.c`.

```text
To categorize a system and its information, an organization must:
1. Categorize the system and the information it processes, stores, and transmits;
2. Document the security categorization results and supporting rationale in the security plan; and
3. Ensure that the authorizing official or authorizing official designated representative reviews and approves the categorization decision.
```

**Baseline**

Status: `OK`. Declared parameters: empty set.

Returned citation IDs: `ra-2_smt`, `ra-2_smt.a`, `ra-2_smt.b`, `ra-2_smt.c`.

```text
The system and information must first be categorized, then the results must be documented in the security plan, and finally, the authorizing official or their designated representative must review and approve the categorization decision.
```

### Gate-by-gate assessment

| System | C | W | L | U | A | F | P | Final strict pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ComplianceGPT | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| Gemini | Pass | Pass | Pass | Pass | Pass | Pass | Pass | Pass |
| Baseline | Pass | Pass | Pass | Pass | Fail | Pass | Pass | Fail |

### Assessment rationale

**ComplianceGPT - Pass.** It returns the three gold-required subclauses and preserves their text for categorization, documentation with supporting rationale, and review and approval by the authorizing official or designated representative.

**Gemini - Pass.** It organizes the answer in its own sentences and explicitly states `Document the security categorization results and supporting rationale in the security plan`. It preserves the objects of categorization, the required documentation content, and the approval responsibility. Both the parent clause and subclauses support content actually expressed in the body. U/A/F/P therefore pass even though the body is not a concatenation of canonical source text.

**Baseline - Fail: A is not satisfied.** It covers categorization, documentation of the results, and approval by the authorizing official, but says only `the results must be documented in the security plan`. It does not express the requirement to document the supporting rationale. It returns `ra-2_smt.b`, so C passes, but the body omits part of that subclause's required documentation content. U can pass because the source supports the expressed proposition about documenting results. A fails because a necessary component is missing.

**What this example shows:** Actual citation use does not by itself establish that the answer expresses all required content of the cited clause. Accurate paraphrases can pass, while a concise answer with every required citation ID can still omit a necessary obligation.

## Example 3: All three paths fail

**Question: Rev5 Q24**

> How should configuration settings be established, approved, and monitored?

**Original gold-required citations:** `cm-6_smt.a`, `cm-6_smt.b`, `cm-6_smt.c`, `cm-6_smt.d`.

**Canonical source text: `cm-6_smt`**

```text
a. Establish and document configuration settings for components employed within the system that reflect the most restrictive mode consistent with operational requirements using {{ insert: param, cm-06_odp.01 }}; b. Implement the configuration settings; c. Identify, document, and approve any deviations from established configuration settings for {{ insert: param, cm-06_odp.02 }} based on {{ insert: param, cm-06_odp.03 }} ; and d. Monitor and control changes to the configuration settings in accordance with organizational policies and procedures.
```

**Canonical source text: `cm-6_smt.b`**

```text
Implement the configuration settings;
```

The original gold labels require separate returned IDs for `cm-6_smt.a`, `.b`, `.c`, and `.d`. The three unbound parameters are `cm-06_odp.01`, `cm-06_odp.02`, and `cm-06_odp.03`; the original gold policy is `ASK`. The key obligations cover establishing and documenting settings, implementing them, approving deviations, and monitoring and controlling changes.

### Original answers and contract fields for the three paths

**ComplianceGPT**

Status: `PARAMS_REQUIRED`. Declared parameters: `cm-06_odp.01`, `cm-06_odp.02`, `cm-06_odp.03`.

Returned citation IDs: `cm-6_smt`, `cm-6_smt.a`, `cm-6_smt.c`, `cm-6_smt.d`.

```text
a. Establish and document configuration settings for components employed within the system that reflect the most restrictive mode consistent with operational requirements using {{ insert: param, cm-06_odp.01 }}; b. Implement the configuration settings; c. Identify, document, and approve any deviations from established configuration settings for {{ insert: param, cm-06_odp.02 }} based on {{ insert: param, cm-06_odp.03 }} ; and d. Monitor and control changes to the configuration settings in accordance with organizational policies and procedures.

Establish and document configuration settings for components employed within the system that reflect the most restrictive mode consistent with operational requirements using {{ insert: param, cm-06_odp.01 }};

Identify, document, and approve any deviations from established configuration settings for {{ insert: param, cm-06_odp.02 }} based on {{ insert: param, cm-06_odp.03 }} ; and

Monitor and control changes to the configuration settings in accordance with organizational policies and procedures.
```

**Gemini**

Status: `PARAMS_REQUIRED`. Declared parameters: `cm-06_odp.01`, `cm-06_odp.02`, `cm-06_odp.03`.

Returned citation IDs: `cm-6_smt`, `cm-6_smt.a`, `cm-6_smt.b`, `cm-6_smt.c`, `cm-6_smt.d`.

```text
Configuration settings should be established and documented for components to reflect the most restrictive mode consistent with operational requirements using an organization-defined security configuration checklist. Deviations from these settings for organization-defined system components must be identified, documented, and approved based on organization-defined operational requirements. Finally, changes to the settings must be monitored and controlled in accordance with organizational policies and procedures.
```

**Baseline**

Status: `OK`. Declared parameters: empty set.

Returned citation IDs: `cm-6_smt`, `cm-6_smt.a`, `cm-6_smt.c`, `cm-6_smt.d`.

```text
Configuration settings should be established and documented using the most restrictive mode consistent with operational requirements. Any deviations from these settings must be identified, documented, and approved based on organizational policies and procedures. Changes to configuration settings should be monitored and controlled according to organizational policies and procedures.
```

### Gate-by-gate assessment

| System | C | W | L | U | A | F | P | Final strict pass |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ComplianceGPT | Fail | Pass | Pass | Not scored | Not scored | Not scored | Not scored | Fail |
| Gemini | Pass | Pass | Pass | Fail | Fail | Pass | Pass | Fail |
| Baseline | Fail | Pass | Fail | Not scored | Not scored | Not scored | Not scored | Fail |

### Assessment rationale

**ComplianceGPT - Fail: C is not satisfied.** Its parent-clause body does contain `Implement the configuration settings;`, and its parameter list and PARAMS_REQUIRED status are correct. However, the returned IDs include only the parent clause and `.a`, `.c`, and `.d`, omitting the gold-required `cm-6_smt.b`. The rule requires coverage of every required ID, so the parent's text cannot compensate for the missing child-clause ID.

**Gemini - Fail: U and A are not satisfied.** It returns `.b` and passes C/W/L, but its body covers only establishing and documenting settings, approving deviations, and monitoring and controlling changes. It does not express the action of implementing the configuration settings. Thus, `.b` is listed but not actually used in the body, and the required implementation obligation is also absent. Placing the correct canonical text in evidence_spans cannot compensate for these omissions.

**Baseline - Fail: C and L are not satisfied.** It also omits `.b`. Its returned parent clause and other spans retain three unbound parameters, but the contract declares `OK` with an empty parameter set. This violates the ASK/status conditions and the requirement to include the complete parameter union. The semantic gates need no further scoring.

**Original error labels:**

ComplianceGPT:

```text
MissedDocIds:['cm-6_smt.b']
```

Baseline:

```text
OKButUnresolvedODPPlaceholders
GoldPolicyASKButStatusNotParamsRequired
MissedDocIds:['cm-6_smt.b']
```

**What this example shows:** All three paths face the same standard: retaining an obligation's canonical wording does not let ComplianceGPT bypass required citation IDs. Gemini cannot bypass the required-body-content condition by returning the correct ID.

## Verification sources

Original run-data snapshot: `72979835f1e05bae513468ca4074b4d43497da2c`. Final verdicts come from the [question-level results](rq2_frontier_baseline_rev5/results_v1/strict_pass_rows.csv); exact answer and source excerpts for semantic failures appear in the [review records](strict_pass_reviews.jsonl). These are retrospective review examples without independent expert adjudication. They do not support a claim that any model is universally superior to another.

| Question | Evidence-window SHA-256 shared by all three paths |
| --- | --- |
| Rev5 Q35 | `796f3610e39533a76159e28238c0b2363c843f352c7e1d73612e221a92a51c47` |
| Rev5 Q76 | `aa4d52c27844f35547a6a1b088a50be2703749fe29f22e41ebf7c08b8892b189` |
| Rev5 Q24 | `44e1f80b745b47a0c29523c9ba224f7ff9e7d42fa9a779ba1958d0884f41fe3c` |

Original contract files:

- [ComplianceGPT](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/references/rev5_compliancegpt_4bit.csv)
- [Gemini](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/contracts/rev5_generative_frontier_api.csv)
- [Baseline](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/references/rev5_generative_baseline_4bit.csv)
- [Rev5 gold](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv)
- [Rev5 canonical clause store](https://github.com/Wenjia1215/ComplianceGPT/blob/72979835f1e05bae513468ca4074b4d43497da2c/data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl)
