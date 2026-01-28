# Micro‑Ablation Validation (Oracle‑only): S4b + S7a (NIST SP 800‑53)

This folder contains a **focused micro‑ablation** that validates two architectural concerns in our retrieval stack by constructing **oracle (upper‑bound) variants**.

**Scope constraints (current phase):**
- **Only NIST SP 800‑53** (Rev. 4 / Rev. 5).  
- Ignore crosswalk / PCI DSS / HIPAA work (out of scope for this run).
- This notebook **does NOT rerun baselines S4 or S7**; we compare against the S4/S7 results produced by our main `AblationStudy_S1_8.ipynb`.

---

## 1) What we are validating (the “why”)

We proactively designed this micro‑ablation to stress‑test two plausible doubts:

1) **Retrieval (S4 / QUR‑RRF):**  
   Does fusing multiple rewrites help, or does it introduce noise? Would fusing only *one best rewrite* be enough?

2) **Reranking (S7 / ComplianceGPT):**  
   For the cross‑encoder reranker, should we rerank using the **original user query**, or a “cleaner” rewrite?

Earlier versions of this micro‑ablation wrote several separate markdown reports and even included ODP subsets and broad claims based on an older corpus. fileciteturn18file1 fileciteturn18file2 fileciteturn18file3  
This **new version** is intentionally minimal (one notebook + one README) and aligned to our **current clause‑level CCS** and our **current S4/S7 logic** (extracted from `AblationStudy_S1_8.ipynb`).

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

The notebook splits Error Bank into rev4/rev5 subsets by the version column(s) present in your `error_bank_v1.csv`.
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
- `MicroAblation_S4b_S7a_ORACLE_ONLY_twofiles_PERFECT.ipynb`

Steps:
1. **Runtime → Restart runtime**
2. **Run All** (important: the setup cell builds indices and instantiates the cross‑encoder)
3. Confirm you see the CCS loader sanity check print a non‑zero number of records.

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

## 9) Comparing to baselines (S4 / S7 from main ablation)

We compare S4b vs S4 and S7a vs S7 using the S4/S7 CSV outputs from `AblationStudy_S1_8.ipynb`.

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

## 10) Notes / pitfalls

- **Oracle ≠ deployable.** It uses gold labels to choose rewrites, by design.
- **Don’t compare across corpora.** Older micro‑ablation markdown reports were generated on different corpus versions and produced different metric scales and conclusions. fileciteturn18file0 fileciteturn18file1
- **Kind filtering matters.** If you change `keep_kinds`, you must apply the same change in the main ablation notebook to keep results comparable.
- **No hardcoded hashes.** We intentionally do not embed SHA256 hashes in this notebook. We add hashes only after finalizing inputs/outputs for artifact freeze.

---

## 11) Historical note (why we replaced the old markdown set)

Older docs (kept for archival reference) include:
- a multi‑file comparison report and separate per‑system reports fileciteturn18file0 fileciteturn18file2 fileciteturn18file3
- an older README that describes a different implementation structure (class‑based, multiple modes, ODP subsets) and draws conclusions based on that older run fileciteturn18file1

This README supersedes them for the **current clause‑level CCS + oracle‑only two‑file output** workflow.
