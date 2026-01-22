# Error Bank Labeling Rationale (Updated)

**Date:** January 21, 2026

This document records the manual labels for the *current* `error_bank_v1.csv` (JSONL‑rebuilt corpus).

---

### (ID: 1)

- **Version:** rev4
- **Control ID (Gold):** AC-2
- **BM25 Rank:** 2
- **Top‑1 Hit:** AC-3.2
- **Question:** "What does AC-2 require the organization to do when managing information system accounts?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query is an underspecified "What does AC-2 require" template without concrete sub-actions (e.g., account types, approvals, monitoring), so it can match many account-related clauses.

---

### (ID: 6)

- **Version:** rev4
- **Control ID (Gold):** AU-3
- **BM25 Rank:** 3
- **Top‑1 Hit:** AU-7.2
- **Question:** "What audit record contents are the system required to generate?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query's main phrase is "What... are the system required to generate?". This is a common, generic structure. It's vague and relies heavily on the other keywords ("audit record") which may be common.

---

### (ID: 10)

- **Version:** rev4
- **Control ID (Gold):** CM-6
- **BM25 Rank:** 2
- **Top‑1 Hit:** CP-7.4
- **Question:** "What are the requirements for establishing and documenting configuration settings?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query's key term is "requirements." The gold answer *never* uses this word. It *states* the requirement ("establishes and documents... using...").

---

### (ID: 11)

- **Version:** rev4
- **Control ID (Gold):** CP-2
- **BM25 Rank:** 4
- **Top‑1 Hit:** CP-2.7
- **Question:** "What does CP-2 require in developing a contingency plan for the information system?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query structure is "What does [Control ID] require...". This is the same generic template as query ID 9.

---

### (ID: 13)

- **Version:** rev4
- **Control ID (Gold):** IA-2
- **BM25 Rank:** 3
- **Top‑1 Hit:** IA-8
- **Question:** "What identification and authentication requirement does IA-2 specify for organizational users?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** This is a subtle but clear mismatch. The query asks for the "requirement," but the gold answer *never* uses this word. It simply states the action ("...uniquely identifies and authenticates..."). *(Note: Your original `error_bank_v1.

---

### (ID: 15)

- **Version:** rev4
- **Control ID (Gold):** IR-4
- **BM25 Rank:** 4
- **Top‑1 Hit:** IR-4.7
- **Question:** "What incident handling capability does IR-4 require the organization to implement?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query structure is "What... does [Control ID] require...". This is the same generic template as queries 9 and 11.

---

### (ID: 21)

- **Version:** rev4
- **Control ID (Gold):** PE-3
- **BM25 Rank:** 3
- **Top‑1 Hit:** PE-16
- **Question:** "What are the requirements for enforcing physical access authorizations at facility entry/exit points?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query asks for generic "requirements" for enforcing physical access authorizations; PE-3 is specific about controlling physical access at entry/exit points, so missing the specific verbs/criteria can reduce match.

---

### (ID: 22)

- **Version:** rev4
- **Control ID (Gold):** PE-6
- **BM25 Rank:** 2
- **Top‑1 Hit:** PE-6.4
- **Question:** "What does PE-6 require regarding monitoring physical access to the facility?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** This query uses the exact same template as the previous one: "What does [Control ID] require...".

---

### (ID: 29)

- **Version:** rev4
- **Control ID (Gold):** RA-2
- **BM25 Rank:** 0
- **Top‑1 Hit:** RA-5.4
- **Question:** "What does RA-2 require regarding categorizing the information system and its resident information?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query uses a broad "require regarding" framing; RA-2’s exact phrasing centers on security categorization, documenting results, and authorizing official approval—details not surfaced in the query.

---

### (ID: 31)

- **Version:** rev4
- **Control ID (Gold):** SA-3
- **BM25 Rank:** 0
- **Top‑1 Hit:** RA-5.4
- **Question:** "What does SA-3 require about managing the system?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query is very broad ("What does SA-3 require about managing the system?") and lacks SDLC/security-integration keywords, making it prone to matching unrelated management controls.

---

### (ID: 32)

- **Version:** rev4
- **Control ID (Gold):** SA-4
- **BM25 Rank:** 10
- **Top‑1 Hit:** SA-12
- **Question:** "What does SA-4 require including in acquisition contracts for information systems?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The question is phrased as a high-level "what does SA-4 require" prompt; SA-4 is contract-language and requirement/criteria oriented, and the lack of specific requirement categories can cause mis-ranking.

---

### (ID: 35)

- **Version:** rev4
- **Control ID (Gold):** SI-2
- **BM25 Rank:** 3
- **Top‑1 Hit:** SI-10.2
- **Question:** "What does SI-2 require for identifying, reporting, and correcting system flaws?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** This query uses the "What does [Control ID] require..." template. The rest of the query ("...for identifying, reporting...") is also just a restatement of the gold answer's first line.

---

### (ID: 2)

- **Version:** rev5
- **Control ID (Gold):** AC-3
- **BM25 Rank:** 2
- **Top‑1 Hit:** SC-8
- **Question:** "What must an organization enforce regarding logical access to its information and systems?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query is broad and uses a generic "What must an organization enforce" template; it doesn’t surface the control’s exact phrase "approved authorizations" and can match many access-related clauses.

---

### (ID: 4)

- **Version:** rev5
- **Control ID (Gold):** AC-7
- **BM25 Rank:** 2
- **Top‑1 Hit:** AC-7.4
- **Question:** "How must a system be configured to handle consecutive invalid logon attempts?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query's main phrase is "How must a system be configured...". This is a common, generic phrase. The key terms "consecutive invalid logon attempts" are good, but the generic opening phrase can dilute the BM25 score by matching many oth

---

### (ID: 9)

- **Version:** rev5
- **Control ID (Gold):** AT-2(1)
- **BM25 Rank:** 0
- **Top‑1 Hit:** AT-2.1
- **Question:** "What type of activity should be included in literacy training to simulate real-world incidents?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query asks for the "type of activity" in literacy training, but AT-2(1) uses the specific term "practical exercises"; missing that term tends to mis-rank results.

---

### (ID: 10)

- **Version:** rev5
- **Control ID (Gold):** AT-3(3)
- **BM25 Rank:** 0
- **Top‑1 Hit:** AT-3
- **Question:** "What method does AT-3(3) specify for reinforcing objectives in role-based security training?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query uses generic wording ("what method") and omits the control’s exact phrase "practical exercises" that reinforce training objectives.

---

### (ID: 12)

- **Version:** rev5
- **Control ID (Gold):** AU-3
- **BM25 Rank:** 3
- **Top‑1 Hit:** AU-11
- **Question:** "What information must each audit record contain to support after-the-fact investigation of security incidents?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query's main phrase is "What information must... contain...". This is a classic generic, non-specific query structure. The only strong keywords are "audit record" and "security incidents."

---

### (ID: 14)

- **Version:** rev5
- **Control ID (Gold):** AU-6
- **BM25 Rank:** 2
- **Top‑1 Hit:** AU-3
- **Question:** "What is the required process for reviewing system audit records, and what actions should be taken based on the findings?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The question frames AU-6 as a broad "process" question; without the control’s concrete terms (review/analyze audit records, report findings, adjust review level), BM25 can match many procedural controls.

---

### (ID: 15)

- **Version:** rev5
- **Control ID (Gold):** AU-8
- **BM25 Rank:** 2
- **Top‑1 Hit:** AU-12.1
- **Question:** "What are the requirements for generating and recording time stamps in audit records to ensure accuracy?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query asks for generic "requirements" for time stamps; AU-8 is specific about internal system clocks, time granularity, and using UTC or a fixed/local offset, so missing those keywords can reduce lexical match.

---

### (ID: 16)

- **Version:** rev5
- **Control ID (Gold):** CA-2
- **BM25 Rank:** 0
- **Top‑1 Hit:** SC-38
- **Question:** "Describe the key steps of the formal control assessment process, from planning to reporting."

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query asks for "key steps" of the assessment process; CA-2 is written as specific actions (select assessor, develop assessment plan scope/procedures/environment/roles), so the step-oriented phrasing can mismatch.

---

### (ID: 19)

- **Version:** rev5
- **Control ID (Gold):** CA-6
- **BM25 Rank:** 2
- **Top‑1 Hit:** CA-6.2
- **Question:** "What are the primary responsibilities of an authorizing official regarding system authorization and risk determination?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query asks for "primary responsibilities" and "risk determination." The gold answer *lists* responsibilities (e.g., "Assign...", "Ensure...", "Authorizes...") but never uses the word "responsibilities." More importantly, the

---

### (ID: 23)

- **Version:** rev5
- **Control ID (Gold):** CM-4
- **BM25 Rank:** 0
- **Top‑1 Hit:** SA-8.17
- **Question:** "What should be analyzed before implementing a system change?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query's main phrase is "What should be...". This is a classic vague, generic query structure. The keywords are good, but the overall phrasing is weak.

---

### (ID: 24)

- **Version:** rev5
- **Control ID (Gold):** CM-6
- **BM25 Rank:** 2
- **Top‑1 Hit:** CM-8.6
- **Question:** "How should configuration settings be established, approved, and monitored?"

**Final Verdict:** `Semantic Gap`

**Rationale (1‑liner):** The query closely matches CM-6 (establish settings, approve deviations, monitor/control changes), yet the gold clause is not top-ranked—suggesting a structural/phrasing gap rather than missing vocabulary.

---

### (ID: 25)

- **Version:** rev5
- **Control ID (Gold):** CM-8
- **BM25 Rank:** 3
- **Top‑1 Hit:** PM-5
- **Question:** "What are the requirements for developing, maintaining, and updating a system component inventory?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query's key term is "requirements." The gold answer *never* uses this word. Instead, it *lists* the requirements (e.g., "Develop... inventory," "Review and update...").

---

### (ID: 26)

- **Version:** rev5
- **Control ID (Gold):** CP-2
- **BM25 Rank:** 3
- **Top‑1 Hit:** CP-4.1
- **Question:** "What are the key elements that must be included in a contingency plan, and how should it be reviewed, distributed, and updated?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query asks for "key elements" of a contingency plan; CP-2 enumerates specific plan contents (essential missions, recovery objectives, roles/responsibilities, etc.), and the generic "elements" wording can weaken match.

---

### (ID: 39)

- **Version:** rev5
- **Control ID (Gold):** IR-5
- **BM25 Rank:** 4
- **Top‑1 Hit:** IR-9.2
- **Question:** "What information should organizations maintain and analyze when documenting and reviewing security incidents?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query's main phrase is "What information should...". This is a very common, generic query structure.

---

### (ID: 44)

- **Version:** rev5
- **Control ID (Gold):** MA-5
- **BM25 Rank:** 3
- **Top‑1 Hit:** MA-5.1
- **Question:** "What process should be established for authorizing maintenance personnel and ensuring appropriate escorting and access control during maintenance?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query's main phrase is "What process should be established...". This is a common, generic query structure.

---

### (ID: 56)

- **Version:** rev5
- **Control ID (Gold):** PL-2
- **BM25 Rank:** 7
- **Top‑1 Hit:** SI-12
- **Question:** "What is the guidance of control PL-2?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** This is a *stronger* pass. The query's entire structure is "What is the guidance of control [X]?". This is the *definition* of a generic, templated query. The only unique keyword is "PL-2," which a keyword retriever can't effectively use

---

### (ID: 59)

- **Version:** rev5
- **Control ID (Gold):** PL-8
- **BM25 Rank:** 2
- **Top‑1 Hit:** PM-7
- **Question:** "What should security and privacy architectures describe to ensure protection of information and integration with the enterprise architecture?"

**Final Verdict:** `Generic Phrasing`

**Rationale (1‑liner):** The query's main phrase is "What should... describe...". This is a generic query structure. Even though the subject is specific, this weak phrasing is the likely cause of the BM25 failure.

---

### (ID: 60)

- **Version:** rev5
- **Control ID (Gold):** PL-10
- **BM25 Rank:** 2
- **Top‑1 Hit:** PL-11
- **Question:** "How does the concept of tailoring allow organizations to customize control baselines to their mission, environment, and risk profile?"

**Final Verdict:** `Semantic Gap`

**Rationale (1‑liner):** This is the only remaining option. This query's failure is subtle. It's not a mismatch or generic. This implies that even with all the right keywords, BM25 (TF-IDF) *still* failed to rank it \#1. This could be because the gold text is ve

---

### (ID: 65)

- **Version:** rev5
- **Control ID (Gold):** PM-9
- **BM25 Rank:** 2
- **Top‑1 Hit:** PM-30
- **Question:** "What are the key components of an organization's risk management strategy, and how should it be implemented and updated?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query's key phrase is "key components." The gold answer *never* uses the word "components." It *lists* the components (i.e., "Security risk" and "Privacy risk") but doesn't use the specific keyword.

---

### (ID: 67)

- **Version:** rev5
- **Control ID (Gold):** PS-3
- **BM25 Rank:** 8
- **Top‑1 Hit:** CA-6
- **Question:** "When and how must individuals be screened before authorizing or maintaining access to organizational systems?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The question is phrased as "when and how" screening occurs; PS-3 uses the precise requirement language "screen prior to authorizing access" and "rescreen under conditions/frequency", so mismatched wording can mis-rank.

---

### (ID: 68)

- **Version:** rev5
- **Control ID (Gold):** PS-4
- **BM25 Rank:** 3
- **Top‑1 Hit:** PT-7.1
- **Question:** "What steps must be taken when an individual's employment or role is terminated?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query is framed as generic "steps" for termination; PS-4 is written as concrete actions (e.g., terminating access, retrieving credentials/assets), so step-oriented wording can mismatch.

---

### (ID: 72)

- **Version:** rev5
- **Control ID (Gold):** PT-3
- **BM25 Rank:** 2
- **Top‑1 Hit:** SI-18
- **Question:** "What must organizations identify and document about the purposes and conditions for collecting, using, and sharing PII, and how should they handle changes to those purposes?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query asks about "collecting, using, and sharing PII." The gold answer uses the much broader, technical term "processing PII." A simple keyword search for "collecting" or "sharing" will fail.

---

### (ID: 76)

- **Version:** rev5
- **Control ID (Gold):** RA-2
- **BM25 Rank:** 2
- **Top‑1 Hit:** PT-7.1
- **Question:** "What steps are required to categorize a system and its information, and who must approve the decision?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query asks *two* things: "What steps...?" and "who must approve...?" The gold answer *lists* the steps ("Categorize...", "Document...", "Verify...") but never uses the word "steps." It also identifies *who* approves ("aut

---

### (ID: 87)

- **Version:** rev5
- **Control ID (Gold):** SC-8
- **BM25 Rank:** 2
- **Top‑1 Hit:** SC-7.4
- **Question:** "What measures should be implemented to protect the confidentiality and integrity of transmitted information across internal and external networks?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query's key term is "measures." The gold answer *never* uses the word "measures." It *lists* the measures (e.g., "physical or logical means," "protected distribution systems," "encryption").

---

### (ID: 89)

- **Version:** rev5
- **Control ID (Gold):** SC-13
- **BM25 Rank:** 2
- **Top‑1 Hit:** IA-7
- **Question:** "How should cryptographic mechanisms be selected and implemented to comply with applicable laws, policies, and standards?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query asks broadly how to select/implement cryptographic mechanisms for compliance; SC-13 is phrased as employing cryptographic mechanisms for protection, so missing the specific protection language can weaken lexical match.

---

### (ID: 93)

- **Version:** rev5
- **Control ID (Gold):** SI-4
- **BM25 Rank:** 3
- **Top‑1 Hit:** SA-8.17
- **Question:** "How should systems be monitored to detect attacks, unauthorized connections, and anomalous activities, and how should such events be analyzed and reported?"

**Final Verdict:** `Semantic Gap`

**Rationale (1‑liner):** The query contains SI-4’s core terms (monitoring, detecting attacks/unauthorized connections, analyzing/reporting), but the gold clause still isn’t rank-1—consistent with a semantic/structural gap.

---

### (ID: 94)

- **Version:** rev5
- **Control ID (Gold):** SI-7
- **BM25 Rank:** 2
- **Top‑1 Hit:** SA-10.1
- **Question:** "What integrity-verification mechanisms should be employed to detect unauthorized changes to software, firmware, or data?"

**Final Verdict:** `Terminology Mismatch`

**Rationale (1‑liner):** The query’s "integrity-verification mechanisms" differs from SI-7’s phrasing around employing integrity verification tools; this vocabulary shift can lead BM25 to prefer other integrity-related controls.
