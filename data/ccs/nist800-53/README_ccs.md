# Canonical Clause Store (CCS) — Clause-Level + Parameters (NIST SP 800-53 Rev4/Rev5)

This repository uses a **clause/part-level Canonical Clause Store (CCS)** in JSONL format derived from the official NIST OSCAL catalog JSON.
The CCS exists because our evaluation artifacts cite evidence at **part IDs** (e.g., `ac-2_smt.h.1`), not just at control IDs.

This README documents:
1) what “CCS (jsonl)” contains,
2) the critical ID conventions (**control_id vs param id**),
3) how to build/validate CCS reproducibly using `builder_clause_level_ccs.py`.

---

## 1) What the CCS contains

### 1.1 Part-level records (used for retrieval + citations)
Each JSONL line is one OSCAL **part** record from the control tree, at one of these granularities:

- **Statements/requirements**: `*_smt*`
- **Guidance**: `*_gdn*`
- **Assessment objectives**: `*_obj*`

These records are what the retriever and generator cite (evidence IDs should match these part IDs).

In the recorded ComplianceGPT pipeline, the default retrieval-ranking corpus uses statement and guidance records (`smt`, `gdn`). Parameter records (`odp`, `prm`) remain in the full CCS inventory for canonicalization, ODP registry alignment, profile validation, and verifier support, but they are not default cited evidence records.

### 1.2 Parameter records (ODP/PRM) — optional but recommended for evaluation hygiene
Many NIST parts contain placeholders like:

- `{{ insert: param, ra-03_odp.02 }}` (Rev5 ODP)
- `{{ insert: param, at-2_prm_1 }}` (Rev4 PRM-style)

To make `odp_required` / `org_profile` alignment deterministic, the builder can also emit **parameter definition records**:

- `kind="odp"` for IDs containing `_odp`
- `kind="prm"` for IDs containing `_prm`

Important: parameter records are **not** meant to be cited as “evidence clauses”. They exist so:
- gold sets can store canonical parameter IDs (zero-padded),
- org profiles can be validated against a canonical parameter universe,
- tools can detect ODP/PRM requirements without relying on brittle regex-only logic.

Enable this with `--include_params`.

---

## 2) Critical ID conventions (do not mix these up)

### 2.1 `control_id` (base control/enhancement)
`control_id` identifies the control or enhancement that *owns* the record:

- `ac-2`
- `ac-2.1` (enhancement)
- `ra-3`

This is useful for “control-family” evaluation and grouping.

### 2.2 `id` (primary key for retrieval/evidence)
`id` is the canonical lookup key used by:
- the retriever corpus index,
- citation IDs in the answer contract,
- strict doc-id evaluation.

There are two *types* of `id`:

**A) Part IDs (citation IDs)**
Examples:
- `ac-2_smt.h`
- `ac-2_smt.h.1`
- `ac-2_gdn`
- `ac-2_obj.1`

These are the IDs that should appear in `gold_control_path` and in final evidence citations.

**B) Parameter IDs (NOT citation IDs)**
Examples:
- `ra-03_odp.02` (Rev5 ODP; note zero-padding)
- `ac-02.02_odp.01`
- `at-2_prm_1` (Rev4 PRM-style)

These are the IDs that should appear in `odp_required` and in org profiles.

Rule of thumb:
- **Evidence citation IDs** → part IDs (`*_smt*`, `*_gdn*`, `*_obj*`)
- **ODP required IDs** → parameter IDs (`*_odp*`, `*_prm*`)

---

## 3) JSONL record schema

### 3.1 Part record (kind = smt | gdn | obj)
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
    "oscal_catalog_version": "...",
    "oscal_catalog_title": "...",
    "version_label": "rev5"
  }
}
```

### 3.2 Parameter record (kind = odp | prm)
```json
{
  "id": "ra-03_odp.02",
  "control_id": "ra-3",
  "title": "Risk Assessment",
  "text": "ra-03_odp.02 document Guidelines: ...",
  "kind": "odp",
  "part_name": "param",
  "label": "document",
  "parent_part_id": "",
  "has_prose": true,
  "used_descendants": false,
  "provenance": {
    "oscal_catalog_version": "...",
    "oscal_catalog_title": "...",
    "version_label": "rev5"
  }
}
```

Notes:
- `label` for params is the OSCAL param label (when available).
- `text` is a compact “definition-like” string for deterministic inspection.

---

## 4) Build logic (high-level)

The builder traverses the OSCAL catalog and emits:
1) one record per selected part ID (`_smt`, `_gdn`, `_obj`),
2) optionally, one record per ODP/PRM param ID (contains `_odp` or `_prm`) when `--include_params` is enabled.

### Handling parts with missing prose (`used_descendants`)
Some OSCAL nodes are structural and may have no `prose`, but gold sets may cite them (e.g., `ac-1_smt`).
For those nodes, we synthesize `text` by concatenating descendant prose and set:
- `has_prose=false`
- `used_descendants=true`

This keeps coverage high without hiding derivation.

---

## 5) How to build CCS (script only)

> If you delete `build_clause_level_ccs.ipynb`, this is the canonical workflow.

From repo root:

```bash
python3 data/ccs/nist800-53/jsonl_builder/builder_clause_level_ccs.py   --rev5_oscal_json data/raw/nist800-53/NIST_SP-800-53_rev5_catalog.json   --rev4_oscal_json data/raw/nist800-53/NIST_SP-800-53_rev4_catalog.json   --out_rev5_jsonl data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl   --out_rev4_jsonl data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl   --include_params   --validate   --rev5_gold_csv data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv   --rev4_gold_csv data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv
```

---

## 6) Sanity checks you should ALWAYS run

### 6.1 Confirm clause IDs exist
```bash
grep -n "_smt" data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl | head
```

### 6.2 Confirm parameter IDs exist (only if you built with --include_params)
```bash
grep -n "ra-03_odp.02" data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl | head
```

### 6.3 Count kinds
```bash
python3 - << 'PY'
import json
from collections import Counter
p="data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl"
c=Counter()
for line in open(p,"r",encoding="utf-8"):
    o=json.loads(line); c[o.get("kind")]+=1
print(c)
PY
```

---

## 7) Example build stats (Rev5)

The exact numbers depend on the OSCAL catalog version, but with the current Rev5 OSCAL JSON used in this repo:

- **Clause-only build** (no `--include_params`): 6,831 records  
  (`obj`: 3,695; `smt`: 2,125; `gdn`: 1,011)

- **Clause + params build** (`--include_params`): 8,423 records  
  (`obj`: 3,695; `smt`: 2,125; `gdn`: 1,011; `odp`: 1,450; `prm`: 142)

Rev4 will differ; treat Rev4 counts as “recorded output” rather than a fixed expectation.

---

## 8) Avoid duplicated documentation

Keep documentation minimal and non-duplicative:
- One authoritative CCS README (this file) next to the CCS artifacts or builder.
- If you want a second file, make it strictly “builder CLI reference” inside `jsonl_builder/README.md` and make it link back here.

Avoid maintaining multiple “CCS readmes” with overlapping content, or you will drift and accidentally document the wrong corpus.
