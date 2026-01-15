#!/usr/bin/env python3
"""

convert.py:

Convert an OSCAL NIST SP 800-53 catalog JSON (rev4 or rev5) to JSONL
(one line per control/enhancement), preserving the original control dict
and adding a small _meta summary for convenience.

Usage:
  python convert.py INPUT.json OUTPUT.jsonl

Tips:
- Works with both Rev 4 and Rev 5 OSCAL catalogs.
- Traverses `catalog -> groups -> controls` and nested `controls` (enhancements).
- Also picks up any `controls` directly under `catalog` (some exports do this).
- Adds _meta fields (family, is_enhancement, group lineage, parent id).

- "back-matter" block is catalog-level metadata (citations/references), not a control.
    So I didn't put them into jsonl.
"""

import argparse
import json
import re
import sys
from typing import Dict, Iterable, List, Tuple, Any, Optional

ENHANCEMENT_RX = re.compile(r"\([0-9]+\)")

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def family_from_id(control_id: str) -> Optional[str]:
    # Examples: "ac-2", "AC-2(1)", "sc-7(3)", etc.
    if not isinstance(control_id, str) or "-" not in control_id:
        return None
    return control_id.split("-", 1)[0].upper()

def is_enhancement(control_id: str) -> bool:
    # Heuristic: presence of "(n)" anywhere in id
    return isinstance(control_id, str) and bool(ENHANCEMENT_RX.search(control_id))

def iter_controls_from_group(group: Dict[str, Any],
                             lineage: List[Tuple[str, str]]) -> Iterable[Tuple[Dict[str, Any], List[Tuple[str, str]], Optional[str]]]:
    """
    Yield (control_dict, lineage, parent_control_id) for all controls/enhancements inside a group.
    lineage is a list of (group_id, group_title) from root to this group.
    parent_control_id is None for base controls; set to the parent's id for enhancements.
    """
    # Controls directly under this group
    for ctrl in group.get("controls", []) or []:
        cid = ctrl.get("id")
        yield (ctrl, lineage, None)  # base control
        # Enhancements: nested "controls" inside a control
        for enh in ctrl.get("controls", []) or []:
            yield (enh, lineage, cid)

    # Nested subgroups
    for subg in group.get("groups", []) or []:
        gid = subg.get("id")
        gtitle = subg.get("title")
        new_lineage = lineage + [(gid, gtitle)]
        yield from iter_controls_from_group(subg, new_lineage)

def iter_controls_from_catalog(catalog: Dict[str, Any]) -> Iterable[Tuple[Dict[str, Any], List[Tuple[str, str]], Optional[str]]]:
    """
    Walk the top-level catalog and yield (control_dict, lineage, parent_control_id).
    Handles:
      - catalog.groups[].controls[] (+ nested control.controls[] for enhancements)
      - catalog.controls[] (+ nested control.controls[] for enhancements)
    """
    # Controls directly under catalog
    for ctrl in catalog.get("controls", []) or []:
        cid = ctrl.get("id")
        yield (ctrl, [], None)
        for enh in ctrl.get("controls", []) or []:
            yield (enh, [], cid)

    # Groups
    for group in catalog.get("groups", []) or []:
        gid = group.get("id")
        gtitle = group.get("title")
        lineage = [(gid, gtitle)]
        yield from iter_controls_from_group(group, lineage)

def fallback_collect_any(obj: Any) -> List[Dict[str, Any]]:
    """
    Fallback: traverse any nested dict/list and collect dicts that look like controls or enhancements:
    have 'id' and 'title' and one of {'parts','params','controls'} keys, and are not groups (no 'groups').
    """
    out: List[Dict[str, Any]] = []

    def _walk(x: Any):
        if isinstance(x, dict):
            # Heuristic for a control-like object
            if (
                "id" in x and "title" in x and
                any(k in x for k in ("parts", "params", "controls")) and
                "groups" not in x
            ):
                out.append(x)
            # Recurse
            for v in x.values():
                _walk(v)
        elif isinstance(x, list):
            for v in x:
                _walk(v)

    _walk(obj)
    return out

def main():
    ap = argparse.ArgumentParser(description="Convert SP 800-53 OSCAL catalog JSON to JSONL.")
    ap.add_argument("input_json", help="Path to OSCAL catalog JSON (rev4 or rev5).")
    ap.add_argument("output_jsonl", help="Path to output JSONL.")
    ap.add_argument("--no-meta", action="store_true",
                    help="Do not add the _meta block; write the original control objects only.")
    ap.add_argument("--dedupe", action="store_true",
                    help="Deduplicate by control 'id' before writing.")
    args = ap.parse_args()

    data = load_json(args.input_json)

    # Find catalog node
    catalog = data.get("catalog", data) if isinstance(data, dict) else {}
    records: List[Tuple[Dict[str, Any], List[Tuple[str, str]], Optional[str]]] = []

    # Primary traversal (covers the common OSCAL shapes)
    if isinstance(catalog, dict):
        records.extend(iter_controls_from_catalog(catalog))

    # If we didn't find much, do a fallback global sweep
    if len(records) < 700:  # heuristic threshold; rev4 typically >800 entries with enhancements
        # Only take unique dict identities; we'll wrap below
        fallback = fallback_collect_any(data)
        # Wrap fallback to match (obj, lineage, parent_id) tuple shape
        records.extend((obj, [], None) for obj in fallback)

    # Optionally dedupe (by control id)
    if args.dedupe:
        seen = set()
        deduped = []
        for ctrl, lineage, parent in records:
            cid = ctrl.get("id")
            if cid not in seen:
                seen.add(cid)
                deduped.append((ctrl, lineage, parent))
        records = deduped

    # Prepare lines
    out_lines: List[str] = []
    for ctrl, lineage, parent in records:
        obj = ctrl
        if not args.no_meta:
            cid = ctrl.get("id")
            fam = family_from_id(cid) if cid else None
            meta = {
                "family": fam,
                "is_enhancement": bool(cid and is_enhancement(cid)),
                "parent_control_id": parent,
                "group_lineage": [{"group_id": g[0], "group_title": g[1]} for g in lineage if g[0] or g[1]],
            }
            # Non-destructive: attach a _meta block without altering original control keys
            obj = dict(ctrl)
            obj["_meta"] = meta
        out_lines.append(json.dumps(obj, ensure_ascii=False))

    # Final write
    with open(args.output_jsonl, "w", encoding="utf-8") as f:
        for line in out_lines:
            f.write(line + "\n")

    # Simple stderr summary
    total = len(out_lines)
    sys.stderr.write(f"Wrote {total} JSONL lines to {args.output_jsonl}\n")

if __name__ == "__main__":
    main()
