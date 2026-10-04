"""Versioned profile resolution with canonical source/value provenance.

Source spans remain verbatim. Configured values are separately recorded inputs,
not quotations from the canonical corpus. A revision-scoped profile is required
to substitute values; an absent or wrong-revision profile leaves obligations
unresolved. This module requires no model or retrieval dependencies.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Dict, List, Mapping, Sequence, Tuple

PROFILE_RESOLUTION_SCHEMA = "compliancegpt-profile-resolution-v1"
PROFILE_RESOLUTION_PATCH_ID = "2026-10-04-profile-resolution-v1"
_KEY_RE = re.compile(r"\{+\s*insert\s*:\s*(?:param\s*,\s*)?([^}]+?)\s*\}+", re.I)
_ASSIGN_RE = re.compile(r"\[\s*assignment\s*:\s*([^\]]+)\]", re.I)
ASSIGNMENT_SENTINEL = "__ASSIGNMENT_REQUIRED__"


def profile_fingerprint(profile: Mapping[str, Any]) -> str:
    payload = json.dumps(dict(profile), sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def visible_keys(text: str) -> List[str]:
    return sorted({m.group(1).strip() for m in _KEY_RE.finditer(text) if m.group(1).strip()})


def lookup_profile_value(profile: Mapping[str, Any], key: str) -> Tuple[Any, List[str]]:
    for container in ("odp_values", "odps"):
        values = profile.get(container)
        if isinstance(values, dict) and key in values:
            return values[key], [container, key]
    return profile.get(key), [key]


def literal_profile_value(value: Any) -> str | None:
    if not isinstance(value, (str, int, float, bool)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    text = str(value)
    if not text.strip() or _KEY_RE.search(text) or _ASSIGN_RE.search(text):
        return None
    return text


def resolve_profile_answer(
    evidence_spans: Sequence[Mapping[str, Any]],
    profile: Dict[str, Any],
    framework_version: str,
) -> Tuple[str, List[str], str, Dict[str, Any]]:
    """Return the resolved answer, remaining obligations, status, and proof record.

    A complete profile resolves only keyed placeholders. Anonymous assignment
    markers remain unresolved. Unsupported or placeholder-bearing values are
    not substituted. Replacement strings are inserted literally in one pass.
    """
    if framework_version not in {"rev4", "rev5"}:
        raise ValueError("Profile resolution requires an explicit rev4/rev5 corpus")
    if not isinstance(profile, dict):
        raise ValueError("Organization profile must be a JSON-compatible object")
    original = "\n\n".join(str(s.get("span_text", "") or "") for s in evidence_spans).strip()
    keys = visible_keys(original)
    profile_revision = str(profile.get("framework_version", "") or "").strip().lower()
    applicable = profile_revision == framework_version
    replacements: Dict[str, str] = {}
    bindings = []
    for key in keys:
        value, path = lookup_profile_value(profile, key)
        literal = literal_profile_value(value) if applicable else None
        if literal is None:
            continue
        replacements[key] = literal
        sources = sorted({str(s.get("source_id", "") or "") for s in evidence_spans
                          if key in visible_keys(str(s.get("span_text", "") or ""))})
        bindings.append({"param_id": key, "value": literal, "profile_path": path,
                         "source_ids": sources})
    answer = _KEY_RE.sub(lambda m: replacements.get(m.group(1).strip(), m.group(0)), original)
    remaining = visible_keys(answer)
    anonymous = bool(_ASSIGN_RE.search(answer))
    required = remaining + ([ASSIGNMENT_SENTINEL] if anonymous else [])
    record = {
        "schema_version": PROFILE_RESOLUTION_SCHEMA,
        "patch_id": PROFILE_RESOLUTION_PATCH_ID,
        "policy": "FILL_FROM_PROFILE",
        "corpus_version": framework_version,
        "profile_revision": profile_revision,
        "profile_applicable": applicable,
        "profile_sha256": profile_fingerprint(profile),
        "bindings": bindings,
        "unresolved_param_ids": remaining,
        "anonymous_assignment_required": anonymous,
    }
    return answer, required, "PARAMS_REQUIRED" if required else "OK", record
