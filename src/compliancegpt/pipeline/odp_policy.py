"""Dependency-light ODP policy functions used by the runtime pipeline.

This module intentionally imports no model or retrieval packages. It keeps
status transitions testable without installing the LLM execution stack.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


_PARAM_CURLY_RE = re.compile(
    r"\{+\s*insert:\s*(?:param,\s*)?([^}]+?)\s*\}+",
    re.IGNORECASE,
)
_PARAM_ASSIGNMENT_RE = re.compile(
    r"\[assignment:\s*([^\]]+?)\s*\]",
    re.IGNORECASE,
)

ASSIGNMENT_REQUIRED_SENTINEL = "__ASSIGNMENT_REQUIRED__"
ODP_POLICY_PATCH_ID = "2026-09-24-preserve-status-v1"


def extract_odp_ids(text: str) -> Tuple[List[str], bool]:
    """Return canonical-looking placeholder IDs and assignment presence."""

    if not isinstance(text, str):
        text = "" if text is None else str(text)

    keys = []
    for match in _PARAM_CURLY_RE.finditer(text):
        key = match.group(1).strip()
        if key:
            keys.append(key)

    has_assignment = bool(_PARAM_ASSIGNMENT_RE.search(text))
    return sorted(set(key.strip() for key in keys if key.strip())), has_assignment


def profile_lookup(profile: Dict[str, Any], key: str) -> Optional[Any]:
    """Look up a value in supported organization-profile shapes."""

    if not isinstance(profile, dict) or not key:
        return None
    for top in ("odp_values", "odps"):
        if isinstance(profile.get(top), dict) and key in profile[top]:
            return profile[top][key]
    return profile.get(key)


def normalize_resolution_policy(policy: Any) -> str:
    """Normalize policy aliases to ASK, PRESERVE, or FILL_FROM_PROFILE."""

    try:
        normalized = "" if policy is None else str(policy).strip().upper()
    except Exception:
        normalized = ""
    if normalized in {"", "NAN", "NA", "N/A", "NONE", "NULL", "AUTO"}:
        normalized = "FILL_FROM_PROFILE"
    if normalized in {"FILL", "PROFILE", "FILL_PROFILE"}:
        normalized = "FILL_FROM_PROFILE"
    return normalized


def apply_odp_policy_to_answer(
    answer_text: str,
    policy: str,
    org_profile: Dict[str, Any],
) -> Tuple[str, List[str], str]:
    """Apply the deterministic ODP policy to canonical answer text."""

    raw_policy = policy
    normalized = normalize_resolution_policy(raw_policy)
    text = str(answer_text or "")
    keys, has_assignment = extract_odp_ids(text)

    if not keys and not has_assignment:
        return text, [], "OK"

    if normalized == "PRESERVE":
        required = list(keys)
        if has_assignment:
            required.append(ASSIGNMENT_REQUIRED_SENTINEL)
        return text, required, "PARAMS_REQUIRED"

    if normalized in {"ASK", "FILL_FROM_PROFILE"}:
        missing: List[str] = []
        for key in keys:
            value = profile_lookup(org_profile, key)

            if normalized == "FILL_FROM_PROFILE" and value is not None and str(value).strip():
                replacement = str(value)
                pattern = r"\{+\s*insert:\s*(?:param,\s*)?" + re.escape(key) + r"\s*\}+"
                try:
                    text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
                except re.error:
                    missing.append(key)
            else:
                missing.append(key)

        required = sorted(set(missing))
        if has_assignment:
            required.append(ASSIGNMENT_REQUIRED_SENTINEL)
        return (text, required, "PARAMS_REQUIRED") if required else (text, [], "OK")

    raise ValueError(f"Unknown resolution_policy={raw_policy!r}")
