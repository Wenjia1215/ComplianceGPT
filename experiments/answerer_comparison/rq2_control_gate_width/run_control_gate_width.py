#!/usr/bin/env python3
"""Run the fixed-width RQ2 control-gate sensitivity study.

The study reuses the immutable, gold-free RQ2 v3 retrieval traces and changes
exactly one factor: the number of top-ranked controls admitted to the shared
24-record evidence window.  Fixed widths 1, 2, 3, and 5 are evaluated.  The
released adaptive gate remains an unchanged reference result.

Prepared contexts are deterministic and can be built without a GPU.  The full
selector sweep requires the same pinned Qwen2.5-7B-Instruct revision used by
RQ2 v3.  Model outputs are checkpointed after every question and are safe to
resume only when the code, model, source archive, and prepared-context hashes
match.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import io
import json
import math
import os
import platform
import random
import shutil
import statistics
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


RESULT_ID = "rq2_control_gate_width_v1"
SCHEMA_VERSION = "compliancegpt-rq2-control-gate-width-v1"
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
WIDTHS = (1, 2, 3, 5)
EXPECTED_ROWS = {"rev5": 100, "rev4": 36}
FROZEN_ARCHIVE_SHA256 = "56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328"
SOURCE_CONTEXT_MEMBERS = {
    "rev5": "contexts/rev5_prepared_contexts.jsonl",
    "rev4": "contexts/rev4_prepared_contexts.jsonl",
}
SOURCE_SELECTOR_MEMBERS = {
    "rev5": "contracts/rev5_compliancegpt.csv",
    "rev4": "contracts/rev4_compliancegpt.csv",
}
INPUTS = {
    "rev5": {
        "gold": "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv",
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl",
        "odp_registry": "data/ODP/rev5/odp_registry_rev5.json",
    },
    "rev4": {
        "gold": "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv",
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl",
        "odp_registry": "data/ODP/rev4/odp_registry_rev4.json",
    },
}
CODE_PATHS = (
    "experiments/answerer_comparison/rq2_control_gate_width/run_control_gate_width.py",
    "src/answerer_comparison/matched_window_runner.py",
    "src/compliancegpt/pipeline/evidence_window.py",
    "src/compliancegpt/pipeline/pipeline.py",
    "src/compliancegpt/generator/generator.py",
    "src/compliancegpt/generator/verifier/verifier.py",
    "src/compliancegpt/generator/citation_contract_80053.md",
)


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[3]
    default_archive = (
        default_root
        / "experiments"
        / "answerer_comparison"
        / "rq2_matched"
        / "results_v3"
        / "compliancegpt_rq2_matched_v3.zip"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--frozen-archive", type=Path, default=default_archive)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--widths",
        nargs="+",
        type=int,
        default=list(WIDTHS),
        help="Fixed control-gate widths. The registered study uses 1 2 3 5.",
    )
    parser.add_argument(
        "--revisions",
        nargs="+",
        choices=("rev5", "rev4"),
        default=("rev5", "rev4"),
    )
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument("--model-revision", default=MODEL_REVISION)
    parser.add_argument("--no-4bit", action="store_true")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Build and audit all fixed-width contexts without loading the model.",
    )
    return parser.parse_args()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: os.PathLike[str] | str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(payload)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
    return sha256_file(path)


def git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def code_manifest(repo_root: Path) -> Dict[str, Any]:
    files: Dict[str, str] = {}
    for relative in CODE_PATHS:
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Experiment code input is missing: {path}")
        files[relative] = sha256_file(path)
    return {
        "experiment_code_files": files,
        "experiment_code_sha256": canonical_sha256(files),
    }


def configure_determinism(seed: int = 42) -> Dict[str, Any]:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except Exception:
        pass
    try:
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
    except Exception:
        pass
    return {
        "seed": seed,
        "torch_deterministic_algorithms": True,
        "cudnn_benchmark": False,
        "cudnn_deterministic": True,
    }


def require_gpu() -> None:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError(
            "A CUDA GPU is required for the pinned Qwen 7B selector sweep. "
            "Use --prepare-only here, or run the full command on a GPU runtime."
        )
    print(f"GPU: {torch.cuda.get_device_name(0)}")


def validate_registered_design(widths: Sequence[int]) -> List[int]:
    normalized = list(dict.fromkeys(int(width) for width in widths))
    if any(width < 1 for width in normalized):
        raise ValueError("Every gate width must be at least 1.")
    if tuple(normalized) != WIDTHS:
        raise ValueError(
            f"The registered {RESULT_ID} design is exactly widths {WIDTHS}; got {tuple(normalized)}. "
            "Use a new result identity before changing the sweep."
        )
    return normalized


def validate_registered_runtime(
    *,
    revisions: Sequence[str],
    model_id: str,
    model_revision: str,
    load_in_4bit: bool,
) -> List[str]:
    normalized_revisions = list(dict.fromkeys(str(value) for value in revisions))
    if normalized_revisions != ["rev5", "rev4"]:
        raise ValueError(
            f"The registered {RESULT_ID} design requires revisions ['rev5', 'rev4']; "
            f"got {normalized_revisions}. Use a new result identity for a partial study."
        )
    if str(model_id) != MODEL_ID or str(model_revision) != MODEL_REVISION:
        raise ValueError(
            f"The registered study requires {MODEL_ID}@{MODEL_REVISION}. "
            "Use a new result identity for another selector model or revision."
        )
    if not bool(load_in_4bit):
        raise ValueError(
            "The registered study matches the RQ2 v3 4-bit selector runtime. "
            "Use a new result identity for another quantization setting."
        )
    return normalized_revisions


def configure_fixed_width_pipeline(pipeline: Any, width: int) -> Dict[str, Any]:
    """Configure the runtime gate to replay one fixed-width context family."""

    requested_width = int(width)
    if requested_width not in WIDTHS:
        raise ValueError(
            f"The registered {RESULT_ID} runtime supports widths {WIDTHS}; "
            f"got {requested_width}."
        )
    pipeline.gen_control_gate_topn = requested_width
    # select_allowed_controls widens only when margin < threshold. Negative
    # infinity disables both adaptive branches for every observed margin while
    # preserving the shared gate implementation used by RQ2 v3.
    pipeline.gen_control_gate_lowconf_top2 = float("-inf")
    pipeline.gen_control_gate_lowconf_top3 = float("-inf")
    pipeline.gen_control_gate_lowconf_maxn = requested_width
    return {
        "mode": "fixed_width_no_adaptive_widening",
        "requested_width": requested_width,
        "gen_control_gate_topn": requested_width,
        "adaptive_widening": False,
    }


def validate_fixed_width_runtime_replay(
    *,
    grid: Mapping[Tuple[int, str], Sequence[Mapping[str, Any]]],
    widths: Sequence[int],
    revisions: Sequence[str],
    select_allowed_controls: Any,
    normalize_control_id: Any,
    build_evidence_window: Any,
    assert_same_evidence_window: Any,
    filter_docs_to_controls: Any,
    apply_doc_filter_mode: Any,
) -> Dict[str, Any]:
    """Replay the runtime gate/window path without a model and match every lock."""

    validated: List[Dict[str, str]] = []
    for width in widths:
        requested_width = int(width)
        for revision in revisions:
            for context in grid[(requested_width, revision)]:
                query_id = str(context.get("query_id", ""))
                gate = dict(context.get("control_gate", {}) or {})
                controls, primary_control, allowed_controls, widen_tier = (
                    select_allowed_controls(
                        retrieved_docs=list(context.get("retrieved_docs", []) or []),
                        retrieval_meta=dict(context.get("retrieval_meta", {}) or {}),
                        normalize_control_id=normalize_control_id,
                        topn=requested_width,
                        lowconf_top2=float("-inf"),
                        lowconf_top3=float("-inf"),
                        lowconf_maxn=requested_width,
                    )
                )
                expected_controls = list(gate.get("normalized_controls", []) or [])
                expected_primary = str(gate.get("primary_control", "") or "")
                expected_allowed = list(gate.get("allowed_controls", []) or [])
                if controls != expected_controls:
                    raise AssertionError(
                        f"Fixed-gate ranked controls changed for top{requested_width} "
                        f"{revision} query {query_id}."
                    )
                if primary_control != expected_primary:
                    raise AssertionError(
                        f"Fixed-gate primary control changed for top{requested_width} "
                        f"{revision} query {query_id}."
                    )
                if allowed_controls != expected_allowed or widen_tier != 0:
                    raise AssertionError(
                        f"Adaptive widening leaked into top{requested_width} "
                        f"{revision} query {query_id}: {allowed_controls}, tier={widen_tier}."
                    )

                window_config = dict(context.get("window_config", {}) or {})
                _, audit = build_evidence_window(
                    retrieved_docs=list(context.get("retrieved_docs", []) or []),
                    retrieval_meta=dict(context.get("retrieval_meta", {}) or {}),
                    allowed_controls=allowed_controls,
                    primary_control=primary_control,
                    doc_filter_mode=str(
                        window_config.get("doc_filter_mode", "prefer_smt_keep_params")
                    ),
                    gen_docs_k=int(window_config.get("gen_docs_k", 24)),
                    filter_docs_to_controls=filter_docs_to_controls,
                    apply_doc_filter_mode=apply_doc_filter_mode,
                    primary_first_min_margin_ratio=float(
                        window_config.get("primary_first_min_margin_ratio", 0.06)
                    ),
                )
                shared_hash = assert_same_evidence_window(
                    dict(audit.get("evidence_window", {}) or {}),
                    dict(context.get("evidence_window_manifest", {}) or {}),
                )
                validated.append(
                    {
                        "configuration": f"top{requested_width}_{revision}",
                        "query_id": query_id,
                        "evidence_window_sha256": shared_hash,
                    }
                )

    expected_count = len(widths) * sum(EXPECTED_ROWS[revision] for revision in revisions)
    if len(validated) != expected_count:
        raise AssertionError(
            f"Expected {expected_count} fixed-width runtime replays, got {len(validated)}."
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "scope": "pre-inference replay of the exact runtime gate and evidence-window path",
        "adaptive_widening": False,
        "widths": [int(width) for width in widths],
        "revisions": list(revisions),
        "validated_contexts": len(validated),
        "replay_sha256": canonical_sha256(validated),
    }


def verify_inputs(repo_root: Path, archive_path: Path, revisions: Iterable[str]) -> None:
    if not archive_path.is_file():
        raise FileNotFoundError(f"Frozen RQ2 v3 archive is missing: {archive_path}")
    actual = sha256_file(archive_path)
    if actual != FROZEN_ARCHIVE_SHA256:
        raise RuntimeError(
            "Frozen RQ2 v3 archive hash changed: "
            f"expected {FROZEN_ARCHIVE_SHA256}, got {actual}"
        )
    missing: List[str] = []
    for revision in revisions:
        for relative in INPUTS[revision].values():
            if not (repo_root / relative).is_file():
                missing.append(relative)
    if missing:
        raise FileNotFoundError("Required inputs are missing:\n" + "\n".join(missing))


def load_source_archive(
    archive_path: Path,
    revisions: Sequence[str],
    validate_prepared_context: Any,
) -> Tuple[
    Dict[str, List[Dict[str, Any]]],
    Dict[str, Dict[str, Dict[str, str]]],
    Dict[str, Any],
]:
    contexts: Dict[str, List[Dict[str, Any]]] = {}
    selector_rows: Dict[str, Dict[str, Dict[str, str]]] = {}
    manifest: Dict[str, Any] = {
        "archive_path": str(archive_path),
        "archive_sha256": sha256_file(archive_path),
        "members": {},
    }
    with zipfile.ZipFile(archive_path) as archive:
        for revision in revisions:
            context_member = SOURCE_CONTEXT_MEMBERS[revision]
            context_payload = archive.read(context_member)
            loaded_contexts = [
                json.loads(line)
                for line in context_payload.decode("utf-8").splitlines()
                if line.strip()
            ]
            for context in loaded_contexts:
                validate_prepared_context(context)
            if len(loaded_contexts) != EXPECTED_ROWS[revision]:
                raise AssertionError(
                    f"Expected {EXPECTED_ROWS[revision]} source contexts for {revision}, "
                    f"loaded {len(loaded_contexts)}."
                )
            contexts[revision] = loaded_contexts
            selector_member = SOURCE_SELECTOR_MEMBERS[revision]
            selector_payload = archive.read(selector_member)
            rows = list(
                csv.DictReader(io.StringIO(selector_payload.decode("utf-8"), newline=""))
            )
            selector_rows[revision] = {str(row["query_id"]): dict(row) for row in rows}
            if len(selector_rows[revision]) != EXPECTED_ROWS[revision]:
                raise AssertionError(
                    f"Expected {EXPECTED_ROWS[revision]} adaptive selector rows for {revision}."
                )
            manifest["members"][context_member] = sha256_bytes(context_payload)
            manifest["members"][selector_member] = sha256_bytes(selector_payload)
    return contexts, selector_rows, manifest


def _normalize_controls(source_context: Mapping[str, Any], normalize_control_id: Any) -> List[str]:
    raw_controls = list(
        ((source_context.get("control_gate") or {}).get("normalized_controls") or [])
    )
    if not raw_controls:
        raw_controls = list(
            ((source_context.get("retrieval_meta") or {}).get("selected_controls") or [])
        )
    controls: List[str] = []
    for raw in raw_controls:
        normalized = normalize_control_id(raw)
        if not normalized:
            continue
        value = str(normalized).upper()
        controls.append(value)
    if not controls:
        raise ValueError(f"Source context {source_context.get('query_id')} has no ranked controls.")
    return controls


def build_fixed_width_context(
    *,
    source_context: Mapping[str, Any],
    width: int,
    normalize_control_id: Any,
    build_evidence_window: Any,
    evidence_window_manifest: Any,
    filter_docs_to_controls: Any,
    apply_doc_filter_mode: Any,
    validate_prepared_context: Any,
) -> Dict[str, Any]:
    """Rebuild one gold-free context with a fixed, non-adaptive gate width."""

    validate_prepared_context(source_context)
    controls = _normalize_controls(source_context, normalize_control_id)
    primary_control = controls[0]
    requested_width = int(width)
    allowed_controls = controls[:requested_width]
    retrieved_docs = [dict(doc) for doc in list(source_context.get("retrieved_docs", []) or [])]
    retrieval_meta = dict(source_context.get("retrieval_meta", {}) or {})
    source_window_config = dict(source_context.get("window_config", {}) or {})
    doc_filter_mode = str(source_window_config.get("doc_filter_mode", "prefer_smt_keep_params"))
    gen_docs_k = int(source_window_config.get("gen_docs_k", 24))
    primary_threshold = float(
        source_window_config.get("primary_first_min_margin_ratio", 0.06)
    )
    window, audit = build_evidence_window(
        retrieved_docs=retrieved_docs,
        retrieval_meta=retrieval_meta,
        allowed_controls=allowed_controls,
        primary_control=primary_control,
        doc_filter_mode=doc_filter_mode,
        gen_docs_k=gen_docs_k,
        filter_docs_to_controls=filter_docs_to_controls,
        apply_doc_filter_mode=apply_doc_filter_mode,
        primary_first_min_margin_ratio=primary_threshold,
    )
    window_controls: List[str] = []
    seen_window_controls = set()
    for doc in window:
        control = normalize_control_id(doc.get("control_id", ""))
        if not control:
            continue
        value = str(control).upper()
        if value not in seen_window_controls:
            seen_window_controls.add(value)
            window_controls.append(value)

    context: Dict[str, Any] = {
        "schema_version": str(source_context["schema_version"]),
        "query_id": str(source_context["query_id"]),
        "framework_version": str(source_context["framework_version"]),
        "question": str(source_context["question"]),
        "rewrites": list(source_context.get("rewrites", []) or []),
        "retrieved_docs": retrieved_docs,
        "retrieval_meta": retrieval_meta,
        "control_gate": {
            "mode": "fixed_width_no_adaptive_widening",
            "requested_width": requested_width,
            "normalized_controls": controls,
            "primary_control": primary_control,
            "allowed_controls": allowed_controls,
            "effective_allowed_width": len(allowed_controls),
            "window_controls": window_controls,
            "effective_window_width": len(window_controls),
            "widen_tier": 0,
        },
        "window_config": {
            "doc_filter_mode": doc_filter_mode,
            "gen_docs_k": gen_docs_k,
            "primary_first_min_margin_ratio": primary_threshold,
        },
        "evidence_window": window,
        "evidence_window_manifest": evidence_window_manifest(window),
        "sensitivity_study": {
            "result_id": RESULT_ID,
            "changed_factor": "fixed_control_gate_width",
            "source_context_sha256": str(source_context.get("context_sha256", "")),
            "all_other_window_settings_frozen": True,
            "audit": audit,
        },
    }
    context["context_sha256"] = canonical_sha256(context)
    validate_prepared_context(context)
    return context


def prepare_context_grid(
    *,
    source_contexts: Mapping[str, Sequence[Mapping[str, Any]]],
    widths: Sequence[int],
    revisions: Sequence[str],
    output_dir: Path,
    helpers: Mapping[str, Any],
) -> Tuple[Dict[Tuple[int, str], List[Dict[str, Any]]], Dict[str, Any]]:
    grid: Dict[Tuple[int, str], List[Dict[str, Any]]] = {}
    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "gate_mode": "fixed_width_no_adaptive_widening",
        "widths": list(widths),
        "revisions": list(revisions),
        "contexts": {},
    }
    for width in widths:
        for revision in revisions:
            contexts = [
                build_fixed_width_context(
                    source_context=source,
                    width=width,
                    normalize_control_id=helpers["normalize_control_id"],
                    build_evidence_window=helpers["build_evidence_window"],
                    evidence_window_manifest=helpers["evidence_window_manifest"],
                    filter_docs_to_controls=helpers["filter_docs_to_controls"],
                    apply_doc_filter_mode=helpers["apply_doc_filter_mode"],
                    validate_prepared_context=helpers["validate_prepared_context"],
                )
                for source in source_contexts[revision]
            ]
            path = output_dir / "contexts" / f"top{width}_{revision}_prepared_contexts.jsonl"
            file_hash = write_jsonl(path, contexts)
            grid[(width, revision)] = contexts
            key = f"top{width}_{revision}"
            manifest["contexts"][key] = {
                "path": str(path),
                "sha256": file_hash,
                "row_count": len(contexts),
                "window_hashes_sha256": canonical_sha256(
                    [
                        str(context["evidence_window_manifest"]["sha256"])
                        for context in contexts
                    ]
                ),
                "unique_window_hashes": len(
                    {
                        str(context["evidence_window_manifest"]["sha256"])
                        for context in contexts
                    }
                ),
            }
    write_json(output_dir / "manifests" / "prepared_contexts.json", manifest)
    return grid, manifest


def listish(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []
    parts = [text]
    for delimiter in ("\r\n", "\n", "|", ",", ";"):
        expanded: List[str] = []
        for part in parts:
            expanded.extend(part.split(delimiter))
        parts = expanded
    return [part.strip() for part in parts if part.strip()]


def csv_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * float(fraction)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def distribution(values: Sequence[float]) -> Dict[str, float]:
    floats = [float(value) for value in values]
    if not floats:
        return {
            "min": float("nan"),
            "mean": float("nan"),
            "median": float("nan"),
            "p95": float("nan"),
            "max": float("nan"),
        }
    return {
        "min": min(floats),
        "mean": statistics.fmean(floats),
        "median": statistics.median(floats),
        "p95": percentile(floats, 0.95),
        "max": max(floats),
    }


def load_gold_rows_simple(path: Path, expected_rows: int) -> Dict[str, Dict[str, str]]:
    rows: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            query_id = str(row.get("query_id") or row.get("ID") or row.get("id") or "").strip()
            if not query_id:
                raise ValueError(f"Gold row has no query id: {path}")
            if query_id in rows:
                raise ValueError(f"Duplicate gold query id {query_id!r}: {path}")
            rows[query_id] = dict(row)
    if len(rows) != expected_rows:
        raise AssertionError(f"Expected {expected_rows} gold rows, loaded {len(rows)}: {path}")
    return rows


def context_preflight(
    *,
    grid: Mapping[Tuple[int, str], Sequence[Mapping[str, Any]]],
    source_contexts: Mapping[str, Sequence[Mapping[str, Any]]],
    gold_rows: Mapping[str, Mapping[str, Mapping[str, str]]],
    widths: Sequence[int],
    revisions: Sequence[str],
    output_dir: Path,
) -> Dict[str, Any]:
    """Audit deterministic window opportunity before any selector inference."""

    row_path = output_dir / "preflight" / "window_diagnostics.csv"
    row_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "revision",
        "query_id",
        "configuration",
        "requested_width",
        "effective_allowed_width",
        "effective_window_width",
        "window_record_count",
        "window_full_gold_clause_coverage",
        "window_gold_clause_recall",
        "window_gold_clause_precision",
        "gold_has_odp",
        "window_contains_gold_odp_marker",
        "window_sha256",
    ]
    diagnostic_rows: List[Dict[str, Any]] = []

    def add_rows(
        revision: str,
        configuration: str,
        contexts: Sequence[Mapping[str, Any]],
        requested_width: str,
    ) -> None:
        for context in contexts:
            query_id = str(context["query_id"])
            gold = gold_rows[revision][query_id]
            gold_ids = {item.lower() for item in listish(gold.get("gold_control_path", ""))}
            window = list(context.get("evidence_window", []) or [])
            window_ids = {
                str(record.get("id", "") or "").strip().lower()
                for record in window
                if str(record.get("id", "") or "").strip()
            }
            gold_odps = {
                item.lower() for item in listish(gold.get("odp_required", ""))
            }
            marker_text = "\n".join(str(record.get("text", "") or "") for record in window).lower()
            gate = dict(context.get("control_gate", {}) or {})
            effective_window_width = gate.get("effective_window_width")
            if effective_window_width is None:
                effective_window_width = len(
                    {
                        str(control).strip().upper()
                        for control in list(gate.get("allowed_controls", []) or [])
                        if str(control).strip()
                    }
                )
            diagnostic_rows.append(
                {
                    "revision": revision,
                    "query_id": query_id,
                    "configuration": configuration,
                    "requested_width": requested_width,
                    "effective_allowed_width": len(list(gate.get("allowed_controls", []) or [])),
                    "effective_window_width": int(effective_window_width),
                    "window_record_count": len(window),
                    "window_full_gold_clause_coverage": gold_ids.issubset(window_ids),
                    "window_gold_clause_recall": (
                        len(gold_ids & window_ids) / len(gold_ids) if gold_ids else 1.0
                    ),
                    "window_gold_clause_precision": (
                        len(gold_ids & window_ids) / len(window_ids) if window_ids else 0.0
                    ),
                    "gold_has_odp": bool(gold_odps),
                    "window_contains_gold_odp_marker": (
                        all(odp in marker_text for odp in gold_odps) if gold_odps else True
                    ),
                    "window_sha256": str(
                        (context.get("evidence_window_manifest") or {}).get("sha256", "")
                    ),
                }
            )

    for revision in revisions:
        add_rows(revision, "adaptive_v3", source_contexts[revision], "adaptive")
        for width in widths:
            add_rows(revision, f"top{width}", grid[(width, revision)], str(width))

    with row_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(diagnostic_rows)

    summary: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "scope": "gold-aware evidence-window opportunity audit; no selector inference",
        "configurations": {},
        "diagnostics_csv": str(row_path),
        "diagnostics_csv_sha256": sha256_file(row_path),
    }
    for revision in revisions:
        for configuration in ["adaptive_v3"] + [f"top{width}" for width in widths]:
            rows = [
                row
                for row in diagnostic_rows
                if row["revision"] == revision and row["configuration"] == configuration
            ]
            key = f"{revision}_{configuration}"
            odp_rows = [row for row in rows if bool(row["gold_has_odp"])]
            summary["configurations"][key] = {
                "n": len(rows),
                "full_gold_clause_coverage_count": sum(
                    bool(row["window_full_gold_clause_coverage"]) for row in rows
                ),
                "full_gold_clause_coverage_rate": (
                    sum(bool(row["window_full_gold_clause_coverage"]) for row in rows) / len(rows)
                    if rows
                    else float("nan")
                ),
                "mean_gold_clause_recall": statistics.fmean(
                    float(row["window_gold_clause_recall"]) for row in rows
                ),
                "mean_gold_clause_precision": statistics.fmean(
                    float(row["window_gold_clause_precision"]) for row in rows
                ),
                "window_record_count": distribution(
                    [float(row["window_record_count"]) for row in rows]
                ),
                "effective_window_width": distribution(
                    [float(row["effective_window_width"]) for row in rows]
                ),
                "gold_odp_marker_coverage_count": sum(
                    bool(row["window_contains_gold_odp_marker"]) for row in odp_rows
                ),
                "gold_odp_marker_coverage_n": len(odp_rows),
                "gold_odp_marker_coverage_rate": (
                    sum(bool(row["window_contains_gold_odp_marker"]) for row in odp_rows)
                    / len(odp_rows)
                    if odp_rows
                    else float("nan")
                ),
            }
    write_json(output_dir / "preflight" / "summary.json", summary)
    return summary


def has_model_checkpoints(output_dir: Path) -> bool:
    contracts = output_dir / "contracts"
    if not contracts.is_dir():
        return False
    for path in contracts.glob("*.csv"):
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            if next(reader, None) is not None:
                return True
    return False


def load_or_create_run_config(
    *,
    output_dir: Path,
    repo_root: Path,
    archive_manifest: Mapping[str, Any],
    context_manifest: Mapping[str, Any],
    widths: Sequence[int],
    revisions: Sequence[str],
    model_id: str,
    model_revision: str,
    load_in_4bit: bool,
) -> Dict[str, Any]:
    path = output_dir / "run_config.json"
    code = code_manifest(repo_root)
    expected: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "model_id": str(model_id),
        "model_revision": str(model_revision),
        "load_in_4bit": bool(load_in_4bit),
        "widths": list(widths),
        "revisions": list(revisions),
        "gate_mode": "fixed_width_no_adaptive_widening",
        "selector_window_cap": 24,
        "source_archive_sha256": str(archive_manifest["archive_sha256"]),
        "source_member_hashes": dict(archive_manifest["members"]),
        "prepared_context_hashes": {
            key: str(value["sha256"])
            for key, value in dict(context_manifest["contexts"]).items()
        },
        **code,
    }
    current_commit = git_head(repo_root)
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
        for key, value in expected.items():
            if stored.get(key) != value:
                if has_model_checkpoints(output_dir):
                    raise RuntimeError(
                        f"Run configuration changed for {key!r} after checkpoints were written. "
                        "Use a new output directory and result identity."
                    )
                stored[key] = value
        observed = [
            str(value)
            for value in list(stored.get("repo_commits_observed", []) or [])
            if str(value)
        ]
        if current_commit and current_commit not in observed:
            observed.append(current_commit)
        stored["repo_commit"] = current_commit
        stored["repo_commits_observed"] = observed
        write_json(path, stored)
        return stored
    config = {
        **expected,
        "repo_commit": current_commit,
        "repo_commits_observed": [current_commit] if current_commit else [],
        "gold_policy": "gold excluded from prepared contexts; used only for offline scoring",
        "changed_factor": "fixed control-gate width only",
        "frozen_factors": [
            "retrieval traces",
            "query variants",
            "document filtering",
            "primary-first threshold",
            "24-record selector window",
            "selector prompt",
            "selector model and revision",
            "ASK ODP policy",
            "offline verifier",
        ],
    }
    write_json(path, config)
    return config


def pipeline_kwargs(
    *,
    repo_root: Path,
    revision: str,
    model_id: str,
    model_revision: str,
    retriever: Any,
    load_in_4bit: bool,
    shared: Tuple[Any, Any] | None,
) -> Dict[str, Any]:
    paths = INPUTS[revision]
    kwargs: Dict[str, Any] = {
        "framework_version": revision,
        "model_id": model_id,
        "model_revision": model_revision,
        "retriever_instance": retriever,
        "ccs_path": str(repo_root / paths["ccs"]),
        "odp_registry_path": str(repo_root / paths["odp_registry"]),
        "use_qur": False,
        "doc_filter_mode": "prefer_smt_keep_params",
        "load_in_4bit": bool(load_in_4bit),
        "resolution_policy": "ASK",
        "verify_strict_extras": False,
        "verify_strict_verbatim": True,
        "verify_strict_version": False,
    }
    if shared is not None:
        kwargs["shared_model"], kwargs["shared_tokenizer"] = shared
    return kwargs


def read_contract_csv(path: Path) -> Dict[str, Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {str(row["query_id"]): dict(row) for row in csv.DictReader(handle)}


def exact_mcnemar(left_only: int, right_only: int) -> float:
    discordant = int(left_only) + int(right_only)
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(left_only, right_only) + 1))
    return min(1.0, 2.0 * tail / (2.0**discordant))


def aggregate_selector_rows(
    *,
    rows: Mapping[str, Mapping[str, str]],
    gold_rows: Mapping[str, Mapping[str, str]],
    normalize_odp_id: Any,
) -> Dict[str, Any]:
    query_ids = sorted(rows, key=lambda value: (0, int(value)) if value.isdigit() else (1, value))
    per_row: List[Dict[str, Any]] = []
    for query_id in query_ids:
        row = rows[query_id]
        gold = gold_rows[query_id]
        contract = json.loads(str(row.get("contract_json", "") or "{}"))
        metrics = json.loads(str(row.get("verifier_metrics_json", "") or "{}"))
        gold_ids = {item.lower() for item in listish(gold.get("gold_control_path", ""))}
        selected_ids = {
            item.lower() for item in listish(row.get("selected_source_ids", ""))
        }
        gold_odps = {
            normalized
            for item in listish(gold.get("odp_required", ""))
            if (normalized := normalize_odp_id(item))
        }
        generated_odps = {
            normalized
            for item in listish(row.get("odp_required_list", ""))
            if (normalized := normalize_odp_id(item))
        }
        status = str(row.get("status", "") or "")
        per_row.append(
            {
                "query_id": query_id,
                "strict_pass": csv_bool(row.get("verifier_pass")),
                "runtime_pass": csv_bool(row.get("contract_validity_pass")),
                "full_gold_clause_coverage": csv_bool(row.get("doc_full_recall")),
                "right_control": csv_bool(row.get("control_hit_any")),
                "gold_clause_precision": (
                    len(gold_ids & selected_ids) / len(selected_ids) if selected_ids else 0.0
                ),
                "gold_clause_recall": float(metrics.get("doc_recall", 0.0) or 0.0),
                "selected_clause_count": len(selected_ids),
                "additional_clause_count": len(selected_ids - gold_ids),
                "answer_word_count": len(str(contract.get("answer_text", "") or "").split()),
                "status": status,
                "gold_has_odp": bool(gold_odps),
                "predicted_params_required": status == "PARAMS_REQUIRED",
                "exact_odp_list": gold_odps == generated_odps,
            }
        )
    n = len(per_row)
    gold_odp_rows = [row for row in per_row if row["gold_has_odp"]]
    gold_non_odp_rows = [row for row in per_row if not row["gold_has_odp"]]
    predicted_positive = [row for row in per_row if row["predicted_params_required"]]

    def count_rate(field: str, subset: Sequence[Mapping[str, Any]] = per_row) -> Dict[str, Any]:
        count = sum(bool(row[field]) for row in subset)
        return {
            "count": count,
            "rate": count / len(subset) if subset else float("nan"),
            "n": len(subset),
        }

    return {
        "n_questions": n,
        "strict_pass": count_rate("strict_pass"),
        "runtime_contract_pass": count_rate("runtime_pass"),
        "full_gold_clause_coverage": count_rate("full_gold_clause_coverage"),
        "right_governing_control": count_rate("right_control"),
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
        "status_counts": dict(sorted(Counter(str(row["status"]) for row in per_row).items())),
        "odp_against_author_labels": {
            "gold_odp_rows": len(gold_odp_rows),
            "params_required_sensitivity": count_rate(
                "predicted_params_required", gold_odp_rows
            ),
            "exact_odp_list_agreement": count_rate("exact_odp_list", gold_odp_rows),
            "gold_non_odp_rows": len(gold_non_odp_rows),
            "specificity": {
                "count": sum(
                    not bool(row["predicted_params_required"]) for row in gold_non_odp_rows
                ),
                "rate": (
                    sum(
                        not bool(row["predicted_params_required"])
                        for row in gold_non_odp_rows
                    )
                    / len(gold_non_odp_rows)
                    if gold_non_odp_rows
                    else float("nan")
                ),
                "n": len(gold_non_odp_rows),
            },
            "status_precision": {
                "count": sum(bool(row["gold_has_odp"]) for row in predicted_positive),
                "rate": (
                    sum(bool(row["gold_has_odp"]) for row in predicted_positive)
                    / len(predicted_positive)
                    if predicted_positive
                    else float("nan")
                ),
                "n_predicted_params_required": len(predicted_positive),
            },
            "boundary": (
                "These ODP sensitivity, specificity, and precision values use the author labels. "
                "They remain provisional until the blinded independent annotation is returned."
            ),
        },
        "per_row": per_row,
    }


def summarize_completed_run(
    *,
    output_dir: Path,
    adaptive_rows: Mapping[str, Mapping[str, Mapping[str, str]]],
    gold_rows: Mapping[str, Mapping[str, Mapping[str, str]]],
    widths: Sequence[int],
    revisions: Sequence[str],
    normalize_odp_id: Any,
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "strict_pass_definition": (
            "The existing gold-based citation-contract endpoint: full expected-clause coverage, "
            "source/revision/verbatim validity, and ODP/status consistency. It permits extra evidence."
        ),
        "configurations": {},
        "pairwise_strict_pass": {},
        "interpretation_boundary": (
            "Gate width is the only changed factor. ODP operating characteristics use author labels "
            "and are provisional pending blinded independent annotation."
        ),
    }
    row_sets: Dict[Tuple[str, str], Dict[str, Dict[str, str]]] = {}
    for revision in revisions:
        row_sets[(revision, "adaptive_v3")] = dict(adaptive_rows[revision])
        aggregate = aggregate_selector_rows(
            rows=adaptive_rows[revision],
            gold_rows=gold_rows[revision],
            normalize_odp_id=normalize_odp_id,
        )
        aggregate.pop("per_row", None)
        summary["configurations"][f"{revision}_adaptive_v3"] = aggregate
        for width in widths:
            path = output_dir / "contracts" / f"top{width}_{revision}_compliancegpt.csv"
            if not path.is_file():
                raise FileNotFoundError(f"Completed contract file is missing: {path}")
            rows = read_contract_csv(path)
            if len(rows) != EXPECTED_ROWS[revision]:
                raise AssertionError(f"Incomplete contract output: {path}")
            row_sets[(revision, f"top{width}")] = rows
            aggregate = aggregate_selector_rows(
                rows=rows,
                gold_rows=gold_rows[revision],
                normalize_odp_id=normalize_odp_id,
            )
            aggregate.pop("per_row", None)
            summary["configurations"][f"{revision}_top{width}"] = aggregate

    comparisons = [("adaptive_v3", "top1")]
    comparisons.extend((f"top{left}", f"top{right}") for left, right in zip(widths, widths[1:]))
    comparisons.extend([("top1", "top5"), ("adaptive_v3", "top5")])
    for revision in revisions:
        for left_name, right_name in comparisons:
            left = row_sets[(revision, left_name)]
            right = row_sets[(revision, right_name)]
            query_ids = sorted(set(left) & set(right))
            left_only = sum(
                csv_bool(left[qid].get("verifier_pass"))
                and not csv_bool(right[qid].get("verifier_pass"))
                for qid in query_ids
            )
            right_only = sum(
                csv_bool(right[qid].get("verifier_pass"))
                and not csv_bool(left[qid].get("verifier_pass"))
                for qid in query_ids
            )
            key = f"{revision}_{left_name}_vs_{right_name}"
            summary["pairwise_strict_pass"][key] = {
                "left_only": left_only,
                "right_only": right_only,
                "exact_mcnemar_two_sided_p": exact_mcnemar(left_only, right_only),
            }
    write_json(output_dir / "summary.json", summary)
    write_summary_markdown(output_dir / "SUMMARY.md", summary, widths, revisions)
    return summary


def _fmt_rate(value: Mapping[str, Any]) -> str:
    return f"{int(value['count'])}/{int(value['n'])} ({float(value['rate']):.3f})"


def write_summary_markdown(
    path: Path,
    summary: Mapping[str, Any],
    widths: Sequence[int],
    revisions: Sequence[str],
) -> None:
    lines = [
        "# RQ2 Control Gate Width Sensitivity",
        "",
        f"Result identity: `{RESULT_ID}`",
        "",
        "The fixed-width sweep changes only the number of ranked controls admitted to the shared 24-record evidence window. The released adaptive gate is shown as an unchanged reference.",
        "",
    ]
    for revision in revisions:
        lines.extend(
            [
                f"## {revision.upper()}",
                "",
                "| Gate | Strict pass | Full clause coverage | Mean clause precision | Mean selected clauses | ODP sensitivity* | ODP specificity* |",
                "|---|---:|---:|---:|---:|---:|---:|",
            ]
        )
        names = ["adaptive_v3"] + [f"top{width}" for width in widths]
        for name in names:
            metrics = dict(summary["configurations"][f"{revision}_{name}"])
            odp = dict(metrics["odp_against_author_labels"])
            lines.append(
                "| "
                + name.replace("adaptive_v3", "Adaptive v3").replace("top", "Top ")
                + f" | {_fmt_rate(metrics['strict_pass'])}"
                + f" | {_fmt_rate(metrics['full_gold_clause_coverage'])}"
                + f" | {float(metrics['mean_gold_clause_precision']):.3f}"
                + f" | {float(metrics['selected_clause_count']['mean']):.2f}"
                + f" | {_fmt_rate(odp['params_required_sensitivity'])}"
                + f" | {_fmt_rate(odp['specificity'])} |"
            )
        lines.extend(
            [
                "",
                "*ODP operating characteristics use the author labels and remain provisional until the blinded independent annotation is returned.*",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation boundary",
            "",
            str(summary["strict_pass_definition"]),
            "",
            str(summary["interpretation_boundary"]),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_preflight_markdown(path: Path, preflight: Mapping[str, Any], widths: Sequence[int]) -> None:
    lines = [
        "# Control Gate Width Prepared Context Audit",
        "",
        "This is a deterministic evidence-window opportunity audit. It does not contain selector outputs and is not the completed sensitivity result.",
        "",
    ]
    for revision in ("rev5", "rev4"):
        lines.extend(
            [
                f"## {revision.upper()}",
                "",
                "| Gate | Full gold-clause opportunity | Mean window recall | Mean window precision | Mean records | Mean effective controls |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for name in ["adaptive_v3"] + [f"top{width}" for width in widths]:
            value = preflight["configurations"][f"{revision}_{name}"]
            label = name.replace("adaptive_v3", "Adaptive v3").replace("top", "Top ")
            lines.append(
                f"| {label}"
                f" | {value['full_gold_clause_coverage_count']}/{value['n']} ({value['full_gold_clause_coverage_rate']:.3f})"
                f" | {value['mean_gold_clause_recall']:.3f}"
                f" | {value['mean_gold_clause_precision']:.3f}"
                f" | {value['window_record_count']['mean']:.2f}"
                f" | {value['effective_window_width']['mean']:.2f} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    archive_path = args.frozen_archive.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    widths = validate_registered_design(args.widths)
    revisions = validate_registered_runtime(
        revisions=args.revisions,
        model_id=str(args.model_id),
        model_revision=str(args.model_revision),
        load_in_4bit=not args.no_4bit,
    )
    verify_inputs(repo_root, archive_path, revisions)
    sys.path.insert(0, str(repo_root / "src"))

    from answerer_comparison.matched_window_runner import (
        FrozenCCSRetriever,
        run_prepared_contexts,
        validate_prepared_context,
    )
    from compliancegpt.generator.verifier.verifier import normalize_odp_id
    from compliancegpt.pipeline.evidence_window import (
        assert_same_evidence_window,
        build_evidence_window,
        evidence_window_manifest,
        select_allowed_controls,
    )
    from compliancegpt.pipeline.pipeline import (
        ComplianceGPTPipeline,
        _apply_doc_filter_mode,
        _filter_docs_to_controls,
        normalize_control_id,
    )

    source_contexts, adaptive_rows, archive_manifest = load_source_archive(
        archive_path,
        revisions,
        validate_prepared_context,
    )
    helpers = {
        "normalize_control_id": normalize_control_id,
        "build_evidence_window": build_evidence_window,
        "evidence_window_manifest": evidence_window_manifest,
        "filter_docs_to_controls": _filter_docs_to_controls,
        "apply_doc_filter_mode": _apply_doc_filter_mode,
        "validate_prepared_context": validate_prepared_context,
    }
    context_grid, context_manifest = prepare_context_grid(
        source_contexts=source_contexts,
        widths=widths,
        revisions=revisions,
        output_dir=output_dir,
        helpers=helpers,
    )
    runtime_replay = validate_fixed_width_runtime_replay(
        grid=context_grid,
        widths=widths,
        revisions=revisions,
        select_allowed_controls=select_allowed_controls,
        normalize_control_id=normalize_control_id,
        build_evidence_window=build_evidence_window,
        assert_same_evidence_window=assert_same_evidence_window,
        filter_docs_to_controls=_filter_docs_to_controls,
        apply_doc_filter_mode=_apply_doc_filter_mode,
    )
    write_json(output_dir / "manifests" / "runtime_window_replay.json", runtime_replay)
    write_json(output_dir / "manifests" / "source_archive.json", archive_manifest)
    gold_rows = {
        revision: load_gold_rows_simple(
            repo_root / INPUTS[revision]["gold"],
            EXPECTED_ROWS[revision],
        )
        for revision in revisions
    }
    preflight = context_preflight(
        grid=context_grid,
        source_contexts=source_contexts,
        gold_rows=gold_rows,
        widths=widths,
        revisions=revisions,
        output_dir=output_dir,
    )
    write_preflight_markdown(output_dir / "PREPARED_CONTEXTS.md", preflight, widths)
    config = load_or_create_run_config(
        output_dir=output_dir,
        repo_root=repo_root,
        archive_manifest=archive_manifest,
        context_manifest=context_manifest,
        widths=widths,
        revisions=revisions,
        model_id=str(args.model_id),
        model_revision=str(args.model_revision),
        load_in_4bit=not args.no_4bit,
    )
    if args.prepare_only:
        print(f"Prepared and audited {len(widths) * sum(EXPECTED_ROWS[r] for r in revisions)} contexts.")
        print(f"Output: {output_dir}")
        return

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    require_gpu()
    config["determinism"] = configure_determinism()
    config["runtime_started_on"] = platform.platform()
    write_json(output_dir / "run_config.json", config)

    shared: Tuple[Any, Any] | None = None
    run_manifests: Dict[str, Any] = {}
    for revision in revisions:
        frozen_retriever = FrozenCCSRetriever.from_jsonl(repo_root / INPUTS[revision]["ccs"])
        pipeline = ComplianceGPTPipeline(
            **pipeline_kwargs(
                repo_root=repo_root,
                revision=revision,
                model_id=str(args.model_id),
                model_revision=str(args.model_revision),
                retriever=frozen_retriever,
                load_in_4bit=not args.no_4bit,
                shared=shared,
            )
        )
        if shared is None:
            shared = (pipeline.model, pipeline.tokenizer)
        for width in widths:
            key = f"top{width}_{revision}"
            output_csv = output_dir / "contracts" / f"{key}_compliancegpt.csv"
            gate_runtime = configure_fixed_width_pipeline(pipeline, width)
            run_manifest = run_prepared_contexts(
                pipeline=pipeline,
                contexts=context_grid[(width, revision)],
                gold_rows_by_id=gold_rows[revision],
                system_name=f"compliancegpt_{RESULT_ID}_top{width}",
                output_csv=output_csv,
                resume=True,
                progress_every=1,
            )
            run_manifest["gate_runtime"] = gate_runtime
            run_manifests[key] = run_manifest
            write_json(output_dir / "manifests" / "runs.json", run_manifests)
        del pipeline, frozen_retriever
        gc.collect()
        try:
            import torch

            torch.cuda.empty_cache()
        except Exception:
            pass

    summarize_completed_run(
        output_dir=output_dir,
        adaptive_rows=adaptive_rows,
        gold_rows=gold_rows,
        widths=widths,
        revisions=revisions,
        normalize_odp_id=normalize_odp_id,
    )
    archive = Path(shutil.make_archive(str(output_dir), "zip", root_dir=output_dir))
    print(f"Completed {RESULT_ID}: {output_dir}")
    print(f"Result archive: {archive}")


if __name__ == "__main__":
    main()
