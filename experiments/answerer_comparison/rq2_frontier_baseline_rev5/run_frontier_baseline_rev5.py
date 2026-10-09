#!/usr/bin/env python3
"""Run Batch 5D: the pre-committed Gemini baseline on 100 Revision 5 rows.

The study preserves the frozen RQ2 v3 questions, ordered evidence windows,
free-form prompt/parser, ASK policy, and offline verifier. It changes the
free-form answer model and serving runtime to the Gemini Developer API.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List, Mapping, Sequence, Tuple


REPO_HINT = Path(__file__).resolve().parents[3]
if str(REPO_HINT) not in sys.path:
    sys.path.insert(0, str(REPO_HINT))
if str(REPO_HINT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_HINT / "src"))

from answerer_comparison import strict_pass as strict_scoring  # noqa: E402

from experiments.answerer_comparison.rq2_bf16_baseline import (  # noqa: E402
    run_bf16_baseline as registered,
)


RESULT_ID = "rq2_frontier_baseline_rev5_v1"
SCHEMA_VERSION = "compliancegpt-rq2-frontier-baseline-rev5-v1"
SYSTEM_NAME = "generative_frontier_api"
FRAMEWORK_VERSION = "rev5"
MODEL_ID = "gemini-3.5-flash"
MODEL_REQUESTED_REVISION = "stable-api-model:gemini-3.5-flash"
MODEL_RESOLVED_REVISION_MARKER = "recorded-per-response"
TOKENIZER_REVISION_MARKER = "server-managed"
EXPECTED_ROWS = 100
EXPECTED_PROMPT_SHA256 = registered.EXPECTED_PROMPT_SHA256
FROZEN_SOURCE_COMMIT = registered.FROZEN_SOURCE_COMMIT
FROZEN_ARCHIVE_SHA256 = registered.FROZEN_ARCHIVE_SHA256
DEFAULT_ARCHIVE = registered.DEFAULT_ARCHIVE
PRECOMMITMENT_PATH = (
    "experiments/answerer_comparison/rq2_frontier_baseline_rev5/precommitment.json"
)
PRECOMMITMENT_SHA256 = "b0cc78debb25c1025f05622348925383b7a19503751680e1a6a0b3ddefa34504"
INPUTS = {
    "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl",
    "gold": "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv",
    "odp_registry": "data/ODP/rev5/odp_registry_rev5.json",
}
INPUT_HASHES = {
    "ccs": "71057ba79c54b8c1f0d171198a6ccb60b4c8818acbd2062e7f7c74ee11242e08",
    "gold": "f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5",
    "odp_registry": "3cd31393ed97df6292a45b749bca5359c802397d68ee6dcb41081b075fd32545",
}
ARCHIVE_MEMBERS = {
    "contexts/rev5_prepared_contexts.jsonl": (
        "b47e58c17ce6d0aca1d8519941f52c3c21e393d9187fcf113de7bfec68cfc473"
    ),
    "contracts/rev5_generative_baseline.csv": (
        "85a3e52b75b283a3fda6c50ae59d8dde4e59748ada7d58c5b88ae8c5c8f2cb63"
    ),
    "contracts/rev5_compliancegpt.csv": (
        "9440fd02c25e30b4b3fe39890fadb3ec3e120dfd8af9e82ea23fab6f87167cc9"
    ),
    "summaries/rev5_paired_summary.json": (
        "46abebc838233b104ed75609a597b204101e4fffc4cc0b6ef2a772b5047fabeb"
    ),
    "run_config.json": "9f87e66c19c8a066aa6d87350eca2b959a3c2315bc7b602eac75f3f13b23acf5",
}
GENERATION_SETTINGS = {
    "thinking_level": "LOW",
    "temperature": 1.0,
    "max_output_tokens": 2048,
    "max_parse_retries": 2,
    "tools_enabled": False,
    "structured_output_enforced": False,
    "sdk_max_retries": 5,
    "sdk_timeout_seconds": 180.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_HINT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frozen-archive", type=Path, default=None)
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Verify and extract registered inputs without an API key or API call.",
    )
    return parser.parse_args()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return registered.sha256_file(path)


def canonical_sha256(value: Any) -> str:
    return registered.canonical_sha256(value)


def write_json(path: Path, value: Any) -> None:
    registered.write_json(path, value)


def write_bytes(path: Path, data: bytes) -> None:
    registered.write_bytes(path, data)


def git_head(repo_root: Path) -> str:
    return registered.git_head(repo_root)


def frontier_csv(output_dir: Path) -> Path:
    return output_dir / "contracts" / "rev5_generative_frontier_api.csv"


def api_log_path(output_dir: Path) -> Path:
    return output_dir / "api" / "responses.jsonl"


def has_api_activity(output_dir: Path) -> bool:
    if api_log_path(output_dir).is_file() and api_log_path(output_dir).stat().st_size:
        return True
    path = frontier_csv(output_dir)
    if not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            return next(reader, None) is not None
    except Exception:
        return True


def ensure_frozen_source_commit(repo_root: Path) -> bool:
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{FROZEN_SOURCE_COMMIT}^{{commit}}"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if probe.returncode == 0:
        return False
    subprocess.run(
        ["git", "fetch", "--filter=blob:none", "origin", FROZEN_SOURCE_COMMIT],
        cwd=repo_root,
        check=True,
    )
    subprocess.run(
        ["git", "cat-file", "-e", f"{FROZEN_SOURCE_COMMIT}^{{commit}}"],
        cwd=repo_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return True


def runner_code_manifest(repo_root: Path) -> Dict[str, str]:
    paths = [
        "experiments/answerer_comparison/rq2_frontier_baseline_rev5/run_frontier_baseline_rev5.py",
        PRECOMMITMENT_PATH,
        "experiments/answerer_comparison/rq2_frontier_baseline/requirements-api.txt",
        "experiments/answerer_comparison/rq2_bf16_baseline/run_bf16_baseline.py",
        "src/answerer_comparison/frontier_api_answerer.py",
    ]
    manifest: Dict[str, str] = {}
    for relative in paths:
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Batch 5D code input is missing: {path}")
        manifest[relative] = sha256_file(path)
    return manifest


def load_precommitment(repo_root: Path) -> Dict[str, Any]:
    path = repo_root / PRECOMMITMENT_PATH
    actual_hash = sha256_file(path)
    if actual_hash != PRECOMMITMENT_SHA256:
        raise RuntimeError(
            f"Pre-commitment changed: expected {PRECOMMITMENT_SHA256}, got {actual_hash}"
        )
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "result_id": RESULT_ID,
        "framework_version": FRAMEWORK_VERSION,
        "n_questions": EXPECTED_ROWS,
        "prompt_sha256": EXPECTED_PROMPT_SHA256,
        "no_api_outputs_observed_at_registration": True,
    }
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise RuntimeError(
                f"Pre-commitment field {key!r} changed: expected {wanted!r}, "
                f"got {value.get(key)!r}"
            )
    api = dict(value.get("api", {}) or {})
    if api.get("model_id") != MODEL_ID:
        raise RuntimeError("Pre-committed Gemini model does not match the runner.")
    if dict(api.get("generation_settings", {}) or {}) != GENERATION_SETTINGS:
        raise RuntimeError("Pre-committed generation settings do not match the runner.")
    return value


def evidence_window_manifest(docs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    records: List[Dict[str, str]] = []
    for position, doc in enumerate(docs):
        text = str((doc or {}).get("text", "") or "")
        records.append(
            {
                "position": str(position),
                "source_id": str((doc or {}).get("id", "") or "").strip(),
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
    return {
        "schema_version": "rq2-evidence-window-v1",
        "record_count": len(records),
        "source_ids": [record["source_id"] for record in records],
        "records": records,
        "sha256": canonical_sha256(records),
    }


def gold_key_paths(value: Any, path: str = "") -> List[str]:
    found: List[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.strip().lower().startswith("gold"):
                found.append(child_path)
            found.extend(gold_key_paths(child, child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found.extend(gold_key_paths(child, f"{path}[{index}]"))
    return found


def validate_context(context: Mapping[str, Any]) -> None:
    if str(context.get("schema_version", "")) != registered.EXPECTED_CONTEXT_SCHEMA:
        raise ValueError("Unexpected frozen prepared-context schema.")
    if str(context.get("framework_version", "")) != FRAMEWORK_VERSION:
        raise ValueError("Batch 5D accepts Revision 5 contexts only.")
    if not str(context.get("query_id", "") or "").strip():
        raise ValueError("Prepared context has no query id.")
    if not str(context.get("question", "") or "").strip():
        raise ValueError("Prepared context has no question.")
    forbidden = gold_key_paths(context)
    if forbidden:
        raise ValueError(f"Gold fields are forbidden in model-visible contexts: {forbidden}")
    clean = dict(context)
    stored_hash = str(clean.pop("context_sha256", "") or "")
    if stored_hash != canonical_sha256(clean):
        raise AssertionError("Prepared-context hash does not match its contents.")
    actual_window = evidence_window_manifest(list(context.get("evidence_window", []) or []))
    if actual_window != dict(context.get("evidence_window_manifest", {}) or {}):
        raise AssertionError("Prepared evidence-window manifest does not match its contents.")


def parse_contexts(data: bytes) -> List[Dict[str, Any]]:
    contexts = [
        json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()
    ]
    if len(contexts) != EXPECTED_ROWS:
        raise AssertionError(
            f"Expected {EXPECTED_ROWS} Revision 5 contexts, found {len(contexts)}"
        )
    for context in contexts:
        validate_context(context)
    query_ids = [str(context["query_id"]) for context in contexts]
    if len(query_ids) != len(set(query_ids)):
        raise AssertionError("Frozen Revision 5 contexts contain duplicate query ids.")
    return contexts


def verify_inputs(repo_root: Path, archive_path: Path) -> Dict[str, Any]:
    if not archive_path.is_file():
        raise FileNotFoundError(f"Frozen RQ2 v3 archive is missing: {archive_path}")
    archive_hash = sha256_file(archive_path)
    if archive_hash != FROZEN_ARCHIVE_SHA256:
        raise RuntimeError(
            f"Frozen archive mismatch: expected {FROZEN_ARCHIVE_SHA256}, got {archive_hash}"
        )
    input_hashes: Dict[str, str] = {}
    for name, relative in INPUTS.items():
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Registered {name} input is missing: {path}")
        value = sha256_file(path)
        if value != INPUT_HASHES[name]:
            raise RuntimeError(
                f"Registered {name} input changed: expected {INPUT_HASHES[name]}, got {value}"
            )
        input_hashes[name] = value
    return {
        "archive_sha256": archive_hash,
        "input_hashes": input_hashes,
        "frozen_source_hashes": registered.verify_frozen_source(repo_root),
    }


def extract_registered_archive(
    *, archive_path: Path, output_dir: Path
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    destinations = {
        "contexts/rev5_prepared_contexts.jsonl": (
            output_dir / "contexts" / "rev5_prepared_contexts.jsonl"
        ),
        "contracts/rev5_generative_baseline.csv": (
            output_dir / "references" / "rev5_generative_baseline_4bit.csv"
        ),
        "contracts/rev5_compliancegpt.csv": (
            output_dir / "references" / "rev5_compliancegpt_4bit.csv"
        ),
        "summaries/rev5_paired_summary.json": (
            output_dir / "references" / "rev5_frozen_paired_summary.json"
        ),
        "run_config.json": output_dir / "references" / "rq2_v3_run_config.json",
    }
    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "archive": str(archive_path),
        "archive_sha256": sha256_file(archive_path),
        "members": {},
    }
    with zipfile.ZipFile(archive_path) as archive:
        for member, expected_hash in ARCHIVE_MEMBERS.items():
            data = archive.read(member)
            actual_hash = sha256_bytes(data)
            if actual_hash != expected_hash:
                raise RuntimeError(
                    f"Frozen archive member changed for {member}: "
                    f"expected {expected_hash}, got {actual_hash}"
                )
            write_bytes(destinations[member], data)
            manifest["members"][member] = {
                "sha256": actual_hash,
                "bytes": len(data),
                "extracted_to": str(destinations[member]),
            }
    context_path = output_dir / "contexts" / "rev5_prepared_contexts.jsonl"
    contexts = parse_contexts(context_path.read_bytes())
    manifest["context_rows"] = len(contexts)
    manifest["distinct_window_hashes"] = len(
        {
            str((context.get("evidence_window_manifest") or {}).get("sha256", ""))
            for context in contexts
        }
    )
    write_json(output_dir / "manifests" / "source_archive.json", manifest)
    return contexts, manifest


def read_csv_rows(path: Path) -> Dict[str, Dict[str, str]]:
    return registered.read_csv_rows(path)


def load_gold_rows(path: Path) -> Dict[str, Dict[str, str]]:
    rows: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            query_id = str(
                row.get("query_id") or row.get("ID") or row.get("id") or ""
            ).strip()
            if not query_id or query_id in rows:
                raise ValueError(f"Missing or duplicate gold query id in {path}: {query_id!r}")
            rows[query_id] = dict(row)
    if len(rows) != EXPECTED_ROWS:
        raise AssertionError(f"Expected {EXPECTED_ROWS} gold rows, found {len(rows)}")
    return rows


def load_or_create_run_config(
    *,
    repo_root: Path,
    output_dir: Path,
    source_manifest: Mapping[str, Any],
    verified: Mapping[str, Any],
) -> Dict[str, Any]:
    precommitment = load_precommitment(repo_root)
    code_files = runner_code_manifest(repo_root)
    expected: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "framework_version": FRAMEWORK_VERSION,
        "n_questions": EXPECTED_ROWS,
        "provider": "google-gemini-developer-api",
        "api_method": "generateContent",
        "api_billing_tier": "Paid Tier 1",
        "model_id": MODEL_ID,
        "model_reference_type": (
            "stable Gemini API model; server model version recorded per response"
        ),
        "frozen_source_commit": FROZEN_SOURCE_COMMIT,
        "frozen_source_hashes": dict(verified["frozen_source_hashes"]),
        "source_archive_sha256": str(source_manifest["archive_sha256"]),
        "source_member_hashes": {
            key: str(value["sha256"])
            for key, value in dict(source_manifest["members"]).items()
        },
        "input_hashes": dict(verified["input_hashes"]),
        "precommitment_path": PRECOMMITMENT_PATH,
        "precommitment_sha256": PRECOMMITMENT_SHA256,
        "precommitted_at_utc": str(precommitment["registered_at_utc"]),
        "prompt_sha256": EXPECTED_PROMPT_SHA256,
        "generation_settings": dict(GENERATION_SETTINGS),
        "experiment_code_files": code_files,
        "experiment_code_sha256": canonical_sha256(code_files),
        "changed_factor": (
            "free-form answer model/runtime: Qwen2.5-7B -> Gemini frontier API"
        ),
        "retrieval_policy": "frozen RQ2 v3 Revision 5 contexts; no live retrieval",
        "gold_policy": (
            "gold excluded from API-visible contexts and used only by offline verifier"
        ),
        "api_data_policy": (
            "no tools; API key read from environment and never recorded; this registered "
            "run uses Gemini API Paid Tier 1, for which Google states submitted content "
            "is not used to improve its products"
        ),
        "api_data_policy_reference": "https://ai.google.dev/gemini-api/docs/pricing",
        "frozen_factors": [
            "100 Revision 5 questions and ordered evidence windows",
            "free-form generative baseline system and user prompts",
            "JSON extraction, fail-closed normalization, and two parse retries",
            "ASK ODP policy and offline verifier",
        ],
    }
    path = output_dir / "run_config.json"
    current_commit = git_head(repo_root)
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
        for key, value in expected.items():
            if stored.get(key) != value:
                if has_api_activity(output_dir):
                    raise RuntimeError(
                        f"Batch 5D configuration changed for {key!r} after API activity. "
                        "Use a new output directory."
                    )
                stored[key] = value
        observed = [
            str(value)
            for value in list(stored.get("repo_commits_observed", []) or [])
            if str(value).strip()
        ]
        if current_commit and current_commit not in observed:
            observed.append(current_commit)
        stored["repo_commit"] = current_commit
        stored["repo_commits_observed"] = observed
        write_json(path, stored)
        return stored
    if has_api_activity(output_dir):
        raise RuntimeError(
            "API activity exists without a Batch 5D run_config.json. Use a new output directory."
        )
    config = {
        **expected,
        "repo_commit": current_commit,
        "repo_commits_observed": [current_commit] if current_commit else [],
    }
    write_json(path, config)
    return config


def write_preflight(output_dir: Path, contexts: Sequence[Mapping[str, Any]]) -> None:
    counts = [len(list(context.get("evidence_window", []) or [])) for context in contexts]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "scope": "gold-free frozen-context integrity audit; no API call",
        "framework_version": FRAMEWORK_VERSION,
        "context_rows": len(contexts),
        "context_jsonl_sha256": sha256_file(
            output_dir / "contexts" / "rev5_prepared_contexts.jsonl"
        ),
        "distinct_context_hashes": len(
            {str(row["context_sha256"]) for row in contexts}
        ),
        "distinct_window_hashes": len(
            {
                str((row.get("evidence_window_manifest") or {}).get("sha256", ""))
                for row in contexts
            }
        ),
        "window_record_count": {
            "min": min(counts),
            "mean": statistics.fmean(counts),
            "max": max(counts),
        },
        "api_calls_performed": 0,
    }
    write_json(output_dir / "preflight" / "summary.json", summary)
    text = "\n".join(
        [
            "# Batch 5D Prepared-Context Audit",
            "",
            "This is a gold-free integrity check, not a completed frontier-model result.",
            "",
            f"- Result identity: `{RESULT_ID}`",
            f"- Frozen Revision 5 contexts: {len(contexts)}",
            f"- Distinct context hashes: {summary['distinct_context_hashes']}",
            f"- Distinct evidence-window hashes: {summary['distinct_window_hashes']}",
            f"- Context SHA-256: `{summary['context_jsonl_sha256']}`",
            f"- Pre-commitment SHA-256: `{PRECOMMITMENT_SHA256}`",
            "- API calls performed: no",
            "",
        ]
    )
    (output_dir / "PREPARED_CONTEXTS.md").write_text(text, encoding="utf-8")


def prepare_experiment(
    repo_root: Path, output_dir: Path, archive_path: Path
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, str]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if ensure_frozen_source_commit(repo_root):
        print(f"Fetched registered frozen source commit: {FROZEN_SOURCE_COMMIT}")
    verified = verify_inputs(repo_root, archive_path)
    contexts, source_manifest = extract_registered_archive(
        archive_path=archive_path,
        output_dir=output_dir,
    )
    load_or_create_run_config(
        repo_root=repo_root,
        output_dir=output_dir,
        source_manifest=source_manifest,
        verified=verified,
    )
    gold_rows = load_gold_rows(repo_root / INPUTS["gold"])
    expected_ids = {str(context["query_id"]) for context in contexts}
    if expected_ids != set(gold_rows):
        raise AssertionError("Frozen contexts and registered gold rows have different query ids.")
    for path in (
        output_dir / "references" / "rev5_generative_baseline_4bit.csv",
        output_dir / "references" / "rev5_compliancegpt_4bit.csv",
    ):
        rows = read_csv_rows(path)
        if len(rows) != EXPECTED_ROWS or set(rows) != expected_ids:
            raise AssertionError(f"Registered reference output is incomplete: {path}")
    write_preflight(output_dir, contexts)
    return contexts, gold_rows


def validate_or_write_api_runtime(output_dir: Path) -> Dict[str, Any]:
    runtime = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "provider": "google-gemini-developer-api",
        "api_method": "generateContent",
        "api_billing_tier": "Paid Tier 1",
        "model_id": MODEL_ID,
        "python": platform.python_version(),
        "python_major_minor": ".".join(platform.python_version_tuple()[:2]),
        "google_genai_python": version("google-genai"),
        "generation_settings": dict(GENERATION_SETTINGS),
        "api_key_source": "GEMINI_API_KEY environment variable; value never recorded",
    }
    path = output_dir / "manifests" / "api_runtime.json"
    if path.exists() and has_api_activity(output_dir):
        stored = json.loads(path.read_text(encoding="utf-8"))
        for key in (
            "provider",
            "api_method",
            "api_billing_tier",
            "model_id",
            "python_major_minor",
            "google_genai_python",
            "generation_settings",
        ):
            if stored.get(key) != runtime.get(key):
                raise RuntimeError(
                    f"API runtime changed for {key!r} after API activity. "
                    "Reconnect with the same runtime or use a new output directory."
                )
        return stored
    write_json(path, runtime)
    return runtime


def validate_generation_contract(system_prompt: str, answerer: Any) -> Dict[str, Any]:
    prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
    if prompt_hash != EXPECTED_PROMPT_SHA256:
        raise RuntimeError(
            f"Frozen generative prompt changed: expected {EXPECTED_PROMPT_SHA256}, "
            f"got {prompt_hash}"
        )
    observed = {
        "thinking_level": str(answerer.thinking_level),
        "temperature": float(answerer.temperature),
        "max_output_tokens": int(answerer.max_output_tokens),
        "max_parse_retries": int(answerer.max_parse_retries),
        "tools_enabled": False,
        "structured_output_enforced": False,
        "sdk_max_retries": GENERATION_SETTINGS["sdk_max_retries"],
        "sdk_timeout_seconds": GENERATION_SETTINGS["sdk_timeout_seconds"],
    }
    if observed != GENERATION_SETTINGS:
        raise RuntimeError(
            f"Registered API generation settings changed: expected {GENERATION_SETTINGS}, "
            f"got {observed}"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "prompt_sha256": prompt_hash,
        "prompt_and_parser_source_commit": FROZEN_SOURCE_COMMIT,
        "generation_settings": observed,
        "same_prompt_boundary": (
            "System prompt, context serialization, user prompt, JSON parser, fail-closed "
            "normalization, and retry prompt are inherited from the frozen Qwen baseline. "
            "Gemini thought signatures are preserved as required for retry turns."
        ),
    }


def validate_matched_rows(
    frontier: Mapping[str, Mapping[str, str]],
    baseline_4bit: Mapping[str, Mapping[str, str]],
    compliance_4bit: Mapping[str, Mapping[str, str]],
) -> Dict[str, Any]:
    mappings = {
        "frontier": frontier,
        "generative_baseline_4bit": baseline_4bit,
        "compliancegpt_4bit": compliance_4bit,
    }
    if any(len(rows) != EXPECTED_ROWS for rows in mappings.values()):
        raise AssertionError("Batch 5D or a registered reference is incomplete.")
    if any(set(rows) != set(frontier) for rows in mappings.values()):
        raise AssertionError("Batch 5D and reference query-id sets do not match.")
    mismatches: List[Tuple[str, str, str]] = []
    for query_id in sorted(frontier):
        current = frontier[query_id]
        for label, reference in mappings.items():
            if label == "frontier":
                continue
            for field in ("context_sha256", "evidence_window_sha256"):
                if str(current.get(field, "")) != str(reference[query_id].get(field, "")):
                    mismatches.append((query_id, label, field))
        expected_model_fields = {
            "model_id": MODEL_ID,
            "model_requested_revision": MODEL_REQUESTED_REVISION,
            "model_resolved_revision": MODEL_RESOLVED_REVISION_MARKER,
            "tokenizer_resolved_revision": TOKENIZER_REVISION_MARKER,
        }
        for field, expected in expected_model_fields.items():
            if str(current.get(field, "")) != expected:
                mismatches.append((query_id, "frontier", field))
    if mismatches:
        raise AssertionError(f"Matched-input validation failed: {mismatches[:10]}")
    return {
        "paired_rows": EXPECTED_ROWS,
        "context_mismatches": 0,
        "evidence_window_mismatches": 0,
        "frontier_model_id": MODEL_ID,
        "model_snapshot_boundary": (
            "The API request uses a named stable Gemini model. Every response id and "
            "server-reported model version is retained; the runner rejects a version "
            "change within one run."
        ),
    }


def audit_api_provenance(
    output_dir: Path, read_api_call_log: Any, summarize_usage: Any
) -> Dict[str, Any]:
    call_log = read_api_call_log(api_log_path(output_dir))
    by_id = {str(row["response_id"]): row for row in call_log}
    rows = read_csv_rows(frontier_csv(output_dir))
    referenced_ids = set()
    response_models = set()
    calls_by_query: Dict[str, int] = {}
    for query_id, row in rows.items():
        contract = json.loads(str(row.get("contract_json", "") or "{}"))
        raw = dict(((contract.get("debug") or {}).get("generative_raw") or {}))
        provenance = dict(raw.get("api_provenance", {}) or {})
        if str(provenance.get("query_id", "")) != query_id:
            raise AssertionError(f"API provenance query id mismatch for row {query_id}.")
        calls = list(provenance.get("api_calls", []) or [])
        if not 1 <= len(calls) <= 1 + int(GENERATION_SETTINGS["max_parse_retries"]):
            raise AssertionError(f"Unexpected API call count for row {query_id}: {len(calls)}")
        calls_by_query[query_id] = len(calls)
        for call in calls:
            response_id = str(call.get("response_id", "") or "")
            if response_id not in by_id:
                raise AssertionError(f"Contract references an unlogged API response: {response_id}")
            if response_id in referenced_ids:
                raise AssertionError(
                    f"API response is referenced by multiple result rows: {response_id}"
                )
            if dict(call) != by_id[response_id]:
                raise AssertionError(
                    f"API response metadata differs from the cumulative log: {response_id}"
                )
            referenced_ids.add(response_id)
            response_models.add(str(call.get("response_model", "") or ""))
        final_output = str(calls[-1].get("output_text", "") or "")
        raw_output = str(raw.get("raw_output", "") or "")
        if hashlib.sha256(final_output.encode("utf-8")).hexdigest() != hashlib.sha256(
            raw_output.encode("utf-8")
        ).hexdigest():
            raise AssertionError(f"Final API output does not match contract raw output: {query_id}")
    response_models.discard("")
    if len(response_models) != 1:
        raise AssertionError(
            f"Expected exactly one server-reported model: {sorted(response_models)}"
        )
    associated = [row for row in call_log if str(row["response_id"]) in referenced_ids]
    orphaned = [
        str(row["response_id"])
        for row in call_log
        if str(row["response_id"]) not in referenced_ids
    ]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "response_model": next(iter(response_models)),
        "call_log": str(api_log_path(output_dir)),
        "call_log_sha256": sha256_file(api_log_path(output_dir)),
        "completed_result_rows": len(rows),
        "all_logged_usage": summarize_usage(call_log),
        "result_associated_usage": summarize_usage(associated),
        "parse_retry_rows": sum(count > 1 for count in calls_by_query.values()),
        "calls_by_query": calls_by_query,
        "orphaned_call_count": len(orphaned),
        "orphaned_response_ids": orphaned,
        "interpretation": (
            "Orphaned calls, if any, are API responses produced before an interrupted row "
            "checkpoint; they are retained for quota and provenance auditing but excluded "
            "from results."
        ),
    }
    write_json(output_dir / "manifests" / "api_responses.json", manifest)
    runtime_path = output_dir / "manifests" / "api_runtime.json"
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    stored_model = str(runtime.get("server_reported_model", "") or "")
    if stored_model and stored_model != manifest["response_model"]:
        raise RuntimeError(
            "Server-reported model differs from the completed API runtime manifest."
        )
    runtime["server_reported_model"] = manifest["response_model"]
    runtime.setdefault("completed_at_utc", datetime.now(timezone.utc).isoformat())
    runtime["api_call_log_sha256"] = manifest["call_log_sha256"]
    write_json(runtime_path, runtime)
    return manifest


def csv_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def listish(value: Any) -> List[str]:
    return registered.listish(value)


def percentile(values: Sequence[float], proportion: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return float("nan")
    index = (len(ordered) - 1) * float(proportion)
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def distribution(values: Sequence[float]) -> Dict[str, float]:
    numbers = [float(value) for value in values]
    if not numbers:
        return {key: float("nan") for key in ("mean", "median", "p95", "min", "max")}
    return {
        "mean": statistics.fmean(numbers),
        "median": statistics.median(numbers),
        "p95": percentile(numbers, 0.95),
        "min": min(numbers),
        "max": max(numbers),
    }


def wilson_interval(count: int, n: int, z: float = 1.959963984540054) -> Dict[str, Any]:
    if n <= 0:
        return {"level": 0.95, "lower": None, "upper": None, "method": "Wilson score"}
    rate = count / n
    denominator = 1.0 + z * z / n
    center = (rate + z * z / (2.0 * n)) / denominator
    half_width = (
        z
        * math.sqrt(rate * (1.0 - rate) / n + z * z / (4.0 * n * n))
        / denominator
    )
    return {
        "level": 0.95,
        "lower": max(0.0, center - half_width),
        "upper": min(1.0, center + half_width),
        "method": "Wilson score",
    }


def rate_record(count: int, n: int) -> Dict[str, Any]:
    return {
        "count": int(count),
        "rate": count / n if n else None,
        "n": int(n),
        "wilson_95_ci": wilson_interval(int(count), int(n)),
    }


def aggregate_rows(
    *,
    rows: Mapping[str, Mapping[str, str]],
    gold_rows: Mapping[str, Mapping[str, str]],
    normalize_odp_id: Any,
    strict_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> Dict[str, Any]:
    if strict_results is None:
        strict_results = strict_scoring.score_rows(
            revision=FRAMEWORK_VERSION, rows=rows, gold_rows=gold_rows,
        )
    query_ids = sorted(
        rows,
        key=lambda value: (0, int(value)) if value.isdigit() else (1, value),
    )
    if len(query_ids) != EXPECTED_ROWS or set(query_ids) != set(gold_rows):
        raise AssertionError("Completed output and gold query-id sets do not match.")
    per_row: List[Dict[str, Any]] = []
    for query_id in query_ids:
        row = rows[query_id]
        gold = gold_rows[query_id]
        contract = json.loads(str(row.get("contract_json", "") or "{}"))
        metrics = json.loads(str(row.get("verifier_metrics_json", "") or "{}"))
        gold_ids = {value.lower() for value in listish(gold.get("gold_control_path", ""))}
        selected_ids = {
            value.lower() for value in listish(row.get("selected_source_ids", ""))
        }
        gold_odps = {
            normalized
            for value in listish(gold.get("odp_required", ""))
            if (normalized := normalize_odp_id(value))
        }
        generated_odps = {
            normalized
            for value in listish(row.get("odp_required_list", ""))
            if (normalized := normalize_odp_id(value))
        }
        status = str(row.get("status", "") or "")
        per_row.append(
            {
                "query_id": query_id,
                "strict_pass": bool(strict_results[query_id]["strict_pass"]),
                "runtime_pass": csv_bool(row.get("contract_validity_pass")),
                "full_gold_clause_coverage": csv_bool(row.get("doc_full_recall")),
                "right_control": csv_bool(row.get("control_hit_any")),
                "gold_clause_recall": float(metrics.get("doc_recall", 0.0) or 0.0),
                "gold_clause_precision": (
                    len(gold_ids & selected_ids) / len(selected_ids)
                    if selected_ids
                    else 0.0
                ),
                "selected_clause_count": len(selected_ids),
                "additional_clause_count": len(selected_ids - gold_ids),
                "answer_word_count": len(str(contract.get("answer_text", "") or "").split()),
                "status": status,
                "gold_has_odp": bool(gold_odps),
                "predicted_params_required": status == "PARAMS_REQUIRED",
                "exact_odp_set": gold_odps == generated_odps,
            }
        )

    def count_rate(field: str, subset: Sequence[Mapping[str, Any]] = per_row) -> Dict[str, Any]:
        return rate_record(sum(bool(row[field]) for row in subset), len(subset))

    odp_rows = [row for row in per_row if row["gold_has_odp"]]
    non_odp_rows = [row for row in per_row if not row["gold_has_odp"]]
    predicted = [row for row in per_row if row["predicted_params_required"]]
    covered = [row for row in per_row if row["full_gold_clause_coverage"]]
    lost = [row for row in covered if not row["strict_pass"]]
    realization_loss = rate_record(len(lost), len(covered))
    realization_loss.update(
        {
            "coverage_complete": len(covered),
            "strict_pass_within_coverage": len(covered) - len(lost),
            "lost_query_ids": [str(row["query_id"]) for row in lost],
            "definition": (
                "coverage-complete rows that fail at least one remaining strict predicate "
                "divided by coverage-complete rows"
            ),
        }
    )
    aggregate = {
        "n_questions": len(per_row),
        "strict_pass": count_rate("strict_pass"),
        "runtime_contract_pass": count_rate("runtime_pass"),
        "full_gold_clause_coverage": count_rate("full_gold_clause_coverage"),
        "right_governing_control": count_rate("right_control"),
        "realization_loss": realization_loss,
        "mean_gold_clause_recall": statistics.fmean(
            float(row["gold_clause_recall"]) for row in per_row
        ),
        "mean_gold_clause_precision": statistics.fmean(
            float(row["gold_clause_precision"]) for row in per_row
        ),
        "selected_clause_count": distribution(
            [float(row["selected_clause_count"]) for row in per_row]
        ),
        "additional_clause_count": distribution(
            [float(row["additional_clause_count"]) for row in per_row]
        ),
        "answer_word_count": distribution(
            [float(row["answer_word_count"]) for row in per_row]
        ),
        "status_counts": dict(
            sorted(Counter(str(row["status"]) for row in per_row).items())
        ),
        "odp_against_author_labels": {
            "gold_odp_rows": len(odp_rows),
            "params_required_sensitivity": count_rate(
                "predicted_params_required", odp_rows
            ),
            "gold_non_odp_rows": len(non_odp_rows),
            "specificity": rate_record(
                sum(not bool(row["predicted_params_required"]) for row in non_odp_rows),
                len(non_odp_rows),
            ),
            "status_precision": rate_record(
                sum(bool(row["gold_has_odp"]) for row in predicted),
                len(predicted),
            ),
            "exact_odp_set_positive_rows": count_rate("exact_odp_set", odp_rows),
            "exact_odp_set_all_rows": count_rate("exact_odp_set"),
            "boundary": (
                "These operating characteristics use the current author labels and are "
                "not independently adjudicated."
            ),
        },
        "per_row": per_row,
    }
    return strict_scoring.apply_strict_pass_metrics(aggregate, strict_results)


def exact_mcnemar(left_only: int, right_only: int) -> float:
    discordant = int(left_only) + int(right_only)
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(left_only, right_only) + 1)
    )
    return min(1.0, 2.0 * tail / (2.0**discordant))


def paired_strict_pass(
    left: Mapping[str, Mapping[str, str]],
    right: Mapping[str, Mapping[str, str]],
) -> Dict[str, Any]:
    return strict_scoring.paired_strict_pass(left, right)


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Return the probability-ordering two-sided Fisher exact p-value."""

    values = [int(a), int(b), int(c), int(d)]
    if any(value < 0 for value in values):
        raise ValueError("Fisher table counts must be non-negative.")
    row_one = a + b
    row_two = c + d
    column_one = a + c
    total = row_one + row_two
    if total == 0:
        return 1.0

    def probability(x: int) -> float:
        return (
            math.comb(row_one, x)
            * math.comb(row_two, column_one - x)
            / math.comb(total, column_one)
        )

    lower = max(0, column_one - row_two)
    upper = min(row_one, column_one)
    observed = probability(a)
    return min(
        1.0,
        sum(
            probability(x)
            for x in range(lower, upper + 1)
            if probability(x) <= observed + 1e-15
        ),
    )


def format_rate(value: Mapping[str, Any], *, include_ci: bool = False) -> str:
    rate = value.get("rate")
    rate_text = "NA" if rate is None else f"{float(rate):.3f}"
    result = f"{int(value['count'])}/{int(value['n'])} ({rate_text})"
    if include_ci:
        interval = dict(value.get("wilson_95_ci", {}) or {})
        if interval.get("lower") is not None:
            result += (
                f" [{float(interval['lower']):.3f}, "
                f"{float(interval['upper']):.3f}]"
            )
    return result


def primary_interpretation(summary: Mapping[str, Any]) -> str:
    comparison = dict(summary["paired_strict_pass"]["compliancegpt_vs_frontier"])
    p_value = float(comparison["exact_mcnemar_two_sided_p"])
    left_only = int(comparison["left_only"])
    right_only = int(comparison["right_only"])
    if p_value >= 0.05:
        return (
            "On these 100 paired rows, ComplianceGPT and Gemini 3.5 Flash are not "
            "statistically distinguishable on strict pass. The point estimate is not "
            "used as evidence of direction."
        )
    winner = "ComplianceGPT" if left_only > right_only else "Gemini 3.5 Flash"
    return (
        f"The two-sided exact McNemar test detects a paired strict-pass difference "
        f"on these 100 rows in favor of {winner}."
    )


def write_summary_markdown(path: Path, summary: Mapping[str, Any]) -> None:
    labels = [
        ("compliancegpt_4bit", "ComplianceGPT, 4-bit selector"),
        ("generative_frontier_api", "Gemini 3.5 Flash, free-form"),
        ("generative_baseline_4bit", "Qwen2.5-7B, free-form 4-bit"),
    ]
    lines = [
        "# Batch 5D — Revision 5 Frontier API Baseline",
        "",
        f"Result identity: `{RESULT_ID}`",
        "",
        (
            "All systems use the same 100 frozen Revision 5 questions, ordered "
            "evidence windows, ASK policy, and strict-pass standard."
        ),
        "",
        "## Primary and supporting outcomes",
        "",
        (
            "| System | Strict pass [95% CI] | Full clause coverage | Runtime pass "
            "| Clause precision | Clause recall | Mean words |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label in labels:
        metrics = dict(summary["configurations"][key])
        lines.append(
            f"| {label} | {format_rate(metrics['strict_pass'], include_ci=True)}"
            f" | {format_rate(metrics['full_gold_clause_coverage'])}"
            f" | {format_rate(metrics['runtime_contract_pass'])}"
            f" | {float(metrics['mean_gold_clause_precision']):.3f}"
            f" | {float(metrics['mean_gold_clause_recall']):.3f}"
            f" | {float(metrics['answer_word_count']['mean']):.1f} |"
        )
    paired = dict(summary["paired_strict_pass"]["compliancegpt_vs_frontier"])
    lines.extend(
        [
            "",
            "## Paired strict-pass test",
            "",
            (
                "| Comparison | ComplianceGPT only | Gemini only | Both pass "
                "| Neither pass | Exact two-sided McNemar p |"
            ),
            "|---|---:|---:|---:|---:|---:|",
            (
                "| ComplianceGPT vs Gemini 3.5 Flash"
                f" | {paired['left_only']} | {paired['right_only']}"
                f" | {paired['both_pass']} | {paired['neither_pass']}"
                f" | {float(paired['exact_mcnemar_two_sided_p']):.8g} |"
            ),
            "",
            primary_interpretation(summary),
            "",
            "## Coverage-complete rejections",
            "",
            (
                "| System | Coverage-complete | Strict pass within coverage | Lost "
                "| Realization loss [95% CI] |"
            ),
            "|---|---:|---:|---:|---:|",
        ]
    )
    for key, label in labels:
        loss = dict(summary["configurations"][key]["realization_loss"])
        lines.append(
            f"| {label} | {loss['coverage_complete']}"
            f" | {loss['strict_pass_within_coverage']} | {loss['count']}"
            f" | {format_rate(loss, include_ci=True)} |"
        )
    realization = dict(summary["realization_loss_comparison"])
    lines.extend(
        [
            "",
            (
                "Two-sided Fisher exact p for ComplianceGPT versus Gemini realization "
                f"loss: `{float(realization['fisher_exact_two_sided_p']):.8g}`."
            ),
            "",
            "The coverage-complete subsets differ by system; this descriptive comparison does not replace the paired end-to-end test.",
            "",
            (
                "ComplianceGPT's observed zero realization loss is predicted by "
                "construction; it confirms that the implementation matches the "
                "citation-contract specification on the coverage-complete rows."
            ),
            "",
            "## ODP status operating point",
            "",
            (
                "| System | Sensitivity [95% CI] | Specificity [95% CI] "
                "| Status precision [95% CI] | Exact ODP set on positive rows |"
            ),
            "|---|---:|---:|---:|---:|",
        ]
    )
    for key, label in labels:
        odp = dict(summary["configurations"][key]["odp_against_author_labels"])
        lines.append(
            f"| {label}"
            f" | {format_rate(odp['params_required_sensitivity'], include_ci=True)}"
            f" | {format_rate(odp['specificity'], include_ci=True)}"
            f" | {format_rate(odp['status_precision'], include_ci=True)}"
            f" | {format_rate(odp['exact_odp_set_positive_rows'])} |"
        )
    lines.extend(
        [
            "",
            (
                "ODP sensitivity and specificity are reported together. These values "
                "use the current author labels and are not independently adjudicated."
            ),
            "",
            "## Interpretation boundary",
            "",
            str(summary["interpretation_boundary"]),
            "",
            "## Strict-pass standard",
            "",
            str(summary["strict_pass_definition"]),
            "",
            str(summary["strict_pass_assessment"]),
            "",
            "See [the complete standard](../../../../src/answerer_comparison/README.md) and [three detailed examples](../../STRICT_PASS_EXAMPLES.md).",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def summarize_completed_run(
    *,
    output_dir: Path,
    gold_rows: Mapping[str, Mapping[str, str]],
    normalize_odp_id: Any,
    api_manifest: Mapping[str, Any],
) -> Dict[str, Any]:
    paths = {
        "generative_frontier_api": frontier_csv(output_dir),
        "generative_baseline_4bit": (
            output_dir / "references" / "rev5_generative_baseline_4bit.csv"
        ),
        "compliancegpt_4bit": (
            output_dir / "references" / "rev5_compliancegpt_4bit.csv"
        ),
    }
    rows = {name: read_csv_rows(path) for name, path in paths.items()}
    validation = validate_matched_rows(
        rows["generative_frontier_api"],
        rows["generative_baseline_4bit"],
        rows["compliancegpt_4bit"],
    )
    assessments = {
        name: strict_scoring.score_rows(revision=FRAMEWORK_VERSION, rows=values, gold_rows=gold_rows)
        for name, values in rows.items()
    }
    configurations: Dict[str, Any] = {}
    for name, values in rows.items():
        aggregate = aggregate_rows(
            rows=values,
            gold_rows=gold_rows,
            normalize_odp_id=normalize_odp_id,
            strict_results=assessments[name],
        )
        aggregate.pop("per_row", None)
        configurations[name] = aggregate

    compliance_loss = dict(configurations["compliancegpt_4bit"]["realization_loss"])
    frontier_loss = dict(configurations["generative_frontier_api"]["realization_loss"])
    realization_table = [
        [
            int(compliance_loss["count"]),
            int(compliance_loss["strict_pass_within_coverage"]),
        ],
        [
            int(frontier_loss["count"]),
            int(frontier_loss["strict_pass_within_coverage"]),
        ],
    ]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "framework_version": FRAMEWORK_VERSION,
        "n_questions": EXPECTED_ROWS,
        "generation_precommitment_sha256": PRECOMMITMENT_SHA256,
        "changed_factor": (
            "free-form answer model/runtime: Qwen2.5-7B -> Gemini frontier API"
        ),
        "matched_input_validation": validation,
        "api_provenance": dict(api_manifest),
        "configurations": configurations,
        "paired_strict_pass": {
            "compliancegpt_vs_frontier": {
                "left": "compliancegpt_4bit",
                "right": "generative_frontier_api",
                **paired_strict_pass(
                    assessments["compliancegpt_4bit"], assessments["generative_frontier_api"]
                ),
            },
            "frontier_vs_qwen_4bit": {
                "left": "generative_frontier_api",
                "right": "generative_baseline_4bit",
                **paired_strict_pass(
                    assessments["generative_frontier_api"],
                    assessments["generative_baseline_4bit"],
                ),
            },
            "compliancegpt_vs_qwen_4bit": {
                "left": "compliancegpt_4bit", "right": "generative_baseline_4bit",
                **paired_strict_pass(assessments["compliancegpt_4bit"], assessments["generative_baseline_4bit"]),
            },
        },
        "realization_loss_comparison": {
            "left": "compliancegpt_4bit",
            "right": "generative_frontier_api",
            "table_rows_are_systems_columns_are_lost_then_retained": realization_table,
            "fisher_exact_two_sided_p": fisher_exact_two_sided(
                realization_table[0][0],
                realization_table[0][1],
                realization_table[1][0],
                realization_table[1][1],
            ),
        },
        "strict_pass_definition": strict_scoring.STRICT_PASS_DEFINITION,
        "strict_pass_rule_version": strict_scoring.RULE_VERSION,
        "strict_pass_assessment": strict_scoring.ASSESSMENT_BOUNDARY,
        "interpretation_boundary": (
            "This is a stronger-system baseline, not an isolation of weight precision or "
            "architecture. Questions, model-visible evidence, prompt/parser, ODP policy, "
            "and verifier are fixed, but the API model and serving runtime differ. The "
            "strict-pass comparison measures agreement with the implemented author-labeled "
            "rules; it does not establish legal sufficiency or auditor approval. The "
            "mechanistic claim concerns realization loss and runtime-verifiable guarantees, "
            "not universal accuracy superiority."
        ),
        "file_hashes": {name: sha256_file(path) for name, path in paths.items()},
    }
    write_json(output_dir / "summary.json", summary)
    write_summary_markdown(output_dir / "SUMMARY.md", summary)
    strict_scoring.write_assessments(output_dir, assessments, rows)
    return summary


def write_output_manifest(output_dir: Path) -> Dict[str, Any]:
    files: Dict[str, str] = {}
    for path in sorted(output_dir.rglob("*")):
        relative = str(path.relative_to(output_dir))
        if (
            path.is_file()
            and not path.name.endswith(".tmp")
            and path.name != "runner_failure_tail.log"
            and relative != "manifests/outputs.json"
        ):
            files[relative] = sha256_file(path)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "files": files,
        "files_sha256": canonical_sha256(files),
    }
    write_json(output_dir / "manifests" / "outputs.json", manifest)
    return manifest


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    archive_path = (
        args.frozen_archive.resolve()
        if args.frozen_archive is not None
        else (repo_root / DEFAULT_ARCHIVE).resolve()
    )
    contexts, gold_rows = prepare_experiment(repo_root, output_dir, archive_path)
    print(f"Frozen Batch 5D inputs verified: {len(contexts)} Revision 5 contexts.")
    if args.prepare_only:
        print(f"Prepared-context audit: {output_dir / 'PREPARED_CONTEXTS.md'}")
        print("No API key was read and no API call was made.")
        return

    api_key = str(os.environ.get("GEMINI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. In Colab, add it to Secrets, enable notebook "
            "access, and rerun. The notebook never prints or writes the key."
        )
    validate_or_write_api_runtime(output_dir)

    current_src = repo_root / "src"
    if str(current_src) not in sys.path:
        sys.path.insert(0, str(current_src))
    from answerer_comparison.frontier_api_answerer import (
        make_gemini_generate_content_answerer_class,
        read_api_call_log,
        summarize_usage,
    )
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=False,
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=int(float(GENERATION_SETTINGS["sdk_timeout_seconds"]) * 1000),
            retry_options=types.HttpRetryOptions(
                attempts=int(GENERATION_SETTINGS["sdk_max_retries"]),
                initial_delay=1.0,
                max_delay=60.0,
                exp_base=2.0,
                jitter=1.0,
                http_status_codes=[408, 429, 500, 502, 503, 504],
            ),
        ),
    )

    with tempfile.TemporaryDirectory(prefix="compliancegpt-rq2-frontier-rev5-") as temporary:
        frozen_src = registered.extract_frozen_source(repo_root, Path(temporary))
        sys.path.insert(0, str(frozen_src))

        if "transformers" not in sys.modules:
            try:
                __import__("transformers")
            except ImportError:
                transformers_stub = ModuleType("transformers")

                class UnusedGenerationConfig:
                    pass

                transformers_stub.GenerationConfig = UnusedGenerationConfig
                transformers_stub.__version__ = "not-installed-api-run"
                sys.modules["transformers"] = transformers_stub
        qur_module_name = "compliancegpt.QUR_generator.qur_generator_ut"
        if qur_module_name not in sys.modules:
            qur_stub = ModuleType(qur_module_name)
            qur_stub.QURComponent = None
            sys.modules[qur_module_name] = qur_stub

        from answerer_comparison import matched_window_runner as matched
        import compliancegpt.pipeline.pipeline as compliance_pipeline_module
        from compliancegpt.generator.verifier.verifier import normalize_odp_id
        from generative_answerer.generator import (
            BaselineGenerativeAnswerer,
            build_system_prompt,
        )
        import generative_answerer.pipeline as generative_pipeline_module

        matched.CONTEXT_SCHEMA = registered.EXPECTED_CONTEXT_SCHEMA
        system_prompt = str(build_system_prompt())
        answerer_class = make_gemini_generate_content_answerer_class(
            BaselineGenerativeAnswerer
        )
        answerer = answerer_class(
            client=client,
            model_id=MODEL_ID,
            system_prompt=system_prompt,
            query_id_by_question={
                str(context["question"]): str(context["query_id"])
                for context in contexts
            },
            call_log_path=api_log_path(output_dir),
            thinking_level=str(GENERATION_SETTINGS["thinking_level"]),
            temperature=float(GENERATION_SETTINGS["temperature"]),
            max_output_tokens=int(GENERATION_SETTINGS["max_output_tokens"]),
            max_parse_retries=int(GENERATION_SETTINGS["max_parse_retries"]),
        )
        generation_contract = validate_generation_contract(system_prompt, answerer)
        write_json(
            output_dir / "manifests" / "generation_contract.json",
            generation_contract,
        )

        class PlaceholderModel:
            config = SimpleNamespace(_commit_hash=MODEL_RESOLVED_REVISION_MARKER)

        class PlaceholderTokenizer:
            init_kwargs = {"_commit_hash": TOKENIZER_REVISION_MARKER}

        compliance_pipeline_module.ComplianceGenerator = lambda *_args, **_kwargs: object()
        generative_pipeline_module.BaselineGenerativeAnswerer = (
            lambda *_args, **_kwargs: answerer
        )
        retriever = matched.FrozenCCSRetriever.from_jsonl(repo_root / INPUTS["ccs"])
        pipeline = generative_pipeline_module.BaselineGenerativeRAGPipeline(
            framework_version=FRAMEWORK_VERSION,
            model_id=MODEL_ID,
            model_revision=MODEL_REQUESTED_REVISION,
            shared_model=PlaceholderModel(),
            shared_tokenizer=PlaceholderTokenizer(),
            retriever_instance=retriever,
            ccs_path=str(repo_root / INPUTS["ccs"]),
            odp_registry_path=str(repo_root / INPUTS["odp_registry"]),
            use_qur=False,
            doc_filter_mode="prefer_smt_keep_params",
            load_in_4bit=False,
            resolution_policy="ASK",
            verify_strict_extras=False,
            verify_strict_verbatim=True,
            verify_strict_version=False,
        )
        if pipeline.model_resolved_revision != MODEL_RESOLVED_REVISION_MARKER:
            raise AssertionError("Frontier model revision marker was not preserved.")
        if pipeline.tokenizer_resolved_revision != TOKENIZER_REVISION_MARKER:
            raise AssertionError("Server-managed tokenizer marker was not preserved.")

        run_manifest = matched.run_prepared_contexts(
            pipeline=pipeline,
            contexts=contexts,
            gold_rows_by_id=gold_rows,
            system_name=SYSTEM_NAME,
            output_csv=frontier_csv(output_dir),
            resume=True,
            progress_every=1,
        )
        run_manifest["api_model_id"] = MODEL_ID
        run_manifest["local_model_loaded"] = False
        write_json(output_dir / "manifests" / "run.json", run_manifest)
        api_manifest = audit_api_provenance(
            output_dir, read_api_call_log, summarize_usage
        )
        summarize_completed_run(
            output_dir=output_dir,
            gold_rows=gold_rows,
            normalize_odp_id=normalize_odp_id,
            api_manifest=api_manifest,
        )

    write_output_manifest(output_dir)
    archive = Path(
        shutil.make_archive(
            str(output_dir.parent / output_dir.name),
            "zip",
            root_dir=output_dir,
        )
    )
    print(f"Batch 5D completed successfully: {output_dir}")
    print(f"Result archive: {archive}")
    print(f"Result archive SHA-256: {sha256_file(archive)}")


if __name__ == "__main__":
    main()
