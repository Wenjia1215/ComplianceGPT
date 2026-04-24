# Micro‑Ablation Validation (Oracle‑only): S4b + S7a (NIST SP 800‑53)

This folder contains a **focused micro‑ablation** that validates two architectural concerns in our retrieval stack by constructing **oracle (upper‑bound) variants**.

**Scope constraints (current phase):**
- **Only NIST SP 800-53** (Rev. 4 / Rev. 5).
- This notebook **does NOT rerun baselines S4 or S7**; we compare against the S4/S7 results produced by our main `AblationStudy_S1_7.ipynb`.

---

## 1) What we are validating (the “why”)

We proactively designed this micro‑ablation to stress‑test two plausible doubts:

1) **Retrieval (S4 / QUR‑RRF):**
   Does fusing multiple rewrites help, or does it introduce noise? Would fusing only *one best rewrite* be enough?

2) **Reranking (S7 / ComplianceGPT):**
   For the cross‑encoder reranker, should we rerank using the **original user query**, or a “cleaner” rewrite?

Earlier versions of this micro‑ablation wrote several separate markdown reports and even included ODP subsets and broad claims based on an older corpus.
This **new version** is intentionally minimal (one notebook + one README) and aligned to our **current clause‑level CCS** and our **current S4/S7 logic** (extracted from `AblationStudy_S1_7.ipynb`).

---

## 2) Oracle definition (upper bound, not deployable)

**Oracle = “theoretical upper bound.”**
For each question, we generate **3 rewrites** and then **peek at the gold control ID** to select the rewrite that performs best in Stage‑1 retrieval.

**Requirement B (“best scoring rewrite”):**
1. Generate 3 rewrites for the question.
2. For each rewrite `r`, run **Stage‑1 hybrid retrieval** (BM25 + Dense + RRF).
3. Compute the **rank of the gold control** in that fused Stage‑1 ranking.
4. Choose the rewrite with the **lowest (best) gold rank**.
   (Tie‑break by the fused score.)

Because this uses the gold label, it is **not a production method**. It is a tool to answer:
> “If rewrite selection were perfect, would this design choice help or hurt?”

---

## 3) Systems produced by this notebook (what runs here)

This notebook runs **only the oracle variants**:

### 3.1 S4b — Oracle best‑rewrite fusion (retrieval micro‑ablation)
- Baseline S4 (from main ablation): **QUR‑RRF** fusing original + multiple rewrites.
- **S4b (this notebook):** fuse **original + oracle‑best rewrite only**.

Implementation notes:
- Retrieval is lexical BM25 at the **control level**, using control docs built by aggregating clause texts.
- Fusion uses **weighted RRF** (config below).

### 3.2 S7a — Oracle best‑rewrite rerank query (reranking micro‑ablation)
- Baseline S7 (from main ablation): ComplianceGPT two‑stage retrieval + rerank; reranker uses **original query**.
- **S7a (this notebook):** candidate generation is unchanged, but the cross‑encoder reranker uses the **oracle‑best rewrite as the rerank query**.

Implementation notes:
- Stage‑1 candidate generation uses our current “superhybrid” approach (BM25 original + BM25 rewrites + Dense original fused by RRF).
- Stage‑2 uses a cross‑encoder with **safe blending** (config below).

### 3.3 Why the names are S7a and S4b?

The suffix letters a/b do not indicate a system version number. They indicate the micro-ablation experiment ID (two different validation questions):

Ablation (a): Reranking input question — should the reranker score candidates using the original query or a rewrite?

Baseline: S7 (rerank with original query)

Variant: S7a (rerank with oracle-best rewrite)

Ablation (b): Fusion breadth question — during retrieval fusion, should we fuse multiple rewrites or only the single best rewrite?

Baseline: S4 (multi-rewrite fusion)

Variant: S4b (oracle best-rewrite-only fusion)

In short: System ID + Experiment ID → S7 + a = S7a, S4 + b = S4b.

---

## 4) Inputs (data + rewrites)

### 4.1 Clause‑level CCS (flat JSONL)
We use the flattened clause‑level CCS JSONL with fields like:
`clause_id`, `control_id`, `title`, `text`, `kind`.

Paths (Colab/Drive):
```python
REV5_CATALOG_PATH = "/content/drive/MyDrive/compliance_data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl"
REV4_CATALOG_PATH = "/content/drive/MyDrive/compliance_data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl"
```

By default we keep clause `kind` in `("smt", "gdn")` to match our current main notebook behavior.

### 4.2 Gold sets + Error Bank
```python
REV5_GOLD_CSV = "/content/drive/MyDrive/compliance_data/gold_standard_datasets/nist800_53/nist_sp800-53_rev5_gold-set_100q.csv"
REV4_GOLD_CSV = "/content/drive/MyDrive/compliance_data/gold_standard_datasets/nist800_53/nist_sp800-53_rev4_gold-set_36q.csv"
ERROR_BANK_CSV = "/content/drive/MyDrive/compliance_data/error_bank/error_bank_v1.csv"
```

The notebook splits Error Bank into rev4/rev5 subsets by the version column(s) present in `error_bank_v1.csv`.
(So counts can differ across older reports.)

### 4.3 QUR rewrite CSVs (3 rewrites per question)
```python
QUR_CSV_REV5 = "/content/drive/MyDrive/compliance_outputs/outputs_qur/qur_rewrites_rev5.csv"
QUR_CSV_REV4 = "/content/drive/MyDrive/compliance_outputs/outputs_qur/qur_rewrites_rev4.csv"
QUR_CSV_ERRB = "/content/drive/MyDrive/compliance_outputs/outputs_qur/qur_rewrites_error_bank.csv"
```

Minimum required columns:
- original query text (e.g., `original_query` / `question`)
- rewritten query text (e.g., `rewritten_query` / `rewrite`)
- a stable ordering per question (e.g., `rewrite_rank`) **or** pre‑sorted rows

---

## 5) Configuration (current run defaults)

These are the critical knobs for matching our current S4/S7 design:

```python
# BM25 defaults (match main notebook)
BM25_K1 = 1.5
BM25_B  = 0.75

# Fusion / RRF
RRF_K_DEFAULT  = 60
REWRITE_WEIGHT = 0.25   # how much rewrite runs contribute vs original in RRF

# Rerank safe blending
RERANK_ALPHA = 0.65     # final_score = alpha * base_rrf + (1-alpha) * rerank_score

# Rewrite filtering inside candidate generation (if enabled in our current S7 logic)
REWRITE_JACCARD_MIN = 0.15

# Oracle selection
NUM_REWRITES_FOR_SELECTION = 3
CANDIDATE_SET_SIZE         = 50
```

---

## 6) Evaluation contract (what “correct” means)

**Correctness unit:** control ID hit (e.g., `AC-2`).
Even though we retrieve over clause content, we evaluate whether the **gold control** appears in the top‑K ranked control list.

**Metrics written per query:**
- `rank` (rank of gold control within top‑K list; 0 if not found)
- `Recall@1`, `Recall@5`, `Recall@10` (hit rates)
- `MRR@10` (1/rank if rank ≤ 10 else 0)
- `nDCG@10` (single‑relevant‑item DCG; 1/log2(rank+1) if rank ≤ 10 else 0)

---

## 7) How to run (Colab)

Open:
- `MicroAblation_S4b_S7a.ipynb`

Steps:

1. **Runtime → Restart runtime** (Choose T4 GPU OR BETTER)

2. **Run All** (important: the setup cell builds indices and instantiates the cross‑encoder)

3. Confirm the CCS loader sanity check print a non‑zero number of records.

---

## 8) Outputs (ONLY two files)

All outputs are saved to:
```python
ABLATION_OUTPUT_DIR = "/content/drive/MyDrive/ablation_outputs/micro_ablations"
```

This notebook writes **exactly two CSVs**:
- `S4b_rrf_best_ALL.csv`
- `S7a_rerank_best_ALL.csv`

Schema (both files):
- `dataset` (e.g., `rev5_gold`, `rev4_gold`, `error_bank_rev5`, `error_bank_rev4`)
- `question_id`, `question`
- `gold_control_id`
- `rank`, `is_hit_at_1`, `is_hit_at_5`, `is_hit_at_10`
- `mrr@10`, `ndcg@10`
- `top_1_hit`
- `retrieved_control_ids` (pipe‑separated string)
- `system_meta` (JSON string; includes whether an oracle rewrite was used)

---

## 9) Results (this run: 2026-02-11)

This section summarizes the **oracle-only** outputs produced by this notebook:
- `S4b_rrf_best_ALL.csv`
- `S7a_rerank_best_ALL.csv`

**Sanity checks passed** (per-file): expected row counts per dataset, unique `(dataset, question_id)`, and metric consistency with `rank` for `MRR@10` / `nDCG@10`.

**S4b (oracle best-rewrite-only fusion)**

| dataset | N | Recall@1 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---:|---:|---:|---:|---:|---:|
| rev5_gold | 100 | 0.710 | 0.960 | 0.980 | 0.824 | 0.863 |
| rev4_gold | 36 | 0.694 | 0.917 | 0.917 | 0.772 | 0.808 |
| error_bank_rev5 | 24 | 0.083 | 0.875 | 0.917 | 0.444 | 0.565 |
| error_bank_rev4 | 13 | 0.231 | 0.769 | 0.769 | 0.429 | 0.515 |
| ALL | 173 | 0.584 | 0.925 | 0.942 | 0.731 | 0.784 |

**S7a (oracle best-rewrite as rerank query)**

| dataset | N | Recall@1 | Recall@5 | Recall@10 | MRR@10 | nDCG@10 |
|---|---:|---:|---:|---:|---:|---:|
| rev5_gold | 100 | 0.860 | 0.970 | 0.990 | 0.913 | 0.933 |
| rev4_gold | 36 | 0.861 | 1.000 | 1.000 | 0.922 | 0.942 |
| error_bank_rev5 | 24 | 0.583 | 0.917 | 0.958 | 0.727 | 0.785 |
| error_bank_rev4 | 13 | 0.538 | 1.000 | 1.000 | 0.731 | 0.799 |
| ALL | 173 | 0.798 | 0.971 | 0.988 | 0.876 | 0.904 |

**Delta (S7a - S4b)**

| dataset | N | ΔRecall@1 | ΔRecall@5 | ΔRecall@10 | ΔMRR@10 | ΔnDCG@10 |
|---|---:|---:|---:|---:|---:|---:|
| rev5_gold | 100 | 0.150 | 0.010 | 0.010 | 0.089 | 0.069 |
| rev4_gold | 36 | 0.167 | 0.083 | 0.083 | 0.150 | 0.134 |
| error_bank_rev5 | 24 | 0.500 | 0.042 | 0.042 | 0.283 | 0.220 |
| error_bank_rev4 | 13 | 0.308 | 0.231 | 0.231 | 0.301 | 0.284 |
| ALL | 173 | 0.214 | 0.046 | 0.046 | 0.145 | 0.120 |

**Interpretation (bounded):**
- These results are **upper bounds** because they use gold labels to select the “best” rewrite.
- To answer the original design questions (S4b vs S4, and S7a vs S7), compare these CSVs against the corresponding baseline outputs from `AblationStudy_S1_7.ipynb` using `(dataset, question_id)` joins.


## 10) Comparing to baselines (S4 / S7 from main ablation)

We compare S4b vs S4 and S7a vs S7 using the S4/S7 CSV outputs from `AblationStudy_S1_7.ipynb`.

Recommended join keys:
- `dataset`
- `question_id`

Example comparison snippet:
```python
import pandas as pd

s4b = pd.read_csv("/content/drive/MyDrive/ablation_outputs/micro_ablations/S4b_rrf_best_ALL.csv")
s7a = pd.read_csv("/content/drive/MyDrive/ablation_outputs/micro_ablations/S7a_rerank_best_ALL.csv")

s4  = pd.read_csv(".../S4_qur_rrf_ALL.csv")            # produced by main ablation
s7  = pd.read_csv(".../S7_compliance_gpt_ALL.csv")     # produced by main ablation

m4 = s4.merge(s4b, on=["dataset","question_id"], suffixes=("_S4","_S4b"))
m7 = s7.merge(s7a, on=["dataset","question_id"], suffixes=("_S7","_S7a"))
```

---

## 11) Notes / pitfalls

- **Oracle ≠ deployable.** It uses gold labels to choose rewrites, by design.

- **Kind filtering matters.** If one change `keep_kinds`, one must apply the same change in the main ablation notebook to keep results comparable.


---

## 12) why only s4 & s7

why the others were excluded from this specific Oracle study:

1. Why S4? (The "Recall Champion")
Role: S4 (QUR-RRF) represents Stage 1 Retrieval Strategy.

The Question it answers: "When we cast the net to find candidates, should we trust one 'perfect' rewrite, or fuse them all together?"

Why not S3? S3 (Rewrite-Replace) is a known inferior architecture (single-point-of-failure). We already know fusion (S4) beats replacement (S3) in the main ablation. We don't need an Oracle to prove S3 is risky.

Why not S5? S5 is just Hybrid RRF without QUR. The "Oracle" test is specifically about Rewrites. Since S5 doesn't use rewrites, an Oracle test is mathematically impossible for it.

2. Why S7? (The "Precision Champion")
Role: S7 (ComplianceGPT) represents Stage 2 Reranking Strategy (The Final System).

The Question it answers: "When the expensive reranker judges a document, should it look at the user's messy query or the AI's clean rewrite?"

Why not S6? S6 is the Reranker without the advanced Candidate Generation. S7 is effectively "S6 + S4". By testing S7, we are testing the Reranker in its final, best environment. If the "Original Query" strategy wins in S7, it applies to S6 too. Testing S6 separately is redundant.

Summary for Dissertation Defense
"We focused the micro-ablation on the two terminal nodes of our architectural decision tree:"

S4 (Candidate Generation): Proving that Fusion is safer than Selection.

S7 (Final Reranking): Proving that Original Intent is more precise than Rewritten Text.

S3, S5, and S6 are intermediate steps. Validating the "Champions" (S4 and S7) implicitly validates the logic for the whole pipeline.
