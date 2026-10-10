"""Select revision-specific request metadata and record its exact identity."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPAIRED_REGISTRY_ID = "odp_registry_source_repair_v2"
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def normalize_revision(revision: str) -> str:
    value = str(revision).strip().lower()
    if value in {"rev4", "r4", "4"}:
        return "rev4"
    if value in {"rev5", "r5", "5"}:
        return "rev5"
    raise ValueError("Registry revision must be rev4 or rev5")


def resolve_registry_path(
    revision: str,
    *,
    registry_version: str = "legacy",
    path_override: str | None = None,
    repository_root: Path = REPOSITORY_ROOT,
) -> Path:
    revision = normalize_revision(revision)
    version = str(registry_version).strip()
    if version not in {"legacy", "source_repair_v2", REPAIRED_REGISTRY_ID}:
        raise ValueError(f"Unknown registry version: {version!r}")
    if version != "legacy" and path_override:
        raise ValueError("Choose the repaired registry version or a custom path, rather than both")
    if path_override:
        return Path(path_override)
    directory = "data/ODP" if version == "legacy" else "data/ODP/registry_v2"
    return Path(repository_root) / directory / revision / f"odp_registry_{revision}.json"


def load_registry_selection(
    revision: str,
    *,
    registry_version: str = "legacy",
    path_override: str | None = None,
    repository_root: Path = REPOSITORY_ROOT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Keep legacy metadata available; verify an explicitly selected repair.

    Types and cardinalities describe requests. This loader does not validate
    organizational values, profile approval, or parameter necessity.
    """
    revision = normalize_revision(revision)
    version = str(registry_version).strip()
    repaired = version != "legacy"
    root = Path(repository_root)
    path = resolve_registry_path(revision, registry_version=version, path_override=path_override,
                                 repository_root=root)
    if repaired:
        directory = root / "data/ODP/registry_v2"
        relative = f"{revision}/odp_registry_{revision}.json"
        manifest = json.loads((directory / "REGISTRY_MANIFEST.json").read_text(encoding="utf-8"))
        if manifest.get("registry_id") != REPAIRED_REGISTRY_ID:
            raise ValueError("Repaired registry manifest has the wrong identity")
        payload = path.read_bytes()
        actual_hash = hashlib.sha256(payload).hexdigest()
        if actual_hash != manifest.get("files_sha256", {}).get(relative):
            raise ValueError("Repaired registry bytes do not match their manifest")
        data = json.loads(payload)
        if not isinstance(data, dict) or any(not isinstance(meta, dict) or meta.get("version") != revision
                                             for meta in data.values()):
            raise ValueError("Repaired registry entries do not match the requested revision")
        registry_id = REPAIRED_REGISTRY_ID
        loaded = True
    else:
        registry_id = "custom" if path_override else f"odp_registry_legacy_{revision}"
        actual_hash, data, loaded = None, {}, False
        # Preserve the historical custom-path fallback for dependency-light fixtures.
        try:
            payload = path.read_bytes()
            actual_hash = hashlib.sha256(payload).hexdigest()
            parsed = json.loads(payload)
            if isinstance(parsed, dict):
                data, loaded = parsed, True
        except (OSError, ValueError, UnicodeError):
            pass
    metadata = {"registry_id": registry_id, "revision": revision, "sha256": actual_hash,
                "selection": "version" if repaired else "custom_path" if path_override else "legacy",
                "loaded": loaded}
    return data, metadata
