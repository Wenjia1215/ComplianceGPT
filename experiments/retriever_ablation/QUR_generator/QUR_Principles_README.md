# Query Reformulation (QUR) Principles

## 1. Overview
This document outlines the core principles for the Query Reformulation (QUR) component (QUR_Generator_UT.py) of the **ComplianceGPT** project. The QUR component's goal is to take a single user query and generate multiple, high-quality alternative queries.

The ultimate objective is to maximize retrieval recall and precision from our compliance corpus (e.g., **NIST SP 800-53**, **HIPAA**, **PCI-DSS**) when using a lexical search algorithm like **BM25** and a fusion method like **Reciprocal Rank Fusion (RRF)**.

>Note:
>UT means Unit Test

## 2. The Problem: The "Paraphrasing" Fallacy
A common but flawed approach to query rewriting is to ask a Large Language Model (LLM) for "alternatives that mean the same thing." This leads to low-diversity, paraphrased queries.

**Original Query**  
*What are the requirements for media protection?*

**Flawed Rewrites**
- What are the media protection requirements?
- Tell me the requirements for media protection.
- Explain media protection requirements.

This approach fails for a keyword-based search engine like BM25 for two critical reasons:

1. **Identical Keyword Sets**: BM25 does not understand semantics; it matches keywords. The queries above all use the exact same primary keywords: "media," "protection," and "requirements." They will retrieve the exact same set of documents, or a very similar one.
2. **Ineffective Fusion (RRF)**: Reciprocal Rank Fusion works by democratically combining multiple different rank lists. If we feed it three nearly identical lists, the fusion adds no value. It's computationally wasteful and will produce the same result as a single query, failing to discover relevant documents that might use different terminology.

## 3. Our Solution: The 3-Strategy Principle
Our approach is to abandon paraphrasing and instead mandate diversity by forcing the LLM to adopt three distinct retrieval strategies.

We instruct the LLM to generate exactly three rewrites, each corresponding to a different "query persona." This provides RRF with three genuinely different result lists to fuse, which is where the retrieval "lift" comes from.

### Strategy 1: The Keyword Query (High Precision)
**What it is:** A "bag of words" query stripped of all conversational fluff, stop words, and filler. It contains only the essential technical keywords.

### Strategy 2: The Expanded Query (High Recall)
**What it is:** A query that strategically adds related technical synonyms, parent concepts, or specific framework IDs that are likely to co-occur with the original query's intent.

### Strategy 3: The Natural Language Query (Contextual Match)
**What it is:** A complete, well-formed question that rephrases the user's original intent in a different natural language structure.

## 4. How This Wins with RRF
By fusing these three strategically different lists, RRF becomes incredibly powerful:

- **Confidence Boosting**: If all three queries (Keyword, Expanded, and Natural) rank MP-6 in their top 5, RRF combines these signals, and MP-6's fused score will be exceptionally high, pushing it to rank 1.
- **Recall Enhancement**: If the Keyword query misses a key document (e.g., a policy on "sanitization"), but the Expanded query finds it and ranks it at #2, RRF ensures this document still appears in the final fused list, dramatically improving recall.
- **Noise Reduction**: If one query (e.g., the Expanded one) accidentally pulls in an irrelevant document, but the other two queries do not rank it at all, its RRF score will remain low, and it will be pushed down the final list.

In short, we are not fusing paraphrases. We are fusing the results of three distinct retrieval strategies, which is a much more robust and effective method for improving search relevance.

## 5. Core Implementation (System Prompt)
This philosophy is captured directly in the battle-tested system prompt for our `QURComponent`:

```python
def _system_prompt(self) -> str:
    return (
        "You are an expert query rewriter for a compliance search system."
        "Your task is to rewrite a user's query into 3 diverse alternatives."
        "\n"
        "--- CRITICAL OUTPUT FORMAT ---"
        "1.  Your output MUST contain ONLY the 3 rewritten queries."
        "2.  Each query MUST be on a new line."
        "3.  DO NOT use any numbers, bullets, or list markers (e.g., '1.', '-')."
        "4.  DO NOT use any labels or markdown (e.g., '**Keyword:**')."
        "5.  DO NOT use any quotation marks."
        "6.  The output must be perfectly clean."
        "\n"
        "--- REWRITE STRATEGIES ---"
        "Generate one query for each of these 3 strategies:"
        "1.  **Keyword:** Strip the query to its core technical keywords."
        "2.  **Expanded:** Add related technical synonyms or concepts."
        "3.  **Natural Language:** Rephrase the query as a complete, natural-sounding question."
        "\n"
        "--- GUARDRAILS (ABSOLUTE) ---"
        "You MUST preserve any control IDs (e.g., AC-2, IA-5) and placeholders "
        "(e.g., {{ insert: param, ... }}) EXACTLY as they appear. "
        "DO NOT CHANGE, ALTER, OR FABRICATE THESE IDs."
    )
```

This prompt is combined with an aggressive "paranoid" cleanup function in the `generate` method to create a two-stage system that guarantees clean, well-formatted output.

**(UPDATED SECTION)**

## 6. Unit Testing & Integrity
A "zero-trust" system prompt and a "paranoid" cleanup function are our primary lines of defense. The final piece is a **Regression Test Suite** to ensure the component's integrity over time.

The purpose of a unit test is not just to validate the code once, but to **protect it from future breakage.** If we change the system prompt, swap the LLM, or alter the cleanup regex, we must have a safety net to prove we didn't re-introduce old bugs (a "regression").

This test suite is implemented in the final cell of the `QUR_Generator.ipynb` notebook. It is a formal `unittest` class that validates the core promises of the generator.

### The 4 Core Test Promises

**1) `test_01_completeness_contract`**  
- **Promise:** The generator will *always* return 3 rewrites, even if the LLM fails.  
- **Test:** Asserts that `len(rewrites)` is exactly `3`. This validates the fallback logic (which fills with the original query) and guarantees the component can never return an empty or incomplete list, which would break the downstream RRF Fuser.

**2) `test_02_format_integrity`**  
- **Promise:** The output must be 100% clean of all formatting artifacts.  
- **Test:** Asserts that no rewrite starts with list markers (`1.`, `-`, `*`), labels (`**Keyword:**`), or is enclosed in quotation marks. This confirms the "paranoid" cleanup function is working.

**3) `test_03_control_id_preservation`**  
- **Promise:** The generator will never alter, fabricate, or lose a Control ID.  
- **Test:** This test uses a **compliance-aware regex** that is whitelisted with all valid NIST SP 800-53 families (e.g., "AC", "SA", "CA") and correctly parses enhancements (e.g., `CA-2(1)`). It finds all IDs in the query and the rewrite, normalizes them to uppercase, and asserts that the two sets are identical. This robustly verifies ID loyalty.

**4) `test_04_placeholder_preservation`**  
- **Promise:** The generator will preserve any `{{ ... }}` placeholders.  
- **Test:** We pass a query containing a literal placeholder (e.g., `What about {{ insert: param }}`) and assert that all 3 rewrites *also* contain the exact string `{{ insert: param }}`.
