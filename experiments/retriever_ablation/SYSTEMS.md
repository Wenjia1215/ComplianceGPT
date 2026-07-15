# Retrieval Systems (S1–S7): Design Rationale and Role in Ablation

This frozen ablation study evaluates seven retrieval systems used to build and justify the ComplianceGPT retriever.

The goal is not only to maximize Recall@K. The study also isolates which retrieval failure modes occur in compliance QA and which architectural components reduce those failures.

All systems retrieve NIST SP 800-53 controls from the same Canonical Clause Store (CCS) and are evaluated with the same gold sets and diagnostic ErrorBank.

---

## Big Picture: What the Ablation Tests

Compliance QA retrieval fails for predictable reasons:

- **Lexical mismatch:** the question uses words that do not appear in the relevant control text.
- **Semantic ambiguity:** multiple controls look similar in meaning.
- **ODP sensitivity:** parameter-heavy questions require stable retrieval grounding. ODP-sensitive retrieval is evaluated through questions whose governing clauses contain unresolved parameter placeholders. The frozen S1–S7 retrieval corpus does not treat standalone ODP/PRM records as ordinary cited evidence candidates.
- **Ranking instability:** rerankers may promote plausible but wrong controls.

The systems below form a controlled ladder from basic to advanced, so each system isolates one additional capability.

---

## S1 — BM25 Baseline

**Why we build it**

- BM25 is the standard sparse retrieval baseline.
- In compliance, BM25 represents keyword search used in many audit workflows.

**How it works**

- Tokenize and normalize the query.
- Retrieve top-K control IDs by lexical overlap.

**What it tests**

- Pure lexical matching performance.
- Baseline behavior used to identify portions of the diagnostic ErrorBank.

**Expected behavior**

- Strong on simple literal queries.
- Weak on paraphrases and semantic mismatch.

---

## S2 — Dense Baseline

**Why we build it**

- Dense embeddings can handle paraphrase and semantic similarity better than sparse lexical matching.

**How it works**

- Encode the query into embedding space.
- Retrieve top-K nearest controls by vector similarity.

**What it tests**

- Whether semantic retrieval alone is sufficient for compliance QA.
- Performance on paraphrase-heavy and ErrorBank cases.

**Expected behavior**

- Stronger than BM25 on semantic mismatch.
- Can confuse neighboring controls with similar meaning.

---

## S3 — Rewrite-only

**Why we build it**

- Query rewriting is common in retrieval systems, but it can help or harm.
- S3 isolates the effect of rewriting without hybrid retrieval or reranking.

**How it works**

- Replace the original query with one rewrite if available.
- Run BM25 on the rewritten query.

**What it tests**

- Whether rewriting alone bridges terminology mismatch.
- Whether rewriting causes topic drift when used without fusion.

**Expected behavior**

- Can improve some semantic mismatch cases.
- Can degrade performance if the rewrite drops important terms.

---

## S4 — QUR + RRF

**Why we build it**

- Single-rewrite replacement is fragile.
- Fusing the original query with multiple rewrites is safer than replacing the query.

**How it works**

- Retrieve with BM25 for the original query and accepted rewrites.
- Fuse rankings using Reciprocal Rank Fusion.

**What it tests**

- Whether controlled query rewriting improves lexical retrieval.
- Whether keeping the original query reduces rewrite drift.

**Expected behavior**

- More stable than S3.
- Still limited because it uses lexical retrieval only.

---

## S5 — Hybrid RRF

**Why we build it**

- BM25 and dense retrieval capture different signals.
- Hybrid retrieval tests whether lexical and semantic evidence complement each other.

**How it works**

- Run BM25 retrieval.
- Run dense retrieval.
- Fuse both result lists using Reciprocal Rank Fusion.

**What it tests**

- Whether lexical and semantic retrieval complement each other.
- Whether hybrid fusion improves recall and rank stability.

**Expected behavior**

- Stronger than either BM25-only or dense-only on most sets.
- May still require reranking for fine-grained top-1 accuracy.

---

## S6 — Hybrid + Rerank

**Why we build it**

- Rank@1 often depends on correct fine-grained ordering.
- A cross-encoder reranker can refine ordering using direct query-document interaction.

**How it works**

- Generate a candidate set using S5.
- Apply cross-encoder scoring on `(query, candidate_text)` pairs.
- Reorder candidates by reranker score.

**What it tests**

- Whether reranking improves top-1 accuracy.
- Whether reranking introduces rank reversal errors.

**Expected behavior**

- Can improve Recall@1 on harder datasets.
- Can degrade results if the reranker is overconfident on wrong matches.

---

## S7 — Frozen Guarded Retriever

This section describes the notebook-local implementation that produced the
stored RQ1 rows.  The current revision-specific runtime is tracked separately
because it also transforms retrieval queries, applies privilege-scope score
adjustments, and relaxes the adoption margin under low base confidence.  The
matched current-source study is documented in `experiments/micro_ablations/`.

**Why we build it**

S7 is the reliability-focused design evaluated in the frozen ladder. It integrates controlled rewriting, hybrid retrieval, and reranking with safety constraints.

**How it works**

1. Generate query variants: original query plus filtered rewrites.
2. Run weighted hybrid retrieval across variants.
3. Fuse candidates using weighted Reciprocal Rank Fusion.
4. Rerank with a cross-encoder using safe blending.
5. Apply gating to reduce unnecessary reranking and avoid weak rank reversals.
6. Extract clause-level evidence for downstream evidence selection.

**Gating behavior**

- Pre-rerank skip gate:
  - compute `base_margin_ratio = (s1 - s2) / max(s1, eps)` on fused base scores;
  - skip reranking if the base ranking is already sufficiently confident.
- Post-rerank no-harm gate:
  - if reranking changes top-1 but the rerank margin is too weak, revert to the base order.
- Audit fields, when available, include `reranker_called`, `rerank_applied`, `skip_reason`, `base_margin_ratio`, `rerank_margin_ratio`, and `final_margin_ratio`.

**Related variants used in the separate performance benchmark**

- `S7_gated`: production S7 with skip gate enabled.
- `S7_worst_always_rerank`: same ranking/rerank pipeline but skip gate disabled.

**What it tests**

- The full ComplianceGPT retrieval hypothesis: multi-stage retrieval with safety constraints reduces compliance retrieval failure modes.

**Expected behavior**

- Best overall robustness in the active ablation ladder.
- Strong performance on ErrorBank and ODP queries.

---

## Interpreting the Ablation

This ablation supports three conclusions:

1. **Hybrid retrieval is a strong foundation.** BM25 and dense retrieval complement each other.
2. **Reranking must be constrained.** Unconstrained reranking can cause rank reversal, while safe blending and no-harm gating improve reliability.
3. **Frozen S7 establishes the guarded design.** The current runtime preserves that design family while adding separately recorded query-planning and scope logic.

---

## Reproducibility Notes

For a fair comparison, all systems must share:

- the same CCS corpus version for Rev4 and Rev5,
- the same gold sets and ErrorBank,
- the same preprocessing,
- the same control-ID normalization,
- the same enhancement canonicalization rules,
- the same evaluation function and metrics.
