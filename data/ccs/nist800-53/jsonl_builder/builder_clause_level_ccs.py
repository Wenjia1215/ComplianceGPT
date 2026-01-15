#!/usr/bin/env python3
"""
Build clause-level JSONL catalogs from NIST SP 800-53 OSCAL JSON.

v2 features:
- Includes statement (_smt), guidance (_gdn), and objective (_obj) parts.
- Synthesizes text for structural nodes (no direct prose) by concatenating descendant prose (verbatim).
- Optional gold coverage validation with robust parsing and ID normalization (ac_11 -> ac-11).

This script is intended to produce the JSONL schema your ComplianceGPT retriever expects:
  {"id": "...", "text": "...", "control_id": "...", "title": "...", ...}
"""

from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

# -----------------------------
# OSCAL walkers
# -----------------------------
def _iter_groups(groups: List[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
    for g in groups or []:
        if not isinstance(g, dict):
            continue
        yield g
        sub = g.get("groups")
        if isinstance(sub, list):
            yield from _iter_groups(sub)

def _iter_controls(control: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    if not isinstance(control, dict):
        return
    yield control
    for c in control.get("controls") or []:
        if isinstance(c, dict):
            yield from _iter_controls(c)

def _iter_catalog_controls(catalog: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    groups = catalog.get("groups") or []
    for group in _iter_groups(groups):
        for ctrl in group.get("controls") or []:
            if isinstance(ctrl, dict):
                yield from _iter_controls(ctrl)

def _iter_parts(parts: List[Dict[str, Any]], parent_part_id: Optional[str]) -> Iterator[Tuple[Dict[str, Any], Optional[str]]]:
    for p in parts or []:
        if not isinstance(p, dict):
            continue
        yield p, parent_part_id
        kids = p.get("parts")
        if isinstance(kids, list) and kids:
            yield from _iter_parts(kids, parent_part_id=(p.get("id") or parent_part_id))

# -----------------------------
# Classification / label
# -----------------------------
def _classify_part_id(pid: str) -> Optional[str]:
    pid = (pid or "").strip().lower()
    if "_smt" in pid:
        return "smt"
    if "_gdn" in pid:
        return "gdn"
    if "_obj" in pid:
        return "obj"
    return None

def _get_label(part: Dict[str, Any]) -> str:
    props = part.get("props")
    if isinstance(props, list):
        for pr in props:
            if isinstance(pr, dict) and pr.get("name") == "label":
                v = str(pr.get("value", "")).strip()
                if v:
                    return v
    return ""

def _collect_descendant_prose(part: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    kids = part.get("parts")
    if not isinstance(kids, list):
        return out
    for child, _ in _iter_parts(kids, parent_part_id=part.get("id")):
        prose = child.get("prose")
        if isinstance(prose, str) and prose.strip():
            lab = _get_label(child)
            txt = prose.strip()
            out.append(f"{lab} {txt}".strip() if lab else txt)
    return out

def _build_fulltext(part: Dict[str, Any], kind: str) -> Tuple[str, bool, bool]:
    prose = part.get("prose")
    has_prose = isinstance(prose, str) and prose.strip()
    base = prose.strip() if has_prose else ""

    part_name = str(part.get("name", "")).strip().lower()
    desc = _collect_descendant_prose(part)
    used_desc = False

    # Synthesize for nodes without prose and for statement/objective roots.
    if desc and (not base or (kind in ("smt", "obj") and part_name in ("statement", "objective", "assessment-objective"))):
        used_desc = True
        base = (base + " " + " ".join(desc)).strip() if base else " ".join(desc).strip()

    return base, bool(has_prose), used_desc

# -----------------------------
# Build JSONL
# -----------------------------
def build_clause_jsonl_records(oscal_json: Dict[str, Any], *, version_label: str) -> List[Dict[str, Any]]:
    catalog = oscal_json.get("catalog")
    if not isinstance(catalog, dict):
        raise ValueError("Input JSON does not have top-level 'catalog' object.")

    meta = catalog.get("metadata") or {}
    prov = {
        "oscal_catalog_version": str(meta.get("version", "")).strip(),
        "oscal_catalog_title": str(meta.get("title", "")).strip(),
        "version_label": version_label,
    }

    out: List[Dict[str, Any]] = []
    seen: set = set()

    for ctrl in _iter_catalog_controls(catalog):
        ctrl_id = str(ctrl.get("id", "")).strip()
        title = str(ctrl.get("title", "")).strip()
        parts = ctrl.get("parts")
        if not isinstance(parts, list):
            continue

        for part, parent_part_id in _iter_parts(parts, parent_part_id=None):
            pid = str(part.get("id", "")).strip()
            if not pid:
                continue
            kind = _classify_part_id(pid)
            if kind is None:
                continue

            pid_norm = pid.lower()
            if pid_norm in seen:
                continue
            seen.add(pid_norm)

            full_text, has_prose, used_desc = _build_fulltext(part, kind)

            # Skip empty-text nodes (common in some OSCAL rev4 guidance parts). These break retrieval indexing.
            if not isinstance(full_text, str) or not full_text.strip():
                continue

            out.append({
                "id": pid_norm,
                "control_id": ctrl_id.lower(),
                "title": title,
                "text": full_text,
                "kind": kind,
                "part_name": str(part.get("name", "")).strip(),
                "label": _get_label(part),
                "parent_part_id": (str(parent_part_id).strip().lower() if parent_part_id else ""),
                "has_prose": bool(has_prose),
                "used_descendants": bool(used_desc),
                "provenance": prov,
            })

    return out

def write_jsonl(records: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

# -----------------------------
# Validation helpers
# -----------------------------
def load_id_set(jsonl_path: Path) -> set:
    ids = set()
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and obj.get("id"):
                    ids.add(str(obj["id"]).strip().lower())
            except Exception:
                pass
    return ids

def _norm_gold_id(gid: str) -> str:
    gid = (gid or "").strip().lower()
    gid = re.sub(r"^([a-z]{2})_", r"\1-", gid)  # ac_11 -> ac-11
    return gid

def gold_missing(jsonl_ids: set, gold_csv: Path, label: str) -> None:
    try:
        import pandas as pd
    except Exception as e:
        raise RuntimeError("pandas required for gold validation") from e

    if not gold_csv.exists():
        print(f"[Validate:{label}] Gold CSV not found at {gold_csv} (skipping)")
        return

    df = pd.read_csv(gold_csv, encoding="latin-1")
    all_gold: List[str] = []
    for _, row in df.iterrows():
        raw = str(row.get("gold_control_path", "")).replace("\\r\\n", "\\n")
        parts = re.split(r"[;\\n]+", raw)
        all_gold.extend([_norm_gold_id(x) for x in parts if x and x.strip()])

    uniq = sorted(set(all_gold))
    missing = [x for x in uniq if x not in jsonl_ids]
    print(f"[Validate:{label}] Gold unique ids: {len(uniq)} | Missing unique ids: {len(missing)}")
    if missing:
        print(f"[Validate:{label}] First 40 missing:")
        for x in missing[:40]:
            print("  -", x)

# -----------------------------
# CLI
# -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev5_oscal_json", type=Path, required=True)
    ap.add_argument("--rev4_oscal_json", type=Path, required=True)
    ap.add_argument("--out_rev5_jsonl", type=Path, required=True)
    ap.add_argument("--out_rev4_jsonl", type=Path, required=True)
    ap.add_argument("--rev5_gold_csv", type=Path, default=None)
    ap.add_argument("--rev4_gold_csv", type=Path, default=None)
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()

    for label, in_path, out_path in [
        ("rev5", args.rev5_oscal_json, args.out_rev5_jsonl),
        ("rev4", args.rev4_oscal_json, args.out_rev4_jsonl),
    ]:
        data = json.load(in_path.open("r", encoding="utf-8"))
        recs = build_clause_jsonl_records(data, version_label=label)
        write_jsonl(recs, out_path)
        print(f"[OK] {label}: wrote {len(recs)} clause docs -> {out_path}")

    if args.validate:
        if args.rev5_gold_csv:
            gold_missing(load_id_set(args.out_rev5_jsonl), args.rev5_gold_csv, "rev5")
        if args.rev4_gold_csv:
            gold_missing(load_id_set(args.out_rev4_jsonl), args.rev4_gold_csv, "rev4")

if __name__ == "__main__":
    main()
