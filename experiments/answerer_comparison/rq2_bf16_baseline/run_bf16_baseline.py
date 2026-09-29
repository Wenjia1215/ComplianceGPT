#!/usr/bin/env python3
"""Run Batch 5B: the Rev. 4 free-form baseline in true BF16.

The registered study changes one factor from the frozen RQ2 v3 comparison:
the Qwen2.5-7B generative baseline is loaded in bfloat16 instead of 4-bit.
The model revision, prompt, deterministic decoding, 36 Rev. 4 questions,
ordered evidence windows, ODP policy, and offline verifier stay fixed.
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
import tarfile
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple


RESULT_ID = "rq2_bf16_baseline_v1"
SCHEMA_VERSION = "compliancegpt-rq2-bf16-baseline-v1"
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
FROZEN_SOURCE_COMMIT = "be862bcadfa61b474d795303e01ce9394909fdcc"
FROZEN_ARCHIVE_SHA256 = "56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328"
EXPECTED_ROWS = 36
EXPECTED_CONTEXT_SCHEMA = "compliancegpt-rq2-prepared-context"
EXPECTED_PROMPT_SHA256 = "91ba0d840befd5517fbec7595f640333bcb8df8e63301e80552dad841744fdef"

DEFAULT_ARCHIVE = (
    "experiments/answerer_comparison/rq2_matched/results_v3/"
    "compliancegpt_rq2_matched_v3.zip"
)
INPUTS = {
    "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl",
    "gold": "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv",
    "odp_registry": "data/ODP/rev4/odp_registry_rev4.json",
}
INPUT_HASHES = {
    "ccs": "500bb5d1f265080752710c2f0ae84b8044b67a1e2118cd5e166353b6fc3ab726",
    "gold": "80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2",
    "odp_registry": "399509be44e720609efa25c0e39646fa2f27b20a0a20248435b9ae9926dbac7c",
}
ARCHIVE_MEMBERS = {
    "contexts/rev4_prepared_contexts.jsonl": (
        "4f1ca834993a34c22bb4b61fa9a984d32382b5e84e3473656a22af688412d7a6"
    ),
    "contracts/rev4_generative_baseline.csv": (
        "cf891ddd0710125e5d37b43913166f0e7cef50426605133d87915229a90f53b5"
    ),
    "contracts/rev4_compliancegpt.csv": (
        "cb8d49cdff4b1ebcd68f0010b4fbecafd457352cb9e963856b03ef1a0aae50f9"
    ),
    "summaries/rev4_paired_summary.json": (
        "a871fb8ab6d604c8a2ab4c09af2875f29b74d786931c942b1898e16fef3d70c5"
    ),
    "run_config.json": "9f87e66c19c8a066aa6d87350eca2b959a3c2315bc7b602eac75f3f13b23acf5",
}
FROZEN_CODE_HASHES = {
    "src/answerer_comparison/matched_window_runner.py": (
        "0dbc6c33bcf993a113e5cd9f63e10399b9f245f026e634c808ca6b32ea2a23df"
    ),
    "src/compliancegpt/pipeline/evidence_window.py": (
        "0e098761074a7ce949adf0d0cf2d89e3e2bb34517b5089793564df66ac816b3d"
    ),
    "src/compliancegpt/pipeline/pipeline.py": (
        "2f5cbaa24e3746d5815e76b2d3553491b3ccfc917ab0b4e22e1886c42d75d181"
    ),
    "src/compliancegpt/retriever/retriever_s7.py": (
        "98abe0c6ef21d4328de5e3a3cf83e6a7750f1c7da2c3ae17dd283be1dd2e988c"
    ),
    "src/generative_answerer/pipeline.py": (
        "10034299b3aea6b608b87625ccc04a69d5ee37870f0d62bb6cc30a043f525be1"
    ),
    "src/compliancegpt/generator/generator.py": (
        "80bd0ac08d1dafb299ad6badb9a080f0a3f7ce4a266e9b9583f736e8f4b49c6c"
    ),
    "src/generative_answerer/generator.py": (
        "dd31b57f4f6a9db343c023e01b5dd2953bc8aa869af4c3f113dbab5f874ef827"
    ),
    "src/compliancegpt/generator/verifier/verifier.py": (
        "6f5a16a47b94e0c17d756f0de58ecf6663bc7e7dd006b9ba10445c1e0210d6af"
    ),
    "src/compliancegpt/generator/citation_contract_80053.md": (
        "7859aef90da277b63385265b552594f76a03d91848cb9967bd79d5bf3bc24d54"
    ),
}
GENERATION_SETTINGS = {
    "do_sample": False,
    "num_beams": 1,
    "repetition_penalty": 1.05,
    "max_new_tokens": 640,
    "max_parse_retries": 2,
}


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frozen-archive", type=Path, default=None)
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Verify and extract the registered inputs without loading a model.",
    )
    return parser.parse_args()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)


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


def git_blob(repo_root: Path, commit: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo_root,
        stderr=subprocess.PIPE,
    )


def verify_frozen_source(repo_root: Path) -> Dict[str, str]:
    subprocess.run(
        ["git", "cat-file", "-e", f"{FROZEN_SOURCE_COMMIT}^{{commit}}"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    actual: Dict[str, str] = {}
    for relative, expected in FROZEN_CODE_HASHES.items():
        value = sha256_bytes(git_blob(repo_root, FROZEN_SOURCE_COMMIT, relative))
        if value != expected:
            raise RuntimeError(
                f"Frozen source mismatch for {relative}: expected {expected}, got {value}"
            )
        actual[relative] = value
    return actual


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
        expected = INPUT_HASHES[name]
        if value != expected:
            raise RuntimeError(
                f"Registered {name} input changed: expected {expected}, got {value}"
            )
        input_hashes[name] = value
    return {
        "archive_sha256": archive_hash,
        "input_hashes": input_hashes,
        "frozen_source_hashes": verify_frozen_source(repo_root),
    }


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


def _gold_key_paths(value: Any, path: str = "") -> List[str]:
    found: List[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.strip().lower().startswith("gold"):
                found.append(child_path)
            found.extend(_gold_key_paths(child, child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            found.extend(_gold_key_paths(child, f"{path}[{index}]"))
    return found


def validate_context(context: Mapping[str, Any]) -> None:
    if str(context.get("schema_version", "")) != EXPECTED_CONTEXT_SCHEMA:
        raise ValueError("Unexpected frozen prepared-context schema.")
    if str(context.get("framework_version", "")) != "rev4":
        raise ValueError("Batch 5B accepts Rev. 4 contexts only.")
    if not str(context.get("query_id", "") or "").strip():
        raise ValueError("Prepared context has no query id.")
    if not str(context.get("question", "") or "").strip():
        raise ValueError("Prepared context has no question.")
    forbidden = _gold_key_paths(context)
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
    contexts = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    if len(contexts) != EXPECTED_ROWS:
        raise AssertionError(f"Expected {EXPECTED_ROWS} Rev. 4 contexts, found {len(contexts)}")
    for context in contexts:
        validate_context(context)
    query_ids = [str(context["query_id"]) for context in contexts]
    if len(query_ids) != len(set(query_ids)):
        raise AssertionError("Frozen Rev. 4 contexts contain duplicate query ids.")
    return contexts


def extract_registered_archive(
    *, archive_path: Path, output_dir: Path
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    destinations = {
        "contexts/rev4_prepared_contexts.jsonl": (
            output_dir / "contexts" / "rev4_prepared_contexts.jsonl"
        ),
        "contracts/rev4_generative_baseline.csv": (
            output_dir / "references" / "rev4_generative_baseline_4bit.csv"
        ),
        "contracts/rev4_compliancegpt.csv": (
            output_dir / "references" / "rev4_compliancegpt_4bit.csv"
        ),
        "summaries/rev4_paired_summary.json": (
            output_dir / "references" / "rev4_frozen_paired_summary.json"
        ),
        "run_config.json": output_dir / "references" / "rq2_v3_run_config.json",
    }
    manifest: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
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
    context_data = (output_dir / "contexts" / "rev4_prepared_contexts.jsonl").read_bytes()
    contexts = parse_contexts(context_data)
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
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows: Dict[str, Dict[str, str]] = {}
        for row in csv.DictReader(handle):
            query_id = str(row.get("query_id", "") or "").strip()
            if not query_id or query_id in rows:
                raise ValueError(f"Missing or duplicate query id in {path}: {query_id!r}")
            rows[query_id] = dict(row)
    return rows


def load_gold_rows(path: Path) -> Dict[str, Dict[str, str]]:
    rows: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            query_id = str(row.get("query_id") or row.get("ID") or row.get("id") or "").strip()
            if not query_id or query_id in rows:
                raise ValueError(f"Missing or duplicate gold query id in {path}: {query_id!r}")
            rows[query_id] = dict(row)
    if len(rows) != EXPECTED_ROWS:
        raise AssertionError(f"Expected {EXPECTED_ROWS} gold rows, found {len(rows)}")
    return rows


def has_model_checkpoints(output_dir: Path) -> bool:
    path = output_dir / "contracts" / "rev4_generative_baseline_bf16.csv"
    if not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            return next(reader, None) is not None
    except Exception:
        return True


def runner_code_manifest(repo_root: Path) -> Dict[str, str]:
    paths = [
        "experiments/answerer_comparison/rq2_bf16_baseline/run_bf16_baseline.py",
        "experiments/answerer_comparison/rq2_matched/requirements-colab.txt",
    ]
    manifest: Dict[str, str] = {}
    for relative in paths:
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Batch 5B code input is missing: {path}")
        manifest[relative] = sha256_file(path)
    return manifest


def load_or_create_run_config(
    *,
    repo_root: Path,
    output_dir: Path,
    source_manifest: Mapping[str, Any],
    verified: Mapping[str, Any],
) -> Dict[str, Any]:
    code_files = runner_code_manifest(repo_root)
    expected: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "framework_version": "rev4",
        "n_questions": EXPECTED_ROWS,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "precision": "bfloat16",
        "load_in_4bit": False,
        "frozen_source_commit": FROZEN_SOURCE_COMMIT,
        "frozen_source_hashes": dict(verified["frozen_source_hashes"]),
        "source_archive_sha256": str(source_manifest["archive_sha256"]),
        "source_member_hashes": {
            key: str(value["sha256"])
            for key, value in dict(source_manifest["members"]).items()
        },
        "input_hashes": dict(verified["input_hashes"]),
        "prompt_sha256": EXPECTED_PROMPT_SHA256,
        "generation_settings": dict(GENERATION_SETTINGS),
        "experiment_code_files": code_files,
        "experiment_code_sha256": canonical_sha256(code_files),
        "changed_factor": "generative baseline weight precision only (4-bit -> bfloat16)",
        "retrieval_policy": "frozen RQ2 v3 Rev. 4 contexts; no live retrieval",
        "gold_policy": "gold excluded from model-visible contexts and used only by verifier",
        "frozen_factors": [
            "Qwen2.5-7B-Instruct model identity and immutable revision",
            "free-form generative baseline system and user prompts",
            "deterministic decoding and parse-retry settings",
            "36 Rev. 4 questions and ordered evidence windows",
            "ASK ODP policy and offline verifier",
        ],
    }
    path = output_dir / "run_config.json"
    current_commit = git_head(repo_root)
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
        for key, value in expected.items():
            if stored.get(key) != value:
                if has_model_checkpoints(output_dir):
                    raise RuntimeError(
                        f"Batch 5B configuration changed for {key!r} after model rows "
                        "were checkpointed. Use a new output directory."
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
    if has_model_checkpoints(output_dir):
        raise RuntimeError(
            "Model checkpoints exist without a Batch 5B run_config.json. "
            "Use a new output directory rather than adopting unregistered rows."
        )
    config = {
        **expected,
        "repo_commit": current_commit,
        "repo_commits_observed": [current_commit] if current_commit else [],
    }
    write_json(path, config)
    return config


def write_preflight(output_dir: Path, contexts: Sequence[Mapping[str, Any]]) -> None:
    record_counts = [len(list(context.get("evidence_window", []) or [])) for context in contexts]
    preflight = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "scope": "gold-free frozen-context integrity audit; no model inference",
        "framework_version": "rev4",
        "context_rows": len(contexts),
        "context_jsonl_sha256": sha256_file(
            output_dir / "contexts" / "rev4_prepared_contexts.jsonl"
        ),
        "distinct_context_hashes": len({str(c["context_sha256"]) for c in contexts}),
        "distinct_window_hashes": len(
            {
                str((c.get("evidence_window_manifest") or {}).get("sha256", ""))
                for c in contexts
            }
        ),
        "window_record_count": {
            "min": min(record_counts),
            "mean": statistics.fmean(record_counts),
            "max": max(record_counts),
        },
    }
    write_json(output_dir / "preflight" / "summary.json", preflight)
    text = "\n".join(
        [
            "# Batch 5B Prepared-Context Audit",
            "",
            "This is a gold-free integrity check, not a completed BF16 result.",
            "",
            f"- Result identity: `{RESULT_ID}`",
            f"- Frozen Rev. 4 contexts: {len(contexts)}",
            f"- Distinct context hashes: {preflight['distinct_context_hashes']}",
            f"- Distinct evidence-window hashes: {preflight['distinct_window_hashes']}",
            f"- Context SHA-256: `{preflight['context_jsonl_sha256']}`",
            "- Model inference performed: no",
            "",
        ]
    )
    (output_dir / "PREPARED_CONTEXTS.md").write_text(text, encoding="utf-8")


def extract_frozen_source(repo_root: Path, destination: Path) -> Path:
    archive = subprocess.check_output(
        ["git", "archive", "--format=tar", FROZEN_SOURCE_COMMIT, "src"],
        cwd=repo_root,
        stderr=subprocess.PIPE,
    )
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        for member in tar.getmembers():
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"Unsafe path in frozen source archive: {member.name}")
        if sys.version_info >= (3, 12):
            tar.extractall(destination, filter="data")
        else:  # pragma: no cover - retained for Python 3.11 compatibility.
            tar.extractall(destination)
    source_root = destination / "src"
    if not source_root.is_dir():
        raise RuntimeError("Frozen source extraction did not produce src/.")
    for relative, expected in FROZEN_CODE_HASHES.items():
        actual = sha256_file(destination / relative)
        if actual != expected:
            raise RuntimeError(f"Extracted frozen source mismatch: {relative}")
    return source_root


def configure_determinism(seed: int = 42) -> Dict[str, Any]:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    return {
        "seed": seed,
        "torch_deterministic_algorithms": True,
        "cudnn_benchmark": False,
        "cudnn_deterministic": True,
    }


def require_bf16_gpu(torch_module: Any) -> Dict[str, Any]:
    torch = torch_module
    if not torch.cuda.is_available():
        raise RuntimeError(
            "Batch 5B requires a CUDA GPU with native BF16 support. In Colab choose an "
            "A100 GPU (preferred) or another Ampere-or-newer GPU with enough memory."
        )
    if not bool(torch.cuda.is_bf16_supported()):
        raise RuntimeError(
            f"{torch.cuda.get_device_name(0)} does not provide the native BF16 path required "
            "by Batch 5B. T4 is not valid; select A100 (preferred) or L4."
        )
    props = torch.cuda.get_device_properties(0)
    capability = tuple(int(value) for value in torch.cuda.get_device_capability(0))
    return {
        "device_name": torch.cuda.get_device_name(0),
        "compute_capability": list(capability),
        "total_memory_bytes": int(props.total_memory),
        "native_bf16_supported": True,
        "cuda_version": str(torch.version.cuda or ""),
        "torch_version": str(torch.__version__),
    }


def validate_bf16_model(model: Any, torch_module: Any) -> Dict[str, Any]:
    torch = torch_module
    dtype_counts: Counter[str] = Counter()
    parameter_counts: Counter[str] = Counter()
    for parameter in model.parameters():
        if parameter.is_floating_point():
            key = str(parameter.dtype)
            dtype_counts[key] += 1
            parameter_counts[key] += int(parameter.numel())
    if set(dtype_counts) != {str(torch.bfloat16)}:
        raise RuntimeError(
            f"Expected every floating model parameter in torch.bfloat16; found {dict(dtype_counts)}"
        )
    quantization_flags = {
        "is_loaded_in_4bit": bool(getattr(model, "is_loaded_in_4bit", False)),
        "is_loaded_in_8bit": bool(getattr(model, "is_loaded_in_8bit", False)),
        "is_quantized": bool(getattr(model, "is_quantized", False)),
        "has_hf_quantizer": getattr(model, "hf_quantizer", None) is not None,
        "has_quantization_config": (
            getattr(getattr(model, "config", None), "quantization_config", None) is not None
        ),
    }
    if any(quantization_flags.values()):
        raise RuntimeError(f"Quantization was detected in the BF16 model: {quantization_flags}")
    device_map = dict(getattr(model, "hf_device_map", {}) or {})
    offloaded = [
        str(device)
        for device in device_map.values()
        if str(device).lower() in {"cpu", "disk"}
    ]
    if offloaded:
        raise RuntimeError(f"BF16 model was offloaded away from CUDA: {offloaded}")
    return {
        "floating_parameter_tensor_dtypes": dict(sorted(dtype_counts.items())),
        "floating_parameter_counts_by_dtype": dict(sorted(parameter_counts.items())),
        "quantization_flags": quantization_flags,
        "hf_device_map": {str(key): str(value) for key, value in device_map.items()},
        "model_memory_footprint_bytes": int(model.get_memory_footprint()),
    }


def package_versions() -> Dict[str, str]:
    from importlib.metadata import version

    versions = {
        name: version(name)
        for name in (
            "accelerate",
            "huggingface-hub",
            "numpy",
            "torch",
            "transformers",
        )
    }
    versions["python"] = platform.python_version()
    return versions


def resolve_tokenizer_revision(tokenizer: Any, requested_revision: str) -> Dict[str, str]:
    """Validate tokenizer revision metadata, with an explicit immutable-request fallback.

    Some Transformers tokenizer classes do not preserve ``_commit_hash`` in
    ``init_kwargs`` even when ``from_pretrained`` was called with an immutable
    commit SHA. A present metadata hash remains a hard check. When the field is
    absent, the exact requested SHA is the resolution evidence and is recorded
    as such rather than being mistaken for a mismatch.
    """

    requested = str(requested_revision or "").strip()
    if not requested:
        raise ValueError("An immutable tokenizer revision is required.")
    init_kwargs = dict(getattr(tokenizer, "init_kwargs", {}) or {})
    candidates = [
        str(init_kwargs.get("_commit_hash", "") or "").strip(),
        str(getattr(tokenizer, "_commit_hash", "") or "").strip(),
    ]
    observed = sorted({value for value in candidates if value})
    if any(value != requested for value in observed):
        raise RuntimeError(
            "Tokenizer revision metadata differs from the registered immutable revision: "
            f"requested={requested!r}, observed={observed!r}"
        )
    return {
        "requested_revision": requested,
        "resolved_revision": observed[0] if observed else requested,
        "metadata_commit_hash": observed[0] if observed else "",
        "verification_source": (
            "tokenizer_metadata" if observed else "immutable_from_pretrained_request"
        ),
    }


def load_bf16_model() -> Tuple[Any, Any, Dict[str, Any]]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    gpu = require_bf16_gpu(torch)
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        trust_remote_code=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        trust_remote_code=True,
        device_map="auto",
        dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    )
    model_revision = str(
        getattr(getattr(model, "config", None), "_commit_hash", "") or ""
    ).strip()
    tokenizer_revision_evidence = resolve_tokenizer_revision(tokenizer, MODEL_REVISION)
    tokenizer_revision = tokenizer_revision_evidence["resolved_revision"]
    if model_revision != MODEL_REVISION:
        raise RuntimeError(
            "Resolved model revision differs from the registered immutable revision: "
            f"model={model_revision!r}, expected={MODEL_REVISION!r}"
        )
    precision = {
        "schema_version": SCHEMA_VERSION,
        "precision": "bfloat16",
        "model_id": MODEL_ID,
        "model_resolved_revision": model_revision,
        "tokenizer_resolved_revision": tokenizer_revision,
        "tokenizer_revision_evidence": tokenizer_revision_evidence,
        "gpu": gpu,
        "packages": package_versions(),
        **validate_bf16_model(model, torch),
    }
    return model, tokenizer, precision


def validate_generation_contract(pipeline: Any, build_system_prompt: Any) -> Dict[str, Any]:
    prompt = str(build_system_prompt())
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    if prompt_hash != EXPECTED_PROMPT_SHA256:
        raise RuntimeError(
            f"Frozen generative prompt changed: expected {EXPECTED_PROMPT_SHA256}, got {prompt_hash}"
        )
    answerer = pipeline.generative_answerer
    cfg = answerer._deterministic_cfg
    observed = {
        "do_sample": bool(cfg.do_sample),
        "num_beams": int(cfg.num_beams),
        "repetition_penalty": float(cfg.repetition_penalty),
        "max_new_tokens": int(cfg.max_new_tokens),
        "max_parse_retries": int(answerer.max_parse_retries),
    }
    if observed != GENERATION_SETTINGS:
        raise RuntimeError(
            f"Frozen generation settings changed: expected {GENERATION_SETTINGS}, got {observed}"
        )
    return {"prompt_sha256": prompt_hash, "generation_settings": observed}


def validate_or_write_precision_manifest(
    output_dir: Path, precision: Mapping[str, Any]
) -> None:
    path = output_dir / "manifests" / "bf16_runtime.json"
    if not path.exists() and has_model_checkpoints(output_dir):
        raise RuntimeError(
            "Model checkpoints exist without the registered BF16 runtime manifest. "
            "Use a new output directory."
        )
    if path.exists() and has_model_checkpoints(output_dir):
        stored = json.loads(path.read_text(encoding="utf-8"))
        keys = (
            "precision",
            "model_id",
            "model_resolved_revision",
            "tokenizer_resolved_revision",
            "tokenizer_revision_evidence",
            "packages",
            "floating_parameter_tensor_dtypes",
            "floating_parameter_counts_by_dtype",
            "quantization_flags",
        )
        for key in keys:
            if stored.get(key) != precision.get(key):
                raise RuntimeError(
                    f"BF16 runtime changed for {key!r} after checkpoints were written. "
                    "Use a new output directory."
                )
        stored_gpu = dict(stored.get("gpu", {}) or {})
        current_gpu = dict(precision.get("gpu", {}) or {})
        for key in (
            "device_name",
            "compute_capability",
            "native_bf16_supported",
            "cuda_version",
            "torch_version",
        ):
            if stored_gpu.get(key) != current_gpu.get(key):
                raise RuntimeError(
                    f"GPU runtime changed for {key!r} after checkpoints were written. "
                    "Use a new output directory."
                )
    write_json(path, dict(precision))


def csv_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def listish(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []
    parts = [text]
    for delimiter in ("\r\n", "\n", "|", ","):
        expanded: List[str] = []
        for part in parts:
            expanded.extend(part.split(delimiter))
        parts = expanded
    return [part.strip() for part in parts if part.strip()]


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


def aggregate_rows(
    *,
    rows: Mapping[str, Mapping[str, str]],
    gold_rows: Mapping[str, Mapping[str, str]],
    normalize_odp_id: Any,
) -> Dict[str, Any]:
    query_ids = sorted(rows, key=lambda value: (0, int(value)) if value.isdigit() else (1, value))
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
                "strict_pass": csv_bool(row.get("verifier_pass")),
                "runtime_pass": csv_bool(row.get("contract_validity_pass")),
                "full_gold_clause_coverage": csv_bool(row.get("doc_full_recall")),
                "right_control": csv_bool(row.get("control_hit_any")),
                "gold_clause_recall": float(metrics.get("doc_recall", 0.0) or 0.0),
                "gold_clause_precision": (
                    len(gold_ids & selected_ids) / len(selected_ids) if selected_ids else 0.0
                ),
                "selected_clause_count": len(selected_ids),
                "additional_clause_count": len(selected_ids - gold_ids),
                "answer_word_count": len(str(contract.get("answer_text", "") or "").split()),
                "status": status,
                "gold_has_odp": bool(gold_odps),
                "predicted_params_required": status == "PARAMS_REQUIRED",
                "exact_odp_list": gold_odps == generated_odps,
            }
        )

    def count_rate(
        field: str, subset: Sequence[Mapping[str, Any]] = per_row
    ) -> Dict[str, Any]:
        count = sum(bool(row[field]) for row in subset)
        return {"count": count, "rate": count / len(subset) if subset else None, "n": len(subset)}

    odp_rows = [row for row in per_row if row["gold_has_odp"]]
    non_odp_rows = [row for row in per_row if not row["gold_has_odp"]]
    predicted = [row for row in per_row if row["predicted_params_required"]]
    return {
        "n_questions": len(per_row),
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
            "gold_odp_rows": len(odp_rows),
            "params_required_sensitivity": count_rate("predicted_params_required", odp_rows),
            "exact_odp_list_agreement": count_rate("exact_odp_list", odp_rows),
            "gold_non_odp_rows": len(non_odp_rows),
            "specificity": {
                "count": sum(not bool(row["predicted_params_required"]) for row in non_odp_rows),
                "rate": (
                    sum(not bool(row["predicted_params_required"]) for row in non_odp_rows)
                    / len(non_odp_rows)
                    if non_odp_rows
                    else None
                ),
                "n": len(non_odp_rows),
            },
            "status_precision": {
                "count": sum(bool(row["gold_has_odp"]) for row in predicted),
                "rate": (
                    sum(bool(row["gold_has_odp"]) for row in predicted) / len(predicted)
                    if predicted
                    else None
                ),
                "n_predicted_params_required": len(predicted),
            },
            "boundary": (
                "These ODP operating characteristics use author labels and remain provisional "
                "until the blinded independent annotation is returned."
            ),
        },
        "per_row": per_row,
    }


def exact_mcnemar(left_only: int, right_only: int) -> float:
    discordant = int(left_only) + int(right_only)
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(left_only, right_only) + 1))
    return min(1.0, 2.0 * tail / (2.0**discordant))


def paired_strict_pass(
    left: Mapping[str, Mapping[str, str]], right: Mapping[str, Mapping[str, str]]
) -> Dict[str, Any]:
    if set(left) != set(right):
        raise AssertionError("Paired outputs have different query-id sets.")
    query_ids = sorted(left)
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
    both = sum(
        csv_bool(left[qid].get("verifier_pass"))
        and csv_bool(right[qid].get("verifier_pass"))
        for qid in query_ids
    )
    return {
        "paired_rows": len(query_ids),
        "left_only": left_only,
        "right_only": right_only,
        "both_pass": both,
        "neither_pass": len(query_ids) - left_only - right_only - both,
        "exact_mcnemar_two_sided_p": exact_mcnemar(left_only, right_only),
    }


def validate_matched_rows(
    bf16: Mapping[str, Mapping[str, str]],
    baseline_4bit: Mapping[str, Mapping[str, str]],
    compliance_4bit: Mapping[str, Mapping[str, str]],
) -> Dict[str, Any]:
    if len(bf16) != EXPECTED_ROWS or set(bf16) != set(baseline_4bit) or set(bf16) != set(compliance_4bit):
        raise AssertionError("Batch 5B and frozen reference query-id sets do not match.")
    mismatches: List[Tuple[str, str, str]] = []
    for query_id in sorted(bf16):
        for label, reference in (
            ("generative_baseline_4bit", baseline_4bit),
            ("compliancegpt_4bit", compliance_4bit),
        ):
            for field in (
                "context_sha256",
                "evidence_window_sha256",
                "model_id",
                "model_requested_revision",
                "model_resolved_revision",
                "tokenizer_resolved_revision",
            ):
                if str(bf16[query_id].get(field, "")) != str(reference[query_id].get(field, "")):
                    mismatches.append((query_id, label, field))
            for field in (
                "model_requested_revision",
                "model_resolved_revision",
                "tokenizer_resolved_revision",
            ):
                if str(reference[query_id].get(field, "")) != MODEL_REVISION:
                    mismatches.append((query_id, label, field))
        for field in (
            "model_requested_revision",
            "model_resolved_revision",
            "tokenizer_resolved_revision",
        ):
            if str(bf16[query_id].get(field, "")) != MODEL_REVISION:
                mismatches.append((query_id, "generative_baseline_bf16", field))
    if mismatches:
        raise AssertionError(f"Matched-input validation failed: {mismatches[:10]}")
    return {
        "paired_rows": EXPECTED_ROWS,
        "context_mismatches": 0,
        "evidence_window_mismatches": 0,
        "model_identity_mismatches": 0,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
    }


def format_rate(value: Mapping[str, Any]) -> str:
    rate = value.get("rate")
    rate_text = "NA" if rate is None else f"{float(rate):.3f}"
    return f"{int(value['count'])}/{int(value['n'])} ({rate_text})"


def write_summary_markdown(path: Path, summary: Mapping[str, Any]) -> None:
    labels = [
        ("generative_baseline_bf16", "Generative baseline, BF16"),
        ("generative_baseline_4bit", "Generative baseline, 4-bit (frozen)"),
        ("compliancegpt_4bit", "ComplianceGPT, 4-bit (frozen)"),
    ]
    lines = [
        "# Batch 5B — Rev. 4 BF16 Generative Baseline",
        "",
        f"Result identity: `{RESULT_ID}`",
        "",
        "Only the free-form baseline's model-weight precision changes from 4-bit to BF16. The model revision, prompt, decoding, questions, ordered evidence windows, ODP policy, and verifier are held fixed.",
        "",
        "| System | Strict pass | Full clause coverage | Runtime contract pass | Mean clause precision | Mean selected clauses | ODP sensitivity* |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label in labels:
        metrics = dict(summary["configurations"][key])
        odp = dict(metrics["odp_against_author_labels"])
        lines.append(
            f"| {label}"
            f" | {format_rate(metrics['strict_pass'])}"
            f" | {format_rate(metrics['full_gold_clause_coverage'])}"
            f" | {format_rate(metrics['runtime_contract_pass'])}"
            f" | {float(metrics['mean_gold_clause_precision']):.3f}"
            f" | {float(metrics['selected_clause_count']['mean']):.2f}"
            f" | {format_rate(odp['params_required_sensitivity'])} |"
        )
    comparisons = dict(summary["paired_strict_pass"])
    lines.extend(
        [
            "",
            "## Paired strict-pass comparisons",
            "",
            "| Comparison (left vs right) | Left only | Right only | Exact McNemar p |",
            "|---|---:|---:|---:|",
        ]
    )
    for key, label in (
        ("bf16_vs_4bit_baseline", "BF16 baseline vs 4-bit baseline"),
        ("bf16_baseline_vs_4bit_compliancegpt", "BF16 baseline vs 4-bit ComplianceGPT"),
    ):
        value = comparisons[key]
        lines.append(
            f"| {label} | {value['left_only']} | {value['right_only']} "
            f"| {float(value['exact_mcnemar_two_sided_p']):.8g} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            str(summary["interpretation_boundary"]),
            "",
            "*ODP operating characteristics use author labels and remain provisional until blinded independent annotation is returned.*",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize_completed_run(
    *, output_dir: Path, gold_rows: Mapping[str, Mapping[str, str]], normalize_odp_id: Any
) -> Dict[str, Any]:
    paths = {
        "generative_baseline_bf16": (
            output_dir / "contracts" / "rev4_generative_baseline_bf16.csv"
        ),
        "generative_baseline_4bit": (
            output_dir / "references" / "rev4_generative_baseline_4bit.csv"
        ),
        "compliancegpt_4bit": output_dir / "references" / "rev4_compliancegpt_4bit.csv",
    }
    rows = {name: read_csv_rows(path) for name, path in paths.items()}
    validation = validate_matched_rows(
        rows["generative_baseline_bf16"],
        rows["generative_baseline_4bit"],
        rows["compliancegpt_4bit"],
    )
    configurations: Dict[str, Any] = {}
    for name, values in rows.items():
        aggregate = aggregate_rows(
            rows=values,
            gold_rows=gold_rows,
            normalize_odp_id=normalize_odp_id,
        )
        aggregate.pop("per_row", None)
        configurations[name] = aggregate
    summary: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "framework_version": "rev4",
        "n_questions": EXPECTED_ROWS,
        "changed_factor": "generative baseline weight precision only (4-bit -> bfloat16)",
        "matched_input_validation": validation,
        "configurations": configurations,
        "paired_strict_pass": {
            "bf16_vs_4bit_baseline": {
                "left": "generative_baseline_bf16",
                "right": "generative_baseline_4bit",
                **paired_strict_pass(
                    rows["generative_baseline_bf16"],
                    rows["generative_baseline_4bit"],
                ),
            },
            "bf16_baseline_vs_4bit_compliancegpt": {
                "left": "generative_baseline_bf16",
                "right": "compliancegpt_4bit",
                **paired_strict_pass(
                    rows["generative_baseline_bf16"],
                    rows["compliancegpt_4bit"],
                ),
            },
        },
        "strict_pass_definition": (
            "The existing gold-based citation-contract endpoint: full expected-clause coverage, "
            "source/revision/verbatim validity, and ODP/status consistency. It permits extra evidence."
        ),
        "interpretation_boundary": (
            "This study isolates model-weight precision within the same Qwen2.5-7B free-form "
            "baseline. It is neither a frontier-model comparison nor a retraining study. A BF16 "
            "change estimates quantization sensitivity on these 36 fixed Rev. 4 rows."
        ),
        "file_hashes": {name: sha256_file(path) for name, path in paths.items()},
    }
    write_json(output_dir / "summary.json", summary)
    write_summary_markdown(output_dir / "SUMMARY.md", summary)
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


def prepare_experiment(
    repo_root: Path, output_dir: Path, archive_path: Path
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, str]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    verified = verify_inputs(repo_root, archive_path)
    contexts, source_manifest = extract_registered_archive(
        archive_path=archive_path, output_dir=output_dir
    )
    load_or_create_run_config(
        repo_root=repo_root,
        output_dir=output_dir,
        source_manifest=source_manifest,
        verified=verified,
    )
    gold_rows = load_gold_rows(repo_root / INPUTS["gold"])
    if {str(context["query_id"]) for context in contexts} != set(gold_rows):
        raise AssertionError("Frozen contexts and registered gold rows have different query ids.")
    for path in (
        output_dir / "references" / "rev4_generative_baseline_4bit.csv",
        output_dir / "references" / "rev4_compliancegpt_4bit.csv",
    ):
        rows = read_csv_rows(path)
        if len(rows) != EXPECTED_ROWS or set(rows) != set(gold_rows):
            raise AssertionError(f"Frozen reference output is incomplete: {path}")
    write_preflight(output_dir, contexts)
    return contexts, gold_rows


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    archive_path = (
        args.frozen_archive.resolve()
        if args.frozen_archive is not None
        else (repo_root / DEFAULT_ARCHIVE).resolve()
    )
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

    contexts, gold_rows = prepare_experiment(repo_root, output_dir, archive_path)
    print(f"Frozen Batch 5B inputs verified: {len(contexts)} Rev. 4 contexts.")
    if args.prepare_only:
        print(f"Prepared-context audit: {output_dir / 'PREPARED_CONTEXTS.md'}")
        print("No model was loaded; this is not a completed Batch 5B result.")
        return

    with tempfile.TemporaryDirectory(prefix="compliancegpt-rq2-bf16-") as temporary:
        frozen_src = extract_frozen_source(repo_root, Path(temporary))
        sys.path.insert(0, str(frozen_src))

        import torch
        from answerer_comparison import matched_window_runner as matched
        from compliancegpt.generator.verifier.verifier import normalize_odp_id
        from generative_answerer.generator import build_system_prompt
        from generative_answerer.pipeline import BaselineGenerativeRAGPipeline

        # The public-release cleanup removed a historical "-v2" label from the
        # archived contexts. The contents and hashes are unchanged. This one
        # compatibility assignment lets the exact frozen runner validate them.
        matched.CONTEXT_SCHEMA = EXPECTED_CONTEXT_SCHEMA

        determinism = configure_determinism()
        model, tokenizer, precision = load_bf16_model()
        precision["determinism"] = determinism
        print(
            f"BF16 model loaded: {precision['gpu']['device_name']} | "
            f"{precision['floating_parameter_tensor_dtypes']}"
        )
        validate_or_write_precision_manifest(output_dir, precision)

        retriever = matched.FrozenCCSRetriever.from_jsonl(repo_root / INPUTS["ccs"])
        pipeline = BaselineGenerativeRAGPipeline(
            framework_version="rev4",
            model_id=MODEL_ID,
            model_revision=MODEL_REVISION,
            shared_model=model,
            shared_tokenizer=tokenizer,
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
        generation_contract = validate_generation_contract(pipeline, build_system_prompt)
        write_json(output_dir / "manifests" / "generation_contract.json", generation_contract)

        run_manifest = matched.run_prepared_contexts(
            pipeline=pipeline,
            contexts=contexts,
            gold_rows_by_id=gold_rows,
            system_name="generative_baseline_bf16",
            output_csv=(
                output_dir / "contracts" / "rev4_generative_baseline_bf16.csv"
            ),
            resume=True,
            progress_every=1,
        )
        run_manifest["precision"] = "bfloat16"
        run_manifest["quantized"] = False
        write_json(output_dir / "manifests" / "run.json", run_manifest)
        summarize_completed_run(
            output_dir=output_dir,
            gold_rows=gold_rows,
            normalize_odp_id=normalize_odp_id,
        )

        del pipeline, retriever, model, tokenizer
        gc.collect()
        torch.cuda.empty_cache()

    write_output_manifest(output_dir)
    archive = Path(
        shutil.make_archive(
            str(output_dir.parent / output_dir.name),
            "zip",
            root_dir=output_dir,
        )
    )
    print(f"Batch 5B completed successfully: {output_dir}")
    print(f"Result archive: {archive}")
    print(f"Result archive SHA-256: {sha256_file(archive)}")


if __name__ == "__main__":
    main()
