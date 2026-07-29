# Clause-Level CCS Builder (NIST SP 800-53 Rev4/Rev5)

This directory contains the **single authoritative build path** for ComplianceGPT’s Canonical Clause Store (CCS).
We only support **NIST SP 800-53** (no crosswalks).

The CCS JSONL produced here is the **single source of truth** used by retrieval, citation, verification, and dataset cleaning.

---

## What the CCS JSONL contains

Each JSONL line is one node with at least these fields:

- `id`: unique node identifier (canonical within a version)
- `control_id`: the *control family id* used for grouping and retrieval (see “ID conventions” below)
- `kind`: one of:
  - `smt` = statement clause
  - `gdn` = guidance clause
  - `obj` = objective clause
  - `odp` = Organization-Defined Parameter node (from OSCAL `controls[].params[]`)
  - `prm` = parameter node (from OSCAL `controls[].params[]`)
- `text`: plain text content (may include `{{ insert: param, ... }}` tokens)
- `parent_part_id`: parent linkage for part trees (empty for top-level)
- `provenance`: source metadata (OSCAL title/version, `version_label`)

> **Important:** We always build CCS **with params included** (`--include_params`).  
> Many valid param IDs do not appear in statement/guidance/objective prose, but they are still official and must be present.

---

## Inputs (raw OSCAL JSON)

We keep the official NIST OSCAL catalogs under `data/raw/`:

- Rev5: `data/raw/nist800-53/NIST_SP-800-53_rev5_catalog.json`
- Rev4: `data/raw/nist800-53/NIST_SP-800-53_rev4_catalog.json`

---

## Outputs (canonical CCS JSONL)

The canonical CCS outputs are:

- Rev5: `data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl`
- Rev4: `data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl`

These are the **only** JSONL CCS files the pipeline should reference.

---

## Build command (canonical)

Run from the project root:

```bash
python3 data/ccs/nist800-53/jsonl_builder/builder_clause_level_ccs.py   --rev5_oscal_json data/raw/nist800-53/NIST_SP-800-53_rev5_catalog.json   --rev4_oscal_json data/raw/nist800-53/NIST_SP-800-53_rev4_catalog.json   --out_rev5_jsonl data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl   --out_rev4_jsonl data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl   --include_params
```

---

## ID conventions (critical)

### 1) `control_id` (control family id; used for grouping and retrieval)
- Example forms: `ra-3`, `ac-2`, `sc-7`
- **No zero-padding** on the numeric portion.
- This is the stable key for:
  - control-family grouping
  - retrieval candidate aggregation
  - metrics like “control-family Top-1 correctness”

### 2) Param IDs (`odp`/`prm` node `id` and placeholder tokens)
- Param node ids preserve OSCAL’s canonical param naming, e.g.:
  - `ra-03_odp.02`
  - `ac-02_odp.08`
  - `at-2_prm_1` (Rev4 often uses `_prm_`)
- For ODPs, the numeric part is **zero-padded** and the ODP index is typically **two digits** (`.02`, `.08`, ...).
- These ids are the stable key for:
  - ODP/PRM normalization and registry alignment
  - placeholder matching in `{{ insert: param, ... }}`
  - gold set cleaning for `odp_required`

### Why we keep both formats
NIST’s OSCAL catalogs use **different canonical conventions** for control identifiers vs param identifiers.
Enforcing a single shared format creates silent join bugs. We keep them separate and explicit:

- Use `control_id` for control-family logic.
- Use param `id` / placeholder tokens for ODP/PRM logic.

If you need to derive a param prefix from a `control_id`, do it explicitly with a helper:
- `ra-3` → `ra-03`
- `ac-2` → `ac-02`

---

## Sanity checks (must pass)

### A) Confirm an ODP-only id exists in JSONL (example)
```bash
grep -n "ra-03_odp.02" data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl | head
```

### B) Confirm the JSONL contains `odp` and/or `prm`
```bash
python3 - << 'PY'
import json
from collections import Counter
p="data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl"
c=Counter()
for line in open(p,"r",encoding="utf-8"):
    c[json.loads(line).get("kind")] += 1
print(c)
PY
```

### C) Confirm JSONL is parseable and `id` is unique
```bash
python3 - << 'PY'
import json
seen=set()
p="data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl"
for i,line in enumerate(open(p,"r",encoding="utf-8"), start=1):
    o=json.loads(line)
    _id=o.get("id")
    if _id in seen:
        raise SystemExit(f"Duplicate id at line {i}: {_id}")
    seen.add(_id)
print("OK: unique ids =", len(seen))
PY
```

---

## When to rebuild

Rebuild CCS only if:
- the upstream OSCAL JSON files change, or
- `builder_clause_level_ccs.py` changes.

Otherwise, treat the JSONL CCS as a versioned artifact for reproducible experiments.
