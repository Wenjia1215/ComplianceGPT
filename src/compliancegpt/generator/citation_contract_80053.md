
### Generator Citation Contract

#### 1. Objective

This document defines the **Citation Contract**, a formal JSON schema that the ComplianceGPT “Answerer” (Generator) component must produce for every query it receives.

The purpose of this contract is to ensure that all outputs are **auditable, verifiable, and strictly grounded** in the provided evidence. This schema is the contract that the Answerer commits to produce and the Verifier commits to consume and audit.

---

#### 2. JSON Schema Definition

The Generator must return a single, valid JSON object matching the following structure:

```json
{
  "answer_text": "<string>",
  "evidence_spans": [
    {
      "source_id": "<string>",
      "span_text": "<string>"
    }
  ],
  "status": "<'OK' | 'NO_EVIDENCE' | 'PARAMS_REQUIRED'>",
  "odp_required_list": [
    "<string>"
  ]
}
```

---

#### 3. Field Descriptions and Rules

##### 3.1 `answer_text`

* **Type:** string
* **Description:** The final, natural-language answer to the user’s query.

**Rules:**

1. When `status = "OK"`:

   * Every factual or normative claim in `answer_text` must be directly supported by one or more entries in `evidence_spans`.
   * The text may synthesize or paraphrase evidence but must not contradict or extend beyond the cited spans.

2. When `status = "NO_EVIDENCE"`:

   * `answer_text` should briefly explain that no sufficient evidence was found (for example, “No relevant requirement could be located in the configured compliance corpus.”).
   * The text must not invent or imply a requirement that is not grounded in evidence.

3. When `status = "PARAMS_REQUIRED"`:

   * `answer_text` should explain that the answer depends on one or more organization-defined parameters and cannot be fully instantiated.
   * The text may reference the relevant control in general terms but must not guess concrete parameter values.

---

##### 3.2 `evidence_spans`

* **Type:** array of objects
* **Description:** A list of exact, verbatim text spans from the source documents that support `answer_text`.

Each object has the following fields:

* `source_id`

  * **Type:** string
  * **Description:** Canonical identifier for the evidence source.

    * Recommended format: a stable identifier that encodes at least framework, version, and control, e.g.
      `NIST_SP800-53:rev5:AC-1` or `NIST_SP800-53:rev5:AC-1:ac-1_smt.a`.
* `span_text`

  * **Type:** string
  * **Description:** The exact, verbatim quote from the source document corresponding to this evidence span.

**Rules:**

1. `span_text` must be copied verbatim from the canonical corpus (no edits, no hallucinated text).
2. When `status = "OK"`:

   * `evidence_spans` must not be empty.
3. When `status = "NO_EVIDENCE"`:

   * `evidence_spans` must be an empty list.
4. When `status = "PARAMS_REQUIRED"`:

   * `evidence_spans` may be used to show the underlying requirement text that contains organization-defined parameters.

---

##### 3.3 `status`

* **Type:** string (enum)
* **Description:** Machine-readable status of the answer.

**Allowed values:**

* `"OK"`
  The answer was successfully generated and is supported by at least one evidence span.

* `"NO_EVIDENCE"`
  Retrieved documents did not contain sufficient information to answer the query.

  * `answer_text` should state this clearly.
  * `evidence_spans` must be empty.

* `"PARAMS_REQUIRED"`
  The answer cannot be fully specified without organization-defined parameters (ODPs).

  * `answer_text` should explain that additional parameter input is required.
  * `odp_required_list` must be populated with the missing parameters.

**Mutual consistency rules:**

* If `status = "OK"`:

  * `evidence_spans` must be non-empty.
  * `odp_required_list` must be empty.
* If `status = "NO_EVIDENCE"`:

  * `evidence_spans` must be empty.
  * `odp_required_list` must be empty.
* If `status = "PARAMS_REQUIRED"`:

  * `odp_required_list` must be non-empty.

---

##### 3.4 `odp_required_list`

* **Type:** array of strings
* **Description:** List of ODP placeholders (for example, `"[Assignment: organization-defined frequency]"` or canonical ODP IDs) that must be defined before the query can be fully answered.

**Rules:**

1. This list must be populated **if and only if** `status = "PARAMS_REQUIRED"`.
2. Each entry should correspond to a specific parameter required by the cited evidence (for example, the placeholder text or an internal ODP identifier such as `ac-2_prm_1`).
3. When `status` is `"OK"` or `"NO_EVIDENCE"`, `odp_required_list` must be an empty list.

---

#### 4. Examples

##### Example 1: `status = "OK"`

**Query:** “What is the policy on access control?”

```json
{
  "answer_text": "The organization must develop, document, and disseminate an access control policy that covers purpose, scope, roles, responsibilities, and compliance.",
  "evidence_spans": [
    {
      "source_id": "NIST_SP800-53:rev5:AC-1",
      "span_text": "a. Develop, document, and disseminate to [Assignment: organization-defined personnel or roles]: 1. An access control policy that addresses purpose, scope, roles, responsibilities, management commitment, coordination among organizational entities, and compliance;"
    }
  ],
  "status": "OK",
  "odp_required_list": []
}
```

---

##### Example 2: `status = "NO_EVIDENCE"`

**Query:** “What is the organization’s policy on holiday bonuses?”

```json
{
  "answer_text": "No relevant requirement regarding holiday bonuses could be located in the configured NIST compliance corpus.",
  "evidence_spans": [],
  "status": "NO_EVIDENCE",
  "odp_required_list": []
}
```

---

##### Example 3: `status = "PARAMS_REQUIRED"`

**Query:** “How often are access agreements reviewed?”

```json
{
  "answer_text": "The review frequency for access agreements is organization-defined. A concrete answer requires specifying the frequency parameter.",
  "evidence_spans": [
    {
      "source_id": "NIST_SP800-53:rev5:AC-3(2)",
      "span_text": "Reviews and updates the access agreements [Assignment: organization-defined frequency]."
    }
  ],
  "status": "PARAMS_REQUIRED",
  "odp_required_list": [
    "[Assignment: organization-defined frequency]"
  ]
}
```

---
