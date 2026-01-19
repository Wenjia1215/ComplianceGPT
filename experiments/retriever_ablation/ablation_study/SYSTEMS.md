# Retrieval Systems (S1–S8): Design Rationale + Role in Ablation

This ablation study evaluates eight retrieval systems (S1–S8) used to build the ComplianceGPT retriever.

The goal is not only to maximize Recall@K, but to scientifically isolate:
1) which retrieval failure modes occur in compliance QA, and  
2) which architectural components reduce those failures.

All systems retrieve NIST SP 800-53 controls from the same Canonical Clause Store (CCS),
and are evaluated with the same gold sets and diagnostic ErrorBank.

---

## Big Picture: What the Ablation Is Testing

Compliance QA retrieval fails for predictable reasons:

- **Lexical mismatch**: the question uses words that do not appear in the relevant control text
- **Semantic ambiguity**: multiple controls look similar in meaning
- **ODP sensitivity**: parameter-heavy questions require stable retrieval grounding
- **Ranking instability**: rerankers may promote plausible-but-wrong controls (“rank reversal”)

The systems below form a controlled ladder from basic to advanced,
so each system isolates one additional capability.

---

# S1 — BM25 Baseline (Lexical Retrieval)

**Why we build it**
- BM25 is the standard sparse retrieval baseline.
- In compliance, BM25 represents “keyword search” used in many real audit workflows.

**How it works**
- Tokenize + normalize query
- BM25 retrieves top-K control IDs by lexical overlap

**What it tests**
- Pure lexical matching performance.
- Serves as the baseline used to create portions of ErrorBank.

**Expected behavior**
- Strong on simple literal queries
- Weak on paraphrases and semantic mismatch

---

# S2 — Dense Baseline (Semantic Retrieval)

**Why we build it**
- Dense embeddings handle paraphrases and semantic similarity better than BM25.

**How it works**
- Encode query into embedding space
- Retrieve top-K nearest controls by vector similarity

**What it tests**
- Whether semantic retrieval alone is sufficient for compliance QA.
- Particularly informative on ErrorBank and paraphrase-heavy queries.

**Expected behavior**
- Stronger than BM25 on semantic mismatch
- Can confuse “neighboring controls” with similar meaning

---

# S3 — Rewrite-only (Single Rewrite Replacement)

**Why we build it**
- Query rewriting is common in retrieval systems, but it can help or harm.
- S3 isolates the effect of rewriting without hybrid retrieval or reranking.

**How it works**
- Replace the original query with a rewrite (if available)
- Run BM25 on the rewritten query

**What it tests**
- Whether rewriting helps lexical mismatch or introduces drift.
- A failure here proves that naive rewriting is risky.

**Expected behavior**
- Can improve BM25 on paraphrase queries
- Can degrade performance if rewrites change intent

---

# S4 — QUR + RRF (Rewrite Fusion)

**Why we build it**
- Instead of trusting one rewrite, we fuse multiple query variants.
- This reduces the risk of a bad rewrite dominating.

**How it works**
- Build query set: {original + filtered rewrites}
- Retrieve with BM25 for each variant
- Fuse rankings with weighted Reciprocal Rank Fusion (RRF)

**What it tests**
- Whether rewrite fusion improves recall reliably.
- Tests robustness against rewrite noise.

**Expected behavior**
- More stable than S3
- May still miss cases that require semantic retrieval (dense)

---

# S5 — Hybrid Retrieval via RRF (BM25 + Dense)

**Why we build it**
- BM25 and Dense retrieve complementary evidence.
- Fusion is a standard strategy in high-reliability retrieval.

**How it works**
- BM25 top-N candidates + Dense top-N candidates
- Fuse both ranked lists using Reciprocal Rank Fusion (RRF)

**What it tests**
- Whether retrieval complementarity improves performance without learning.
- This is the core “strong retriever” baseline used by later systems.

**Expected behavior**
- Usually strong overall
- Still struggles with ranking errors in ambiguous cases

---

# S6 — Hybrid + Rerank (Cross-Encoder Reranking)

**Why we build it**
- Rank@1 often depends on correct fine-grained ordering.
- A cross-encoder reranker can refine ordering using deep query-document interaction.

**How it works**
- Generate candidate set using S5
- Apply cross-encoder scoring on (query, candidate_text) pairs
- Reorder candidates by reranker score

**What it tests**
- Whether reranking improves top-1 accuracy.
- Also reveals the risk of “rank reversal” (plausible but wrong promotions).

**Expected behavior**
- Improves Recall@1 on many datasets
- May degrade if reranker is overconfident on wrong matches

---

# S7 — ComplianceGPT Retriever (Safe Multi-Stage Retrieval)

**Why we build it**
S7 is designed as the best *reliability-focused* retriever for compliance.
It integrates rewriting, hybrid retrieval, and reranking, but adds safety constraints.

**How it works (high level)**
1) Generate query variants: original + filtered rewrites
2) Run weighted hybrid retrieval (BM25 + Dense) across variants
3) Fuse candidates using weighted RRF
4) Rerank with cross-encoder using **safe blending**
   - blend base retrieval score with reranker score
   - avoid full rank reversal when reranker evidence is weak

**What it tests**
- The full ComplianceGPT retrieval hypothesis:
  "multi-stage retrieval with safety constraints reduces compliance failure modes."

**Expected behavior**
- Best overall Recall@1 / robustness
- Strong performance on ErrorBank and ODP queries

---

# S8 — Adaptive Retrieval (FAST vs HEAVY Routing)

**Why we build it**
- S7 is strongest but expensive (rewrites + rerank).
- S8 tests whether we can match S7 quality at lower cost by routing queries.

**How it works**
- Compute fast hybrid results (S5-style) + statistics
- Compute confidence score from agreement + margin
- If confident → return FAST (S5)
- Else → call HEAVY retrieval (S7)

**What it tests**
- Whether performance can be preserved with fewer heavy rerank calls.
- A system-level engineering question: quality vs cost.

**Expected behavior**
- Ideally close to S7 accuracy with fewer HEAVY calls
- Provides a cost-aware extension, not necessarily a higher-recall model

---

## Interpreting the Ablation

This ablation supports three conclusions:

1) **Hybrid retrieval (S5) is a strong foundation**
   - BM25 and Dense complement each other

2) **Reranking must be constrained (S7 > S6)**
   - naive reranking can cause rank reversal
   - safe blending / no-harm gating improves reliability

3) **Adaptive routing (S8) is an engineering extension**
   - its value is reduced heavy calls while preserving S7-level accuracy

---

## Reproducibility Notes (What Must Stay Constant)

For a fair ablation comparison, all systems must share:
- the same CCS corpus version (Rev4/Rev5 JSONL)
- the same gold sets + ErrorBank
- the same preprocessing (control ID normalization)
- the same evaluation function and metrics
