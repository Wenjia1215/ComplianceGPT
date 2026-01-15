ComplianceGPT: A Novel RAG for Auditable Compliance

1. Project Goal: The "Why"

The ultimate goal of this project is to build ComplianceGPT: a Retrieval-Augmented Generation (RAG) system designed to answer high-stakes, technical questions about cybersecurity and privacy compliance.

The core problem is that standard RAG systems are not good enough for compliance. The source documents (like NIST SP 800-53) are dense, highly versioned (Rev. 4 vs. Rev. 5), and use specific legal terminology. An answer that is "close enough" is 100% wrong.

Our goal is to build a RAG system that provides auditable, version-aware, and provably accurate answers. The "Generation" (G) part is relatively simple. The entire challenge—and the focus of our research—is in perfecting the "Retrieval" (R) part. If we retrieve the wrong document, the LLM will generate the wrong answer.

2. The Core Problem: Baseline Failure

Our research began by establishing a baseline, System 1 (BM25), a standard keyword-based search. We immediately identified three critical failure modes:

Keyword Mismatch: The user's query ("fix vulnerabilities") does not contain the same keywords as the document's text ("flaw remediation"). BM25 fails.

Generic Phrasing: Vague user queries ("What are the requirements for access control?") do not match any specific, high-value text.

Semantic Gaps: The system does not understand that "personnel" and "individuals" are synonyms in this context.

Our entire research plan is designed to find the best possible solution to these specific failure modes.

3. Our Research Plan (The 3-Notebook Structure)

To solve this problem scientifically, we have structured our work into three distinct phases and notebooks.

Notebook 1: QUR_Simple_Benchmark.ipynb

Hypothesis: Can we "fix the query" by using an LLM as a "Translator" to rewrite it with better keywords?

System Tested: System 2 (QUR-Simple)

Findings: This "patch" works, but it is extremely slow, expensive, and difficult to tune. We found that a 3B-parameter LLM (Qwen-3B) was too slow for this task, while a 1.5B model was "good enough," proving this is a delicate, time-consuming process.

Notebook 2: Retrieval_4Way_Ablation_Study.ipynb

Hypothesis: Can we "fix the search engine" itself, so it doesn't need the query to be rewritten?

Systems Tested (The "Bake-Off"): This is a 4-way race to compare modern, non-QUR architectures.

System 1 (BM25) - The Baseline

System 3 (Dense) - The Semantic Fix

System 4 (Hybrid) - The "Best of Both Worlds"

System 5 (Hybrid + Reranker) - The "Expert Judge"

Goal: To scientifically prove which non-QUR architecture provides the best performance and is the most robust fix for our failure modes.

Notebook 3: Final_ComplianceGPT_Retriever.ipynb

Hypothesis: The ultimate retrieval system will be a "super-hybrid" that combines the best ideas from all experiments.

System Tested: System 6 (ComplianceGPT Retriever)

Goal: To build and evaluate our final, novel, multi-stage architecture (based on our supervisor's "Figure 2" diagram) that uses QUR, Hybrid, and Reranking all together.

4. The 6 Retrieval Systems Explained

This project evaluates six distinct retrieval architectures in total.

The "Bake-Off" Competitors (Systems 1-5)

BM25 (The Baseline)

How it works: A simple, fast, non-AI algorithm that matches exact keywords. It's our baseline to measure all other systems against.

QUR-Simple (Solution A: "The Translator")

How it works: Query -> Qwen-1.5B (LLM) -> 3 Rewritten Queries -> BM25 Search.

Solves: Keyword Mismatch.

Weakness: Very slow, expensive, and complex to tune.

Dense (Solution B: "The Semantic Matcher")

How it works: Query -> Embedding Model -> FAISS Vector Search.

Solves: Keyword Mismatch and Semantic Gaps. It natively understands that "fix vulnerabilities" and "flaw remediation" are semantically close because their vector embeddings are mathematically similar.

Hybrid (Solution C: "Best of Both Worlds")

How it works: Runs BM25 and Dense searches in parallel and combines their rank lists using Reciprocal Rank Fusion (RRF).

Solves: Catches both exact keyword matches and semantic meaning matches.

Hybrid + Reranker (Solution D: "The Judge")

How it works: A two-stage system.

Stage 1 (Retrieve): The Hybrid system finds the Top 50 potential candidates.

Stage 2 (Rerank): A powerful CrossEncoder model (the "Judge") reads the query and each of the 50 candidates together to produce a final, highly-accurate Top 10 list.

The Final System (System 6)

ComplianceGPT Retriever (The Ultimate System)

This is our final, novel architecture that combines all of our successful techniques into one "super-hybrid" pipeline.

How it works:

QUR: Query is first sent to the Qwen-1.5B LLM to get 3 optimized rewrites.

Hybrid Search: A Hybrid (BM25 + Dense) search is run for all 3 of those rewrites.

Pool: All candidate documents from all searches are pooled into one large list.

Rerank: The CrossEncoder ("The Judge") re-scores this entire pool to find the absolute best Top 10 answers.

5. Our Novelty & Contribution

Our novelty is not in "inventing" hybrid search. Our scientific contribution is threefold:

The Benchmark: We created a specialized test suite, including our Error Bank, to scientifically measure retrieval performance on the unique failure modes of compliance data.

The Ablation Study (The Proof): We are the first to conduct a rigorous, head-to-head "bake-off" comparing these 5 architectures (QUR vs. Dense vs. Hybrid) for this specific, high-stakes domain.

The Novel Architecture: Our final ComplianceGPT Retriever (System 6) is a new, multi-stage pipeline that combines these components in a novel way, specifically designed to provide the state-of-the-art in auditable, accurate compliance retrieval.