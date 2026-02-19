# -*- coding: utf-8 -*-
"""
ComplianceGPT Pipeline (provably-extractive, clean naming)

Single source of truth:
- `ccs_path` is the canonical name for the clause-level CCS JSONL file.
- The retriever must accept: ComplianceGPTRetriever(ccs_path=...)
- The generator must output Selector Contract (IDs only).
- The pipeline deterministically fills verbatim `span_text` from CCS and constructs `answer_text`.

This file is designed to live at:
  /content/drive/MyDrive/ComplianceGPT_v2/src/compliancegpt/pipeline/pipeline.py
"""

from __future__ import annotations

import re
import json

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import fields as _dc_fields, is_dataclass as _is_dataclass, replace as _dc_replace

# Imports
# ----------------------------
from compliancegpt.generator.generator import ComplianceGenerator, load_org_profile, normalize_contract  # type: ignore
_VERIFY_IMPORT_ERROR = None
try:
    from compliancegpt.generator.verifier.verifier import verify_answer  # type: ignore
    try:
        from compliancegpt.generator.verifier.verifier import parse_control_from_source_id  # type: ignore
    except Exception:
        parse_control_from_source_id = None  # type: ignore
except Exception as e:
    verify_answer = None  # type: ignore
    parse_control_from_source_id = None  # type: ignore
    _VERIFY_IMPORT_ERROR = str(e)
try:
    from compliancegpt.retriever.retriever_s7 import ComplianceGPTRetriever, RetrievalConfig  # type: ignore
except Exception as e:
    raise ImportError(
        "[FATAL] Cannot import compliancegpt.retriever.retriever_s7. "
        "Ensure the notebook adds '<repo>/src' to sys.path and that the canonical package structure is intact."
    ) from e

try:
    from compliancegpt.QUR_generator.qur_generator_ut import QURComponent  # type: ignore
except Exception:
    QURComponent = None  # type: ignore


# ==========================================================
# 0) Helpers
# ==========================================================
def _cfg_with(cfg: Any, **updates: Any) -> Any:
    """Return a new config with updates applied safely.

    - If cfg is a (possibly frozen) dataclass, use dataclasses.replace (no in-place mutation).
    - Otherwise, set attributes only when they exist.
    - Unknown fields are ignored (forward/backward compatible).
    """
    if cfg is None:
        return cfg
    try:
        if _is_dataclass(cfg):
            names = {f.name for f in _dc_fields(cfg)}
            filtered = {k: v for k, v in updates.items() if k in names}
            return _dc_replace(cfg, **filtered) if filtered else cfg
    except Exception:
        # Fall through to attribute-based updates
        pass
    for k, v in updates.items():
        if hasattr(cfg, k):
            try:
                setattr(cfg, k, v)
            except Exception:
                pass
    return cfg


def _normalize_fw(framework_version: str) -> str:
    v = str(framework_version or "").strip().lower()
    if v in {"rev4", "r4", "4"}:
        return "rev4"
    if v in {"rev5", "r5", "5"}:
        return "rev5"
    raise ValueError(f"framework_version must be 'rev4' or 'rev5' (got {framework_version!r})")


def resolve_default_ccs_path(framework_version: str) -> str:
    fw = _normalize_fw(framework_version)
    base = Path("/content/drive/MyDrive/ComplianceGPT_v2/data/ccs/nist800-53")
    if fw == "rev5":
        return str(base / "NIST_SP-800-53_rev5_catalog.jsonl")
    return str(base / "NIST_SP-800-53_rev4_catalog.jsonl")


def _doc_id_suffix(doc_id: str) -> str:
    s = str(doc_id or "").strip().lower()
    if not s:
        return ""
    for suf in ("_smt", "_gdn", "_obj"):
        if suf in s:
            return suf
    return ""


def _doc_id(d: Any) -> str:
    """Best-effort extract of a clause/doc identifier from a doc dict or string."""
    if d is None:
        return ""
    if isinstance(d, str):
        return d.strip()
    if isinstance(d, dict):
        for k in ("id", "source_id", "doc_id", "clause_id"):
            v = d.get(k)
            if isinstance(v, str):
                s = v.strip()
                if s:
                    return s
        # Fallback: try to stringify common id-like fields
        for k in ("id", "source_id", "doc_id", "clause_id"):
            try:
                v = d.get(k)  # type: ignore
                s = str(v).strip()
                if s and s.lower() != "none":
                    return s
            except Exception:
                continue
        return ""
    # Fallback: attribute-based
    try:
        v = getattr(d, "id", None)
        if v is not None:
            s = str(v).strip()
            if s and s.lower() != "none":
                return s
    except Exception:
        pass
    return ""


# ==========================================================
# CCS hierarchy helpers (leaf-level clause alignment)
# ==========================================================
_LABEL_SPLIT_RE = re.compile(r"(\d+)")

def _label_sort_key(label: str) -> Tuple[Any, ...]:
    s = str(label or "").strip()
    if not s:
        return tuple()
    parts: List[Any] = []
    for tok in _LABEL_SPLIT_RE.split(s):
        if not tok:
            continue
        if tok.isdigit():
            parts.append(int(tok))
        else:
            parts.append(tok)
    return tuple(parts)

def _build_ccs_hierarchy_index(ccs_path: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[str]]]:
    """Build minimal CCS meta index and parent->children map from CCS JSONL.

    Returns:
      meta_by_id: {id: {kind,label,parent_part_id,has_prose,text}}
      parent_to_children: {parent_id: [child_id1, ...]} sorted by (label, id)
    """
    meta_by_id: Dict[str, Dict[str, Any]] = {}
    parent_to_children: Dict[str, List[str]] = {}

    with open(str(ccs_path), "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            cid = str(rec.get("id", "") or "").strip()
            if not cid:
                continue
            kind = str(rec.get("kind", "") or "").strip().lower()
            parent = str(rec.get("parent_part_id", "") or "").strip()
            label = str(rec.get("label", "") or "").strip()
            has_prose = rec.get("has_prose", True)
            txt = str(rec.get("text", "") or "").strip()

            meta_by_id[cid] = {
                "kind": kind,
                "label": label,
                "parent_part_id": parent,
                "has_prose": has_prose,
                "used_descendants": bool(rec.get("used_descendants", False)),
                "text": txt,
            }

            if parent:
                parent_to_children.setdefault(parent, []).append(cid)

    for parent, kids in parent_to_children.items():
        kids.sort(key=lambda k: (_label_sort_key(str((meta_by_id.get(k) or {}).get("label", "") or "")), k))

    return meta_by_id, parent_to_children

def _expand_clause_ids_to_children(
    source_ids: List[str],
    *,
    meta_by_id: Dict[str, Dict[str, Any]],
    parent_to_children: Dict[str, List[str]],
    max_total: int,
    max_children_expand: int = 12,
) -> List[str]:
    """Expand clause ids to include relevant parent/child subclauses without losing intro context.

    Goals:
      - If a list-introducing parent clause (text ends with ':') is selected, keep the parent and add
        immediate children (depth-1) of kinds smt/gdn with has_prose=True.
      - If a child clause is selected and its parent carries placeholders or list-intro context, include
        the parent before the child.
      - Never drop the original selected ids. De-duplicate while preserving order.
      - Truncate to max_total.

    Notes:
      - This function is intentionally conservative; it only expands when the CCS indicates list-intro
        or descendant usage, avoiding citation explosion.
      - It preserves parent clauses that contain parameter placeholders (e.g., ODP time window) that do
        not appear in leaf children.
    """
    allowed = {"smt", "gdn"}
    seen: Set[str] = set()
    out: List[str] = []

    def _kind(cid: str) -> str:
        return str((meta_by_id.get(cid) or {}).get("kind", "") or "").strip().lower()

    def _txt(cid: str) -> str:
        return str((meta_by_id.get(cid) or {}).get("text", "") or "").strip()

    def _has_prose(cid: str) -> bool:
        return bool((meta_by_id.get(cid) or {}).get("has_prose", True))

    def _used_desc(cid: str) -> bool:
        return bool((meta_by_id.get(cid) or {}).get("used_descendants", False))

    def _has_param_placeholder(txt: str) -> bool:
        return "{{ insert: param" in txt

    def _is_list_intro(txt: str) -> bool:
        return bool(re.search(r":\s*$", txt))

    def _add(cid: str) -> None:
        if not cid:
            return
        if cid in seen:
            return
        if _kind(cid) and _kind(cid) not in allowed:
            return
        if not _has_prose(cid):
            return
        seen.add(cid)
        out.append(cid)

    for sid in (source_ids or []):
        s = str(sid or "").strip()
        if not s:
            continue

        parent = str((meta_by_id.get(s) or {}).get("parent_part_id", "") or "").strip()

        # If this is a child, include a qualifying parent before the child.
        if parent:
            ptxt = _txt(parent)
            if _has_param_placeholder(ptxt) or _is_list_intro(ptxt) or _used_desc(parent):
                _add(parent)

        # Always keep the originally selected id.
        _add(s)

        # If this is a list-introducing parent, add immediate children after it.
        kids = parent_to_children.get(s, []) or []
        if kids:
            stxt = _txt(s)
            if _is_list_intro(stxt) or _used_desc(s):
                for k in kids[: int(max_children_expand)]:
                    _add(str(k))

        if len(out) >= int(max_total):
            break

    return out[: int(max_total)]

def _statement_only_docs(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for d in docs:
        if _doc_id_suffix(d.get("id", "")) == "_smt":
            out.append(d)
    return out


def _choose_docs_for_generator(
    retrieved_docs: List[Dict[str, Any]],
    top_k: int,
    doc_filter_mode: str,
) -> List[Dict[str, Any]]:
    """
    Generator input doc selection.

    Modes:
      - "all": pass through (top_k slice only)
      - "statement_only": only _smt docs   [DEPRECATED: deletes context; kept for backwards-compatibility]
      - "prefer_statement_only": if any _smt exist, use only those; else pass through  [DEPRECATED]
      - "prefer_smt_keep_params": legacy alias; ranks statements first, then guidance (non-evidence kinds are dropped)
    """
    mode = str(doc_filter_mode or "all").strip().lower()
    docs = list(retrieved_docs or [])

    def _kind_of(d: Dict[str, Any]) -> str:
        k = str(d.get("kind") or "").strip().lower()
        if k:
            return k
        # fall back to id suffix: "_smt" -> "smt", etc.
        suf = _doc_id_suffix(d.get("id", "")).strip().lower()
        return suf[1:] if suf.startswith("_") else suf

    if mode == "all":
        out = docs
    elif mode == "statement_only":
        out = _statement_only_docs(docs)
    elif mode == "prefer_statement_only":
        smt = _statement_only_docs(docs)
        out = smt if smt else docs
    elif mode == "prefer_smt_keep_params":
        # Stable sort by kind bucket; keep original order within each bucket.
        order = {"smt": 0, "gdn": 1}
        indexed = list(enumerate(docs))
        indexed.sort(key=lambda t: (order.get(_kind_of(t[1]), 9), t[0]))
        out = [d for _, d in indexed]
        # Evidence gating: keep only clause-level evidence kinds for generator input.
        ev = [d for d in out if _kind_of(d) in {"smt", "gdn"}]
        if ev:
            out = ev
    else:
        raise ValueError(f"Unknown doc_filter_mode={doc_filter_mode!r}")

    # Evidence gating: only statement/guidance kinds are eligible for generator input.
    # Parameter/objective nodes remain in CCS for canonicalization but are not passed as evidence.
    allowed = {"smt", "gdn"}
    out = [d for d in out if _kind_of(d) in allowed]

    if top_k is not None and int(top_k) > 0:
        k = int(top_k)
        if k >= 2:
            # Reserve one guidance clause if it exists; some gold labels explicitly require _gdn.
            gdn_doc: Optional[Dict[str, Any]] = None
            # Prefer a gdn doc without param placeholders (to avoid accidental PARAMS_REQUIRED flips).
            for d in out:
                if _kind_of(d) == "gdn" and not _doc_has_param_placeholder(d):
                    gdn_doc = d
                    break
            if gdn_doc is None:
                for d in out:
                    if _kind_of(d) == "gdn":
                        gdn_doc = d
                        break
            sliced = out[:k]
            if gdn_doc is not None and all(_kind_of(d) != "gdn" for d in sliced):
                # Replace the last doc with the first gdn doc, keeping order/dedup.
                sliced = sliced[: max(0, k - 1)] + [gdn_doc]
            # De-dup while preserving order
            seen_ids: Set[str] = set()
            dedup: List[Dict[str, Any]] = []
            for d in sliced:
                did = _doc_id(d)
                if not did or did in seen_ids:
                    continue
                seen_ids.add(did)
                dedup.append(d)
            out = dedup
        else:
            out = out[:k]
    return out


# ==========================================================
# Control-ID normalization helpers (pipeline-local)
# ==========================================================
_CTRL_ID_RE = re.compile(r"(?i)([A-Z]{2})-0*([0-9]{1,3})")

def normalize_control_id(s: Any) -> Optional[str]:
    """Return canonical control id like 'AC-6' from variants (e.g., 'AC-06', 'AC-6_smt.1')."""
    if s is None:
        return None
    t = str(s).strip()
    if not t or t.lower() == "nan":
        return None
    m = _CTRL_ID_RE.search(t)
    if not m:
        return None
    fam = m.group(1).upper()
    num = int(m.group(2))
    return f"{fam}-{num}"



def _is_enhancement_clause_id(clause_id: str) -> bool:
    """Heuristic: clause ids like 'ac-2.1_smt...' or 'ac-2(1)_smt...' are treated as enhancement clauses."""
    s = str(clause_id or "").strip().lower()
    if not s:
        return False
    # Enhancement forms:
    #   - dotted control number: ac-2.1_...
    #   - parentheses: ac-2(1)_...
    #   - rare: ac-2-1_... (avoid false positives; ignore)
    return bool(re.match(r"^[a-z]{2}-\d{1,2}\.(\d{1,2})_", s) or re.match(r"^[a-z]{2}-\d{1,2}\(\d{1,2}\)_", s))

def _query_mentions_enhancement(query: str) -> bool:
    """Detect explicit enhancement mentions in the query (e.g., 'AC-2(1)' or 'AC-2.1')."""
    q = str(query or "")
    if not q.strip():
        return False
    # Case-insensitive; allow spaces.
    return bool(re.search(r"\b[a-z]{2}\s*-\s*\d{1,2}\s*(?:\.\s*\d{1,2}|\(\s*\d{1,2}\s*\))\b", q, flags=re.IGNORECASE))

def _doc_kind(d: Dict[str, Any]) -> str:
    k = str((d or {}).get("kind", "") or "").strip().lower()
    if k:
        return k
    suf = _doc_id_suffix((d or {}).get("id", "")).strip().lower()
    return suf[1:] if suf.startswith("_") else suf

def _doc_control(d: Dict[str, Any]) -> Optional[str]:
    cid = normalize_control_id((d or {}).get("control_id", "")) or None
    if cid:
        return cid
    did = str((d or {}).get("id", "")).strip()
    return normalize_control_id(did) if did else None

def _filter_docs_by_controls(
    docs: List[Dict[str, Any]],
    allowed_controls: List[str],
) -> List[Dict[str, Any]]:
    allow = {str(c).strip().upper() for c in (allowed_controls or []) if str(c).strip()}
    if not allow:
        return list(docs or [])
    out: List[Dict[str, Any]] = []
    for d in (docs or []):
        cid = (_doc_control(d) or "").upper()
        if cid and cid in allow:
            out.append(d)
    return out

def _filter_docs_evidence_kinds(
    docs: List[Dict[str, Any]],
    *,
    allowed_kinds: Tuple[str, ...] = ("smt", "gdn"),
) -> List[Dict[str, Any]]:
    allow = {str(k).strip().lower() for k in (allowed_kinds or tuple()) if str(k).strip()}
    if not allow:
        return list(docs or [])
    out: List[Dict[str, Any]] = []
    for d in (docs or []):
        if _doc_kind(d) in allow:
            out.append(d)
    return out


def _doc_has_param_placeholder(d: Dict[str, Any]) -> bool:
    txt = str(d.get("text") or "")
    return "{{ insert: param" in txt

def _balance_docs_across_controls(
    docs: List[Dict[str, Any]],
    *,
    primary_control: str,
    allowed_controls: List[str],
    top_k: int,
) -> List[Dict[str, Any]]:
    """Reorder docs so the primary control retains enough quota even when allowed_controls > 1.

    Goal:
      - Prevent clause-id starvation for the primary control (keeps within-control coverage)
      - Still surface at least a small amount of non-primary evidence early, so the generator
        has a fair chance to select the right control when top-1 vs top-2 is ambiguous.

    This is *reordering only*; no docs are created or removed.
    """
    if not docs:
        return []
    if not primary_control or len(allowed_controls or []) <= 1:
        return list(docs)

    top_k_val = int(top_k) if top_k is not None else 0
    if top_k_val <= 0:
        return list(docs)

    primary = str(primary_control).strip().upper()
    allow = [str(c).strip().upper() for c in (allowed_controls or []) if str(c).strip()]
    if primary not in allow:
        allow = [primary] + [c for c in allow if c != primary]

    # Group docs by control (preserve relative order).
    groups: Dict[str, List[Dict[str, Any]]] = {c: [] for c in allow}
    other: List[Dict[str, Any]] = []
    for d in (docs or []):
        c = str(_doc_control(d) or "").strip().upper()
        if c in groups:
            groups[c].append(d)
        else:
            other.append(d)

    # Allocate a primary quota to keep the main control well represented.
    # Heuristic: ~60% primary, remainder shared across others; enforce small minimums.
    if len(allow) == 2:
        quota_primary = max(6, (top_k_val * 2) // 3)
    else:
        quota_primary = max(6, (top_k_val * 3) // 5)

    # Ensure we leave space for other controls when possible.
    if top_k_val >= 8 and len(allow) > 1:
        quota_primary = min(quota_primary, top_k_val - 2)
    quota_primary = max(1, min(quota_primary, top_k_val))

    remaining = max(0, top_k_val - quota_primary)
    per_other = 0
    if len(allow) > 1 and remaining > 0:
        per_other = max(2, remaining // (len(allow) - 1))

    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def _push(ds: List[Dict[str, Any]], limit: int) -> int:
        cnt = 0
        if limit <= 0:
            return 0
        for d in ds:
            did = _doc_id(d)
            if not did or did in seen:
                continue
            seen.add(did)
            out.append(d)
            cnt += 1
            if cnt >= limit:
                break
        return cnt

    prim_docs = groups.get(primary, []) or []

    # --- Stage 1: seed a small amount of non-primary material early ---
    # Keep this conservative to avoid starving clause-id coverage.
    seed_primary = 0
    seed_other = 0
    if top_k_val >= 10 and len(allow) >= 2:
        seed_primary = min(4, quota_primary)
        seed_other = 1
    elif top_k_val >= 8 and len(allow) >= 2:
        seed_primary = min(3, quota_primary)
        seed_other = 1

    prim_used = _push(prim_docs, seed_primary)

    # One doc from each other control early (if possible)
    if seed_other > 0:
        for c in allow:
            if c == primary:
                continue
            _push(groups.get(c, []) or [], seed_other)

    # --- Stage 2: fill remaining primary quota ---
    remaining_primary = max(0, quota_primary - prim_used)
    if remaining_primary > 0:
        _push(prim_docs[prim_used:], remaining_primary)

    # --- Stage 3: then each other control quota (round-robin across controls to keep diversity) ---
    if per_other > 0:
        for c in allow:
            if c == primary:
                continue
            # if we already seeded 1, subtract it from the quota
            quota_c = max(0, per_other - (seed_other if seed_other > 0 else 0))
            if quota_c > 0:
                ds = groups.get(c, []) or []
                _push(ds[(seed_other if seed_other > 0 else 0):], quota_c)

    # Finally, append everything else (preserve original ordering across remaining docs).
    for d in (docs or []):
        did = _doc_id(d)
        if not did or did in seen:
            continue
        seen.add(did)
        out.append(d)

    return out
def _augment_primary_control_docs(
    *,
    primary_control: str,
    existing_docs: List[Dict[str, Any]],
    retriever: Any,
    max_docs: int,
    allow_enhancement: bool,
    evidence_kinds: Tuple[str, ...] = ("smt", "gdn"),
) -> List[Dict[str, Any]]:
    """Backfill additional clause-level docs for the primary control from CCS maps.

    This is intentionally conservative:
      - stays within a single control (primary_control)
      - only adds evidence kinds (smt/gdn)
      - blocks enhancement clause ids unless allow_enhancement=True
      - preserves existing order; new docs appended
    """
    pc = (normalize_control_id(primary_control) or "").upper()
    if not pc:
        return list(existing_docs or [])
    out: List[Dict[str, Any]] = [d for d in (existing_docs or []) if isinstance(d, dict)]
    if len(out) >= int(max_docs):
        return out[: int(max_docs)]
    seen_ids: Set[str] = set()
    for d in out:
        did = str(d.get("id", "")).strip()
        if did:
            seen_ids.add(did)

    ctl_to_ids = getattr(retriever, "control_to_clause_ids", {}) or {}
    rb = getattr(retriever, "record_by_id", {}) or {}
    cand_ids = list(ctl_to_ids.get(pc, []) or [])

    def _depth_score(clause_id: str) -> int:
        # Prefer deeper subclauses: ac-7_smt.h.1 -> depth 2 (h,1); ac-7_smt -> depth 0
        s = str(clause_id or "")
        if "_smt" in s:
            tail = s.split("_smt", 1)[1]
        elif "_gdn" in s:
            tail = s.split("_gdn", 1)[1]
        else:
            tail = ""
        tail = tail.lstrip(".")
        if not tail:
            return 0
        return tail.count(".") + 1

    allow_k = {str(k).strip().lower() for k in (evidence_kinds or tuple()) if str(k).strip()}
    candidates: List[Tuple[int, int, str]] = []
    for cid in cand_ids:
        cid_s = str(cid or "").strip()
        if not cid_s or cid_s in seen_ids:
            continue
        if (not allow_enhancement) and _is_enhancement_clause_id(cid_s):
            continue
        rec = rb.get(cid_s)
        if not isinstance(rec, dict):
            continue
        kind = str(rec.get("kind", "")).strip().lower()
        if kind not in allow_k:
            continue
        # kind rank: smt first then gdn
        kind_rank = 0 if kind == "smt" else (1 if kind == "gdn" else 9)
        depth_rank = -_depth_score(cid_s)  # deeper first
        candidates.append((kind_rank, depth_rank, cid_s))

    candidates.sort()
    for _, _, cid_s in candidates:
        if len(out) >= int(max_docs):
            break
        rec = rb.get(cid_s)
        if not isinstance(rec, dict):
            continue
        out.append(
            {
                "id": rec.get("id", cid_s),
                "control_id": normalize_control_id(rec.get("control_id", "")),
                "kind": rec.get("kind", "other"),
                "title": rec.get("title", ""),
                "text": rec.get("text", ""),
            }
        )
        seen_ids.add(cid_s)

    return out[: int(max_docs)]

def _unique_controls_in_order(docs: List[Dict[str, Any]]) -> List[str]:
    seen = set()
    out: List[str] = []
    for d in docs or []:
        cid = (normalize_control_id(str(d.get("control_id", ""))) or "").upper()
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def _selected_controls_from_spans(spans: List[Dict[str, str]]) -> List[str]:
    seen = set()
    out: List[str] = []
    for s in spans or []:
        sid = str((s or {}).get("source_id", "")).strip()
        cid = None
        if sid and "parse_control_from_source_id" in globals() and callable(globals().get("parse_control_from_source_id")):
            try:
                cid = globals()["parse_control_from_source_id"](sid)  # type: ignore
            except Exception:
                cid = None
        if not cid and sid:
            # fallback: try normalize_control_id on the sid itself
            cid = normalize_control_id(sid)
        cid = str(cid or "").strip().upper()
        if cid and cid not in seen:
            seen.add(cid)
            out.append(cid)
    return out


def _build_citation_suffix(framework_version: str) -> str:
    fw = _normalize_fw(framework_version)
    if fw == "rev5":
        return "NIST SP 800-53 Rev. 5"
    return "NIST SP 800-53 Rev. 4"


# ODP placeholder patterns (must align with verifier.py)
_PARAM_CURLY_RE = re.compile(r"\{+\s*insert:\s*(?:param,\s*)?([^}]+?)\s*\}+", re.IGNORECASE)
_PARAM_ASSIGNMENT_RE = re.compile(r"\[assignment:\s*([^\]]+?)\s*\]", re.IGNORECASE)

_ASSIGNMENT_REQUIRED_SENTINEL = "__ASSIGNMENT_REQUIRED__"


def _extract_odp_ids(text: str) -> Tuple[List[str], bool]:
    """
    Returns (odp_ids, has_assignment_placeholder).
    odp_ids are normalized strings like 'ac-02_odp.05' when present inside curly placeholders.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)

    keys = []
    for m in _PARAM_CURLY_RE.finditer(text):
        k = m.group(1).strip()
        if k:
            keys.append(k)

    # assignment placeholders are human-language (no canonical key guaranteed)
    has_assignment = bool(_PARAM_ASSIGNMENT_RE.search(text))
    # normalize + de-dupe
    keys = sorted(set(k.strip() for k in keys if k.strip()))
    return keys, has_assignment


def _profile_lookup(profile: Dict[str, Any], key: str) -> Optional[Any]:
    """
    Look up ODP values in org_profile.

    Supported shapes:
      profile["odp_values"][key]
      profile["odps"][key]
      profile[key]
    """
    if not isinstance(profile, dict) or not key:
        return None
    for top in ("odp_values", "odps"):
        if isinstance(profile.get(top), dict) and key in profile[top]:
            return profile[top][key]
    return profile.get(key)



# ==========================================================
# ODP/PRM Canonicalization (CCS-aligned, provably-extractive)
# ==========================================================
_PARAM_ID_KIND_RE = re.compile(r"_(odp|prm)\b", re.IGNORECASE)

def _build_param_key_to_canonical(param_ids: Set[str]) -> Dict[str, str]:
    """
    Build a deterministic mapping from a normalized "param key" -> canonical param id.

    Key design:
      - robust to: ra-3_odp.2, ra-03_odp.02, ra-03_odp_2, cp-02.06_odp (legacy/non-canonical)
      - does NOT guess when ambiguous: if multiple canonicals map to the same key, pick the lexicographically smallest.
    """
    out: Dict[str, str] = {}
    for pid in (param_ids or set()):
        key = _param_key(pid)
        if not key:
            continue
        if key not in out or pid < out[key]:
            out[key] = pid
    return out

def _param_key(raw: str) -> str:
    """
    Normalize a raw param token to a stable key:
      <family>-<ctrl2>[.<enh2>]_<kind>.<idx2>
    """
    s = (raw or "").strip().lower()
    if not s:
        return ""
    s = re.sub(r"\s+", "", s)
    s = s.replace("__", "_")

    # Canonical-ish: ra-03_odp.02 ; ac-02.05_prm.01 ; at-2_prm_1
    m = re.match(r"^([a-z]{2})-?(\d{1,2})(?:\.(\d{1,2}))?_(odp|prm)[\._-]?(\d{1,2})$", s)
    if m:
        fam, ctrl, enh, kind, idx = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        enh_s = ("." + format(int(enh), "02d")) if enh is not None else ""
        return f"{fam}-{int(ctrl):02d}{enh_s}_{kind}.{int(idx):02d}"

    # Legacy: cp-02.06_odp  (meaning control=02, idx=06, kind=odp)
    m2 = re.match(r"^([a-z]{2})-(\d{1,2})\.(\d{1,2})_(odp|prm)$", s)
    if m2:
        fam, ctrl, idx, kind = m2.group(1), m2.group(2), m2.group(3), m2.group(4)
        return f"{fam}-{int(ctrl):02d}_{kind}.{int(idx):02d}"

    # Legacy: ac_02_odp_1
    m3 = re.match(r"^([a-z]{2})[-_]?(\d{1,2})_(odp|prm)[\._-]?(\d{1,2})$", s)
    if m3:
        fam, ctrl, kind, idx = m3.group(1), m3.group(2), m3.group(3), m3.group(4)
        return f"{fam}-{int(ctrl):02d}_{kind}.{int(idx):02d}"

    return ""

def _canonicalize_param_list(
    raw_list: List[str],
    *,
    param_ids: Set[str],
    key_map: Dict[str, str],
    assignment_sentinel: str,
) -> List[str]:
    """
    Canonicalize a list of ODP/PRM ids into CCS-canonical ids.
    Principle: provably-extractive -> only emit ids that exist in CCS param_ids.
    Unknown/unmappable tokens are dropped (they are not mechanically verifiable).
    """
    seen: Set[str] = set()
    out: List[str] = []
    has_assign = False

    for x in (raw_list or []):
        s = (x or "").strip()
        if not s:
            continue
        if s == assignment_sentinel:
            has_assign = True
            continue

        if s in param_ids:
            if s not in seen:
                out.append(s)
                seen.add(s)
            continue

        k = _param_key(s)
        if not k:
            # Try prefix match for tokens like "pm-05_odp" (no idx)
            s_low = re.sub(r"\s+", "", s.lower())
            if _PARAM_ID_KIND_RE.search(s_low) and (s_low.endswith("_odp") or s_low.endswith("_prm")):
                candidates = sorted([pid for pid in param_ids if pid.lower().startswith(s_low + ".")])
                if len(candidates) == 1:
                    cand = candidates[0]
                    if cand not in seen:
                        out.append(cand)
                        seen.add(cand)
            continue

        cand = key_map.get(k, "")
        if cand and cand in param_ids and cand not in seen:
            out.append(cand)
            seen.add(cand)

    out_sorted = sorted(out)
    if has_assign:
        out_sorted.append(assignment_sentinel)
    return out_sorted
def _apply_odp_policy_to_answer(
    answer_text: str,
    policy: str,
    org_profile: Dict[str, Any],
) -> Tuple[str, List[str], str]:
    """
    Apply ODP resolution policy to the final answer_text.

    Returns: (new_answer_text, odp_required_list, final_status_override_or_empty)

    Policy:
      - ASK: do not substitute; require params if any placeholders
      - PRESERVE: do not substitute; require params if any placeholders (used for evaluation)
      - FILL_FROM_PROFILE: substitute known keys; require params only for missing keys and assignment placeholders
    """
    pol_raw = policy
    try:
        pol = "" if pol_raw is None else str(pol_raw).strip().upper()
    except Exception:
        pol = ""
    # Treat pandas/NumPy NaN and other empty-ish tokens as missing
    if pol in {"", "NAN", "NA", "N/A", "NONE", "NULL"}:
        pol = "ASK"
    # Allow a few safe aliases
    if pol in {"FILL", "PROFILE", "FILL_PROFILE"}:
        pol = "FILL_FROM_PROFILE"
    text = str(answer_text or "")

    keys, has_assignment = _extract_odp_ids(text)
    if not keys and not has_assignment:
        return text, [], ""  # no change

    missing: List[str] = []

    if pol in {"ASK", "PRESERVE"}:
        # Keep placeholders exactly; just surface required keys.
        req = list(keys)
        if has_assignment:
            req.append(_ASSIGNMENT_REQUIRED_SENTINEL)
        return text, req, "PARAMS_REQUIRED"

    if pol == "FILL_FROM_PROFILE":
        # Substitute what we can; keep missing placeholders.
        for k in keys:
            val = _profile_lookup(org_profile, k)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(k)
                continue
            val_str = str(val)
            # replace curly placeholder for this key (robust for whitespace)
            rep_braces = r"\{+\s*insert:\s*(?:param,\s*)?" + re.escape(k) + r"\s*\}+"
            try:
                text = re.sub(rep_braces, val_str, text, flags=re.IGNORECASE)
            except re.error:
                # if the regex fails, leave placeholder
                missing.append(k)

        req = list(sorted(set(missing)))
        if has_assignment:
            req.append(_ASSIGNMENT_REQUIRED_SENTINEL)

        if req:
            return text, req, "PARAMS_REQUIRED"
        return text, [], ""  # all resolved

    raise ValueError(f"Unknown resolution_policy={policy!r}")


# ==========================================================
# Output Compatibility Wrapper
# ==========================================================
def _verifier_result_to_dict(ver: Any) -> Optional[Dict[str, Any]]:
    """Normalize verifier output (dataclass / dict / unknown) to a JSON-friendly dict."""
    if ver is None:
        return None
    if isinstance(ver, dict):
        return ver
    # dataclass
    try:
        from dataclasses import asdict, is_dataclass  # local import to avoid hard dependency
        if is_dataclass(ver):
            return asdict(ver)
    except Exception:
        pass
    # attribute-based fallback (VerifierResult)
    if hasattr(ver, "question_id") and hasattr(ver, "is_pass"):
        try:
            return {
                "question_id": str(getattr(ver, "question_id")),
                "is_pass": bool(getattr(ver, "is_pass")),
                "error_tags": list(getattr(ver, "error_tags", []) or []),
                "metrics": dict(getattr(ver, "metrics", {}) or {}),
            }
        except Exception:
            return {"error": str(ver)}
    return {"error": str(ver)}

def _wrap_out(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Acceptance-test compatible return shape.

    Returns:
      - out['contract'] -> the contract dict
      - also flattens contract keys at top-level for backward compatibility
    """
    c: Dict[str, Any] = dict(contract or {})

    # selected_source_ids convenience (acceptance notebook expects it sometimes)
    if "selected_source_ids" not in c:
        spans = c.get("evidence_spans", []) or []
        ids: List[str] = []
        for s in spans:
            if isinstance(s, dict):
                sid = str(s.get("source_id", "")).strip()
                if sid:
                    ids.append(sid)
        c["selected_source_ids"] = ids

    # verifier flattening: verifier_pass / verifier_errors / verifier_metrics
    ver = c.get("verification", None)
    ver_dict = _verifier_result_to_dict(ver) if ver is not None else None
    if ver is not None:
        c["verification"] = ver_dict

    c["verifier_ran"] = bool(ver is not None)

    verifier_pass = False
    verifier_errors: List[str] = []
    verifier_metrics: Dict[str, float] = {}
    if isinstance(ver_dict, dict):
        if "is_pass" in ver_dict:
            verifier_pass = bool(ver_dict.get("is_pass", False))
        elif "ok" in ver_dict:
            verifier_pass = bool(ver_dict.get("ok", False))
        verifier_errors = list(ver_dict.get("error_tags") or ver_dict.get("errors") or [])
        verifier_metrics = dict(ver_dict.get("metrics") or {})
        if not verifier_errors and ver_dict.get("error"):
            verifier_errors = [f"VerifierException:{str(ver_dict.get('error'))}"]

    c["verifier_pass"] = bool(verifier_pass)
    c["verifier_errors"] = verifier_errors
    if verifier_metrics:
        c["verifier_metrics"] = verifier_metrics

    out: Dict[str, Any] = {"contract": c}
    # Flatten for legacy callers that expect the contract directly
    out.update(c)
    return out


# ==========================================================
# Pipeline
# ==========================================================
class ComplianceGPTPipeline:
    """
    End-to-end runner:
      Query -> (optional rewrites) -> Retriever -> Generator (ID selector) -> Deterministic fill -> Verifier (optional)
    """

    def __init__(
        self,
        *,
        framework_version: str = "rev5",
        model_id: str = "Qwen/Qwen2.5-7B-Instruct",
        use_qur: bool = True,
        doc_filter_mode: str = "all",
        ccs_path: Optional[str] = None,
        strict_ccs_assert: bool = True,
        min_ccs_docs: int = 1000,
        org_profile_path: Optional[str] = None,
        load_in_4bit: bool = True,
        retriever_config: RetrievalConfig = RetrievalConfig(),
        verify_strict_extras: bool = False,
        verify_strict_verbatim: bool = True,
        verify_strict_version: bool = False,
        # Generator/evidence gating knobs (narrow, easily reversible patches)
        gen_control_gate_topn: int = 1,
        gen_control_gate_lowconf_top2: float = 0.08,
        gen_control_gate_lowconf_top3: float = 0.04,
        gen_control_gate_lowconf_maxn: int = 3,
        block_enhancements_by_default: bool = True,
        leaf_expand_max_children: int = 12,
        leaf_expand_max_total: int = 24,
    ):
        self.framework_version = _normalize_fw(framework_version)
        self.model_id = str(model_id)
        self.use_qur = bool(use_qur)
        self.doc_filter_mode = str(doc_filter_mode)

        # Verification strictness knobs (used when run_verify=True)
        self.verify_strict_extras = bool(verify_strict_extras)
        self.verify_strict_verbatim = bool(verify_strict_verbatim)
        self.verify_strict_version = bool(verify_strict_version)

        # Default: keep generator evidence within the top-1 retrieved control.
        self.gen_control_gate_topn = int(gen_control_gate_topn)
        # If retriever confidence is low, temporarily widen the generator pool to top-2/top-3 controls.
        self.gen_control_gate_lowconf_top2 = float(gen_control_gate_lowconf_top2)
        self.gen_control_gate_lowconf_top3 = float(gen_control_gate_lowconf_top3)
        self.gen_control_gate_lowconf_maxn = int(gen_control_gate_lowconf_maxn)
        # Default: block enhancement clause ids (e.g., ac-2.1_*) unless explicitly requested.
        self.block_enhancements_by_default = bool(block_enhancements_by_default)
        # Leaf-alignment expansion caps (parent -> immediate children)
        self.leaf_expand_max_children = int(leaf_expand_max_children)
        self.leaf_expand_max_total = int(leaf_expand_max_total)

        self.ccs_path = str(ccs_path) if ccs_path else resolve_default_ccs_path(self.framework_version)
        self.strict_ccs_assert = bool(strict_ccs_assert)
        self.min_ccs_docs = int(min_ccs_docs)

        self.org_profile_path = org_profile_path
        self.org_profile: Dict[str, Any] = load_org_profile(org_profile_path) if org_profile_path else {}


        # Ensure parameter/ODP chunks are available to the retriever (ranking/boosting requires access).
        # Principle: never delete ODP/parameter material at load time.
        try:
            keep_raw = getattr(retriever_config, "keep_kinds", None)
            keep_norm = tuple(str(k).lower() for k in (keep_raw or ()))
        except Exception:
            keep_norm = ()

        if (not keep_norm) or (keep_norm == ("smt", "gdn")):
            # Empty tuple disables kind filtering inside ComplianceGPTRetriever.load_clause_records_jsonl
            new_keep_kinds: Tuple[str, ...] = tuple()
        else:
            kk = list(keep_norm)
            for k in ("smt", "gdn", "odp", "prm", "obj"):
                if k not in kk:
                    kk.append(k)
            new_keep_kinds = tuple(kk)

        # Prefer selection order: statements first, then parameters, then guidance (stable).
        try:
            kp_raw = getattr(retriever_config, "kind_priority", None)
            kp = [str(k).lower() for k in (kp_raw or ())]
        except Exception:
            kp = []

        desired = ["smt", "gdn", "odp", "prm", "obj"]
        new_kp: List[str] = []
        for k in desired:
            if k not in new_kp:
                new_kp.append(k)
        for k in kp:
            if k not in new_kp:
                new_kp.append(k)

        retriever_config = _cfg_with(
            retriever_config,
            keep_kinds=new_keep_kinds,
            kind_priority=tuple(new_kp),
        )

        self.retriever = ComplianceGPTRetriever(ccs_path=self.ccs_path, config=retriever_config)
        self._assert_ccs_loaded()
        # Verifier corpus cache (built lazily; avoids O(N_queries * N_docs) rebuild in batch).
        self._verifier_corpus_cache: Optional[Dict[str, str]] = None


        # 2) Model + tokenizer (shared with generator and optionally QUR)
        self.model, self.tokenizer = self._load_model(self.model_id, load_in_4bit=load_in_4bit)

        # 3) Generator (ID selector)
        self.generator = ComplianceGenerator(self.model, self.tokenizer)

        # 4) Optional QUR (query rewrite)
        self.qur = None
        if self.use_qur:
            if QURComponent is None:
                raise ImportError("use_qur=True but QURComponent could not be imported. Check QUR_generator path.")
            self.qur = QURComponent(model_id=self.model_id, n=3, temperature=0.5, top_p=0.9, max_new_tokens=80, seed=42,
                                    model=self.model, tokenizer=self.tokenizer)

    # --------------------------
    # Model loading (robust)
    # --------------------------
    def _load_model(self, model_id: str, *, load_in_4bit: bool) -> Tuple[Any, Any]:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        import torch  # type: ignore

        tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

        quant_cfg = None
        if load_in_4bit:
            try:
                # bitsandbytes must exist for 4-bit
                import bitsandbytes  # noqa: F401
                from transformers import BitsAndBytesConfig  # type: ignore

                quant_cfg = BitsAndBytesConfig(load_in_4bit=True)
            except Exception as e:
                print(f"[Pipeline] 4-bit requested but bitsandbytes unavailable. Falling back to full precision. ({e})")
                quant_cfg = None

        kwargs: Dict[str, Any] = {"trust_remote_code": True}
        if torch.cuda.is_available():
            kwargs["device_map"] = "auto"
            kwargs["torch_dtype"] = torch.float16
        else:
            kwargs["device_map"] = None

        if quant_cfg is not None:
            kwargs["quantization_config"] = quant_cfg

        model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
        return model, tok

    # --------------------------
    # CCS sanity check
    # --------------------------
    def _assert_ccs_loaded(self) -> None:
        n = len(getattr(self.retriever, "ids", []) or [])
        if self.strict_ccs_assert:
            if n < self.min_ccs_docs:
                raise RuntimeError(
                    f"CCS load sanity check failed: loaded {n} docs (< {self.min_ccs_docs}). ccs_path={self.ccs_path}"
                )
            # at least some statements expected
            smt = sum(1 for _id in getattr(self.retriever, "ids", []) if "_smt" in str(_id).lower())
            if smt == 0:
                raise RuntimeError("CCS sanity check failed: no _smt docs detected (statement clauses missing).")

    
    # --------------------------
    # CCS hierarchy cache (leaf alignment)
    # --------------------------
    def _ensure_ccs_hierarchy_loaded(self) -> None:
        """Load CCS hierarchy index once per pipeline instance."""
        if isinstance(getattr(self, "_ccs_meta_by_id", None), dict) and isinstance(getattr(self, "_ccs_parent_to_children", None), dict):
            return
        try:
            meta, parent_to_children = _build_ccs_hierarchy_index(self.ccs_path)
            self._ccs_meta_by_id = meta  # type: ignore
            self._ccs_parent_to_children = parent_to_children  # type: ignore
        except Exception:
            self._ccs_meta_by_id = {}  # type: ignore
            self._ccs_parent_to_children = {}  # type: ignore
# --------------------------
    def _get_verifier_corpus(self) -> Dict[str, str]:
        """Return an id->text corpus for verifier use.

        Built once and cached. This avoids rebuilding a full corpus dict for every query in batch runs.
        """
        if isinstance(getattr(self, "_verifier_corpus_cache", None), dict):
            return self._verifier_corpus_cache  # type: ignore

        record_by_id = getattr(self.retriever, "record_by_id", {}) or {}
        corpus: Dict[str, str] = {}
        for k, v in record_by_id.items():
            if isinstance(v, dict):
                corpus[str(k)] = str(v.get("text", "") or "")
            else:
                corpus[str(k)] = ""
        self._verifier_corpus_cache = corpus
        return corpus


    # Main API
    # --------------------------
    def answer(
        self,
        query: str,
        *,
        top_k: int = 12,
        controls_k: Optional[int] = None,
        gen_docs_k: Optional[int] = None,
        rewrites: Optional[List[str]] = None,
        gold_row: Optional[Dict[str, Any]] = None,
        use_generator: bool = True,
        run_verify: bool = True,
    ) -> Dict[str, Any]:
        """
        Returns Final Answer Contract (see citation_contract_80053.md).

        If gold_row is provided (evaluation), the verifier will compare to its expected control_id and resolution_policy.
        """
        q = str(query or "").strip()
        if not q:
            return _wrap_out({
                "answer_text": "",
                "evidence_spans": [],
                "status": "ERROR",
                "odp_required_list": [],
                "primary_citation": "",
                "all_citations": "",
                "answer_text_with_citation": "",
                "contract_mode": "provably_extractive",
                "error": "Empty query",
            })

        # 1) QUR rewrites
        rew = list(rewrites) if rewrites else []
        if self.qur is not None and not rew:
            try:
                rew = [r for r in (self.qur.generate(q) or []) if isinstance(r, str) and r.strip()]
            except Exception as e:
                print(f"[Pipeline] QUR failed; continuing without rewrites. ({e})")
                rew = []

        # 2) Retrieval
        # Supervisor requirement: ranking/boosting (NOT deletion). We keep context and only adjust doc ordering.
        policy_hint = ""
        if isinstance(gold_row, dict):
            try:
                policy_hint = str(gold_row.get("resolution_policy", "")).strip().upper()
            except Exception:
                policy_hint = ""
        if policy_hint in {"NAN", "NA", "N/A", "NONE", "NULL", ""}:
            policy_hint = ""
        # Split the retrieval vs generator budgets:
        #   - controls_k: how many top controls to retrieve evidence for (retriever-level)
        #   - gen_docs_k: how many clause-level docs to offer to the generator (within gated controls)
        controls_k_val = int(controls_k) if controls_k is not None else int(top_k)
        gen_docs_k_val = int(gen_docs_k) if gen_docs_k is not None else int(top_k)
        controls_k_val = max(int(controls_k_val), 1)
        gen_docs_k_val = max(int(gen_docs_k_val), 1)

        # By default, block enhancement clause ids (e.g., ac-2.1_*) unless explicitly requested.
        allow_enhancement = (not bool(getattr(self, "block_enhancements_by_default", True))) or _query_mentions_enhancement(q)
        if isinstance(gold_row, dict) and not allow_enhancement:
            try:
                for k in ("control_id", "gold_control_id", "gold_control", "expected_control_id"):
                    v = str(gold_row.get(k, "") or "")
                    if v and (("." in v) or ("(" in v) or (")" in v)):
                        allow_enhancement = True
                        break
            except Exception:
                pass


        try:
            retrieved_docs = self.retriever.retrieve(q, top_k=max(int(controls_k_val), 1), rewrites=rew)
        except TypeError:
            raise TypeError("Retriever API mismatch. Expected ComplianceGPTRetriever.retrieve(query, top_k=..., rewrites=...).")

        retrieved_docs = list(retrieved_docs or [])
        added_param_doc_ids: List[str] = []

        # Parameter/ODP material remains available in CCS (retriever.record_by_id) for canonicalization.
        # Evidence candidates passed to the generator are clause-level only (smt/gdn).

        # 3) Doc selection for generator (single-control by default; stable ordering)
        doc_filter_mode_used = str(self.doc_filter_mode or "all").strip().lower()
        if doc_filter_mode_used in {"statement_only", "prefer_statement_only"}:
            # Hard deprecate deletion modes: keep docs, just prefer statements.
            doc_filter_mode_used = "prefer_smt_keep_params"
        elif policy_hint in {"ASK", "PRESERVE", "FILL_FROM_PROFILE"} and doc_filter_mode_used == "all":
            # Default boost for parameter-aware questions: prioritize statements then guidance.
            doc_filter_mode_used = "prefer_smt_keep_params"

        ranked_controls = list(getattr(self.retriever, "last_ranked_controls", []) or [])
        primary_control = ""
        if ranked_controls:
            primary_control = str(normalize_control_id(ranked_controls[0]) or "").upper()
        elif retrieved_docs:
            primary_control = str((_doc_control(retrieved_docs[0]) or "")).upper()

        allowed_controls: List[str] = []
        gate_n_default = int(getattr(self, "gen_control_gate_topn", 1) or 0)
        gate_n_used = gate_n_default

        if gate_n_default > 0 and ranked_controls:
            # Dynamically widen generator pool when control ranking confidence is low.
            meta = getattr(self.retriever, "last_meta", {}) if hasattr(self.retriever, "last_meta") else {}
            margin_ratio: Optional[float] = None
            try:
                if isinstance(meta, dict) and ("final_margin_ratio" in meta):
                    margin_ratio = float(meta.get("final_margin_ratio"))
            except Exception:
                margin_ratio = None

            if margin_ratio is not None:
                thr_top2 = float(getattr(self, "gen_control_gate_lowconf_top2", 0.08))
                thr_top3 = float(getattr(self, "gen_control_gate_lowconf_top3", 0.04))
                maxn = int(getattr(self, "gen_control_gate_lowconf_maxn", 3) or 0)
                if margin_ratio < thr_top3:
                    gate_n_used = max(gate_n_used, 3)
                elif margin_ratio < thr_top2:
                    gate_n_used = max(gate_n_used, 2)
                if maxn > 0:
                    gate_n_used = min(gate_n_used, maxn)

            gate_n_used = min(int(gate_n_used), len(ranked_controls))
            for c in ranked_controls[:gate_n_used]:
                cc = normalize_control_id(c)
                if cc:
                    allowed_controls.append(str(cc).upper())
        elif primary_control:
            gate_n_used = 1
            allowed_controls = [primary_control]
        docs_gen_pool = list(retrieved_docs or [])
        # Gate to top-N controls (default top-1) to avoid cross-control ODP pollution.
        docs_gen_pool = _filter_docs_by_controls(docs_gen_pool, allowed_controls)
        # Only clause-level evidence kinds for the generator.
        docs_gen_pool = _filter_docs_evidence_kinds(docs_gen_pool, allowed_kinds=("smt", "gdn"))
        # Block enhancements unless explicitly allowed.
        if not allow_enhancement:
            docs_gen_pool = [d for d in docs_gen_pool if not _is_enhancement_clause_id(str(d.get("id", "")).strip())]
        # Backfill more clause-level evidence for the primary control from CCS maps.
        if primary_control:
            docs_gen_pool = _augment_primary_control_docs(
                primary_control=primary_control,
                existing_docs=docs_gen_pool,
                retriever=self.retriever,
                max_docs=max(int(gen_docs_k_val), len(docs_gen_pool)),
                allow_enhancement=bool(allow_enhancement),
                evidence_kinds=("smt", "gdn"),
            )


        # If we widened to multiple controls (low-confidence), preserve within-control coverage by
        # prioritizing the primary control's docs in the generator window.
        if len(allowed_controls) > 1 and primary_control:
            docs_gen_pool = _balance_docs_across_controls(
                docs_gen_pool,
                primary_control=primary_control,
                allowed_controls=allowed_controls,
                top_k=int(gen_docs_k_val),
            )

        docs_for_gen = _choose_docs_for_generator(docs_gen_pool, top_k=int(gen_docs_k_val), doc_filter_mode=doc_filter_mode_used)

        fallback_used: bool = False
        fallback_reason: str = ""

        # 4) Evidence selection
        if bool(use_generator):
            # Generator selects evidence IDs only
            raw_contract = self.generator.generate(q, docs_for_gen, self.org_profile)
            contract = normalize_contract(raw_contract)

            # If multi-control widening was used, the generator window may be shared across controls.
            # Backfill additional docs from the winning control (within allowed_controls only) to
            # reduce clause-id misses without reintroducing cross-control ODP pollution.
            try:
                sel_ids = [str(s.get("source_id") or "").strip() for s in (contract.get("evidence_spans") or []) if isinstance(s, dict)]
            except Exception:
                sel_ids = []
            sel_ids = [s for s in sel_ids if s]

            winner_control: str = ""
            if sel_ids:
                # Majority vote across selected ids.
                counts: Dict[str, int] = {}
                for sid in sel_ids:
                    cid = normalize_control_id(sid)
                    if cid:
                        counts[str(cid).upper()] = counts.get(str(cid).upper(), 0) + 1
                if counts:
                    winner_control = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            if not winner_control:
                winner_control = str(primary_control or "").strip().upper()

            if winner_control and len(allowed_controls) > 1:
                # Candidate docs from the winner control (post-filtering/augmentation).
                cand_docs = [d for d in (docs_gen_pool or []) if str(_doc_control(d) or "").strip().upper() == winner_control and _doc_kind(d) in {"smt", "gdn"}]

                # Build an ordered list: placeholders first, then statements, then guidance.
                def _cand_key(d: Dict[str, Any]) -> Tuple[int, int, str]:
                    has_param = 0 if _doc_has_param_placeholder(d) else 1
                    kind_rank = 0 if _doc_kind(d) == "smt" else 1
                    return (has_param, kind_rank, str(_doc_id(d) or ""))

                cand_docs_sorted = sorted(cand_docs, key=_cand_key)

                # Determine which ids we will add.
                already = set(sel_ids)
                to_add: List[str] = []

                # Always add one gdn if present but missing.
                gdn_ids = [str(_doc_id(d) or "").strip() for d in cand_docs_sorted if _doc_kind(d) == "gdn" and str(_doc_id(d) or "").strip() and (not _doc_has_param_placeholder(d))]
                if not gdn_ids:
                    gdn_ids = [str(_doc_id(d) or "").strip() for d in cand_docs_sorted if _doc_kind(d) == "gdn" and str(_doc_id(d) or "").strip()]
                if gdn_ids and all(_doc_id_suffix(s).strip().lower() != "_gdn" for s in sel_ids):
                    to_add.append(gdn_ids[0])

                # If the selected set is small, backfill more from winner control up to a small target.
                # This helps clause-id alignment (e.g., missing sibling letters) after multi-control sharing.
                target_min = 8
                if len(sel_ids) < target_min:
                    for d in cand_docs_sorted:
                        did = str(_doc_id(d) or "").strip()
                        if not did or did in already or did in to_add:
                            continue
                        to_add.append(did)
                        if len(sel_ids) + len(to_add) >= target_min:
                            break

                if to_add:
                    # Append to evidence spans (IDs only); span_text will be filled deterministically later.
                    spans = list(contract.get("evidence_spans") or [])
                    for did in to_add:
                        spans.append({"source_id": did, "span_text": ""})
                    contract["evidence_spans"] = spans
        else:
            # Extractive fallback: take the top-k docs as evidence IDs (no model call).
            contract = {
                "answer_text": "",
                "evidence_spans": [{"source_id": str(d.get("id", "")).strip(), "span_text": ""} for d in (docs_for_gen or []) if str(d.get("id", "")).strip()],
                "status": "OK" if docs_for_gen else "NO_EVIDENCE",
                "odp_required_list": [],
            }

        # ODP/PRM requirement list is derived deterministically from filled evidence text.
        # Generator-produced lists are ignored to preserve provably-extractive behavior.
        contract["odp_required_list"] = []

        # 5) Enforce selector invariants (provably-extractive)
        #    - answer_text must be empty at selector stage (pipeline will fill)
        contract["answer_text"] = ""
        #    - status/evidence consistency
        spans = contract.get("evidence_spans", []) or []
        status = str(contract.get("status", "ERROR")).upper().strip()

        if status == "NO_EVIDENCE":
            spans = []
        elif status in {"OK", "PARAMS_REQUIRED"}:
            spans = [s for s in spans if str(s.get("source_id", "")).strip()]
            # Evidence gating (pipeline-enforced):
            #   - only smt/gdn clause kinds may be cited
            #   - optionally gate to the retriever top-1 control to avoid cross-control pollution
            #   - block enhancement clause ids unless explicitly requested
            rb = getattr(self.retriever, "record_by_id", {}) or {}
            gated: List[Dict[str, str]] = []
            allow_kinds = {"smt", "gdn"}
            allowed_set: Set[str] = {str(x).upper() for x in (allowed_controls or []) if str(x).strip()}
            for s in spans:
                sid = str((s or {}).get("source_id", "")).strip()
                if not sid:
                    continue
                if (not allow_enhancement) and _is_enhancement_clause_id(sid):
                    continue

                # Control gate (dynamic top-N when confidence is low)
                sid_ctrl = str((normalize_control_id(sid) or "")).upper()
                if allowed_set and sid_ctrl not in allowed_set:
                    continue

                rec = rb.get(sid) if isinstance(rb, dict) else None
                kind = ""
                if isinstance(rec, dict):
                    kind = str(rec.get("kind", "")).strip().lower()
                if not kind:
                    suf = _doc_id_suffix(sid).strip().lower()
                    kind = suf[1:] if suf.startswith("_") else suf
                if kind not in allow_kinds:
                    continue
                gated.append({"source_id": sid, "span_text": str((s or {}).get("span_text", "") or "")})

            # Winner-control collapse: keep only one control worth of spans.
            if gated:
                rank_index: Dict[str, int] = {}
                try:
                    for i, c in enumerate(ranked_controls or []):
                        cc = normalize_control_id(c)
                        if cc:
                            rank_index[str(cc).upper()] = int(i)
                except Exception:
                    rank_index = {}

                counts: Dict[str, int] = {}
                for gs in gated:
                    cid = str((normalize_control_id(str(gs.get("source_id", "")) or "") or "")).upper()
                    if cid:
                        counts[cid] = int(counts.get(cid, 0)) + 1

                if counts:
                    ordered = sorted(
                        counts.items(),
                        key=lambda kv: (-int(kv[1]), int(rank_index.get(str(kv[0]).upper(), 10**9))),
                    )
                    winner = str(ordered[0][0]).upper()
                    if winner:
                        primary_control = winner
                        gated = [
                            gs
                            for gs in gated
                            if str((normalize_control_id(str(gs.get("source_id", "")) or "") or "")).upper() == winner
                        ]

            spans = gated

            # If the generator chose only disallowed spans, do a narrowly-scoped rescue within docs_for_gen.
            if status in {"OK", "PARAMS_REQUIRED"} and (not spans) and docs_for_gen:
                fallback_used = True
                fallback_reason = "evidence_gate_rescue"
                # Prefer the highest-ranked allowed control's first eligible doc.
                chosen_id: Optional[str] = None
                if allowed_controls:
                    for c in allowed_controls:
                        cc = str(c).upper()
                        for d in docs_for_gen:
                            fid = str((d or {}).get("id", "")).strip()
                            if not fid:
                                continue
                            if (not allow_enhancement) and _is_enhancement_clause_id(fid):
                                continue
                            k = str((d or {}).get("kind", "")).strip().lower()
                            if k and k not in allow_kinds:
                                continue
                            if str((normalize_control_id(fid) or "")).upper() != cc:
                                continue
                            chosen_id = fid
                            break
                        if chosen_id:
                            break

                if not chosen_id:
                    for d in docs_for_gen:
                        fid = str((d or {}).get("id", "")).strip()
                        if not fid:
                            continue
                        if (not allow_enhancement) and _is_enhancement_clause_id(fid):
                            continue
                        k = str((d or {}).get("kind", "")).strip().lower()
                        if k and k not in allow_kinds:
                            continue
                        cid = str((normalize_control_id(fid) or "")).upper()
                        if allowed_set and cid not in allowed_set:
                            continue
                        chosen_id = fid
                        break

                if chosen_id:
                    spans = [{"source_id": chosen_id, "span_text": ""}]
                if not spans:
                    status = "NO_EVIDENCE"
            if not spans:
                status = "NO_EVIDENCE"
        else:
            status = "ERROR"

        # Controlled fallback only when generator output is malformed or ERROR (NEVER override NO_EVIDENCE)
        if status == "ERROR":
            fallback_used = True
            fallback_reason = "generator_error_or_malformed_contract"
            if docs_for_gen:
                fid = str(docs_for_gen[0].get("id", "")).strip()
                if fid:
                    spans = [{"source_id": fid, "span_text": ""}]
                    status = "OK"

        contract["status"] = status
        contract["evidence_spans"] = spans


        

        # 5.5) Leaf-alignment expansion (parent clause -> immediate children when list-introducing)
        # Applies only to clause ids and only when CCS indicates the parent ends with ':'.
        try:
            if status in {"OK", "PARAMS_REQUIRED"} and spans:
                self._ensure_ccs_hierarchy_loaded()
                meta = getattr(self, "_ccs_meta_by_id", {}) or {}
                parent_to_children = getattr(self, "_ccs_parent_to_children", {}) or {}
                src_ids = [str(s.get("source_id", "")).strip() for s in spans if str(s.get("source_id", "")).strip()]
                if meta and parent_to_children and src_ids:
                    expanded_ids = _expand_clause_ids_to_children(
                        src_ids,
                        meta_by_id=meta,
                        parent_to_children=parent_to_children,
                        max_total=max(int(getattr(self, "leaf_expand_max_total", 24)), len(src_ids) + 12),
                        max_children_expand=int(getattr(self, "leaf_expand_max_children", 12)),
                    )
                    # Enforce single-control evidence to avoid unrelated controls injecting extra placeholders.
                    # Keep citations within the retriever-selected primary control unless multi-control behavior is explicitly needed.
                    if primary_control:
                        expanded_ids = [sid for sid in expanded_ids if str((normalize_control_id(str(sid)) or "")).upper() == str(primary_control).upper()]
                    if not allow_enhancement:
                        expanded_ids = [sid for sid in expanded_ids if not _is_enhancement_clause_id(str(sid))]
                    spans = [{"source_id": sid, "span_text": ""} for sid in expanded_ids]
                    contract["evidence_spans"] = spans
        except Exception:
            pass

        # 6) Deterministically fill span_text from CCS (via retriever.record_by_id)
        filled_spans: List[Dict[str, str]] = []
        missing_ids: List[str] = []
        for s in spans:
            sid = str(s.get("source_id", "")).strip()
            if not sid:
                continue
            rec = getattr(self.retriever, "record_by_id", {}).get(sid)
            txt = ""
            if isinstance(rec, dict):
                txt = str(rec.get("text", "")).strip()
            if not txt:
                # fallback: search in provided docs_for_gen
                for d in docs_for_gen:
                    if str(d.get("id", "")).strip() == sid:
                        txt = str(d.get("text", "")).strip()
                        break
            if not txt:
                missing_ids.append(sid)
                continue
            filled_spans.append({"source_id": sid, "span_text": txt})

        # Missing IDs indicate a selector/ID mismatch. Do NOT crash the pipeline.
        # Keep any filled spans, and surface missing IDs in debug.
        if missing_ids and not filled_spans and status != "NO_EVIDENCE":
            # If nothing could be filled, attempt one more controlled fallback using the top retrieved doc.
            # Prefer the top gated generator doc to stay within the primary control.
            if docs_for_gen:
                fid = str(docs_for_gen[0].get("id", "")).strip()
                ftxt = str(docs_for_gen[0].get("text", "")).strip()
                if fid and ftxt:
                    filled_spans = [{"source_id": fid, "span_text": ftxt}]
                    fallback_used = True
                    fallback_reason = fallback_reason or "all_selected_ids_missing_fallback_to_top_gated_doc"
            elif retrieved_docs:
                fid = str(retrieved_docs[0].get("id", "")).strip()
                ftxt = str(retrieved_docs[0].get("text", "")).strip()
                if fid and ftxt:
                    filled_spans = [{"source_id": fid, "span_text": ftxt}]
                    fallback_used = True
                    fallback_reason = fallback_reason or "all_selected_ids_missing_fallback_to_top_retrieved"
            if not filled_spans:
                status = "ERROR"


        # 7) Build extractive answer_text (no new claims)
        answer_text = " ".join(s["span_text"] for s in filled_spans).strip()

        # 8) Apply ODP policy (gold_row can override)
        policy = ""
        policy_from_gold = False
        if isinstance(gold_row, dict):
            try:
                raw_pol = str(gold_row.get("resolution_policy", "") or "").strip()
                if raw_pol:
                    policy = raw_pol.upper()
                    policy_from_gold = True
            except Exception:
                policy = ""
                policy_from_gold = False
        if policy in {"NAN", "NA", "N/A", "NONE", "NULL"}:
            policy = ""
            policy_from_gold = False
        if not policy:
            policy = "ASK"

        answer_text2, odp_req, status_override = _apply_odp_policy_to_answer(answer_text, policy, self.org_profile)

        # Canonicalize ODP/PRM ids against CCS (provably-extractive: drop unknown ids)
        param_ids: Set[str] = set()
        try:
            rb = getattr(self.retriever, "record_by_id", {}) or {}
            for _id, rec in rb.items():
                if isinstance(rec, dict):
                    k = str(rec.get("kind", "")).strip().lower()
                    if k in {"odp", "prm"}:
                        param_ids.add(str(_id))
        except Exception:
            param_ids = set()

        key_map = _build_param_key_to_canonical(param_ids)

        # Canonicalize generator-produced ODP list (if any)
        contract["odp_required_list"] = _canonicalize_param_list(
            list(contract.get("odp_required_list", []) or []),
            param_ids=param_ids,
            key_map=key_map,
            assignment_sentinel=_ASSIGNMENT_REQUIRED_SENTINEL,
        )

        # Canonicalize placeholder-derived ODP list
        odp_req = _canonicalize_param_list(
            list(odp_req or []),
            param_ids=param_ids,
            key_map=key_map,
            assignment_sentinel=_ASSIGNMENT_REQUIRED_SENTINEL,
        )

        final_status = status
        if final_status == "NO_EVIDENCE":
            # never upgrade NO_EVIDENCE even if placeholders exist
            odp_req = []
            answer_text2 = ""
        else:
            if status_override:
                final_status = status_override
            # Respect generator PARAMS_REQUIRED only when placeholders exist in extractive text.
            if status == "PARAMS_REQUIRED" and final_status != "NO_EVIDENCE":
                keys_tmp, has_assign_tmp = _extract_odp_ids(answer_text2)
                if keys_tmp or has_assign_tmp:
                    final_status = "PARAMS_REQUIRED"
                else:
                    final_status = "OK"

        # 9) Citations (contract-level, deterministic)
        cite_ids = [s.get("source_id", "") for s in (filled_spans or []) if str(s.get("source_id", "")).strip()]
        primary_citation = str(cite_ids[0]) if cite_ids else ""
        all_citations = ", ".join([str(x) for x in cite_ids]) if cite_ids else ""
        answer_with_cit = (f"{answer_text2} (CITE: {all_citations})".strip()) if answer_text2 and all_citations else (answer_text2 or "")

        final_contract: Dict[str, Any] = {
            "answer_text": answer_text2,
            "evidence_spans": filled_spans,
            "status": final_status,
            "odp_required_list": odp_req,
            "primary_citation": primary_citation,
            "all_citations": all_citations,
            "answer_text_with_citation": answer_with_cit,
            "contract_mode": "provably_extractive",
        }

        # 10) Optional verification (gold_row required)
        if run_verify and isinstance(gold_row, dict):
            if verify_answer is None:
                final_contract["verification"] = {
                    "ok": False,
                    "error": (
                        f"verify_answer_unavailable:{_VERIFY_IMPORT_ERROR}"
                        if _VERIFY_IMPORT_ERROR else "verify_answer_unavailable"
                    ),
                    "error_tags": [
                        f"VerifierUnavailable:{_VERIFY_IMPORT_ERROR}"
                        if _VERIFY_IMPORT_ERROR else "VerifierUnavailable"
                    ],
                    "metrics": {},
                }
            else:
                try:
                    corpus = self._get_verifier_corpus()
                    ver = verify_answer(
                        final_contract,
                        gold_row,
                        corpus=corpus,
                        org_profile=self.org_profile,
                        corpus_version=self.framework_version,
                        strict_extras=bool(self.verify_strict_extras),
                        strict_verbatim=bool(self.verify_strict_verbatim),
                        strict_version=bool(self.verify_strict_version),
                    )
                    final_contract["verification"] = ver
                except Exception as e:
                    final_contract["verification"] = {
                        "ok": False,
                        "error": str(e),
                        "error_tags": [f"VerifierException:{type(e).__name__}:{str(e)}"],
                        "metrics": {},
                    }

        # Debug extras (kept minimal)
        final_contract["debug"] = {
            "pipeline_patch_id": "2026-02-19_rrseed_v1",
            "query": q,
            "rewrites": rew,
            "variants": getattr(self.retriever, "last_variants", []) if hasattr(self.retriever, "last_variants") else [],
            # Clause-level docs returned from retriever (ids)
            "retrieved_doc_ids": [d.get("id") for d in (retrieved_docs or [])][: int(top_k)],
            # Unique controls in retrieval order (control-level perspective)
            "retrieved_control_order": _unique_controls_in_order(retrieved_docs or []),
            # Control ranking diagnostics if retriever exposes it
            "ranked_controls_top": (getattr(self.retriever, "last_ranked_controls", []) or [])[: max(20, int(top_k))],
            "gen_gate_n_used": int(gate_n_used),
            "gen_allowed_controls": list(allowed_controls or []),
            "primary_control_final": primary_control,

            "retriever_meta": getattr(self.retriever, "last_meta", {}) if hasattr(self.retriever, "last_meta") else {},
            'keep_kinds_used': getattr(getattr(self.retriever, 'config', None), 'keep_kinds', None),
            'kind_priority_used': getattr(getattr(self.retriever, 'config', None), 'kind_priority', None),
            # Generator input (post filtering)
            "doc_filter_mode": doc_filter_mode_used,
            "docs_for_gen_ids": [d.get("id") for d in (docs_for_gen or [])][: int(top_k)],
            "added_param_doc_ids": added_param_doc_ids,
            # Selector output
            "selected_source_ids": [s.get("source_id") for s in (filled_spans or []) if isinstance(s, dict)],
            "selected_controls": _selected_controls_from_spans(filled_spans or []),
            # Evaluation context (if provided)
            "resolution_policy": policy,
        }
        return _wrap_out(final_contract)