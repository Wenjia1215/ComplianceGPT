# ComplianceGPT — Answerer v0

**Date:** 2025-10-01

This package contains a reproducible baseline for a lightweight, **hybrid RAG** answerer using a small instruct model on Colab plus BM25 retrieval. It focuses on **NIST SP 800-53 (rev4, rev5), HIPAA Security Rule (2023, 2024), PCI-DSS (3.2.1, 4.0)**.

---

## 1. Model & Reproducibility

- **Model (pinned):** `Qwen/Qwen2.5-7B-Instruct-AWQ`
- **Tokenizer:** same as model ID
- **Quantization:** AWQ (4-bit) (weights are already quantized in the above repo)
- **Min GPU memory:** ~10–12GB VRAM recommended for comfortable generation with context; smaller VRAM may work with reduced max tokens.
- **Decoding for eval (deterministic):**
  - `temperature=0.0`
  - `top_p=1.0`
  - `top_k=0`
  - `seed=42`

To switch models, `Llama-3.1-8B-Instruct` (fp16 or 4-bit GGUF via llama.cpp) is a fine alternate; keep the same decoding params and log the exact checkpoint tag/commit.

---

## 2. Safety & Compliance Guardrails

- **No unsupported answers:** system prompt requires “answer only from retrieved context; otherwise state insufficient info.”
- **Citation required:** answers must include bracketed citations (e.g., `[NIST AC-2(3); HIPAA 164.308(a)(1)(ii)(A)]`). If no citations, discard/return null.
- **PHI/PII redaction in logs:** apply `guardrails.mask_log(text)` before storing queries/retrieval context.
- **ODP awareness:** NIST ODP placeholders (e.g., `Organization-Defined Parameter`, `ODP`, `{organization-defined}`) trigger deferral/request for the value; see `guardrails.detect_odp(text)`.

---

## 3. Data Scope

Index exactly these versions (feel free to edit the paths in your Colab):

- `nist_sp800-53/rev4.jsonl`, `nist_sp800-53/rev5.jsonl`
- `hipaa/2023.jsonl`, `hipaa/2024.jsonl`
- `pci/3_2_1.jsonl`, `pci/4_0.jsonl`

Normalization choices:
- Lowercase for BM25 tokenization
- Strip multiple spaces, preserve control IDs verbatim
- Keep `framework`, `version`, `control_id`, `title`, `text`, `category`, `effective_date` (if present)

BM25 implementation: `rank_bm25.BM25Okapi` with defaults (k1=1.5, b=0.75). Document text = `title + " — " + text` (chunked to ~800 tokens with ~120 overlap as needed).

---

## 4. Interface

**Endpoint contract (pseudo):**

- **Input JSON:**
  ```json
  {
    "question": "How should inactive accounts be handled?",
    "preferred_versions": {"NIST":"rev5","HIPAA":"2024","PCI":"4.0"},
    "topk": 8
  }
  ```
- **Output JSON:**
  ```json
  {
    "answer": "Disable or remove ... [NIST AC-2(3); PCI 8.2.6]",
    "citations": [
      {"framework":"NIST","id":"AC-2(3)","title":"Account Management","version":"rev5","score":0.81},
      {"framework":"PCI","id":"8.2.6","title":"...","version":"4.0","score":0.74}
    ],
    "retrieval_debug": {"bm25_topk":60,"emb_topk":60,"rrf_k":60},
    "confidence": 0.67
  }
  ```

**Colab run steps:**
1. `pip install -U transformers accelerate autoawq sentence-transformers faiss-cpu rank_bm25 tiktoken rapidfuzz`
2. Mount/upload your six JSONL files under `/content/ccs/...`
3. Run the RAG cells (index build, retrieval, generation).
4. For BM25-only metrics: use `scripts/eval_bm25.py` with `templates/queries_gold.csv`.

---

## 5. Metrics & Evaluation (BM25-only slice)

**Tasks:** Provide results for 6 queries/tasks (or more).  
**Metrics:** Recall@k and nDCG@k for k ∈ {1,3,5,10}.  
**Deliverables:**
- `retrieval_results.csv` — per-query metrics
- `retrieval_aggregate.csv` — micro avg across queries
- Short write‑up: BM25 parameters, tokenization, indexed versions

Run:
```bash
python scripts/eval_bm25.py   --jsonl_root /content/ccs   --queries_csv templates/queries_gold.csv   --out_csv retrieval_results.csv   --aggregate_csv retrieval_aggregate.csv
```

---

## 6. Citation Precision & Error Taxonomy

Fill `templates/citation_precision_template.csv` after manual review.  
Include a confusion table and 5–10 examples across: over‑citation, under‑citation, off‑by‑version, wrong framework, fabricated reference, unsupported claim.

---

## 7. No‑Hallucination / ODP awareness

- Report `% of answers fully supported by cited clauses`
- Show 2–3 cases where ODP was detected and answerer defers/asks for the ODP value.

---

## 8. JSONL fixes

- Regenerate `pci/v4_0_to_v4_0_1.jsonl` (typo fixed; see below).
- Rename `hippa_2023to2024.jsonl` → `hipaa_2023_to_2024.jsonl`.
- Use `scripts/validate.py` to check schema compliance.

---

## 9. Seeds & Logs

- `seed=42`
- Log: model ID, tokenizer ID, decoding params, BM25 params, chunk size/overlap, index commit hash

---

## 10. Contact

This is a v0 baseline. Tighten retrieval, then consider small QLoRA for style normalization only.
