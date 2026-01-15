**Author:** Wen
**Purpose of this README:** keep some tech details here, in case I forgot everything when i look back in the future
**Date:**11/19/2025


# ComplianceGPT Answerer Engine (`generator.py`)

**Component:** Citation-Contracted Answerer (Generator v0)  
**Context:** ComplianceGPT RAG pipeline – NIST SP 800-53 Rev.4/Rev.5  
**Status:** Ready for RAG integration (Phase 1/2)

---

## 1. Purpose and Role

`generator.py` implements the **Answerer** (Generator) component for ComplianceGPT.

Instead of producing free-form text, this engine generates a structured **Citation Contract**: a JSON object that encodes:

- the natural language answer,
- the exact evidence spans from NIST used to support that answer,
- the resolution status of organization-defined parameters (ODPs),
- and a machine-readable status flag.

The module is designed to be:

- **LLM-agnostic within the Qwen family** (currently tuned for `Qwen/Qwen2.5-7B-Instruct`),
- **RAG-compatible**, taking pre-retrieved context as input,
- **ODP-aware**, with parameter substitution and traffic-cop logic enforced in Python, not left to LLM behavior.

This file is suitable for direct import into any Retrieval-Augmented Generation (RAG) pipeline that adheres to the expected data contracts.

---

## 2. External Dependencies

`generator.py` assumes that the runtime environment has:

- **Python**
  - Version: 3.9+ recommended.

- **Core libraries (imported in the notebook / calling code)**
  - `torch`
  - `transformers` (Hugging Face)
  - `accelerate` (Hugging Face)
  - `bitsandbytes` (for 4-bit quantization)
  - `pyyaml` (used directly by `generator.py`)

The module itself imports:

```python
import json
import re
import yaml
from typing import Any, Dict, List, Optional
from pathlib import Path
````

Model loading is performed outside this module (typically in a notebook or an application entrypoint) using the Hugging Face `transformers` stack.

---

## 3. High-Level Architecture

### 3.1 Integration in the ComplianceGPT Pipeline

In the broader ComplianceGPT RAG architecture, this Answerer fits into the pipeline as follows:

1. **Retriever** (e.g., S7 Hybrid+QUR pipeline) returns a list of context documents:

   * Each document has keys `id` and `text`.
2. **Answerer Engine** (this module) receives:

   * the user’s query,
   * the retrieved documents,
   * an organization profile (YAML-loaded dict with ODP values).
3. The engine constructs a prompt, calls the LLM, parses the output into JSON, normalizes it, and enforces ODP logic.
4. The engine returns a **Citation Contract** dictionary to:

   * a **Verifier** (for metric computation), or
   * a **UI/Frontend** (for display and interaction).

### 3.2 Responsibilities of `generator.py`

The module provides:

* **Utility functions**

  * `load_org_profile(path: str) -> Dict[str, Any]`
  * `normalize_contract(raw: Dict[str, Any]) -> Dict[str, Any]`
  * `apply_odp_logic(contract: Dict[str, Any], org_profile: Dict[str, Any]) -> Dict[str, Any]`

* **Prompt template**

  * `SYSTEM_PROMPT_TEMPLATE`: an instruction block that enforces JSON-only, evidence-backed behavior.

* **Answerer class**

  * `ComplianceGenerator`: encapsulates the model, tokenizer, and the end-to-end `generate` method.

---

## 4. Public API Surface

### 4.1 `load_org_profile`

```python
def load_org_profile(filepath: str) -> Dict[str, Any]:
    ...
```

**Purpose**

* Load an organization profile from a YAML file on disk.
* Profiles contain ODP keys (e.g., `ac-02_odp.05`, `ac-1_prm_1`) mapped to concrete values (e.g., `"90 days"`, `"Security Officer"`).

**Behavior**

* If the file does not exist, prints a warning and returns `{}`.
* If YAML parsing fails, prints an error message and returns `{}`.
* Returns a dictionary (possibly empty).

**Expected Structure of YAML**

Example (Rev.5):

```yaml
ac-02_odp.05: "90 days"
ir-04_odp.01: "24 hours"
```

Example (Rev.4):

```yaml
ac-1_prm_1: "Security Officer"
ac-2_prm_3: "35 days"
```

---

### 4.2 `normalize_contract`

```python
ALLOWED_STATUS = {"OK", "NO_EVIDENCE", "PARAMS_REQUIRED", "ERROR"}

def normalize_contract(raw: Dict[str, Any]) -> Dict[str, Any]:
    ...
```

**Purpose**

* Convert raw JSON from the LLM into a **canonical Citation Contract** shape.
* Ensure correct types and allowed values, even if the LLM output deviates slightly from the expected schema.

**Normalization Rules**

* `answer_text`

  * Ensured to be a string (`str`). Non-string values are converted via `str(...)`.
* `evidence_spans`

  * Ensured to be a list of dictionaries:

    * Each span has keys:

      * `source_id: str`
      * `span_text: str`
  * If the model outputs strings instead of dicts, those strings are interpreted as `span_text` with empty `source_id`.
* `status`

  * Ensured to be one of `{"OK", "NO_EVIDENCE", "PARAMS_REQUIRED", "ERROR"}`.
  * Any other value is mapped to `"ERROR"`.
* `odp_required_list`

  * Ensured to be a list of non-empty strings.
  * If a single string or non-list is produced, it is wrapped into a single-element list when non-empty.

Fields not explicitly used by the Citation Contract (extra keys) are currently ignored by the normalizer.

---

### 4.3 `apply_odp_logic`

```python
ODP_PATTERN = re.compile(
    r"\{+\s*insert:\s*(?:param,\s*)?([^}]+?)\s*\}+",
    re.IGNORECASE
)

def apply_odp_logic(contract: Dict[str, Any], org_profile: Dict[str, Any]) -> Dict[str, Any]:
    ...
```

**Purpose**

* Enforce **ODP-aware behavior** independent of the LLM.
* Detect placeholders in the output and decide whether:

  * all necessary ODPs are filled (`status: "OK"`),
  * or additional input is required (`status: "PARAMS_REQUIRED"`).

**Detection Logic**

* Scans for ODP placeholders of the form:

  * `{{ insert: param, ac-02_odp.05 }}`
  * `{ insert: ac-02_odp.05 }`
  * and similar variants (with one or more braces and optional `param,`).

* Searches in two locations:

  1. `answer_text`
  2. Each `span_text` in `evidence_spans`

* Extracts the content after `insert:` and before the closing braces.
  Example raw captures might include:

  * `"ac-02_odp.05"`
  * `"ac-1_prm_1"`

* Normalization:

  * Trims whitespace.
  * If additional descriptive text is present (e.g., `"ac-1_prm_1, assignment: role"`), only the part before the first comma is kept (`"ac-1_prm_1"`).

**Substitution Behavior**

* For each normalized ODP key:

  * If the key exists in `org_profile`:

    * Its value is inserted into `answer_text` only.
    * A regex replacement allows for both `{ ... }` and `{{ ... }}` forms.
    * `evidence_spans` remain unmodified to preserve verbatim citations.
  * If the key does not exist:

    * The key is added to `missing_params`.

**Final Status Enforcement**

* If `missing_params` is non-empty:

  * `contract["status"] = "PARAMS_REQUIRED"`
  * `contract["odp_required_list"] = missing_params`
* Else, if `status` is not already `"NO_EVIDENCE"`:

  * `contract["status"] = "OK"`
  * `contract["odp_required_list"] = []`

This logic guarantees that:

* The engine does not invent ODP values.
* Missing configuration is explicitly exposed via `status` and `odp_required_list`.

---

### 4.4 `SYSTEM_PROMPT_TEMPLATE`

```python
SYSTEM_PROMPT_TEMPLATE = """
You are ComplianceGPT, an expert auditor.
Your goal is to answer the query STRICTLY based on the provided Context.

INSTRUCTIONS:
1. CITATION CONTRACT: Every claim must be backed by a verbatim quote from the Context.
2. EVIDENCE SPANS: Must include the **full sentence** containing the requirement, preserving any {{ insert: ... }} placeholders exactly.
3. JSON ONLY: Output valid JSON.

JSON SCHEMA:
{
  "answer_text": "string (Draft the answer using the {{ insert: ... }} placeholders found in the text)",
  "evidence_spans": [{"source_id": "string", "span_text": "string"}],
  "status": "OK",
  "odp_required_list": []
}

### INPUT CONTEXT
{context_str}

### USER QUERY
{query_str}
"""
```

**Purpose**

* Provide a fixed system prompt that:

  * instructs the LLM to act as a compliance auditor,
  * forces JSON-only output,
  * and makes explicit reference to the Citation Contract structure.

The template is formatted with:

* `context_str`: formatted context built from retrieved documents.
* `query_str`: sanitized user query.

---

### 4.5 `ComplianceGenerator` Class

```python
class ComplianceGenerator:
    def __init__(self, model, tokenizer, max_new_tokens=768):
        ...

    def generate(self, query, retrieved_docs, org_profile=None) -> Dict[str, Any]:
        ...
```

**Constructor**

* Parameters:

  * `model`: a `transformers` causal language model (e.g., `AutoModelForCausalLM` instance).
  * `tokenizer`: a compatible tokenizer (e.g., `AutoTokenizer` instance).
  * `max_new_tokens`: upper bound on tokens generated by the model.

**Internal Methods**

* `_sanitize_input(text)`:

  * Ensures that any embedded triple double-quotes in input are replaced with `'` to avoid breaking string-based prompts.
* `format_context(retrieved_docs)`:

  * Transforms an iterable of retrieved documents into a structured string.

Example `retrieved_docs` structure:

```python
retrieved_docs = [
    {
        "id": "NIST_SP800-53:rev5:AC-2",
        "text": "The organization reviews accounts for compliance {{ insert: param, ac-02_odp.05 }}."
    },
    ...
]
```

Output format (illustrative):

```text
[Context 1] Source ID: NIST_SP800-53:rev5:AC-2
Text: The organization reviews accounts for compliance {{ insert: param, ac-02_odp.05 }}.
```

* `_clean_json_output(raw_output)`:

  * Removes Markdown fences (`json ... `),
  * Attempts to extract the largest `{ ... }` block using a regex,
  * Falls back to substring search between the first `{` and last `}` if regex fails.

**`generate` Method**

Signature:

```python
def generate(self, query, retrieved_docs, org_profile=None) -> Dict[str, Any]:
    ...
```

Inputs:

* `query: str`

  * The user’s natural language question.
* `retrieved_docs: List[Dict[str, Any]]`

  * Documents retrieved by the RAG retriever.
  * Each item should contain at least:

    * `"id"`: a source identifier (e.g., NIST control ID),
    * `"text"`: the text span used as context.
* `org_profile: Dict[str, Any]` (optional)

  * A dictionary of ODP keys to values.
  * If `None`, an empty profile `{}` is used.

Processing steps (simplified):

1. Sanitize `query`.
2. Format `retrieved_docs` into `context_str`.
3. Fill `SYSTEM_PROMPT_TEMPLATE` with `context_str` and `query_str`.
4. Wrap into chat-style messages:

   * System role: “strict JSON-only compliance engine”.
   * User role: full prompt.
5. Use `tokenizer.apply_chat_template(...)` to produce the final text prompt.
6. Tokenize and move inputs to `model.device`.
7. Call `model.generate(...)` with:

   * `max_new_tokens=self.max_new_tokens`
   * `do_sample=False` (deterministic, greedy decoding).
8. Decode the generated segment (excluding the input prompt).
9. Clean the text with `_clean_json_output(...)`.
10. Parse the JSON:

    * On success:

      * `raw = json.loads(clean_json)`
      * `contract = normalize_contract(raw)`
      * `contract = apply_odp_logic(contract, org_profile)`
      * return `contract`.
    * On JSON parse failure:

      * return an error contract:

        ```python
        {
          "status": "ERROR",
          "answer_text": "JSON Parsing Failed",
          "raw_output": response_text
        }
        ```

Output:

* A dictionary conforming to the Citation Contract schema:

  * `answer_text: str`
  * `evidence_spans: List[Dict[str, str]]`
  * `status: str`
  * `odp_required_list: List[str]`
  * (optionally `raw_output` if parsing failed)

---

## 5. Citation Contract Schema

The normalized output of `generate(...)` conforms to the following shape:

```jsonc
{
  "answer_text": "The organization reviews accounts for compliance 90 days.",
  "evidence_spans": [
    {
      "source_id": "NIST_SP800-53:rev5:AC-2",
      "span_text": "The organization reviews accounts for compliance {{ insert: param, ac-02_odp.05 }}."
    }
  ],
  "status": "OK",
  "odp_required_list": []
}
```

Key invariants:

* `answer_text` may contain ODP-substituted values (e.g., `"90 days"`, `"Security Officer"`).
* `evidence_spans` preserve the original NIST text, including ODP placeholders.
* `status` reflects success, missing evidence, missing ODPs, or internal error.
* `odp_required_list` explicitly lists unresolved ODP keys when `status == "PARAMS_REQUIRED"`.

---

## 6. Typical Usage in RAG Code

Example integration snippet:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch
from generator import ComplianceGenerator, load_org_profile

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

answerer = ComplianceGenerator(model, tokenizer)

profile_path = "/content/drive/MyDrive/answerer_v0/generator/ODP/rev5/org_profile_example_rev5.yaml"
org_profile = load_org_profile(profile_path)

query = "How often must account management reviews occur according to AC-2?"
retrieved_docs = [
    {
        "id": "NIST_SP800-53:rev5:AC-2",
        "text": "The organization reviews accounts for compliance {{ insert: param, ac-02_odp.05 }}."
    }
]

contract = answerer.generate(query, retrieved_docs, org_profile=org_profile)
# contract is now a ready-to-use Citation Contract dict
```

This contract can then be:

* logged for audit,
* passed to a **Verifier** for metric computation,
* or serialized and returned by an API.

---

## 7. Testing and Validation

The behavior of `generator.py` has been validated via the `Generator_v0_TestBench.ipynb` notebook, which includes unit tests for:

* **Rev.5 Happy Path (AC-2)**

  * Profile defines `ac-02_odp.05: "90 days"`.
  * Expected:

    * `answer_text` contains `"90 days"`,
    * `status == "OK"`,
    * `odp_required_list == []`.

* **Rev.4 Happy Path (AC-1)**

  * Profile defines `ac-1_prm_1: "Security Officer"`.
  * Expected:

    * `answer_text` contains `"Security Officer"`,
    * `status == "OK"`,
    * `odp_required_list == []`.

* **Missing Data Path (Traffic Cop)**

  * Empty org profile.
  * Expected:

    * `status == "PARAMS_REQUIRED"`,
    * `odp_required_list` includes the appropriate ODP key (e.g., `"ac-02_odp.05"`).

These tests serve as regression checks for future modifications to the engine.

---

## 8. Limitations and Future Improvements

The current implementation is a robust v0 but still has known limitations:

* **JSON extraction greediness**

  * `_clean_json_output` uses a greedy `{.*}` regex; if multiple JSON objects are emitted, the extracted span may be invalid.
  * A future version can iterate over multiple candidate `{ ... }` blocks and select the first valid JSON.

* **ODP key format assumptions**

  * Basic handling of suffixes (e.g., `", assignment: role"`) is provided via `split(",")[0]`.
  * If more complex metadata appears inside placeholders, additional parsing logic may be required.

* **Single-model assumption**

  * The engine is currently tuned for `Qwen/Qwen2.5-7B-Instruct` with 4-bit quantization.
  * Other models may require prompt adjustments, decoding tweaks, or different generation parameters.

Despite these limitations, the module is suitable for:

* immediate integration into the ComplianceGPT RAG pipeline,
* use as the authoritative implementation of the Phase 1 Answerer,
* and serving as a stable dependency for the upcoming Verifier and full-system evaluation scripts.

--- 