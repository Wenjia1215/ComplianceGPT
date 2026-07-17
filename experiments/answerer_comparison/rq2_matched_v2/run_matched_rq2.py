#!/usr/bin/env python3
"""Run the corrected, immutable-window RQ2 comparison.

The script reconstructs a gold-independent evidence context from the frozen S7
contract traces, hashes that context, and gives the identical model-visible
window to both answer paths.  Gold rows enter only after generation, inside the
verifier.  Outputs are checkpointed after every question and can be resumed.
"""

from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
EXPECTED_ROWS = {"rev5": 100, "rev4": 36}
EXPECTED_CONTEXT_HASHES = {
    "rev5": {
        "context_jsonl_sha256": "6a9c42001b7268eab469c9f0b4952efb1f7ae8d5e33b4078498bd677ce99d963",
        "window_hashes_sha256": "80e4b20ba4c32c5ef7375b0426273b217747bc1e52966bddfb8f1163a44435f5",
        "contracts_csv_sha256": "1132810eb9f486821479a50865b3176946823d336a2fed3e216bff5113518bfc",
        "ccs_sha256": "0d4bf5e6e237318aee0b757c2c01c900b4447c5e8a61bf8bfdb8dc5b8a289113",
    },
    "rev4": {
        "context_jsonl_sha256": "2f3570a1bf0fccb2b9eea3b0e4f935af6350d99fcf23eb67178bf97b99bc5787",
        "window_hashes_sha256": "f03caa7f9954a12685f4cc302d582564b242047ff23035d79a7e9b6833d656c1",
        "contracts_csv_sha256": "c0b66ee611fba755a9a667644021c324b441b486558ab57047bcfe0d57d4ca04",
        "ccs_sha256": "fedfb47c566dd9d85059159b9c6e7fa5f82fdcf4b928079e699c5ab433fbd08c",
    },
}
INPUTS = {
    "rev5": {
        "contracts": "experiments/pipeline_runs/pipeline_rev5_contracts_20260312_150620.csv",
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl",
        "gold": "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv",
        "odp_registry": "data/ODP/rev5/odp_registry_rev5.json",
    },
    "rev4": {
        "contracts": "experiments/pipeline_runs/pipeline_rev4_contracts_20260312_152654.csv",
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl",
        "gold": "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv",
        "odp_registry": "data/ODP/rev4/odp_registry_rev4.json",
    },
}

EXPERIMENT_CODE_PATHS = (
    "experiments/answerer_comparison/rq2_matched_v2/run_matched_rq2.py",
    "src/answerer_comparison/matched_window_runner.py",
    "src/compliancegpt/pipeline/evidence_window.py",
    "src/compliancegpt/pipeline/pipeline.py",
    "src/compliancegpt/retriever/retriever_s7.py",
    "src/generative_answerer/pipeline.py",
    "src/compliancegpt/generator/generator.py",
    "src/generative_answerer/generator.py",
    "src/compliancegpt/generator/verifier/verifier.py",
    "src/compliancegpt/generator/citation_contract_80053.md",
    "experiments/answerer_comparison/rq2_matched_v2/requirements-colab.txt",
)


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-id", default=MODEL_ID)
    parser.add_argument(
        "--model-revision",
        default=None,
        help="Exact Hugging Face commit. If omitted, the first run resolves and freezes main.",
    )
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit model loading.")
    parser.add_argument(
        "--systems",
        nargs="+",
        choices=("compliancegpt", "generative_baseline"),
        default=("compliancegpt", "generative_baseline"),
    )
    parser.add_argument(
        "--revisions",
        nargs="+",
        choices=("rev5", "rev4"),
        default=("rev5", "rev4"),
    )
    return parser.parse_args()


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def experiment_code_manifest(repo_root: Path) -> Dict[str, Any]:
    files: Dict[str, str] = {}
    for relative in EXPERIMENT_CODE_PATHS:
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Experiment code input is missing: {path}")
        files[relative] = _sha256_file(path)
    canonical = json.dumps(files, sort_keys=True, separators=(",", ":"))
    return {
        "experiment_code_files": files,
        "experiment_code_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def has_contract_checkpoints(output_dir: Path) -> bool:
    """Return True only after at least one model-output row was checkpointed."""

    contracts_dir = output_dir / "contracts"
    if not contracts_dir.is_dir():
        return False
    for path in contracts_dir.glob("*.csv"):
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.reader(handle)
                next(reader, None)
                if next(reader, None) is not None:
                    return True
        except Exception:
            return True
    return False


def resolve_model_revision(model_id: str, requested: str | None) -> str:
    from huggingface_hub import HfApi

    info = HfApi().model_info(model_id, revision=requested or "main")
    revision = str(info.sha or "").strip()
    if not revision:
        raise RuntimeError(f"Could not resolve an immutable revision for {model_id!r}.")
    return revision


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
            "A CUDA GPU is required for the full 7B RQ2 rerun. "
            "In Colab choose Runtime > Change runtime type > T4 GPU (or better)."
        )
    print(f"GPU: {torch.cuda.get_device_name(0)}")


def validate_inputs(repo_root: Path, revisions: Iterable[str]) -> None:
    missing = []
    for revision in revisions:
        for relative in INPUTS[revision].values():
            path = repo_root / relative
            if not path.is_file():
                missing.append(str(path))
    if missing:
        raise FileNotFoundError("Required active inputs are missing:\n" + "\n".join(missing))


def load_or_create_run_config(
    *,
    output_dir: Path,
    repo_root: Path,
    model_id: str,
    requested_revision: str | None,
    revisions: Iterable[str],
    systems: Iterable[str],
    load_in_4bit: bool,
    write_json: Any,
) -> Dict[str, Any]:
    path = output_dir / "run_config.json"
    current_commit = git_head(repo_root)
    code_manifest = experiment_code_manifest(repo_root)
    requested_revisions = list(revisions)
    requested_systems = list(systems)
    if path.exists():
        config = json.loads(path.read_text(encoding="utf-8"))
        checkpoints_exist = has_contract_checkpoints(output_dir)

        stored_code_hash = str(config.get("experiment_code_sha256", "") or "")
        current_code_hash = str(code_manifest["experiment_code_sha256"])
        if stored_code_hash and stored_code_hash != current_code_hash and checkpoints_exist:
            raise RuntimeError(
                "Experiment code changed after model-output checkpoints were written. "
                "Use a new output directory instead of mixing experiments."
            )
        if not stored_code_hash and checkpoints_exist:
            raise RuntimeError(
                "The existing run predates code-fingerprint validation and already contains "
                "model outputs. Use a new output directory instead of migrating it."
            )

        # A stale pre-run config is safe to migrate when no model rows exist.
        # Repository commits may also change because the notebook itself was
        # saved; only the experiment-code fingerprint governs resumability.
        config.update(code_manifest)
        checks = {
            "model_id": model_id,
            "revisions": requested_revisions,
            "systems": requested_systems,
            "load_in_4bit": bool(load_in_4bit),
        }
        for key, current in checks.items():
            if config.get(key) != current:
                raise RuntimeError(
                    f"Existing run configuration differs for {key!r}. "
                    "Use a new output directory instead of mixing experiments."
                )
        if requested_revision and config.get("model_revision") != requested_revision:
            raise RuntimeError("Requested model revision differs from the existing run.")
        observed = [
            str(value)
            for value in list(config.get("repo_commits_observed", []) or [])
            if str(value).strip()
        ]
        previous_commit = str(config.get("repo_commit", "") or "")
        for value in (previous_commit, current_commit):
            if value and value not in observed:
                observed.append(value)
        config["repo_commit"] = current_commit
        config["repo_commits_observed"] = observed
        config["schema_version"] = "compliancegpt-rq2-matched-config-v3"
        write_json(path, config)
        return config

    resolved_revision = resolve_model_revision(model_id, requested_revision)
    config = {
        "schema_version": "compliancegpt-rq2-matched-config-v3",
        "repo_commit": current_commit,
        "repo_commits_observed": [current_commit] if current_commit else [],
        "model_id": model_id,
        "model_revision": resolved_revision,
        "revisions": requested_revisions,
        "systems": requested_systems,
        "load_in_4bit": bool(load_in_4bit),
        "retrieval_policy": "frozen stored S7 trace; no live retrieval",
        "evidence_policy": "one immutable ordered window shared by both answer paths",
        "gold_policy": "gold excluded from prepared context and used only by verifier",
        **code_manifest,
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


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    sys.path.insert(0, str(repo_root / "src"))

    require_gpu()
    validate_inputs(repo_root, args.revisions)

    from answerer_comparison.matched_window_runner import (
        FrozenCCSRetriever,
        build_context_file,
        load_context_file,
        load_gold_rows,
        run_prepared_contexts,
        summarize_paired_outputs,
        validate_paired_outputs,
        write_json,
    )
    from compliancegpt.pipeline.pipeline import ComplianceGPTPipeline
    from generative_answerer.pipeline import BaselineGenerativeRAGPipeline

    determinism = configure_determinism()
    config = load_or_create_run_config(
        output_dir=output_dir,
        repo_root=repo_root,
        model_id=str(args.model_id),
        requested_revision=args.model_revision,
        revisions=args.revisions,
        systems=args.systems,
        load_in_4bit=not args.no_4bit,
        write_json=write_json,
    )
    config["determinism"] = determinism
    write_json(output_dir / "run_config.json", config)

    context_manifests: Dict[str, Any] = {}
    contexts: Dict[str, Any] = {}
    gold_rows: Dict[str, Any] = {}
    for revision in args.revisions:
        paths = INPUTS[revision]
        context_path = output_dir / "contexts" / f"{revision}_prepared_contexts.jsonl"
        context_manifests[revision] = build_context_file(
            contracts_csv=repo_root / paths["contracts"],
            ccs_path=repo_root / paths["ccs"],
            output_jsonl=context_path,
            framework_version=revision,
            expected_rows=EXPECTED_ROWS[revision],
        )
        for field, expected_hash in EXPECTED_CONTEXT_HASHES[revision].items():
            actual_hash = str(context_manifests[revision].get(field, "") or "")
            if actual_hash != expected_hash:
                raise RuntimeError(
                    f"Frozen {revision} input/context hash changed for {field}: "
                    f"expected {expected_hash}, got {actual_hash}."
                )
        contexts[revision] = load_context_file(context_path)
        gold_rows[revision] = load_gold_rows(
            repo_root / paths["gold"], expected_rows=EXPECTED_ROWS[revision]
        )
    write_json(output_dir / "manifests" / "contexts.json", context_manifests)

    shared: Tuple[Any, Any] | None = None
    run_manifests: Dict[str, Any] = {}
    for system in args.systems:
        pipeline_class = (
            ComplianceGPTPipeline if system == "compliancegpt" else BaselineGenerativeRAGPipeline
        )
        for revision in args.revisions:
            frozen_retriever = FrozenCCSRetriever.from_jsonl(
                repo_root / INPUTS[revision]["ccs"]
            )
            pipeline = pipeline_class(
                **pipeline_kwargs(
                    repo_root=repo_root,
                    revision=revision,
                    model_id=str(args.model_id),
                    model_revision=str(config["model_revision"]),
                    retriever=frozen_retriever,
                    load_in_4bit=not args.no_4bit,
                    shared=shared,
                )
            )
            if shared is None:
                shared = (pipeline.model, pipeline.tokenizer)

            output_csv = output_dir / "contracts" / f"{revision}_{system}.csv"
            key = f"{revision}_{system}"
            run_manifests[key] = run_prepared_contexts(
                pipeline=pipeline,
                contexts=contexts[revision],
                gold_rows_by_id=gold_rows[revision],
                system_name=system,
                output_csv=output_csv,
                resume=True,
                progress_every=1,
            )
            write_json(output_dir / "manifests" / "runs.json", run_manifests)
            del pipeline, frozen_retriever
            gc.collect()
            try:
                import torch

                torch.cuda.empty_cache()
            except Exception:
                pass

    paired: Dict[str, Any] = {}
    if {"compliancegpt", "generative_baseline"}.issubset(set(args.systems)):
        for revision in args.revisions:
            compliance_csv = output_dir / "contracts" / f"{revision}_compliancegpt.csv"
            baseline_csv = output_dir / "contracts" / f"{revision}_generative_baseline.csv"
            validation = validate_paired_outputs(compliance_csv, baseline_csv)
            summary = summarize_paired_outputs(
                compliance_csv=compliance_csv,
                baseline_csv=baseline_csv,
                gold_rows_by_id=gold_rows[revision],
            )
            paired[revision] = {"validation": validation, "summary": summary}
            write_json(output_dir / "summaries" / f"{revision}_paired_summary.json", summary)
        write_json(output_dir / "manifests" / "paired_validation.json", paired)

    archive = Path(
        shutil.make_archive(
            str(output_dir.parent / output_dir.name),
            "zip",
            root_dir=output_dir,
        )
    )
    print(f"Completed immutable-window RQ2 run: {output_dir}")
    print(f"Result archive: {archive}")


if __name__ == "__main__":
    main()
