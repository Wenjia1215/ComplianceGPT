# Clause-Level CCS Builder (NIST SP 800-53 Rev4/Rev5)

This folder contains the **reproducible build step** that turns the original NIST OSCAL catalog JSON into a **clause/part-level Canonical Clause Store (CCS)** in JSONL format.

It exists because our evaluation gold sets (Rev4 36Q, Rev5 100Q) cite evidence at **clause/part granularity** (e.g., `ac-2_smt.h.1`). A control-level corpus (IDs like `ac-2`, `ac-2.1`) cannot match those citations, so strict doc-id/citation evaluation becomes impossible.

---

## Why clause-level CCS is required

### The problem
- NIST OSCAL catalogs represent each control as a tree of **parts** (`parts[]`), including:
  - statement/requirements (`*_smt*`)
  - guidance (`*_gdn*`)
  - assessment objectives (`*_obj*`)
- Our gold sets’ `gold_control_path` points to these **part IDs**, not just the top-level control IDs.

If the CCS only contains control IDs (e.g., created by a “one record per control” converter), then:
- the retriever can only return `ac-2`-style IDs,
- the pipeline cannot cite `ac-2_smt.*` IDs,
- strict evaluation reports 100% missing evidence IDs even if the semantic answer is “right”.

### The fix
Build a CCS where **each JSONL line corresponds to one OSCAL part ID** such as:
- `ac-2_smt.h`
- `ac-2_smt.h.1`
- `ac-2_gdn`
- `ac-2_obj.1`, etc.

This makes the system:
- **citation-evaluable** at the same granularity as the gold sets,
- compatible with “verbatim evidence + provenance” claims, and
- compatible with a verifier that checks extracted spans exist in the corpus.

---

## Inputs and outputs

### Inputs
- `NIST_SP-800-53_rev5_catalog.json` (original OSCAL JSON)
- `NIST_SP-800-53_rev4_catalog.json` (original OSCAL JSON)

### Outputs (clause-level CCS JSONL)
- `NIST_SP-800-53_rev5_catalog.jsonl`
- `NIST_SP-800-53_rev4_catalog.jsonl`

---

## JSONL record schema

Each line is a single JSON object:

```json
{
  "id": "ac-2_smt.h.1",
  "control_id": "ac-2",
  "title": "Account Management",
  "text": "The organization ...",
  "kind": "smt",
  "part_name": "item",
  "label": "h.1",
  "parent_part_id": "ac-2_smt.h",
  "has_prose": true,
  "used_descendants": false,
  "provenance": {
    "oscal_catalog_version": "5.1.1+u4",
    "oscal_catalog_title": "Electronic Version of NIST SP 800-53 ...",
    "version_label": "rev5"
  }
}
```

Field meanings:
- `id`: **the clause/part ID** used for citations and evaluation (must align with `gold_control_path`)
- `control_id`: base control/enhancement ID (e.g., `ac-2`, `ac-2.1`)
- `text`: the evidence text used by retriever and pipeline
- `kind`:
  - `smt` if `id` contains `_smt`
  - `gdn` if `id` contains `_gdn`
  - `obj` if `id` contains `_obj`
- `label`: if available from OSCAL part props (e.g., `a.`, `1.`, etc.); empty string otherwise
- `parent_part_id`: parent part’s ID (empty if root)
- `has_prose`: True if this part had its own OSCAL `prose`
- `used_descendants`: True if we synthesized `text` by concatenating descendant prose (see below)
- `provenance`: minimal metadata for reproducibility and auditing

---

## Build logic (high-level)

We traverse the OSCAL catalog:
1. Visit every control + nested enhancement controls.
2. Traverse every `part` in the control’s parts tree.
3. Keep only parts whose IDs classify as one of: `_smt`, `_gdn`, `_obj`.
4. Create one JSONL record per part ID.

### Handling parts with missing prose (`used_descendants`)
Many OSCAL nodes are structural and may have no `prose` (common for statement/objective roots).
However, gold sets may cite those IDs (e.g., `ac-1_smt`), so the CCS must contain them.

For such nodes, we synthesize `text` by concatenating descendant prose (with labels where available), and mark:
- `has_prose = false`
- `used_descendants = true`

This makes citation coverage possible without hiding the fact that the text is derived.

**Recommendation for “provably extractive” claims:**
- Prefer to cite leaf parts with `has_prose=true` when possible.
- If a gold citation points to a structural node, `used_descendants=true` provides a deterministic, auditable fallback.

---

## Gold coverage validation

The builder includes an optional validation step:
- parses each row’s `gold_control_path`
- splits IDs by newline and `;`
- applies a minimal normalization:
  - `ac_11_*` → `ac-11_*` (underscore → hyphen between family and number)
- reports missing IDs vs the generated JSONL.

A successful build should report **0 missing unique gold IDs** for both rev4 and rev5.

---

## Integration with ComplianceGPT 

With clause-level CCS (compare to control-level):
- the retriever’s corpus size increases (~6–7k records, not ~1k)
- returned evidence IDs become clause IDs (matching gold)
- strict evaluation becomes meaningful (MissedDocIds/ExtraDocIds reflect real errors)

**Critical integration note:**
If any pipeline logic filters to only `_smt` IDs, it must be updated to allow `_gdn` and `_obj` when questions or gold sets require them. Otherwise, pipeline can still fail strict citation checks even with a correct corpus.

---

## Reproducibility checklist

For each experiment run, record:
1. Input OSCAL JSON filenames + SHA-256 hashes
2. Builder version (notebook/script commit hash)
3. Output JSONL filenames + SHA-256 hashes
4. Gold set filenames + SHA-256 hashes
5. Retrieval config (BM25 params, embedding model, reranker model)
6. Generator/pipeline/verifier versions (commit hashes)

To our Readers: This is the minimum needed for a reader to reproduce the exact corpus and evaluation.

---

## Notes: 
To my dissertation, this build step directly supports the core dissertation contributions:
- **Version-aware retrieval:** rev4 and rev5 corpora are built separately and traceably.
- **ODP-aware QA:** ODP placeholders (`{{ insert: ... }}`) appear in clause text and can be detected deterministically.
- **Citation-contracted answering:** answer evidence IDs match a canonical, auditable clause store.
- **Provably extractive verification:** a verifier can check that cited spans are present in the corpus (and can treat `used_descendants` nodes explicitly as derived).

---

## Usage

### Option A: Notebook (recommended )
Run the dedicated notebook:
- `build_clause_level_ccs.ipynb`

### Option B: Script
Run the script from the repo root:

```bash
python builder_clause_level_ccs \
  --rev5_oscal_json path/to/NIST_SP-800-53_rev5_catalog.json \
  --rev4_oscal_json path/to/NIST_SP-800-53_rev4_catalog.json \
  --out_rev5_jsonl path/to/NIST_SP-800-53_rev5_catalog_clause.jsonl \
  --out_rev4_jsonl path/to/NIST_SP-800-53_rev4_catalog_clause.jsonl \
  --validate \
  --rev5_gold_csv path/to/nist_sp800-53_rev5_gold-set_100q.csv \
  --rev4_gold_csv path/to/nist_sp800-53_rev4_gold-set_36q.csv
```

---

## Common pitfalls (and how to avoid them)

1. **Overwriting the wrong JSONL**
   - Keep `*_controls.jsonl` (baseline) separate from `*_clause.jsonl` (gold-compatible).

2. **Pipeline still loading the old corpus**
   - Add a hard assertion after initialization:
     - “must contain at least one `_smt` ID” and “must contain expected clause IDs”.

3. **Whitespace/header normalization breaking “verbatim”**
   - Do not prefix IDs/titles into `text`.
   - Do not collapse newlines unless your verifier/gold normalization also does.

---

## Current build stats (for the run that produced the `new_*.jsonl` files)

These counts will vary slightly by OSCAL version, but for the latest build in this repo we observed:
- Rev5: 6,831 records (`smt`: 2,125; `gdn`: 1,011; `obj`: 3,695)
- Rev4: 6,563 records (`smt`: 1,586; `gdn`: 695; `obj`: 4,282)
- Empty `text`: 0; duplicate IDs: 0
- `used_descendants=true`: Rev5 1,216; Rev4 1,487
