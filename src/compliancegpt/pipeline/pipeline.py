# -*- coding: utf-8 -*-
"""
ComplianceGPT Pipeline (provably-extractive, clean naming)

Single source of truth:
- `ccs_path` is the canonical name for the clause-level CCS JSONL file.
- The retriever must accept: ComplianceGPTRetriever(ccs_path=...)
- The generator must output Selector Contract (IDs only).
- The pipeline deterministically fills verbatim `span_text` from CCS and constructs `answer_text`.

This file is designed to live at:
  /content/drive/MyDrive/ComplianceGPT/src/compliancegpt/pipeline/pipeline.py
"""

from __future__ import annotations

import re
import json
import copy

# Control id regex used by normalize_control_id().
# Matches variants like 'AC-2', 'AC 02', 'ac-2_smt.h.1', and 'AC-2(1)'.
_CTRL_ID_RE = re.compile(r"\b([A-Za-z]{2})\s*[-_ ]?\s*0*([0-9]{1,2})(?:\([0-9]+\))?(?=[^A-Za-z0-9]|$)")

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import fields as _dc_fields, is_dataclass as _is_dataclass, replace as _dc_replace

# Imports
# ----------------------------
from compliancegpt.generator.generator import ComplianceGenerator, load_org_profile, normalize_contract  # type: ignore
from compliancegpt.pipeline.evidence_window import (  # type: ignore
    assert_same_evidence_window,
    build_evidence_window,
    evidence_window_manifest,
    select_allowed_controls,
)
from compliancegpt.pipeline.odp_policy import (
    ASSIGNMENT_REQUIRED_SENTINEL as _ASSIGNMENT_REQUIRED_SENTINEL,
    apply_odp_policy_to_answer as _apply_odp_policy_to_answer,
    extract_odp_ids as _extract_odp_ids,
    normalize_resolution_policy as _normalize_resolution_policy,
    profile_lookup as _profile_lookup,
)
from compliancegpt.pipeline.profile_resolution import resolve_profile_answer

PIPELINE_PATCH_ID = "2026-03-12-odp-statement-rescue-v3"

_VERIFY_IMPORT_ERROR = None
try:
    from compliancegpt.generator.verifier.verifier import verify_answer, verify_contract_validity  # type: ignore
    try:
        from compliancegpt.generator.verifier.verifier import parse_control_from_source_id  # type: ignore
    except Exception:
        parse_control_from_source_id = None  # type: ignore
except Exception as e:
    verify_answer = None  # type: ignore
    parse_control_from_source_id = None  # type: ignore
    verify_contract_validity = None  # type: ignore
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
    base = Path("/content/drive/MyDrive/ComplianceGPT/data/ccs/nist800-53")
    if fw == "rev5":
        return str(base / "NIST_SP-800-53_rev5_catalog.jsonl")
    return str(base / "NIST_SP-800-53_rev4_catalog.jsonl")


def resolve_default_odp_registry_path(framework_version: str) -> str:
    fw = _normalize_fw(framework_version)
    base = Path("/content/drive/MyDrive/ComplianceGPT/data/ODP")
    if fw == "rev5":
        return str(base / "rev5" / "odp_registry_rev5.json")
    return str(base / "rev4" / "odp_registry_rev4.json")


def load_odp_registry(path: Optional[str]) -> Dict[str, Any]:
    """Load ODP registry mapping param_id -> metadata.

    This is safe/non-cheating: it contains labels/prompts only (no values).
    """
    if not path:
        return {}
    try:
        p = Path(str(path))
        if not p.exists():
            return {}
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _build_query_plan_debug(original_query: str, rewrites: Any, retrieval_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    plan: Dict[str, Any] = {
        "original_query": str(original_query or ""),
        "rewrites": list(rewrites or []),
    }
    try:
        qt = dict(((retrieval_meta or {}).get("query_transform") or {}))
    except Exception:
        qt = {}

    rq = str(qt.get("retrieval_query") or "").strip()
    if rq:
        plan["retrieval_query"] = rq

    rr = qt.get("retrieval_rewrites")
    if isinstance(rr, list):
        plan["retrieval_rewrites"] = list(rr)

    qs = str(qt.get("query_scope") or "").strip()
    if qs:
        plan["query_scope"] = qs

    qmeta = qt.get("query_meta")
    if isinstance(qmeta, dict):
        removed = qmeta.get("meta_removed")
        expansions = qmeta.get("expansions")
        if isinstance(removed, list) and removed:
            plan["retrieval_meta_removed"] = list(removed)
        if isinstance(expansions, list) and expansions:
            plan["retrieval_expansions"] = list(expansions)

    return plan

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
    small_child_threshold: int = 4,
    max_ancestor_hops: int = 6,
) -> List[str]:
    """Apply a conservative hierarchy closure over clause ids.

    Primary goal (general, non-gold-specific): reduce "MissedDocIds" caused by missing
    base statements or small, clearly-defined child clauses.

    Closure rules (bounded):
      1) If a selected clause has ancestors (via parent_part_id), include ancestors up to the
         top-level clause (max_ancestor_hops). This captures "base statement" ids such as
         'ra-5_smt' when citing 'ra-5_smt.a'.
      2) If a selected clause is a parent with a *small* number of children (<= small_child_threshold),
         include those children (depth-1). This captures cases like citing 'si-4_smt.c' while
         gold expects 'si-4_smt.c.1' and 'si-4_smt.c.2'.
      3) Preserve original order as much as possible, de-duplicate, and truncate to max_total.

    Safety constraints:
      - Only expands within smt/gdn kinds.
      - Avoids citation explosion by requiring small branching factor for child expansion.
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

    def _ancestors(cid: str) -> List[str]:
        chain: List[str] = []
        cur = cid
        hops = 0
        while hops < int(max_ancestor_hops):
            parent = str((meta_by_id.get(cur) or {}).get("parent_part_id", "") or "").strip()
            if not parent:
                break
            if parent in chain:
                break
            if _kind(parent) and _kind(parent) not in allowed:
                break
            if not _has_prose(parent):
                # Skip non-prose nodes but continue climbing; they sometimes exist as structural nodes.
                cur = parent
                hops += 1
                continue
            chain.append(parent)
            cur = parent
            hops += 1
        # Return from root-most to leaf-most ancestor
        chain.reverse()
        return chain

    for sid in (source_ids or []):
        s = str(sid or "").strip()
        if not s:
            continue

        # 1) Always include ancestor chain (bounded). This captures missing base statement ids.
        for anc in _ancestors(s):
            _add(anc)

        parent = str((meta_by_id.get(s) or {}).get("parent_part_id", "") or "").strip()

        # If this is a child and parent carries important context (params / list intro), ensure parent is kept.
        if parent and parent not in seen:
            ptxt = _txt(parent)
            if _has_param_placeholder(ptxt) or _is_list_intro(ptxt) or _used_desc(parent):
                _add(parent)

        # Always keep the originally selected id.
        _add(s)

        # 2) If this is a parent, optionally add immediate children.
        kids = parent_to_children.get(s, []) or []
        if kids:
            stxt = _txt(s)
            should_expand = _is_list_intro(stxt) or _used_desc(s) or (0 < len(kids) <= int(small_child_threshold))
            if should_expand:
                for k in kids[: int(max_children_expand)]:
                    _add(str(k))

        # 3) If this is a child of a small parent, include siblings (bounded by threshold).
        if parent:
            pkids = parent_to_children.get(parent, []) or []
            if 0 < len(pkids) <= int(small_child_threshold):
                for k in pkids[: int(max_children_expand)]:
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

    Evidence kinds passed to the generator are restricted to clause-level:
      - statement ("_smt")
      - supplemental guidance ("_gdn")

    Modes:
      - "all": pass through (top_k slice only, then kind gating)
      - "statement_only": only _smt docs   [DEPRECATED: deletes context; kept for backwards-compatibility]
      - "prefer_statement_only": if any _smt exist, use only those; else pass through  [DEPRECATED]
      - "prefer_smt_keep_params": stable sort statements first then guidance
      - "prefer_smt_drop_params": legacy alias; behaves like prefer_smt_keep_params (no placeholder-based re-ranking)
    """
    mode = str(doc_filter_mode or "all").strip().lower()
    docs = list(retrieved_docs or [])

    def _kind_of(d: Dict[str, Any]) -> str:
        k = str(d.get("kind") or "").strip().lower()
        if k:
            return k
        suf = _doc_id_suffix(d.get("id", "")).strip().lower()
        return suf[1:] if suf.startswith("_") else suf

    if mode == "all":
        out = docs
    elif mode == "statement_only":
        out = _statement_only_docs(docs)
    elif mode == "prefer_statement_only":
        smt = _statement_only_docs(docs)
        out = smt if smt else docs
    elif mode in {"prefer_smt_keep_params", "prefer_smt_drop_params"}:
        order = {"smt": 0, "gdn": 1}
        indexed = list(enumerate(docs))
        indexed.sort(key=lambda t: (order.get(_kind_of(t[1]), 9), t[0]))
        out = [d for _, d in indexed]
    else:
        raise ValueError(f"Unknown doc_filter_mode={doc_filter_mode!r}")

    # Evidence gating
    allowed = {"smt", "gdn"}
    out = [d for d in out if _kind_of(d) in allowed]

    # Slice + de-dup (preserve order)
    if top_k is not None and int(top_k) > 0:
        k = int(top_k)
        out = out[:k]

    seen_ids: Set[str] = set()
    dedup: List[Dict[str, Any]] = []
    for d in out:
        did = str(d.get("id", "")).strip()
        if not did or did in seen_ids:
            continue
        seen_ids.add(did)
        dedup.append(d)

    return dedup
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



def _filter_docs_to_controls(
    docs: List[Dict[str, Any]],
    allowed_controls: List[str],
) -> List[Dict[str, Any]]:
    """Backward-compatible alias for older pipeline code."""
    return _filter_docs_by_controls(docs, allowed_controls)


def _apply_doc_filter_mode(
    docs: List[Dict[str, Any]],
    doc_filter_mode: str,
) -> List[Dict[str, Any]]:
    """Apply generator doc filter mode to an already assembled doc pool.

    This is a thin compatibility wrapper over `_choose_docs_for_generator`.
    """
    mode = str(doc_filter_mode or "all").strip().lower()
    # Historical aliases seen in older notebooks
    if mode in {"smt_only", "statement_only"}:
        mode = "statement_only"
    elif mode in {"prefer_smt", "prefer_statement"}:
        mode = "prefer_statement_only"

    try:
        return _choose_docs_for_generator(list(docs or []), top_k=len(docs or []), doc_filter_mode=mode)
    except Exception:
        # Fail open: never crash batch because a mode name drifted.
        return list(docs or [])
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



def _best_primary_citation(query: str, spans: List[Dict[str, str]]) -> str:
    """Pick primary citation by simple token overlap between query and span text."""
    q = str(query or "").lower()
    qtoks = set(re.findall(r"[a-z0-9]+", q))
    if not qtoks:
        # fallback to first
        for s in (spans or []):
            sid = str(s.get("source_id", "")).strip()
            if sid:
                return sid
        return ""
    best_sid = ""
    best_score = -1
    for s in (spans or []):
        sid = str(s.get("source_id", "")).strip()
        txt = str(s.get("span_text", "")).lower()
        if not sid or not txt:
            continue
        stoks = set(re.findall(r"[a-z0-9]+", txt))
        score = len(qtoks & stoks)
        if score > best_score:
            best_score = score
            best_sid = sid
    if best_sid:
        return best_sid
    for s in (spans or []):
        sid = str(s.get("source_id", "")).strip()
        if sid:
            return sid
    return ""
def _build_citation_suffix(framework_version: str) -> str:
    fw = _normalize_fw(framework_version)
    if fw == "rev5":
        return "NIST SP 800-53 Rev. 5"
    return "NIST SP 800-53 Rev. 4"


def _build_ask_list(
    required_param_ids: List[str],
    filled_spans: List[Dict[str, str]],
    odp_registry: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build structured ask_list entries from registry + cited spans (no values)."""
    req = [str(x).strip() for x in (required_param_ids or []) if str(x).strip()]
    if not req:
        return []
    # map param_id -> list[source_id] where it appears
    param_to_sources: Dict[str, List[str]] = {}
    for sp in (filled_spans or []):
        sid = str(sp.get("source_id", "")).strip()
        txt = str(sp.get("span_text", "") or "")
        if not sid or not txt:
            continue
        keys, has_assign = _extract_odp_ids(txt)
        for k in keys:
            kid = str(k).strip()
            if kid:
                param_to_sources.setdefault(kid, [])
                if sid not in param_to_sources[kid]:
                    param_to_sources[kid].append(sid)
        if has_assign:
            param_to_sources.setdefault(_ASSIGNMENT_REQUIRED_SENTINEL, [])
            if sid not in param_to_sources[_ASSIGNMENT_REQUIRED_SENTINEL]:
                param_to_sources[_ASSIGNMENT_REQUIRED_SENTINEL].append(sid)

    out: List[Dict[str, Any]] = []
    for pid in req:
        if pid == _ASSIGNMENT_REQUIRED_SENTINEL:
            out.append({
                "param_id": _ASSIGNMENT_REQUIRED_SENTINEL,
                "friendly_label": "Assignment placeholder",
                "raw_marker": "[assignment: ...]",
                "ask_prompt": "Provide the organization-defined assignment value referenced in the cited clause(s).",
                "source_ids": param_to_sources.get(_ASSIGNMENT_REQUIRED_SENTINEL, []),
            })
            continue
        meta = odp_registry.get(pid) if isinstance(odp_registry, dict) else None
        if isinstance(meta, dict):
            out.append({
                "param_id": pid,
                "friendly_label": meta.get("friendly_label"),
                "raw_marker": meta.get("raw_marker"),
                "ask_prompt": meta.get("ask_prompt"),
                "data_type": meta.get("data_type"),
                "cardinality": meta.get("cardinality"),
                "source_ids": param_to_sources.get(pid, []),
            })
        else:
            out.append({
                "param_id": pid,
                "friendly_label": None,
                "raw_marker": None,
                "ask_prompt": f"What value does your organization use for parameter: {pid}?",
                "source_ids": param_to_sources.get(pid, []),
            })
    return out




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

def _query_allows_enhancements(query: str) -> bool:
    """Allow enhancements only when the query explicitly references a control enhancement (e.g., AC-2(1))."""
    q = str(query or "").upper()
    if not q:
        return False
    return bool(re.search(r"\b[A-Z]{2}-\d{1,2}\(\d+\)(?!\w)", q)) or ("ENHANCEMENT" in q)


def _extract_control_hints(query: str) -> List[str]:
    """Extract explicit control references from the query (base + enhancements).

    Returns canonical forms aligned with CCS ids:
      - base: "AC-2"
      - enhancement: "AC-2.1"  (from "AC-2(1)")
    """
    q = str(query or "")
    if not q:
        return []
    out: List[str] = []

    # Enhancements: AC-2(1) -> AC-2.1
    for m in re.finditer(r"\b([A-Za-z]{2}-\d{1,2})\((\d+)\)(?!\w)", q):
        base = str(m.group(1) or "").upper()
        num = str(m.group(2) or "").strip()
        try:
            n = str(int(num))
        except Exception:
            n = num
        if base and n:
            out.append(f"{base}.{n}")

    # Base controls
    for m in re.finditer(r"\b([A-Za-z]{2}-\d{1,2})\b", q):
        base = str(m.group(1) or "").upper()
        if not base:
            continue
        # Avoid duplicating base when enhancement already present.
        if any(x.startswith(base + ".") for x in out):
            continue
        out.append(base)

    # De-dup preserve order
    seen: Set[str] = set()
    final: List[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            final.append(x)
    return final


def _rescue_odp_statement_spans(
    *,
    filled_spans: List[Dict[str, str]],
    winner_control: str,
    record_by_id: Dict[str, Dict[str, Any]],
    resolution_policy: Any,
    allow_enhancements: bool = False,
    max_add: int = 4,
) -> Tuple[List[Dict[str, str]], List[str], bool]:
    """
    Deterministic guardrail for ASK/FILL_FROM_PROFILE paths.

    If the current final evidence contains no unresolved ODP markers, but the selected
    base control has statement clauses with ODP placeholders, prepend those statement
    clauses so downstream ODP policy can see them.

    This does not consult any gold labels and remains fully extractive.
    """
    pol = _normalize_resolution_policy(resolution_policy)
    if pol not in {"ASK", "FILL_FROM_PROFILE"}:
        return list(filled_spans or []), [], False

    current = "\n\n".join([str(s.get("span_text", "") or "") for s in (filled_spans or [])]).strip()
    keys_now, has_assign_now = _extract_odp_ids(current)
    if keys_now or has_assign_now:
        return list(filled_spans or []), [], False

    wc = normalize_control_id(winner_control)
    if not wc:
        return list(filled_spans or []), [], False

    wc_low = wc.lower()
    existing_ids: Set[str] = {
        str(s.get("source_id", "")).strip() for s in (filled_spans or [])
        if str(s.get("source_id", "")).strip()
    }

    def _sort_key(sid: str) -> Tuple[int, str]:
        s = str(sid or "").strip().lower()
        base_leaf_prefix = f"{wc_low}_smt."
        base_exact = f"{wc_low}_smt"
        if s.startswith(base_leaf_prefix):
            return (0, s)
        if s == base_exact:
            return (1, s)
        return (2, s)

    rescue: List[Dict[str, str]] = []
    for sid, rec in sorted((record_by_id or {}).items(), key=lambda kv: _sort_key(kv[0])):
        if len(rescue) >= int(max_add):
            break
        if sid in existing_ids:
            continue
        if not isinstance(rec, dict):
            continue

        rid = str(rec.get("id", sid) or sid).strip()
        if not rid:
            continue
        if rid in existing_ids:
            continue
        if not allow_enhancements and _is_enhancement_clause_id(rid):
            continue

        rec_ctl = normalize_control_id(rec.get("control_id", ""))
        if str(rec_ctl or "").upper() != wc.upper():
            continue

        kind = str(rec.get("kind", "") or "").strip().lower()
        if kind != "smt":
            continue

        txt = str(rec.get("text", "") or "").strip()
        if not txt:
            continue

        keys, has_assign = _extract_odp_ids(txt)
        if not keys and not has_assign:
            continue

        rescue.append({"source_id": rid, "span_text": txt})

    if not rescue:
        return list(filled_spans or []), [], False

    merged: List[Dict[str, str]] = []
    seen: Set[str] = set()
    for sp in rescue + list(filled_spans or []):
        sid = str(sp.get("source_id", "")).strip()
        txt = str(sp.get("span_text", "") or "").strip()
        if not sid or not txt or sid in seen:
            continue
        seen.add(sid)
        merged.append({"source_id": sid, "span_text": txt})

    added_ids = [str(sp.get("source_id", "")).strip() for sp in rescue if str(sp.get("source_id", "")).strip()]
    return merged, added_ids, True


def _build_identifier_provenance(
    *,
    final_spans: List[Dict[str, str]],
    selector_ids: List[str],
    fallback_ids: List[str],
    hierarchy_ids: List[str],
    rescue_ids: List[str],
    evidence_window_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Emit one positive runtime origin for every final source identifier."""
    selector_set = {str(value).strip() for value in selector_ids if str(value).strip()}
    fallback_set = {str(value).strip() for value in fallback_ids if str(value).strip()}
    hierarchy_set = {str(value).strip() for value in hierarchy_ids if str(value).strip()}
    rescue_set = {str(value).strip() for value in rescue_ids if str(value).strip()}
    window_set = (
        {str(value).strip() for value in evidence_window_ids if str(value).strip()}
        if evidence_window_ids is not None
        else None
    )

    provenance: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for span in final_spans or []:
        source_id = str(span.get("source_id", "") or "").strip()
        if not source_id:
            raise ValueError("A final evidence span has no source_id.")
        if source_id in seen:
            raise ValueError(f"Duplicate final source_id: {source_id}")
        seen.add(source_id)

        matching_origins = [
            origin
            for origin, identifiers in (
                ("selector", selector_set),
                ("fallback", fallback_set),
                ("hierarchy", hierarchy_set),
                ("rescue", rescue_set),
            )
            if source_id in identifiers
        ]
        if len(matching_origins) != 1:
            raise ValueError(
                f"Expected exactly one provenance origin for {source_id}; "
                f"found {matching_origins}."
            )

        record: Dict[str, Any] = {
            "source_id": source_id,
            "origin": matching_origins[0],
        }
        if window_set is not None:
            record["in_evidence_window"] = source_id in window_set
        provenance.append(record)

    return provenance


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

    # Acceptance-tests compatibility aliases
    if "answer_text_with_citation" not in c:
        c["answer_text_with_citation"] = str(c.get("answer_text_with_citations", c.get("answer_text", "")) or "")
    if "answer_text_with_citations" not in c:
        c["answer_text_with_citations"] = str(c.get("answer_text_with_citation", c.get("answer_text", "")) or "")
    if "contract_mode" not in c:
        c["contract_mode"] = "provably_extractive"

    out: Dict[str, Any] = {"contract": c}
    # Flatten for legacy callers that expect the contract directly
    out.update(c)
    return out


# ==========================================================
# Pipeline
# ==========================================================
def _ensure_ccs_hierarchy_loaded(
    meta_by_id: Dict[str, Dict[str, Any]],
    parent_to_children: Dict[str, List[str]],
) -> None:
    """Module-level alias used by older pipeline code paths.

    Builds parent-to-children mapping from CCS metadata if `parent_to_children` is empty.
    This is non-cheating: it uses only CCS fields (e.g., `parent_part_id`).
    """
    if parent_to_children:
        return
    try:
        for cid, meta in (meta_by_id or {}).items():
            if not isinstance(meta, dict):
                continue
            parent = meta.get("parent_part_id")
            if parent:
                parent = str(parent)
                parent_to_children.setdefault(parent, []).append(str(cid))
        for p in list(parent_to_children.keys()):
            parent_to_children[p] = sorted(set(parent_to_children[p]))
    except Exception:
        return
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
        model_revision: Optional[str] = None,
        shared_model: Any = None,
        shared_tokenizer: Any = None,
        generator_instance: Any = None,
        retriever_instance: Any = None,
        use_qur: bool = True,
        doc_filter_mode: str = "all",
        ccs_path: Optional[str] = None,
        odp_registry_path: Optional[str] = None,
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
        leaf_expand_max_children: int = 16,
        leaf_expand_max_total: int = 64,
        leaf_expand_levels: int = 2,
        enable_hierarchy_closure: bool = False,
        resolution_policy: str = "ASK",
    ):
        self.framework_version = _normalize_fw(framework_version)
        self.model_id = str(model_id)
        self.model_revision = str(model_revision).strip() if model_revision else None
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
        self.leaf_expand_levels = int(leaf_expand_levels)

        # Optional: hierarchy closure expansion of cited clause ids (strict mode keeps this off).
        self.enable_hierarchy_closure = bool(enable_hierarchy_closure)
        # ODP resolution policy for single/batch runs (MUST NOT be sourced from gold labels).
        self.resolution_policy = str(resolution_policy or "ASK")

        self.ccs_path = str(ccs_path) if ccs_path else resolve_default_ccs_path(self.framework_version)
        self.strict_ccs_assert = bool(strict_ccs_assert)
        self.min_ccs_docs = int(min_ccs_docs)

        self.org_profile_path = org_profile_path
        self.org_profile: Dict[str, Any] = load_org_profile(org_profile_path) if org_profile_path else {}

        # ODP registry (labels/prompts only; never contains values)
        self.odp_registry_path = (
            str(odp_registry_path)
            if odp_registry_path
            else resolve_default_odp_registry_path(self.framework_version)
        )
        self.odp_registry: Dict[str, Any] = load_odp_registry(self.odp_registry_path)



        # Keep the default retrieval corpus clause-level: statements and guidance only.
        # The retriever also loads the full CCS inventory into record_by_id, including
        # ODP/PRM parameter records, so the pipeline can canonicalize parameters,
        # validate ODP IDs, apply ODP policy, and support verifier checks.
        # Parameter records are not default evidence-ranking candidates.
        try:
            keep_raw = getattr(retriever_config, "keep_kinds", None)
            keep_norm = tuple(str(k).lower() for k in (keep_raw or ()))
        except Exception:
            keep_norm = ()

        if not keep_norm:
            # Default: retrieval corpus is clause-only.
            new_keep_kinds: Tuple[str, ...] = ("smt", "gdn")
        else:
            # Respect explicit keep_kinds from config; do not auto-expand with params.
            new_keep_kinds = tuple(keep_norm)

        # Stable kind priority for downstream inventory ordering and diagnostics.
        # Evidence generation remains gated to clause-level kinds (smt/gdn).
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

        # A prepared-context RQ2 run must not initialize or invoke a live
        # retriever.  It only needs the recorded CCS inventory for deterministic
        # citation filling and verification.  Supplying ``retriever_instance``
        # makes that separation explicit while preserving the normal runtime
        # path when it is omitted.
        if retriever_instance is None:
            self.retriever = ComplianceGPTRetriever(ccs_path=self.ccs_path, config=retriever_config)
        else:
            self.retriever = retriever_instance
        self._assert_ccs_loaded()
        # Verifier corpus cache (built lazily; avoids O(N_queries * N_docs) rebuild in batch).
        self._verifier_corpus_cache: Optional[Dict[str, str]] = None


        # 2) Model + tokenizer (shared with generator and optionally QUR)
        if (shared_model is None) != (shared_tokenizer is None):
            raise ValueError("shared_model and shared_tokenizer must be supplied together.")
        if shared_model is not None:
            self.model, self.tokenizer = shared_model, shared_tokenizer
        else:
            self.model, self.tokenizer = self._load_model(
                self.model_id,
                load_in_4bit=load_in_4bit,
                revision=self.model_revision,
            )
        self.model_resolved_revision = str(
            getattr(getattr(self.model, "config", None), "_commit_hash", "")
            or self.model_revision
            or ""
        ).strip()
        self.tokenizer_resolved_revision = str(
            (getattr(self.tokenizer, "init_kwargs", {}) or {}).get("_commit_hash", "")
            or self.model_revision
            or ""
        ).strip()

        # 3) Generator (ID selector).  A frozen selector can be injected for a
        # prepared-context replay; the ordinary runtime still constructs the
        # model-backed selector exactly as before.
        self.generator = (
            generator_instance
            if generator_instance is not None
            else ComplianceGenerator(self.model, self.tokenizer)
        )

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
    def _load_model(
        self,
        model_id: str,
        *,
        load_in_4bit: bool,
        revision: Optional[str] = None,
    ) -> Tuple[Any, Any]:
        from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        import torch  # type: ignore

        tok = AutoTokenizer.from_pretrained(
            model_id,
            revision=revision,
            trust_remote_code=True,
        )

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
        if revision:
            kwargs["revision"] = str(revision)
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

    def _ensure_param_inventory_loaded(self) -> None:
        """Build and cache CCS parameter inventory (ODP/PRM ids) for canonicalization."""
        if getattr(self, "_param_ids", None) is not None and getattr(self, "_param_key_map", None) is not None:
            return
        self._assert_ccs_loaded()
        param_ids: Set[str] = set()
        try:
            for rid, rec in (self.retriever.record_by_id or {}).items():
                k = str(rec.get("kind", "") or "").strip().lower()
                if k in {"odp", "prm"}:
                    param_ids.add(str(rid))
        except Exception:
            param_ids = set()
        self._param_ids = param_ids
        self._param_key_map = _build_param_key_to_canonical(param_ids)

    def _hierarchy_closure_expand(self, source_ids: List[str]) -> Tuple[List[str], List[str]]:
        """
        Defensible hierarchy closure for clause ids.

        Allowed expansions (bounded; no gold use):
          - add ancestors up to the base statement (*_smt) for each cited clause
          - expand small container/list-intro nodes to their children (bounded), up to N levels

        Returns: (expanded_ids_preserving_order, added_ids)
        """
        if not source_ids:
            return [], []
        if not bool(self.enable_hierarchy_closure):
            return list(source_ids), []

        self._assert_ccs_loaded()
        self._ensure_ccs_hierarchy_loaded()

        meta_by_id = self._ccs_meta_by_id
        parent_to_children = self._ccs_parent_to_children

        max_children = max(0, int(getattr(self, "leaf_expand_max_children", 0)))
        max_total = max(0, int(getattr(self, "leaf_expand_max_total", 0)))
        max_levels = max(0, int(getattr(self, "leaf_expand_levels", 1)))

        original_set = set([str(s) for s in source_ids if str(s).strip()])
        seen: Set[str] = set()
        ordered: List[str] = []

        def _add(x: str) -> None:
            x2 = str(x or "").strip()
            if not x2:
                return
            if x2 in seen:
                return
            if x2 not in meta_by_id:
                return
            seen.add(x2)
            ordered.append(x2)

        def _is_base_stmt(x: str) -> bool:
            xl = (x or "").strip().lower()
            return bool(re.search(r"_smt$", xl))

        def _is_container_node(x: str) -> bool:
            m = meta_by_id.get(x) or {}
            if not m:
                return False
            kids = list(parent_to_children.get(x, []) or [])
            if not kids:
                return False
            if bool(m.get("used_descendants")):
                return True
            txt = str(m.get("text", "") or "").strip()
            if txt.endswith(":"):
                return True
            hp = m.get("has_prose")
            if hp is False:
                return True
            # If the node has children at all, treat it as container (bounded by caps below).
            return True

        # 1) Add originals + ancestors (up to base statement)
        for sid in source_ids:
            _add(sid)
            cur = str(sid or "").strip()
            guard = 0
            while cur and guard < 32:
                guard += 1
                parent = str((meta_by_id.get(cur) or {}).get("parent_part_id") or "").strip()
                if not parent or parent == cur:
                    break
                _add(parent)
                if _is_base_stmt(parent):
                    break
                cur = parent

        # 2) Expand container nodes to children (bounded; multi-level downward closure)
        if max_children > 0 and max_total > 0 and max_levels > 0:
            # BFS seeded from the ORIGINAL ids only; descendants may be expanded up to max_levels.
            queue: List[Tuple[str, int]] = []
            best_level: Dict[str, int] = {}
            for sid in source_ids:
                s = str(sid or "").strip()
                if not s:
                    continue
                if s not in meta_by_id:
                    continue
                best_level[s] = 0
                queue.append((s, 0))

            while queue:
                pid, lvl = queue.pop(0)
                if len(ordered) >= max_total:
                    break
                if lvl >= max_levels:
                    continue
                if not _is_container_node(pid):
                    continue

                kids = list(parent_to_children.get(pid, []) or [])
                if not kids:
                    continue
                if len(kids) > max_children:
                    try:
                        kids = sorted(str(x) for x in kids)
                    except Exception:
                        kids = list(kids)
                    kids = kids[: int(max_children)]

                for kid in kids:
                    if len(ordered) >= max_total:
                        break
                    km = meta_by_id.get(kid) or {}
                    kind = str(km.get("kind", "") or "").strip().lower()
                    txt = str(km.get("text", "") or "").strip()
                    if kind not in {"smt", "gdn"}:
                        continue
                    if not txt:
                        continue
                    _add(kid)
                    # Queue child for further expansion (if within level budget).
                    nl = lvl + 1
                    if nl < max_levels and kid in meta_by_id and _is_container_node(kid):
                        prev = best_level.get(kid)
                        if prev is None or nl < prev:
                            best_level[kid] = nl
                            queue.append((kid, nl))

        expanded = list(ordered)
        added = [x for x in expanded if x not in original_set]
        return expanded, added


    def _resolve_rewrites(
        self,
        query: str,
        rewrites: Any = None,
    ) -> List[str]:
        """
        Resolve query rewrites for a single run.

        Priority:
          1) caller-provided rewrites
          2) auto-generated rewrites from QUR (when enabled)
          3) empty list
        """
        if rewrites is not None:
            out: List[str] = []
            if isinstance(rewrites, (list, tuple)):
                for r in rewrites:
                    if isinstance(r, str) and r.strip():
                        out.append(r.strip())
                    elif isinstance(r, dict):
                        txt = str(r.get("rewrite") or r.get("text") or "").strip()
                        if txt:
                            out.append(txt)
                    elif r is not None:
                        txt = str(r).strip()
                        if txt:
                            out.append(txt)
            elif isinstance(rewrites, str):
                txt = rewrites.strip()
                if txt:
                    out = [txt]
            else:
                txt = str(rewrites).strip()
                if txt:
                    out = [txt]
            return list(dict.fromkeys(out))

        if self.use_qur and self.qur is not None:
            try:
                gen = self.qur.generate(str(query))
                out = [str(x).strip() for x in (gen or []) if str(x).strip()]
                return list(dict.fromkeys(out))
            except Exception:
                return []

        return []

    def answer(
        self,
        query: str,
        top_k: int = 10,
        rewrites: Any = None,
        gold_row: Optional[Dict[str, Any]] = None,
        use_generator: bool = True,
        run_verify: bool = False,
        doc_filter_mode: Optional[str] = None,
        statement_only_on_param_queries: bool = True,
        prepared_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        End-to-end single query -> extractive contract.

        Hard constraints:
          - No gold leakage: `gold_row` is used ONLY inside the verifier call.
          - Evidence must be clause-level (smt/gdn) with verbatim spans from CCS.
          - No CCS inventory backfill (adding clauses that were not retrieved) unless explicitly enabled.
        """
        q = str(query or "").strip()
        if not q:
            err_contract = {
                "question": "",
                "framework_version": self.framework_version,
                "answer_text": "",
                "answer_text_with_citations": "",
                "evidence_spans": [],
                "status": "ERROR",
                "odp_required_list": [],
                "primary_citation": "",
                "all_citations": "",
                "debug": {"error": "empty_query"},
            }
            return _wrap_out(err_contract)

        self._assert_ccs_loaded()
        context = dict(prepared_context or {})
        if context:
            context_question = str(context.get("question", "") or "").strip()
            context_revision = str(context.get("framework_version", "") or "").strip().lower()
            if context_question and context_question != q:
                raise ValueError("Prepared RQ2 context question does not match the requested question.")
            if context_revision and _normalize_fw(context_revision) != self.framework_version:
                raise ValueError("Prepared RQ2 context revision does not match the pipeline revision.")
            rewrites_used = self._resolve_rewrites(q, context.get("rewrites", []))
        else:
            rewrites_used = self._resolve_rewrites(q, rewrites)

        def _attach_contract_validity(contract_obj: Dict[str, Any]) -> Dict[str, Any]:
            if "verify_contract_validity" in globals() and callable(globals().get("verify_contract_validity")):
                try:
                    vp, verrs = verify_contract_validity(
                        json_output=contract_obj,
                        corpus=self._get_verifier_corpus(),
                        org_profile=self.org_profile,
                        strict_verbatim=bool(self.verify_strict_verbatim),
                        corpus_version=self.framework_version,
                        expected_resolution_policy=("FILL_FROM_PROFILE" if
                            _normalize_resolution_policy(self.resolution_policy) == "FILL_FROM_PROFILE" else None),
                    )
                    contract_obj["validity_check"] = {
                        "is_pass": bool(vp),
                        "errors": list(verrs or []),
                    }
                except Exception as e:
                    contract_obj["validity_check"] = {
                        "is_pass": False,
                        "errors": [f"ValidityCheckException:{repr(e)}"],
                    }
            return contract_obj

        # 1) Retrieve docs (clause-level)
        top_k = max(1, int(top_k))
        retrieval_meta: Dict[str, Any] = {}
        retrieved_docs: List[Dict[str, Any]] = []
        try:
            if context:
                retrieved_docs = copy.deepcopy(list(context.get("retrieved_docs", []) or []))
                retrieval_meta = copy.deepcopy(dict(context.get("retrieval_meta", {}) or {}))
            elif hasattr(self.retriever, "retrieve_debug"):
                retrieved_docs, retrieval_meta = self.retriever.retrieve_debug(q, top_k=top_k, rewrites=rewrites_used)
            else:
                retrieved_docs = self.retriever.retrieve(q, top_k=top_k, rewrites=rewrites_used)
                retrieval_meta = dict(getattr(self.retriever, "last_meta", {}) or {})
        except Exception as e:
            err_contract = {
                "question": q,
                "framework_version": self.framework_version,
                "answer_text": "",
                "answer_text_with_citations": "",
                "evidence_spans": [],
                "status": "ERROR",
                "odp_required_list": [],
                "primary_citation": "",
                "all_citations": "",
                "debug": {"error": "retrieval_failed", "exception": repr(e)},
            }
            return _wrap_out(err_contract)

        if not retrieved_docs:
            no_ev = {
                "question": q,
                "framework_version": self.framework_version,
                "answer_text": "",
                "answer_text_with_citations": "",
                "evidence_spans": [],
                "status": "NO_EVIDENCE",
                "odp_required_list": [],
                "primary_citation": "",
                "all_citations": "",
                "debug": {
                    "query_plan": _build_query_plan_debug(q, rewrites_used, retrieval_meta),
                    "retrieval_meta": retrieval_meta,
                    "retrieved_docs": 0,
                },
            }
            no_ev = _attach_contract_validity(no_ev)
            # Even if no evidence, allow verifier call to label agreement metrics.
            if bool(run_verify) and gold_row is not None:
                ver = verify_answer(
                    json_output=no_ev,
                    gold_row=gold_row,
                    corpus=self._get_verifier_corpus(),
                    org_profile=self.org_profile,
                    corpus_version=self.framework_version,
                    strict_extras=bool(self.verify_strict_extras),
                    strict_verbatim=bool(self.verify_strict_verbatim),
                    strict_version=bool(self.verify_strict_version),
                )
                no_ev["verification"] = _verifier_result_to_dict(ver)
            return _wrap_out(no_ev)

        try:
            topn = max(1, int(getattr(self, "gen_control_gate_topn", 1)))
        except Exception:
            topn = 1
        try:
            low2 = float(getattr(self, "gen_control_gate_lowconf_top2", 0.08))
            low3 = float(getattr(self, "gen_control_gate_lowconf_top3", 0.04))
            maxn = max(1, int(getattr(self, "gen_control_gate_lowconf_maxn", 3)))
        except Exception:
            low2, low3, maxn = 0.08, 0.04, 3
        controls, primary_control, allowed_controls, widen_tier = select_allowed_controls(
            retrieved_docs=retrieved_docs,
            retrieval_meta=retrieval_meta,
            normalize_control_id=normalize_control_id,
            topn=topn,
            lowconf_top2=low2,
            lowconf_top3=low3,
            lowconf_maxn=maxn,
        )

        # 4) Doc filtering for generator window
        # Policy-aware default: when we are ASK-ing or FILL-ing, keep both statement + guidance
        # and do not apply any query-keyword heuristics.
        doc_filter_mode_used = str(
            doc_filter_mode if doc_filter_mode is not None else self.doc_filter_mode
        ).strip().lower()
        if not doc_filter_mode_used:
            doc_filter_mode_used = "prefer_smt_keep_params"
        pol_eff = str(self.resolution_policy or "").strip().upper()
        if pol_eff in {"", "NAN", "NA", "N/A", "NONE", "NULL", "AUTO"}:
            pol_eff = "FILL_FROM_PROFILE"
        if pol_eff in {"FILL", "PROFILE", "FILL_PROFILE"}:
            pol_eff = "FILL_FROM_PROFILE"

        if pol_eff in {"ASK", "FILL_FROM_PROFILE"} and doc_filter_mode_used == "all":
            doc_filter_mode_used = "prefer_smt_keep_params"

        try:
            primary_first_min_margin = float(getattr(self, "gen_primary_first_min_margin_ratio", 0.06))
        except Exception:
            primary_first_min_margin = 0.06
        docs_for_gen, window_audit = build_evidence_window(
            retrieved_docs=retrieved_docs,
            retrieval_meta=retrieval_meta,
            allowed_controls=allowed_controls,
            primary_control=primary_control,
            doc_filter_mode=doc_filter_mode_used,
            gen_docs_k=int(getattr(self, "gen_docs_k", 24)),
            filter_docs_to_controls=_filter_docs_to_controls,
            apply_doc_filter_mode=_apply_doc_filter_mode,
            primary_first_min_margin_ratio=primary_first_min_margin,
        )
        if context.get("evidence_window") is not None:
            locked_docs = copy.deepcopy(list(context.get("evidence_window", []) or []))
            locked_manifest = evidence_window_manifest(locked_docs)
            expected_manifest = dict(context.get("evidence_window_manifest", {}) or locked_manifest)
            assert_same_evidence_window(
                window_audit.get("evidence_window", {}),
                locked_manifest,
                expected_manifest,
            )
            docs_for_gen = locked_docs
            window_audit["evidence_window"] = locked_manifest
        primary_first_applied = bool(window_audit.get("primary_first_applied", False))

        # 5) Evidence selection
        fallback_used = False
        fallback_reason = ""
        raw_contract: Dict[str, Any] = {}

        if bool(use_generator):
            try:
                raw_contract = self.generator.generate(q, docs_for_gen, self.org_profile)
            except Exception as e:
                raw_contract = {"status": "ERROR", "evidence_spans": [], "debug": {"exception": repr(e)}}
        else:
            raw_contract = {"status": "OK", "evidence_spans": [{"source_id": d.get("id", "")} for d in docs_for_gen[:3]]}

        contract = normalize_contract(raw_contract)

        # Determine which control the generator actually cited (if any).
        def _control_from_clause_id(cid_like: str) -> str:
            s = str(cid_like or "").strip()
            if not s:
                return ""
            # Prefer authoritative mapping via record_by_id when available.
            rec = self.retriever.record_by_id.get(s)
            if rec:
                cc = normalize_control_id(rec.get("control_id", ""))
                return cc.upper() if cc else ""
            # Fall back: take prefix before '_' and normalize.
            prefix = s.split("_", 1)[0]
            cc = normalize_control_id(prefix)
            return cc.upper() if cc else ""

        sel_ids_raw: List[str] = []
        try:
            sel_ids_raw = [str(s.get("source_id") or "").strip() for s in (contract.get("evidence_spans") or []) if isinstance(s, dict)]
        except Exception:
            sel_ids_raw = []
        sel_ids_raw = [s for s in sel_ids_raw if s]
        control_hints = _extract_control_hints(q)
        has_enh_hint = any('.' in c for c in (control_hints or []))
        # Filter out enhancement clause ids unless query explicitly allows enhancements.
        allow_enh = bool(_query_allows_enhancements(q)) or bool(has_enh_hint)
        if bool(getattr(self, "block_enhancements_by_default", False)) and not allow_enh:
            sel_ids_raw = [cid for cid in (sel_ids_raw or []) if not _is_enhancement_clause_id(str(cid))]



        winner_control = primary_control

        # Prefer explicit control references in the question (base + enhancements).
        if control_hints:
            winner_control = str(control_hints[0]).upper()
        elif sel_ids_raw:
            counts: Dict[str, int] = {}
            for sid in sel_ids_raw:
                cc = _control_from_clause_id(sid)
                if not cc:
                    continue
                counts[cc] = counts.get(cc, 0) + 1
            if counts:
                winner_control = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]

        # Lightweight re-rank among candidate controls using lexical overlap with control texts.
        # This helps when retrieval confuses nearby controls (e.g., IA-5 vs IA-6) without using gold.
        try:
            if not control_hints:
                cand: Set[str] = set()
                if primary_control:
                    cand.add(str(primary_control).upper())
                for d in (docs_for_gen or [])[:25]:
                    cc0 = normalize_control_id(d.get("control_id", ""))
                    if cc0:
                        cand.add(str(cc0).upper())
                for sid in (sel_ids_raw or [])[:25]:
                    cc1 = _control_from_clause_id(sid)
                    if cc1:
                        cand.add(str(cc1).upper())

                def _tok(s: str) -> Set[str]:
                    s2 = str(s or "").lower()
                    parts = re.findall(r"[a-z0-9]{3,}", s2)
                    return set(parts)

                qtok = _tok(q)
                best_ctl = winner_control
                best_score = -1.0

                for ctl in sorted(cand):
                    text_parts: List[str] = []
                    for suf in ("_smt", "_gdn"):
                        sid2 = f"{str(ctl).lower()}{suf}"
                        rec2 = self.retriever.record_by_id.get(sid2)
                        if rec2:
                            t2 = str(rec2.get("text", "") or "").strip()
                            if t2:
                                text_parts.append(t2)
                    if not text_parts:
                        continue

                    ctoks = _tok(" ".join(text_parts))
                    overlap = float(len(qtok & ctoks))

                    rs = 0.0
                    for d in (docs_for_gen or [])[:25]:
                        dc = normalize_control_id(d.get("control_id", ""))
                        if dc and str(dc).upper() == str(ctl).upper():
                            try:
                                rs += float(d.get("score", 0.0) or 0.0)
                            except Exception:
                                rs += 0.0

                    score = overlap * 10.0 + rs
                    if score > best_score:
                        best_score = score
                        best_ctl = str(ctl).upper()

                if best_score >= 0.0:
                    winner_control = best_ctl
        except Exception:
            pass

        # Deterministic fallback if generator returned nothing or errored
        if not sel_ids_raw and docs_for_gen:
            fallback_used = True
            fallback_reason = "empty_evidence_from_generator" if bool(use_generator) else "no_generator"
            top_doc = docs_for_gen[0]
            contract = {
                "answer_text": "",
                "evidence_spans": [{"source_id": str(top_doc.get("id", "")).strip(), "span_text": ""}],
                "status": "OK",
                "odp_required_list": [],
                "debug": {"fallback": fallback_reason},
            }
            sel_ids_raw = [str(top_doc.get("id", "")).strip()]
        # 6) Hierarchy closure (defensible; bounded)
        if bool(self.enable_hierarchy_closure):
            expanded_ids, added_ids = self._hierarchy_closure_expand(sel_ids_raw)
        else:
            expanded_ids, added_ids = list(sel_ids_raw), []


        # Ensure clause-only and fill verbatim span_text from CCS
        filled_spans: List[Dict[str, str]] = []
        for sid in expanded_ids:
            rec = self.retriever.record_by_id.get(sid)
            if not rec:
                continue
            kind = str(rec.get("kind", "") or "").strip().lower()
            if kind not in {"smt", "gdn"}:
                continue
            txt = str(rec.get("text", "") or "").strip()
            if not txt:
                continue
            filled_spans.append({"source_id": str(rec.get("id", sid)), "span_text": txt})

        secondary_fallback_used = False
        secondary_fallback_reason = ""
        secondary_fallback_selected_id = ""
        secondary_fallback_candidates_checked: List[str] = []

        if not filled_spans:
            # Secondary deterministic fallback: if the generator-selected ids cannot be filled into valid
            # clause spans (e.g., missing record, non-clause kind, or empty text), select the first
            # retriever-returned clause record with non-empty text. This remains fully extractive and does
            # not consult any gold labels.
            cand_ids: List[str] = []
            # Prefer hierarchy-expanded ids first, then retriever candidates.
            for _sid in (expanded_ids or []):
                s2 = str(_sid or "").strip()
                if s2 and s2 not in cand_ids:
                    cand_ids.append(s2)
            for d in (docs_for_gen or [])[:50]:
                s2 = str(d.get("id", "") or "").strip()
                if s2 and s2 not in cand_ids:
                    cand_ids.append(s2)

            # If we are in an ODP asking mode, prefer candidates that actually contain ODP markers.
            want_odp = str(contract.get("status", "") or "").strip().upper() == "PARAMS_REQUIRED" or bool(contract.get("odp_required_list"))
            best_id = ""
            best_txt = ""

            def _is_valid_clause_text(_rec: Dict[str, Any]) -> bool:
                k = str(_rec.get("kind", "") or "").strip().lower()
                if k not in {"smt", "gdn"}:
                    return False
                t = str(_rec.get("text", "") or "").strip()
                return bool(t)

            for _sid in cand_ids:
                rec2 = self.retriever.record_by_id.get(_sid)
                if not isinstance(rec2, dict):
                    continue
                if not _is_valid_clause_text(rec2):
                    continue
                t2 = str(rec2.get("text", "") or "").strip()
                secondary_fallback_candidates_checked.append(str(rec2.get("id", _sid)))
                if want_odp:
                    keys, has_assign = _extract_odp_ids(t2)
                    if keys or has_assign:
                        best_id = str(rec2.get("id", _sid))
                        best_txt = t2
                        break
                if not best_id:
                    best_id = str(rec2.get("id", _sid))
                    best_txt = t2
                if want_odp and len(secondary_fallback_candidates_checked) >= 25:
                    break

            if best_id and best_txt:
                secondary_fallback_used = True
                secondary_fallback_reason = "no_valid_clause_spans_after_fill"
                secondary_fallback_selected_id = best_id
                filled_spans = [{"source_id": best_id, "span_text": best_txt}]

        odp_statement_rescue_used = False
        odp_statement_rescue_added_ids: List[str] = []
        if filled_spans:
            filled_spans, odp_statement_rescue_added_ids, odp_statement_rescue_used = _rescue_odp_statement_spans(
                filled_spans=filled_spans,
                winner_control=winner_control,
                record_by_id=self.retriever.record_by_id,
                resolution_policy=self.resolution_policy,
                allow_enhancements=allow_enh,
                max_add=4,
            )

        if not filled_spans:
            final_contract = {
                "question": q,
                "framework_version": self.framework_version,
                "answer_text": "",
                "answer_text_with_citations": "",
                "evidence_spans": [],
                "status": "NO_EVIDENCE",
                "odp_required_list": [],
                "primary_citation": "",
                "all_citations": "",
                "provenance": [],
                "debug": {
                    "query_plan": _build_query_plan_debug(q, rewrites_used, retrieval_meta),
                    "retrieval_meta": retrieval_meta,
                    "allowed_controls": allowed_controls,
                    "doc_filter_mode_used": doc_filter_mode_used,
                    "primary_first_applied": primary_first_applied,
                    "winner_control": winner_control,
                    "selector_raw": contract,
                    "hierarchy_added_ids": added_ids,
                    "fallback_used": fallback_used,
                    "fallback_reason": fallback_reason,
                    "secondary_fallback_used": secondary_fallback_used,
                    "secondary_fallback_reason": secondary_fallback_reason,
                    "secondary_fallback_selected_id": secondary_fallback_selected_id,
                    "secondary_fallback_candidates_checked": secondary_fallback_candidates_checked[:10],
                    "odp_statement_rescue_used": odp_statement_rescue_used,
                    "odp_statement_rescue_added_ids": odp_statement_rescue_added_ids,
                },
            }
            final_contract = _attach_contract_validity(final_contract)
            if bool(run_verify) and gold_row is not None:
                ver = verify_answer(
                    json_output=final_contract,
                    gold_row=gold_row,
                    corpus=self._get_verifier_corpus(),
                    org_profile=self.org_profile,
                    corpus_version=self.framework_version,
                    strict_extras=bool(self.verify_strict_extras),
                    strict_verbatim=bool(self.verify_strict_verbatim),
                    strict_version=bool(self.verify_strict_version),
                )
                final_contract["verification"] = _verifier_result_to_dict(ver)
            return _wrap_out(final_contract)

        # 7) Build answer text (extractive)
        answer_text = "\n\n".join([s["span_text"] for s in filled_spans]).strip()

        # 8) Apply ODP policy (ASK/PRESERVE/FILL_FROM_PROFILE), then canonicalize required list
        profile_resolution = None
        if _normalize_resolution_policy(self.resolution_policy) == "FILL_FROM_PROFILE":
            answer_text2, odp_required_raw, status_override, profile_resolution = resolve_profile_answer(
                filled_spans, self.org_profile, self.framework_version,
            )
        else:
            answer_text2, odp_required_raw, status_override = _apply_odp_policy_to_answer(
                answer_text=answer_text,
                policy=self.resolution_policy,
                org_profile=self.org_profile,
            )

        self._ensure_param_inventory_loaded()
        param_ids: Set[str] = getattr(self, "_param_ids", set()) or set()
        key_map: Dict[str, str] = getattr(self, "_param_key_map", {}) or {}

        odp_required_canon = _canonicalize_param_list(
            raw_list=odp_required_raw,
            param_ids=param_ids,
            key_map=key_map,
            assignment_sentinel=_ASSIGNMENT_REQUIRED_SENTINEL,
        )

        odp_final = odp_required_canon if odp_required_canon else list(dict.fromkeys([str(x).strip() for x in (odp_required_raw or []) if str(x).strip()]))

        status = str(status_override or "").strip().upper()
        if not status:
            status = "OK"

        
        # 8.1) Build ask_list (structured prompts) only when we are actively asking for params.
        ask_list: List[Dict[str, Any]] = []
        pol_eff = str(self.resolution_policy or "").strip().upper()
        if pol_eff in {"", "NAN", "NA", "N/A", "NONE", "NULL", "AUTO"}:
            pol_eff = "FILL_FROM_PROFILE"
        if pol_eff in {"FILL", "PROFILE", "FILL_PROFILE"}:
            pol_eff = "FILL_FROM_PROFILE"

        if status == "PARAMS_REQUIRED" and pol_eff in {"ASK", "FILL_FROM_PROFILE"}:
            ask_list = _build_ask_list(odp_final, filled_spans, self.odp_registry)
        # 9) Citations fields
        cite_ids = [str(s.get("source_id", "")).strip() for s in filled_spans if str(s.get("source_id", "")).strip()]
        citation_query = str((((retrieval_meta or {}).get("query_transform") or {}).get("retrieval_query")) or q)
        primary_citation = _best_primary_citation(citation_query, filled_spans) if cite_ids else ""
        all_citations = ", ".join(cite_ids)

        suffix = _build_citation_suffix(self.framework_version)
        if all_citations:
            answer_text_with_citations = f"{answer_text2}\n\nCitations: {all_citations} ({suffix})".strip()
        else:
            answer_text_with_citations = answer_text2

        selector_origin_ids = [] if fallback_used else list(sel_ids_raw)
        fallback_origin_ids = list(sel_ids_raw) if fallback_used else []
        if secondary_fallback_used and secondary_fallback_selected_id:
            selector_origin_ids = []
            fallback_origin_ids = [secondary_fallback_selected_id]
        evidence_window_ids = list(
            dict(window_audit.get("evidence_window", {}) or {}).get("source_ids", []) or []
        )
        provenance = _build_identifier_provenance(
            final_spans=filled_spans,
            selector_ids=selector_origin_ids,
            fallback_ids=fallback_origin_ids,
            hierarchy_ids=added_ids,
            rescue_ids=odp_statement_rescue_added_ids,
            evidence_window_ids=evidence_window_ids,
        )

        final_contract = {
            "question": q,
            "framework_version": self.framework_version,
            "answer_text": answer_text2,
            "answer_text_with_citations": answer_text_with_citations,
            "evidence_spans": filled_spans,
            "status": status,
            "odp_required_list": odp_final,
            "ask_list": ask_list,
            "primary_citation": primary_citation,
            "all_citations": all_citations,
            "provenance": provenance,
            "debug": {
                "query_plan": _build_query_plan_debug(q, rewrites_used, retrieval_meta),
                "retrieval_meta": retrieval_meta,
                "allowed_controls": allowed_controls,
                "control_widen_tier": widen_tier,
                "primary_control": primary_control,
                "winner_control": winner_control,
                "selector_raw": contract,
                "doc_filter_mode_used": doc_filter_mode_used,
                "primary_first_applied": primary_first_applied,
                "evidence_window": window_audit.get("evidence_window", {}),
                "prepared_context_sha256": str(context.get("context_sha256", "") or ""),
                "hierarchy_added_ids": added_ids,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
                "secondary_fallback_used": secondary_fallback_used,
                "secondary_fallback_reason": secondary_fallback_reason,
                "secondary_fallback_selected_id": secondary_fallback_selected_id,
                "secondary_fallback_candidates_checked": secondary_fallback_candidates_checked[:10],
                "odp_statement_rescue_used": odp_statement_rescue_used,
                "odp_statement_rescue_added_ids": odp_statement_rescue_added_ids,
                "counts": {
                    "retrieved_docs": int(len(retrieved_docs)),
                    "docs_for_gen": int(len(docs_for_gen)),
                    "evidence_spans": int(len(filled_spans)),
                },
            },
        }

        if profile_resolution is not None:
            final_contract["profile_resolution"] = profile_resolution
            final_contract["resolution_policy"] = "FILL_FROM_PROFILE"
        final_contract = _attach_contract_validity(final_contract)

        # 10) Verifier (gold-only)
        if bool(run_verify) and gold_row is not None:
            ver = verify_answer(
                json_output=final_contract,
                gold_row=gold_row,
                corpus=self._get_verifier_corpus(),
                org_profile=self.org_profile,
                corpus_version=self.framework_version,
                strict_extras=bool(self.verify_strict_extras),
                strict_verbatim=bool(self.verify_strict_verbatim),
                strict_version=bool(self.verify_strict_version),
            )
            final_contract["verification"] = _verifier_result_to_dict(ver)

        return _wrap_out(final_contract)


# ---------------------------------------------------------------------------
# Backward-compatible API shim
# ---------------------------------------------------------------------------
# The research-clean pipeline *should* expose `answer`. This shim preserves that
# public API without changing retrieval or citation behavior.
try:
    if "ComplianceGPTPipeline" in globals():
        _cls = globals()["ComplianceGPTPipeline"]
        if not hasattr(_cls, "answer"):
            # Fallback to common legacy entrypoints if present.
            if hasattr(_cls, "run_single"):
                def answer(self, *args, **kwargs):  # type: ignore
                    return self.run_single(*args, **kwargs)
                setattr(_cls, "answer", answer)
            elif any("__call__" in c.__dict__ for c in _cls.mro()):
                def answer(self, *args, **kwargs):  # type: ignore
                    return self.__call__(*args, **kwargs)
                setattr(_cls, "answer", answer)
except Exception:
    # Do not fail import because of a shim.
    pass
