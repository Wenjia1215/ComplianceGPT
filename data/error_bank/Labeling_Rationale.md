# Error Bank Labeling Rationale

This document explains *how each query was labeled* into one of three failure categories:

- **Terminology Mismatch** — the query and the gold clause refer to the same intent, but the query misses the *exact* clause anchors (e.g., asks for "requirements"/"components"/"steps" while the clause lists items without that keyword), or retrieval confuses a **base control vs an enhancement** (e.g., `AC-7` vs `AC-7.4`).
- **Generic Phrasing** — the query is dominated by a template (e.g., “What does X require…”) or lacks distinguishing keywords, so a keyword retriever (BM25) cannot strongly separate it from many nearby clauses.
- **Semantic Gap** — the query intent matches the gold control, but keyword overlap is not sufficient; the query requires *conceptual interpretation* (e.g., tailoring, policy-level meaning), so BM25 prefers a semantically-adjacent control.

### Current Error Bank Snapshot

- rows: 37 (rev5: 24 / rev4: 13)
- failure_category_counts: {'Terminology Mismatch': 22, 'Generic Phrasing': 13, 'Semantic Gap': 2}

## Decision Procedure (per query)

1. **Test for Terminology Mismatch**
2. **If not, test for Generic Phrasing**
3. **If neither explains the miss, classify as Semantic Gap**

Notes:
- **BM25 Rank** uses the Error Bank convention: `1` = correct at top-1; `2` = correct at rank-2; `0` = not found in the top-10 list.
- **Top-1 retrieved** is the highest-ranked BM25 result for that query.

---

## (Question ID: 2, REV5)

- **Question:** "What must an organization enforce regarding logical access to its information and systems?"
- **Gold Control ID:** `AC-3`
- **Gold Clause IDs:** `ac_3_smt`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SC-8`
- **Top-5 Retrieved List:** `SC-8`, `AC-3`, `PM-20`, `CM-5`, `AC-3.7`

**Gold Answer (from Gold Set):**

> Enforce approved authorizations for logical access to information and system resources in
> accordance with applicable access control policies. [NIST SP 800-53 Rev.5: AC-3]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query is conceptually about the gold control, but it does **not** include the most discriminative clause-specific anchors (often the *enumerated items* or precise action verbs), so BM25 drifts to a nearby control.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `SC-8` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query is close in intent but lacks the gold clause’s most discriminative lexical anchors.

---

## (Question ID: 4, REV5)

- **Question:** "How must a system be configured to handle consecutive invalid logon attempts?"
- **Gold Control ID:** `AC-7`
- **Gold Clause IDs:** `ac-7_smt.a
ac-7_smt.b`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `AC-7.4`
- **Top-5 Retrieved List:** `AC-7.4`, `AC-7`, `AC-7.2`, `AC-9.1`, `AC-9.2`

**Gold Answer (from Gold Set):**

> Enforce a limit of {{ insert: param, ac-7_odp_1 }} consecutive invalid logon attempts by a user
> during a {{ insert: param, ac-7_odp_2 }} ; and
> Automatically {{ insert: param, ac-7_odp_3 }} when the maximum number of unsuccessful attempts
> is exceeded. [NIST SP 800-53 Rev.5: AC-7]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - BM25 ranked an **enhancement or variant** (`AC-7.4`) above the **base control** (`AC-7`), which is a classic wording/granularity mismatch.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `AC-7.4` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** BM25 confuses the base control with an enhancement/variant (granularity mismatch).

---

## (Question ID: 10, REV5)

- **Question:** "What method does AT-3(3) specify for reinforcing objectives in role-based security training?"
- **Gold Control ID:** `AT-3.3`
- **Gold Clause IDs:** `at-3.3_gdn`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `AT-3`
- **Top-5 Retrieved List:** `AT-3`, `AT-3.3`, `AT-4`, `AC-3.7`, `AT-6`

**Gold Answer (from Gold Set):**

> Practical exercises for security include training for software developers that addresses
> simulated attacks that exploit common software vulnerabilities or spear or whale phishing
> attacks targeted at senior leaders or executives. Practical exercises for privacy include
> modules with quizzes on identifying and processing personally identifiable information in
> various scenarios or scenarios on conducting privacy impact assessments. [NIST SP 800-53 Rev.5:
> AT-3(3)]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - BM25 ranked an **enhancement or variant** (`AT-3`) above the **base control** (`AT-3(3)`), which is a classic wording/granularity mismatch.
   - The query uses anchor term(s) **`method`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `AT-3` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** BM25 confuses the base control with an enhancement/variant (granularity mismatch).

---

## (Question ID: 12, REV5)

- **Question:** "What information must each audit record contain to support after-the-fact investigation of security incidents?"
- **Gold Control ID:** `AU-3`
- **Gold Clause IDs:** `au-3_smt
au-3_smt.a
au-3_smt.b
au-3_smt.c
au-3_smt.d
au-3_smt.e
au-3_smt.f`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `AU-11`
- **Top-5 Retrieved List:** `AU-11`, `AU-7`, `AU-3`, `AU-6.1`, `CM-5.1`

**Gold Answer (from Gold Set):**

> Ensure that audit records contain information that establishes what type of event occurred;
> when the event occurred; where the event occurred; source of the event; outcome of the event;
> and identity of any individuals, subjects, or objects/entities associated with the event. [NIST
> SP 800-53 Rev.5: AU-3]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query is conceptually about the gold control, but it does **not** include the most discriminative clause-specific anchors (often the *enumerated items* or precise action verbs), so BM25 drifts to a nearby control.
   - Evidence in outputs: gold control appears at **rank #3**, while BM25 prefers `AU-11` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query is close in intent but lacks the gold clause’s most discriminative lexical anchors.

---

## (Question ID: 14, REV5)

- **Question:** "What is the required process for reviewing system audit records, and what actions should be taken based on the findings?"
- **Gold Control ID:** `AU-6`
- **Gold Clause IDs:** `au-6_smt.a
au-6_smt.b
au-6_smt.c`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `AU-3`
- **Top-5 Retrieved List:** `AU-3`, `AU-6`, `AU-5`, `CM-5.1`, `CM-13`

**Gold Answer (from Gold Set):**

> Review and analyze system audit records {{ insert: param, au-6_odp_1 }} for indications of {{
> insert: param, au-6_odp_2 }} and the potential impact of the inappropriate or unusual activity;
> Report findings to {{ insert: param, au-6_odp_3 }} ; and
> Adjust the level of audit record review, analysis, and reporting within the system when there
> is a change in risk based on law enforcement information, intelligence information, or other
> credible sources of information. [NIST SP 800-53 Rev.5: AU-6]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`process`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `AU-3` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 15, REV5)

- **Question:** "What are the requirements for generating and recording time stamps in audit records to ensure accuracy?"
- **Gold Control ID:** `AU-8`
- **Gold Clause IDs:** `au-8_smt.a`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `AU-12.1`
- **Top-5 Retrieved List:** `AU-12.1`, `AU-8`, `AU-3`, `AU-7`, `AU-11`

**Gold Answer (from Gold Set):**

> Use internal system clocks to generate time stamps for audit records; and record time stamps
> for audit records that include the local time offset as part of the time stamp. [NIST SP 800-53
> Rev.5: AU-8]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`requirements`, `requirement`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `AU-12.1` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 16, REV5)

- **Question:** "Describe the key steps of the formal control assessment process, from planning to reporting."
- **Gold Control ID:** `CA-2`
- **Gold Clause IDs:** `ca-2_smt.a
ca-2_smt.b
ca-2_smt.b.1
ca-2_smt.b.2
ca-2_smt.b.3
ca-2_smt.c
ca-2_smt.d
ca-2_smt.e
ca-2_smt.f`
- **BM25 Rank of Gold:** `0`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SC-38`
- **Top-5 Retrieved List:** `SC-38`, `SA-17.1`, `AU-6.1`, `RA-3`, `SA-17.3`

**Gold Answer (from Gold Set):**

> Select the appropriate assessor or assessment team for the type of assessment to be conducted;
> Develop a control assessment plan that describes the scope of the assessment including:
> Controls and control enhancements under assessment;
> Assessment procedures to be used to determine control effectiveness; and
> Assessment environment, assessment team, and assessment roles and responsibilities;
> Ensure the control assessment plan is reviewed and approved by the authorizing official, senior
> agency information security officer, or authorizing official designated representative prior to
> conducting the assessment;
> Assess the controls in the system and its environment of operation to determine the extent to
> which the controls are implemented correctly, operating as intended, and producing the desired
> outcome with respect to meeting established security and privacy requirements;
> Produce a control assessment report that document the results of the assessment; and
> Provide the results of the control assessment to {{ insert: param, ca-2_odp_2 }}. [NIST SP
> 800-53 Rev.5: CA-2]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`steps`, `step`, `process`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #0**, while BM25 prefers `SC-38` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 23, REV5)

- **Question:** "What should be analyzed before implementing a system change?"
- **Gold Control ID:** `CM-4`
- **Gold Clause IDs:** `cm-4_smt`
- **BM25 Rank of Gold:** `0`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SA-8.17`
- **Top-5 Retrieved List:** `SA-8.17`, `SI-19.6`, `CM-5.1`, `MA-6.1`, `PE-3`

**Gold Answer (from Gold Set):**

> Analyze changes to the system to determine potential security and privacy impacts prior to
> change implementation. [NIST SP 800-53 Rev.5: CM-4]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `0`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 24, REV5)

- **Question:** "How should configuration settings be established, approved, and monitored?"
- **Gold Control ID:** `CM-6`
- **Gold Clause IDs:** `cm-6_smt.a
cm-6_smt.b
cm-6_smt.c
cm-6_smt.d`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `CM-8.6`
- **Top-5 Retrieved List:** `CM-8.6`, `CM-6`, `SI-7.7`, `CM-9`, `CM-6.2`

**Gold Answer (from Gold Set):**

> Establish and document configuration settings for components employed in the system that
> reflect the most restrictive mode consistent with operational requirements using {{ insert:
> param, cm-6_odp_1 }}; implement the configuration settings; identify, document, and approve any
> deviations from established configuration settings for {{ insert: param, cm-6_odp_2 }} based on
> {{ insert: param, cm-6_odp_3 }} ; and monitor and control changes to the configuration settings
> in accordance with organizational policies and procedures. [NIST SP 800-53 Rev.5: CM-6]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (PASS)**
   - The query intent aligns with the gold control, but the mapping relies on **conceptual interpretation** rather than shared keywords alone.
   - Evidence in outputs: BM25 prefers a semantically-adjacent control (`CM-8.6`) even though the gold control is present at rank `2`.

#### Final Verdict: `Semantic Gap`

**Rationale:** The query requires conceptual interpretation beyond simple keyword overlap, so BM25 drifts to a semantically-adjacent control.

---

## (Question ID: 25, REV5)

- **Question:** "What are the requirements for developing, maintaining, and updating a system component inventory?"
- **Gold Control ID:** `CM-8`
- **Gold Clause IDs:** `cm-8_smt.a.1
cm-8_smt.a.2
cm-8_smt.a.3
cm-8_smt.a.4
cm-8_smt.a.5
cm-8_smt.b`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `PM-5`
- **Top-5 Retrieved List:** `PM-5`, `SA-17.9`, `CM-8`, `PM-5.1`, `CM-8.2`

**Gold Answer (from Gold Set):**

> Develop and document an inventory of system components that accurately reflects the system;
> includes all components within the system; does not include duplicate accounting of components
> or components assigned to any other system; is at the level of granularity deemed necessary for
> tracking and reporting; and includes the following information to achieve system component
> accountability: {{ insert: param, cm-8_odp_1 }} ; and review and update the system component
> inventory {{ insert: param, cm-8_odp_2 }}. [NIST SP 800-53 Rev.5: CM-8]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`requirements`, `requirement`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #3**, while BM25 prefers `PM-5` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 26, REV5)

- **Question:** "What are the key elements that must be included in a contingency plan, and how should it be reviewed, distributed, and updated?"
- **Gold Control ID:** `CP-2`
- **Gold Clause IDs:** `cp-2_smt.a
cp-2_smt.a.1
cp-2_smt.a.2
cp-2_smt.a.3
cp-2_smt.a.4
cp-2_smt.a.5
cp-2_smt.a.6
cp-2_smt.a.7
cp-2_smt.b
cp-2_smt.c
cp-2_smt.d
cp-2_smt.e
cp-2_smt.f
cp-2_smt.g
cp-2_smt.h`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `CP-4.1`
- **Top-5 Retrieved List:** `CP-4.1`, `CP-3`, `CP-2`, `CM-9`, `SA-8.17`

**Gold Answer (from Gold Set):**

> Develop a contingency plan for the system that identifies essential mission and business
> functions and associated contingency requirements; provides recovery objectives, restoration
> priorities, and metrics; addresses contingency roles, responsibilities, assigned individuals
> with contact information; addresses maintaining essential mission and business functions
> despite a system disruption, compromise, or failure; addresses eventual, full system
> restoration without deterioration of the controls originally planned and implemented; addresses
> the sharing of contingency information; and is reviewed and approved by {{ insert: param,
> cp-2_prm_1 }}; distribute copies of the contingency plan to {{ insert: param, cp-2_prm_2 }};
> coordinate contingency planning activities with incident handling activities; review the
> contingency plan for the system {{ insert: param, cp-2_odp_5 }};
> Update the contingency plan to address changes to the organization, system, or environment of
> operation and problems identified during contingency plan implementation, execution, or
> testing;
> Communicate contingency plan changes to {{ insert: param, cp-2_prm_4 }};
> Protect the contingency plan from unauthorized disclosure and modification. [NIST SP 800-53
> Rev.5: CP-2]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query is conceptually about the gold control, but it does **not** include the most discriminative clause-specific anchors (often the *enumerated items* or precise action verbs), so BM25 drifts to a nearby control.
   - Evidence in outputs: gold control appears at **rank #3**, while BM25 prefers `CP-4.1` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query is close in intent but lacks the gold clause’s most discriminative lexical anchors.

---

## (Question ID: 39, REV5)

- **Question:** "What information should organizations maintain and analyze when documenting and reviewing security incidents?"
- **Gold Control ID:** `IR-5`
- **Gold Clause IDs:** `ir-5_gdn`
- **BM25 Rank of Gold:** `4`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `IR-9.2`
- **Top-5 Retrieved List:** `IR-9.2`, `CM-4`, `SA-8.33`, `IR-5`, `IR-5.1`

**Gold Answer (from Gold Set):**

> Documenting incidents includes maintaining records about each incident, the status of the
> incident, and other pertinent information necessary for forensics as well as evaluating
> incident details, trends, and handling. Incident information can be obtained from a variety of
> sources, including network monitoring, incident reports, incident response teams, user
> complaints, supply chain partners, audit monitoring, physical access monitoring, and user and
> administrator reports. [IR-4](../raw/nist800-53/source/NIST.SP.800-53r5.pdf#page=179) provides information on the types of incidents that are
> appropriate for monitoring. [NIST SP 800-53 Rev.5: IR-5]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `4`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 44, REV5)

- **Question:** "What process should be established for authorizing maintenance personnel and ensuring appropriate escorting and access control during maintenance?"
- **Gold Control ID:** `MA-5`
- **Gold Clause IDs:** `ma-5_smt.a
ma-5_smt.b
ma-5_smt.c`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `MA-5.1`
- **Top-5 Retrieved List:** `MA-5.1`, `MA-6.2`, `MA-5`, `MA-5.3`, `MA-5.2`

**Gold Answer (from Gold Set):**

> Establish a process for maintenance personnel authorization and maintain a list of authorized
> maintenance organizations or personnel;
> Verify that non-escorted personnel performing maintenance on the system possess the required
> access authorizations; and
> Designate organizational personnel with required access authorizations and technical competence
> to supervise the maintenance activities of personnel who do not possess the required access
> authorizations. [NIST SP 800-53 Rev.5: MA-5]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `3`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 56, REV5)

- **Question:** "What is the guidance of control PL-2?"
- **Gold Control ID:** `PL-2`
- **Gold Clause IDs:** `pl-2_gdn`
- **BM25 Rank of Gold:** `7`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SI-12`
- **Top-5 Retrieved List:** `SI-12`, `PL-10`, `PL-11`, `PL-8.1`, `PL-8.2`

**Gold Answer (from Gold Set):**

> System security and privacy plans are scoped to the system and system components within the
> defined authorization boundary and contain an overview of the security and privacy requirements
> for the system and the controls selected to satisfy the requirements. The plans describe the
> intended application of each selected control in the context of the system with a sufficient
> level of detail to correctly implement the control and to subsequently assess the effectiveness
> of the control. The control documentation describes how system-specific and hybrid controls are
> implemented and the plans and expectations regarding the functionality of the system. System
> security and privacy plans can also be used in the design and development of systems in support
> of life cycle-based security and privacy engineering processes. System security and privacy
> plans are living documents that are updated and adapted throughout the system development life
> cycle (e.g., during capability determination, analysis of alternatives, requests for proposal,
> and design reviews). [Section 2.1](../raw/nist800-53/source/NIST.SP.800-53r5.pdf#page=34) describes the
> different types of requirements that are relevant to organizations during the system
> development life cycle and the relationship between requirements and controls.\n\nOrganizations
> may develop a single, integrated security and privacy plan or maintain separate plans. Security
> and privacy plans relate security and privacy requirements to a set of controls and control
> enhancements. The plans describe how the controls and control enhancements meet the security
> and privacy requirements but do not provide detailed, technical descriptions of the design or
> implementation of the controls and control enhancements. Security and privacy plans contain
> sufficient information (including specifications of control parameter values for selection and
> assignment operations explicitly or by reference) to enable a design and implementation that is
> unambiguously compliant with the intent of the plans and subsequent determinations of risk to
> organizational operations and assets, individuals, other organizations, and the Nation if the
> plan is implemented.\n\nSecurity and privacy plans need not be single documents. The plans can
> be a collection of various documents, including documents that already exist. Effective
> security and privacy plans make extensive use of references to policies, procedures, and
> additional documents, including design and implementation specifications where more detailed
> information can be obtained. The use of references helps reduce the documentation associated
> with security and privacy programs and maintains the security- and privacy-related information
> in other established management and operational areas, including enterprise architecture,
> system development life cycle, systems engineering, and acquisition. Security and privacy plans
> need not contain detailed contingency plan or incident response plan information but can
> instead provideÑexplicitly or by referenceÑsufficient information to define what needs to be
> accomplished by those plans.\n\nSecurity- and privacy-related activities that may require
> coordination and planning with other individuals or groups within the organization include
> assessments, audits, inspections, hardware and software maintenance, acquisition and supply
> chain risk management, patch management, and contingency plan testing. Planning and
> coordination include emergency and nonemergency (i.e., planned or non-urgent unplanned)
> situations. The process defined by organizations to plan and coordinate security- and privacy-
> related activities can also be included in other documents, as appropriate. [NIST SP 800-53
> Rev.5: PL-2]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `7`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 59, REV5)

- **Question:** "What should security and privacy architectures describe to ensure protection of information and integration with the enterprise architecture?"
- **Gold Control ID:** `PL-8`
- **Gold Clause IDs:** `pl-8_smt.a
pl-8_smt.a.1
pl-8_smt.a.2
pl-8_smt.a.3
pl-8_smt.a.4
pl-8_smt.b
pl-8_smt.c`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `PM-7`
- **Top-5 Retrieved List:** `PM-7`, `PL-8`, `SA-17`, `SA-3`, `PL-2`

**Gold Answer (from Gold Set):**

> Develop security and privacy architectures for the system that describe the requirements and
> approach to be taken for protecting the confidentiality, integrity, and availability of
> organizational information; describe the requirements and approach to be taken for processing
> personally identifiable information to minimize privacy risk to individuals; describe how the
> architectures are integrated into and support the enterprise architecture; describe any
> assumptions about, and dependencies on, external systems and services; and review and update
> the architectures {{ insert: param, pl-8_odp }} to reflect changes in the enterprise
> architecture ; and
> Reflect planned architecture changes in security and privacy plans, Concept of Operations
> (CONOPS), criticality analysis, organizational procedures, and procurements and acquisitions.
> [NIST SP 800-53 Rev.5: PL-8]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `2`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 65, REV5)

- **Question:** "What are the key components of an organization's risk management strategy, and how should it be implemented and updated?"
- **Gold Control ID:** `PM-9`
- **Gold Clause IDs:** `pm-9_smt.a
pm-9_smt.a.1
pm-9_smt.a.2
pm-9_smt.b
pm-9_smt.c`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `PM-30`
- **Top-5 Retrieved List:** `PM-30`, `PM-9`, `PM-4`, `PM-7`, `SR-1`

**Gold Answer (from Gold Set):**

> Develops a comprehensive strategy to manage security risk to organizational operations and
> assets, individuals, other organizations, and the Nation associated with the operation and use
> of organizational systems; and privacy risk to individuals resulting from the authorized
> processing of personally identifiable information; implement the risk management strategy
> consistently across the organization; and review and update the risk management strategy {{
> insert: param, pm-9_odp }} or as required, to address organizational changes. [NIST SP 800-53
> Rev.5: PM-9]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`components`, `component`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `PM-30` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 67, REV5)

- **Question:** "When and how must individuals be screened before authorizing or maintaining access to organizational systems?"
- **Gold Control ID:** `PS-3`
- **Gold Clause IDs:** `ps-3_smt.a
ps-3_smt.b`
- **BM25 Rank of Gold:** `8`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `CA-6`
- **Top-5 Retrieved List:** `CA-6`, `CM-3.2`, `PL-4`, `AC-2.13`, `AT-3`

**Gold Answer (from Gold Set):**

> Screen individuals prior to authorizing access to the system; and Rescreen individuals in
> accordance with {{ insert: param, ps-3_prm_1 }}. [NIST SP 800-53 Rev.5: PS-3]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query is conceptually about the gold control, but it does **not** include the most discriminative clause-specific anchors (often the *enumerated items* or precise action verbs), so BM25 drifts to a nearby control.
   - Evidence in outputs: gold control appears at **rank #8**, while BM25 prefers `CA-6` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query is close in intent but lacks the gold clause’s most discriminative lexical anchors.

---

## (Question ID: 68, REV5)

- **Question:** "What steps must be taken when an individual's employment or role is terminated?"
- **Gold Control ID:** `PS-4`
- **Gold Clause IDs:** `ps-4_smt
ps-4_smt.a
ps-4_smt.b
ps-4_smt.c
ps-4_smt.d
ps-4_smt.e`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `PT-7.1`
- **Top-5 Retrieved List:** `PT-7.1`, `PS-4.1`, `PS-4`, `SI-18.3`, `PS-6.3`

**Gold Answer (from Gold Set):**

> Disable system access within {{ insert: param, ps-4_odp_1 }}; Terminate or revoke any
> authenticators and credentials associated with the individual; Conduct exit interviews that
> include a discussion of {{ insert: param, ps-4_odp_2 }}; Retrieve all security-related
> organizational system-related property; and Retain access to organizational information and
> systems formerly controlled by terminated individual. [NIST SP 800-53 Rev.5: PS-4]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`steps`, `step`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #3**, while BM25 prefers `PT-7.1` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 72, REV5)

- **Question:** "What must organizations identify and document about the purposes and conditions for collecting, using, and sharing PII, and how should they handle changes to those purposes?"
- **Gold Control ID:** `PT-3`
- **Gold Clause IDs:** `pt-3_smt.a
pt-3_smt.b
pt-3_smt.c
pt-3_smt.d`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SI-18`
- **Top-5 Retrieved List:** `SI-18`, `PT-3`, `PT-5`, `PT-2`, `PT-3.1`

**Gold Answer (from Gold Set):**

> Identify and document the {{ insert: param, pt-3_odp_1 }} for which personally identifiable
> information is collected, used, maintained, shared, and disclosed; and Restrict the processing
> of personally identifiable information to only those {{ insert: param, pt-3_odp_2 }} identified
> by the organization or for which the organization has provided notice or received consent, and
> ensure any changes to {{ insert: param, pt-3_odp_3 }} are made in accordance with {{ insert:
> param, pt-3_odp_4 }}. [NIST SP 800-53 Rev.5: PT-3]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`collecting`, `sharing`, `using`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `SI-18` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 76, REV5)

- **Question:** "What steps are required to categorize a system and its information, and who must approve the decision?"
- **Gold Control ID:** `RA-2`
- **Gold Clause IDs:** `ra-2_smt.a
ra-2_smt.b
ra-2_smt.c`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `PT-7.1`
- **Top-5 Retrieved List:** `PT-7.1`, `RA-2`, `SA-10.2`, `MP-6.1`, `AC-3.4`

**Gold Answer (from Gold Set):**

> Categorize the system and information it processes, stores, and transmits; Document the
> security categorization results, including supporting rationale, in the security plan for the
> system; and Verify that the authorizing official or authorizing official designated
> representative reviews and approves the security categorization decision. [NIST SP 800-53
> Rev.5: RA-2]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`steps`, `step`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `PT-7.1` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 77, REV5)

* **Question:** "How should organizations conduct and document risk assessments, and how often should the results be reviewed?"
* **Gold Control ID:** `RA-3`
* **Gold Clause IDs:** `N/A (not recorded in the Error Bank export)`
* **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
* **Top-1 Retrieved:** `RA-8`
* **Top-5 Retrieved List:** `RA-8`, `RA-3`, `CA-2(1)`, `CA-2`, `PM-28`

**Gold Answer (from Gold Set):**

> (Gold answer text is not included in the Error Bank export. Use the Rev.5 gold set entry for `RA-3`.)

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**

   * The query explicitly targets **risk assessments** (`RA-3`), but BM25 ranked a different **assessment-focused control** (`RA-8`) above the gold.
   * This is consistent with a **terminology/anchor dominance issue**: the shared token “assessments” pulls BM25 toward a neighboring control even when the intended subtype is “risk assessment.”
   * Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `RA-8` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**

   * The query includes concrete anchors (“risk assessments”, “conduct and document”, “how often reviewed”), so it is not primarily a generic template query.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**

   * A semantic gap explanation is unnecessary because the gold control is already retrieved at **rank #2**; the issue is ranking preference among nearby controls, not conceptual mismatch.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** BM25 over-weights shared “assessment” terminology and ranks a neighboring assessment-related control above the intended risk assessment control (gold at #2).

---

## (Question ID: 87, REV5)

- **Question:** "What measures should be implemented to protect the confidentiality and integrity of transmitted information across internal and external networks?"
- **Gold Control ID:** `SC-8`
- **Gold Clause IDs:** `sc-8_gdn`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SC-7.4`
- **Top-5 Retrieved List:** `SC-7.4`, `SC-8`, `AC-17.2`, `SI-18`, `SC-7`

**Gold Answer (from Gold Set):**

> Protecting the confidentiality and integrity of transmitted information applies to internal and
> external networks as well as any system components that can transmit information, including
> servers, notebook computers, desktop computers, mobile devices, printers, copiers, scanners,
> facsimile machines, and radios. Unprotected communication paths are exposed to the possibility
> of interception and modification. Protecting the confidentiality and integrity of information
> can be accomplished by physical or logical means. Physical protection can be achieved by using
> protected distribution systems. A protected distribution system is a wireline or fiber-optics
> telecommunications system that includes terminals and adequate electromagnetic, acoustical,
> electrical, and physical controls to permit its use for the unencrypted transmission of
> classified information. Logical protection can be achieved by employing encryption
> techniques.\n\nOrganizations that rely on commercial providers who offer transmission services
> as commodity services rather than as fully dedicated services may find it difficult to obtain
> the necessary assurances regarding the implementation of needed controls for transmission
> confidentiality and integrity. In such situations, organizations determine what types of
> confidentiality or integrity services are available in standard, commercial telecommunications
> service packages. If it is not feasible to obtain the necessary controls and assurances of
> control effectiveness through appropriate contracting vehicles, organizations can implement
> appropriate compensating controls. [NIST SP 800-53 Rev.5: SC-8]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`measures`, `measure`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `SC-7.4` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 89, REV5)

- **Question:** "How should cryptographic mechanisms be selected and implemented to comply with applicable laws, policies, and standards?"
- **Gold Control ID:** `SC-13`
- **Gold Clause IDs:** `sc-13_gdn`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `IA-7`
- **Top-5 Retrieved List:** `IA-7`, `SC-13`, `PS-8`, `SC-12`, `SC-40.2`

**Gold Answer (from Gold Set):**

> Cryptography can be employed to support a variety of security solutions, including the
> protection of classified information and controlled unclassified information, the provision and
> implementation of digital signatures, and the enforcement of information separation when
> authorized individuals have the necessary clearances but lack the necessary formal access
> approvals. Cryptography can also be used to support random number and hash generation.
> Generally applicable cryptographic standards include FIPS-validated cryptography and NSA-
> approved cryptography. For example, organizations that need to protect classified information
> may specify the use of NSA-approved cryptography. Organizations that need to provision and
> implement digital signatures may specify the use of FIPS-validated cryptography. Cryptography
> is implemented in accordance with applicable laws, executive orders, directives, regulations,
> policies, standards, and guidelines. [NIST SP 800-53 Rev.5: SC-13]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query is conceptually about the gold control, but it does **not** include the most discriminative clause-specific anchors (often the *enumerated items* or precise action verbs), so BM25 drifts to a nearby control.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `IA-7` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query is close in intent but lacks the gold clause’s most discriminative lexical anchors.

---

## (Question ID: 93, REV5)

- **Question:** "How should systems be monitored to detect attacks, unauthorized connections, and anomalous activities, and how should such events be analyzed and reported?"
- **Gold Control ID:** `SI-4`
- **Gold Clause IDs:** `si-4_smt.a
si-4_smt.a.1
si-4_smt.a.2
si-4_smt.b
si-4_smt.c
si-4_smt.c.1
si-4_smt.c.2
si-4_smt.d
si-4_smt.e
si-4_smt.f
si-4_smt.g`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SA-8.17`
- **Top-5 Retrieved List:** `SA-8.17`, `AT-2.4`, `SI-4`, `SI-18`, `SI-19.6`

**Gold Answer (from Gold Set):**

> Monitor the system to detect attacks and indicators of potential attacks in accordance with
> organization-defined monitoring objectives: {{ insert: param, si-4_odp_1 }}; and unauthorized
> local, network, and remote connections; identify unauthorized use of the system through the
> following techniques and methods: {{ insert: param, si-4_odp_2 }}; invoke internal monitoring
> capabilities or deploy monitoring devices strategically within the system to collect
> organization-determined essential information and at ad hoc locations within the system to
> track specific types of transactions of interest to the organization; analyze detected events
> and anomalies; adjust the level of system monitoring activity when there is an indication of
> increased risk to organizational operations and assets, individuals, other organizations, or
> the Nation; obtain legal opinion regarding system monitoring activities; and provide {{ insert:
> param, si-4_odp_3 }} to {{ insert: param, si-4_odp_4 }} {{ insert: param, si-4_odp_5 }}. [NIST
> SP 800-53 Rev.5: SI-4]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (PASS)**
   - The query intent aligns with the gold control, but the mapping relies on **conceptual interpretation** rather than shared keywords alone.
   - Evidence in outputs: BM25 prefers a semantically-adjacent control (`SA-8.17`) even though the gold control is present at rank `3`.

#### Final Verdict: `Semantic Gap`

**Rationale:** The query requires conceptual interpretation beyond simple keyword overlap, so BM25 drifts to a semantically-adjacent control.

---

## (Question ID: 1, REV4)

- **Question:** "What does AC-2 require the organization to do when managing information system accounts?"
- **Gold Control ID:** `AC-2`
- **Gold Clause IDs:** `ac-2_smt.f`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `AC-3.2`
- **Top-5 Retrieved List:** `AC-3.2`, `AC-2`, `AC-6.10`, `AC-10`, `PE-6.3`

**Gold Answer (from Gold Set):**

> The organization manages information system accounts, including establishing, modifying,
> disabling, and removing accounts in accordance with {{ insert: param, ac-2_prm_3 }}.[NIST SP
> 800-53 Rev.4: AC-2]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `2`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 6, REV4)

- **Question:** "What audit record contents are the system required to generate?"
- **Gold Control ID:** `AU-3`
- **Gold Clause IDs:** `au-3_smt`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `AU-7.2`
- **Top-5 Retrieved List:** `AU-7.2`, `AU-7`, `AU-3`, `AU-3.2`, `AU-6.5`

**Gold Answer (from Gold Set):**

> The information system generates audit records containing information that establishes what
> type of event occurred, when the event occurred, where the event occurred, the source of the
> event, the outcome of the event, and the identity of any user/subject associated with the
> event.[NIST SP 800-53 Rev.4: AU-3]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`contents`, `content`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #3**, while BM25 prefers `AU-7.2` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 10, REV4)

- **Question:** "What are the requirements for establishing and documenting configuration settings?"
- **Gold Control ID:** `CM-6`
- **Gold Clause IDs:** `cm-6_smt.a`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `CP-7.4`
- **Top-5 Retrieved List:** `CP-7.4`, `CM-6`, `CM-8.6`, `SC-7.7`, `CM-6.2`

**Gold Answer (from Gold Set):**

> The organization establishes and documents configuration settings for information technology
> products employed within the information system using {{ insert: param, cm-6_prm_1 }} that
> reflect the most restrictive mode consistent with operational requirements.[NIST SP 800-53
> Rev.4: CM-6]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query is conceptually about the gold control, but it does **not** include the most discriminative clause-specific anchors (often the *enumerated items* or precise action verbs), so BM25 drifts to a nearby control.
   - Evidence in outputs: gold control appears at **rank #2**, while BM25 prefers `CP-7.4` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query is close in intent but lacks the gold clause’s most discriminative lexical anchors.

---

## (Question ID: 11, REV4)

- **Question:** "What does CP-2 require in developing a contingency plan for the information system?"
- **Gold Control ID:** `CP-2`
- **Gold Clause IDs:** `cp-2_smt.a;cp-2_smt.a.1`
- **BM25 Rank of Gold:** `4`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `CP-2.7`
- **Top-5 Retrieved List:** `CP-2.7`, `CP-4.1`, `CP-4`, `CP-2`, `CP-3`

**Gold Answer (from Gold Set):**

> The organization develops a contingency plan for the information system that identifies
> essential mission and business functions and associated contingency requirements.[NIST SP
> 800-53 Rev.4: CP-2]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `4`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 13, REV4)

- **Question:** "What identification and authentication requirement does IA-2 specify for organizational users?"
- **Gold Control ID:** `IA-2`
- **Gold Clause IDs:** `ia-2_smt`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `IA-8`
- **Top-5 Retrieved List:** `IA-8`, `IA-1`, `IA-2`, `IA-9.2`, `IA-3`

**Gold Answer (from Gold Set):**

> The information system uniquely identifies and authenticates organizational users (or processes
> acting on behalf of organizational users).[NIST SP 800-53 Rev.4: IA-2]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`requirement`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #3**, while BM25 prefers `IA-8` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 15, REV4)

- **Question:** "What incident handling capability does IR-4 require the organization to implement?"
- **Gold Control ID:** `IR-4`
- **Gold Clause IDs:** `ir-4_smt`
- **BM25 Rank of Gold:** `4`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `IR-4.7`
- **Top-5 Retrieved List:** `IR-4.7`, `IR-4.6`, `IR-4.1`, `IR-4`, `IR-4.8`

**Gold Answer (from Gold Set):**

> The organization implements an incident handling capability for security incidents that
> includes preparation, detection and analysis, containment, eradication, and recovery.[NIST SP
> 800-53 Rev.4: IR-4]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `4`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 21, REV4)

- **Question:** "What are the requirements for enforcing physical access authorizations at facility entry/exit points?"
- **Gold Control ID:** `PE-3`
- **Gold Clause IDs:** `pe-3_smt.a;pe-3_smt.a.1;pe-3_smt.a.2;pe-3_smt.b;pe-3_smt.c;pe-3_smt.d;pe-3_smt.e;pe-3_smt.f;pe-3_smt.g`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `PE-16`
- **Top-5 Retrieved List:** `PE-16`, `SI-8`, `PE-3`, `PE-18`, `PE-3.1`

**Gold Answer (from Gold Set):**

> The organization enforces physical access authorizations at {{ insert: param, pe-3_prm_1 }} by
> verifying individual access authorizations before granting access to the facility, controlling
> ingress/egress to the facility using {{ insert: param, pe-3_prm_2 }}, maintains physical access
> audit logs for {{ insert: param, pe-3_prm_4 }}, provides {{ insert: param, pe-3_prm_5 }} to
> control access to areas within the facility officially designated as publicly accessible,
> escorts visitors and monitors visitor activity {{ insert: param, pe-3_prm_6 }}, secures keys,
> combinations, and other physical access devices, inventories {{ insert: param, pe-3_prm_7 }}
> every {{ insert: param, pe-3_prm_8 }}, and changes combinations and keys {{ insert: param,
> pe-3_prm_9 }} and/or when keys are lost, combinations are compromised, or individuals are
> transferred or terminated. [NIST SP 800-53 Rev.4: PE-3]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query uses anchor term(s) **`requirements`, `requirement`**, but these words do **not** appear in the gold clause text verbatim. BM25 therefore has weaker lexical evidence for the correct clause.
   - Evidence in outputs: gold control appears at **rank #3**, while BM25 prefers `PE-16` as top-1.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes meaningful domain anchors beyond a bare template, so generic phrasing is not the primary driver.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The query uses anchor words that do not appear verbatim in the gold clause, weakening lexical match.

---

## (Question ID: 22, REV4)

- **Question:** "What does PE-6 require regarding monitoring physical access to the facility?"
- **Gold Control ID:** `PE-6`
- **Gold Clause IDs:** `pe-6_smt.a`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `PE-6.4`
- **Top-5 Retrieved List:** `PE-6.4`, `PE-6`, `PE-3.6`, `PE-3`, `PE-6.3`

**Gold Answer (from Gold Set):**

> The organization monitors physical access to the facility where the information system resides
> to detect and respond to physical security incidents.[NIST SP 800-53 Rev.4: PE-6]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `2`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---


## (Question ID: 26, REV4)

- **Question:** "What specific documentation artifacts must the organization employ to record information security resource requirements during capital planning, and how must exceptions to resource inclusion be handled?"
- **Gold Control ID:** `PM-3`
- **Gold Clause IDs:** `pm-3_smt.a
pm-3_smt.b
pm-3_smt.c`
- **BM25 Rank of Gold:** `2`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SA-2`
- **Top-5 Retrieved List:** `SA-2`, `PM-3`, `CM-3.2`, `SC-20`, `SA-11`

**Gold Answer (from Gold Set):**

> Ensures that all capital planning and investment requests include the resources needed to implement the information security program and documents all exceptions to this requirement; Employs a business case/Exhibit 300/Exhibit 53 to record the resources required; Ensures that information security resources are available for expenditure as planned.  [NIST SP 800-53 Rev.4: PM-3]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (PASS)**
   - The query asks for a general category ("documentation artifacts"), but the gold control answers using specific document names (e.g., "business case/Exhibit 300/Exhibit 53").
   - BM25 therefore latches onto semantically-adjacent controls with more obvious shared terms and ranks the gold control at **#2** instead of **#1**.

2. **Step 2: Test for `Generic Phrasing`: (FAIL)**
   - The query includes multiple discriminative anchors (capital planning, resource requirements, exceptions), so the miss is not primarily due to being template-like or underspecified.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - The miss is explained by lexical anchoring (generic category vs specific examples) without requiring deeper conceptual inference.

#### Final Verdict: `Terminology Mismatch`

**Rationale:** The gold control (PM-3) answers the question using specific artifact names ("business case/Exhibit 300/Exhibit 53") and requires documenting exceptions; the query uses the generic phrase "documentation artifacts," which weakens lexical match and causes BM25 to rank SA-2 above PM-3.


## (Question ID: 29, REV4)

- **Question:** "What does RA-2 require regarding categorizing the information system and its resident information?"
- **Gold Control ID:** `RA-2`
- **Gold Clause IDs:** `ra-2_smt.a`
- **BM25 Rank of Gold:** `0`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `RA-5.4`
- **Top-5 Retrieved List:** `RA-5.4`, `RA-5.2`, `AC-3.3`, `RA-5.5`, `RA-1`

**Gold Answer (from Gold Set):**

> The organization categorizes the information system and the information resident therein in
> accordance with applicable federal laws, Executive Orders, directives, policies, regulations,
> standards, and guidance.[NIST SP 800-53 Rev.4: RA-2]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `0`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 31, REV4)

- **Question:** "What does SA-3 require about managing the system?"
- **Gold Control ID:** `SA-3`
- **Gold Clause IDs:** `sa-3_smt.a
sa-3_smt.b
sa-3_smt.c
sa-3_smt.d`
- **BM25 Rank of Gold:** `0`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `RA-5.4`
- **Top-5 Retrieved List:** `RA-5.4`, `PE-6.3`, `CP-4.1`, `IA-5.14`, `SC-5.2`

**Gold Answer (from Gold Set):**

> The organization manages the information system using a system development life cycle {{
> insert: param, sa-3_prm_1 }} that incorporates information security considerations.[NIST SP
> 800-53 Rev.4: SA-3]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `0`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 32, REV4)

- **Question:** "What does SA-4 require including in acquisition contracts for information systems?"
- **Gold Control ID:** `SA-4`
- **Gold Clause IDs:** `sa-4_smt

sa-4_smt.a
sa-4_smt.b
sa-4_smt.c
sa-4_smt.d
sa-4_smt.e
sa-4_smt.f
sa-4_smt.g`
- **BM25 Rank of Gold:** `10`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SA-12`
- **Top-5 Retrieved List:** `SA-12`, `SA-1`, `CP-4.1`, `SA-9.1`, `SA-11.4`

**Gold Answer (from Gold Set):**

> The organization includes the following requirements, descriptions, and criteria, explicitly or
> by reference, in the acquisition contract for the information system, system component, or
> information system service in accordance with applicable federal laws, Executive Orders,
> directives, policies, regulations, standards, guidelines, and organizational mission/business
> needs:
> Security functional requirements;
> Security strength requirements;
> Security assurance requirements;
> Security-related documentation requirements;
> Requirements for protecting security-related documentation;
> Description of the information system development environment and environment in which the
> system is intended to operate; and
> Acceptance criteria. [NIST SP 800-53 Rev.4: SA-4]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `10`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.

---

## (Question ID: 35, REV4)

- **Question:** "What does SI-2 require for identifying, reporting, and correcting system flaws?"
- **Gold Control ID:** `SI-2`
- **Gold Clause IDs:** `si-2_smt.a

si-2_smt.b

si-2_smt.c

si-2_smt.d`
- **BM25 Rank of Gold:** `3`  *(0 = not in top-10)*
- **Top-1 Retrieved:** `SI-10.2`
- **Top-5 Retrieved List:** `SI-10.2`, `SI-2.3`, `SI-2`, `SI-3.6`, `SA-12.14`

**Gold Answer (from Gold Set):**

> Identifies, reports, and corrects information system flaws;
> Tests software and firmware updates related to flaw remediation for effectiveness and potential
> side effects before installation;
> Installs security-relevant software and firmware updates within {{ insert: param, si-2_prm_1 }}
> of the release of the updates; and
> Incorporates flaw remediation into the organizational configuration management process.[NIST SP
> 800-53 Rev.4: SI-2]

### My Reasoning Process

1. **Step 1: Test for `Terminology Mismatch`: (FAIL)**
   - The query and gold clause share visible keywords, and there is no single “missing synonym” that fully explains the miss as a pure terminology mismatch.

2. **Step 2: Test for `Generic Phrasing`: (PASS)**
   - The query is dominated by a **template-like structure** (e.g., “What does X require…”, “What should…”) and provides limited clause-specific anchors.
   - Evidence in outputs: BM25 fails to rank the correct control at #1 (gold appears at rank `3`), indicating insufficient lexical separation.

3. **Step 3: Test for `Semantic Gap`: (FAIL)**
   - A semantic gap explanation is not necessary once the earlier category accounts for the miss.

#### Final Verdict: `Generic Phrasing`

**Rationale:** The query is template-heavy/underspecified, so BM25 cannot separate the correct clause from many similar ones.
