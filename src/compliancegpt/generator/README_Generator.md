
# ComplianceGPT Component: Citation-Contracted Answerer (Generator)

**Date:** November 19, 2025  
**Component:** Generator v0 (Logic & Unit Tests)  
**Status:** Implemented & Verified  

---

## 1. Executive Summary

This folder contains the **Answerer (Generator) component** of the ComplianceGPT RAG pipeline.

Unlike a traditional LLM chatbot that produces free-form text, this component acts as a **deterministic Compliance Engine**. Its output is a structured **Citation Contract** – a JSON object that:

- ties every claim to explicit evidence spans from NIST SP 800-53, and  
- encodes whether the answer is complete, unsupported, or blocked on organization-defined parameters (ODPs).

The Generator is designed so that downstream components (Verifier, UI, batch evaluation scripts) can **programmatically inspect and audit** every answer. :contentReference[oaicite:4]{index=4}

---

## 2. System Architecture

To keep the logic reusable and research-grade, the implementation is split into two main artifacts:

### 2.1 Engine: `generator.py`

- **Role:** Production-ready logic core.
- **Location:** `answerer_v0/generator/generator.py` (built by the test bench; In the Colab-based prototype, the test bench notebook writes this file into the runtime so the environment is self-contained. In the long-term repo, generator.py is intended to live as a normal module and be imported directly).
- **Responsibilities:**
  - Wraps the LLM (`Qwen/Qwen2.5-7B-Instruct`).
  - Applies a hardened system prompt that forbids open-ended chat and mandates JSON output.
  - Parses the model output into a strict Citation Contract.
  - Enforces ODP behavior via Python code (Traffic Cop).
  - Normalizes the result so the Verifier can consume it safely.

### 2.2 Test Bench Notebook: `Generator_v0_TestBench.ipynb`

- **Role:** Experimental laboratory for Phase 1.
- **Responsibilities:**
  - Installs dependencies (`transformers`, `accelerate`, `bitsandbytes`, `pyyaml`).
  - Loads the quantized Qwen 2.5-7B model on a Colab GPU.
  - Dynamically writes `generator.py` into the runtime.
  - Runs a suite of **unit tests** using controlled “mock retrieval” examples and real organization profiles from `ODP/`.

This separation allows you to:

- iterate on the engine logic in a single Python module, and  
- use the notebook only as a “test harness” and demo environment. :contentReference[oaicite:5]{index=5}

---

## 3. The Citation Contract (JSON Schema)

The Generator never returns raw paragraphs. It always emits a JSON object with four core fields:

```jsonc
{
  "answer_text": "string",
  "evidence_spans": [
    {
      "source_id": "string",
      "span_text": "string"
    }
  ],
  "status": "OK | NO_EVIDENCE | PARAMS_REQUIRED | ERROR",
  "odp_required_list": ["string", "..."]
}
````

* `answer_text`
  Natural language answer, which may include ODP substitutions (e.g., “90 days”).

* `evidence_spans`
  A list of verbatim quotes from the retrieved context.
  Each span:

  * identifies a `source_id` (e.g., `NIST_SP800-53:rev5:AC-2`), and
  * preserves the original text, including raw `{{ insert: ... }}` placeholders.

* `status`
  Machine-readable result flag:

  * `OK` – Answer is complete and backed by evidence.
  * `NO_EVIDENCE` – No supporting span found in the context.
  * `PARAMS_REQUIRED` – The answer is blocked on missing ODP values.
  * `ERROR` – JSON parsing or other internal failure.

* `odp_required_list`
  A list of ODP keys that must be provided by the organization (e.g., `["ac-02_odp.05"]`) before a complete answer can be given.

The **Verifier** and other downstream tooling depend on this contract to compute metrics such as citation precision and ODP handling quality. 

---

## 4. ODP Handling: The “Traffic Cop”

NIST controls often include placeholders such as:

> `[Assignment: organization-defined frequency]`
> `{{ insert: ac-02_odp.05 }}`

The Generator implements a **two-stage ODP pipeline**:

### 4.1 JSON Normalization

After extracting the JSON from the model output, the engine runs:

```python
contract = normalize_contract(raw_json)
```

This step:

* ensures `answer_text` is a string,
* converts `evidence_spans` into a canonical list of `{source_id, span_text}` dictionaries,
* normalizes `status` into the set `{OK, NO_EVIDENCE, PARAMS_REQUIRED, ERROR}`, and
* coerces `odp_required_list` into a list of strings.

This makes the contract structurally reliable, even if the model’s raw JSON is slightly off.

### 4.2 Traffic Cop Logic (`apply_odp_logic`)

The normalized contract is then passed through the Traffic Cop:

```python
contract = apply_odp_logic(contract, org_profile)
```

The logic:

1. **Detects ODP placeholders**

   * Scans both `answer_text` and each `span_text` in `evidence_spans` using a regex that accepts both `{ insert: ... }` and `{{ insert: ... }}`.
   * Collects all keys (e.g., `ac-02_odp.05`, `ac-1_prm_1`).

2. **Substitutes values when known**

   * For any key present in the loaded organization profile (`org_profile_example_rev5.yaml`, etc.), it:

     * substitutes the value into `answer_text` (e.g., “90 days”),
     * leaves `evidence_spans` untouched to preserve verbatim citations.

3. **Flags missing values**

   * For any key not present in the profile, it:

     * sets `status = "PARAMS_REQUIRED"`, and
     * populates `odp_required_list` with the missing keys.

4. **Default behavior**

   * If there are no missing ODPs and `status` is not already `NO_EVIDENCE`, the Traffic Cop forces `status = "OK"` with an empty `odp_required_list`.

This design guarantees:

* The engine never silently guesses an ODP value.
* The presence or absence of ODP configuration is **visible in the JSON**, not hidden in text. 

---

## 5. Robustness & Security Features

The engine includes several defensive features:

* **Input Sanitization**

  * Replaces dangerous triple quotes in user queries and context to prevent prompt-injection attempts from breaking the system prompt.

* **JSON Extraction**

  * Strips Markdown fences (`json … `), then uses regex to locate the largest `{ ... }` block in the model output.
  * Falls back to substring search if necessary.
  * If parsing fails, returns a structured error contract with `status: "ERROR"` and `raw_output` for debugging.

* **Deterministic Decoding**

  * Uses greedy decoding (`do_sample = False`, effectively `temperature = 0`) so the same input consistently yields the same JSON, which is critical for auditability.



---

## 6. Technical Specifications

* **Model:** `Qwen/Qwen2.5-7B-Instruct`
* **Quantization:** 4-bit (NF4) via `bitsandbytes`

  * Designed to fit on a standard Google Colab T4 GPU.
* **Runtime:**

  * Primarily developed and tested in **Google Colab**.
  * Dependencies: `transformers`, `accelerate`, `bitsandbytes`, `pyyaml`.



---

## 7. How to Run the Test Bench in Colab

1. Open `Generator_v0_TestBench.ipynb` in Google Colab.

2. Set the runtime to **GPU** (T4).

3. Run the cells in order:

   * **Cell 1:** Install dependencies and mount Google Drive.
   * **Cell 2:** Load the quantized Qwen 2.5-7B model.
   * **Cell 3:** Write `generator.py` to the Colab filesystem (current hardened logic).
   * **Cell 4:** Import `ComplianceGenerator` and helper functions from `generator.py`.
   * **Cell 5:** Run the unit tests for:

     * Rev 5 (AC-2, substitution from profile, e.g., “90 days”)
     * Rev 4 (AC-1, substitution from profile, e.g., “Security Officer”)
     * Missing-profile scenario (Traffic Cop returns `PARAMS_REQUIRED`)

4. Confirm that all tests print their corresponding `SUCCESS` messages.

These tests serve as the minimal regression suite for Phase 1: they prove that the Generator correctly implements FILL_FROM_PROFILE, PARAMS_REQUIRED, and legacy Rev 4 support.



---

## 8. Next Steps

With the Generator logic stabilized and unit-tested, the next milestones are:

1. **Verifier (Phase 2)**

   * A dedicated script that ingests the Citation Contract JSON and computes metrics such as:

     * citation precision,
     * wrong-version rate,
     * ODP handling accuracy.

2. **Retriever Integration (S7 pipeline)**

   * Replace mock context with actual retrieval results from the S7 retriever.
   * Run the Generator over the full 100-query Gold Standard.

3. **End-to-end Evaluation**

   * Use the Verifier to grade the full RAG pipeline.
   * Report results in terms of compliance-specific metrics instead of generic LLM scores.

This README describes the behavior and interface of the Generator so that it can be safely reused in those later phases without re-reading the implementation code.


---