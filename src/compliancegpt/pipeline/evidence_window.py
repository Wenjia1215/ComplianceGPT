"""Deterministic evidence-window construction for matched answerer experiments.

This module contains no model or retriever imports.  Both ComplianceGPT and the
generative baseline call the same function so a paired experiment cannot drift
because one answer path implements a different ordering or truncation rule.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple


Doc = Dict[str, Any]
FilterControls = Callable[[List[Doc], List[str]], List[Doc]]
ApplyFilterMode = Callable[[List[Doc], str], List[Doc]]
NormalizeControl = Callable[[Any], Any]


def select_allowed_controls(
    *,
    retrieved_docs: Sequence[Mapping[str, Any]],
    retrieval_meta: Mapping[str, Any],
    normalize_control_id: NormalizeControl,
    topn: int = 1,
    lowconf_top2: float = 0.08,
    lowconf_top3: float = 0.04,
    lowconf_maxn: int = 3,
) -> Tuple[List[str], str, List[str], int]:
    """Apply the shared, gold-independent control gate used by both answer paths."""

    controls: List[str] = []
    try:
        controls = [
            str(normalize_control_id(control)).upper()
            for control in ((retrieval_meta or {}).get("selected_controls") or [])
            if normalize_control_id(control)
        ]
    except Exception:
        controls = []

    if not controls:
        seen = set()
        for doc in retrieved_docs or []:
            control = normalize_control_id((doc or {}).get("control_id", ""))
            if not control:
                continue
            normalized = str(control).upper()
            if normalized in seen:
                continue
            seen.add(normalized)
            controls.append(normalized)

    primary_control = controls[0] if controls else ""
    limit = max(1, int(topn))
    allowed_controls = controls[:limit] if primary_control else controls[:1]
    widen_tier = 0

    try:
        value = (retrieval_meta or {}).get("final_margin_ratio", None)
        margin = float(value) if value is not None else 1.0
    except Exception:
        margin = 1.0

    maximum = max(1, int(lowconf_maxn))
    if primary_control and len(controls) >= 2:
        if margin < float(lowconf_top3) and len(controls) >= 3:
            count = min(len(controls), maximum, 3)
            allowed_controls = controls[:count]
            widen_tier = max(0, count - 1)
        elif margin < float(lowconf_top2):
            count = min(len(controls), maximum, 2)
            allowed_controls = controls[:count]
            widen_tier = max(0, count - 1)

    return controls, primary_control, allowed_controls, widen_tier


def evidence_window_manifest(docs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Return an order-sensitive, text-sensitive manifest for a model window."""

    records: List[Dict[str, str]] = []
    for position, doc in enumerate(docs):
        source_id = str((doc or {}).get("id", "") or "").strip()
        text = str((doc or {}).get("text", "") or "")
        records.append(
            {
                "position": str(position),
                "source_id": source_id,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )

    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": "rq2-evidence-window-v1",
        "record_count": len(records),
        "source_ids": [record["source_id"] for record in records],
        "records": records,
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def build_evidence_window(
    *,
    retrieved_docs: Sequence[Mapping[str, Any]],
    retrieval_meta: Mapping[str, Any],
    allowed_controls: Sequence[str],
    primary_control: str,
    doc_filter_mode: str,
    gen_docs_k: int,
    filter_docs_to_controls: FilterControls,
    apply_doc_filter_mode: ApplyFilterMode,
    primary_first_min_margin_ratio: float = 0.06,
) -> Tuple[List[Doc], Dict[str, Any]]:
    """Build the sole model-visible evidence window for both RQ2 answer paths.

    The function preserves the recorded ComplianceGPT policy: filter to the
    allowed controls, conditionally prioritize the primary control, apply the
    configured evidence-kind ordering, drop empty records, and then truncate.
    """

    docs = [dict(doc) for doc in (retrieved_docs or [])]
    allowed = [str(control).strip() for control in (allowed_controls or []) if str(control).strip()]
    primary = str(primary_control or "").strip()

    docs_gen_pool = filter_docs_to_controls(docs, allowed)

    try:
        margin = float((retrieval_meta or {}).get("final_margin_ratio", 0.0) or 0.0)
    except Exception:
        margin = 0.0
    try:
        threshold = float(primary_first_min_margin_ratio)
    except Exception:
        threshold = 0.06

    primary_first_applied = False
    if primary and margin >= threshold:
        primary_docs = filter_docs_to_controls(docs_gen_pool, [primary])
        if primary_docs:
            primary_ids = {
                str(doc.get("id", "") or "").strip()
                for doc in primary_docs
                if str(doc.get("id", "") or "").strip()
            }
            other_docs = [
                doc
                for doc in docs_gen_pool
                if str(doc.get("id", "") or "").strip() not in primary_ids
            ]
            docs_gen_pool = primary_docs + other_docs
            primary_first_applied = True

    docs_for_model = apply_doc_filter_mode(docs_gen_pool, str(doc_filter_mode or "all"))
    docs_for_model = [doc for doc in docs_for_model if str(doc.get("text", "") or "").strip()]

    fallback_used = False
    if not docs_for_model and primary:
        fallback_used = True
        fallback_pool = filter_docs_to_controls(docs, [primary])
        docs_for_model = apply_doc_filter_mode(fallback_pool, "smt_only")
        docs_for_model = [doc for doc in docs_for_model if str(doc.get("text", "") or "").strip()]

    limit = max(1, int(gen_docs_k))
    docs_for_model = docs_for_model[:limit]
    manifest = evidence_window_manifest(docs_for_model)

    audit = {
        "primary_first_applied": primary_first_applied,
        "primary_first_min_margin_ratio": threshold,
        "final_margin_ratio": margin,
        "fallback_used": fallback_used,
        "pre_cap_count": len(docs_gen_pool),
        "evidence_window": manifest,
    }
    return docs_for_model, audit


def assert_same_evidence_window(*manifests: Mapping[str, Any]) -> str:
    """Return the shared hash or raise when paired windows differ."""

    hashes = [str((manifest or {}).get("sha256", "") or "").strip() for manifest in manifests]
    if not hashes or any(not value for value in hashes):
        raise ValueError("Every answer path must provide a nonempty evidence-window hash.")
    if len(set(hashes)) != 1:
        raise AssertionError(f"Matched RQ2 evidence-window mismatch: {hashes}")
    return hashes[0]
