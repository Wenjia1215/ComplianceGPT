#!/usr/bin/env python3
"""Run Batch 5C: a frontier API baseline on the 36 frozen Rev. 4 rows.

The registered study preserves the exact RQ2 v3 questions, ordered evidence
windows, free-text JSON prompt, parser/retry logic, ASK policy, and verifier.
It replaces only the free-form Qwen answer call with the OpenAI Responses API.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Dict, List, Mapping, Sequence, Tuple


REPO_HINT = Path(__file__).resolve().parents[3]
if str(REPO_HINT) not in sys.path:
    sys.path.insert(0, str(REPO_HINT))

from experiments.answerer_comparison.rq2_bf16_baseline import (  # noqa: E402
    run_bf16_baseline as registered,
)


RESULT_ID = "rq2_frontier_baseline_v1"
SCHEMA_VERSION = "compliancegpt-rq2-frontier-baseline-v1"
SYSTEM_NAME = "generative_frontier_api"
MODEL_ID = "gpt-6-astra"
MODEL_REQUESTED_REVISION = "api-alias:gpt-6-astra"
MODEL_RESOLVED_REVISION_MARKER = "recorded-per-response"
TOKENIZER_REVISION_MARKER = "server-managed"
EXPECTED_ROWS = 36
EXPECTED_PROMPT_SHA256 = registered.EXPECTED_PROMPT_SHA256
FROZEN_SOURCE_COMMIT = registered.FROZEN_SOURCE_COMMIT
DEFAULT_ARCHIVE = registered.DEFAULT_ARCHIVE
INPUTS = registered.INPUTS
BF16_REFERENCE = (
    "experiments/answerer_comparison/rq2_bf16_baseline/results_v1/"
    "contracts/rev4_generative_baseline_bf16.csv"
)
BF16_REFERENCE_SHA256 = "1b84eb673145bdae15d8e52c22678f2cf780d5f09f6e8603e6578ec586c2fc60"
GENERATION_SETTINGS = {
    "reasoning_effort": "low",
    "max_output_tokens": 2048,
    "max_parse_retries": 2,
    "store": False,
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


def frontier_csv(output_dir: Path) -> Path:
    return output_dir / "contracts" / "rev4_generative_frontier_api.csv"


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


def runner_code_manifest(repo_root: Path) -> Dict[str, str]:
    paths = [
        "experiments/answerer_comparison/rq2_frontier_baseline/run_frontier_baseline.py",
        "experiments/answerer_comparison/rq2_frontier_baseline/requirements-api.txt",
        "experiments/answerer_comparison/rq2_bf16_baseline/run_bf16_baseline.py",
        "src/answerer_comparison/frontier_api_answerer.py",
    ]
    manifest: Dict[str, str] = {}
    for relative in paths:
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Batch 5C code input is missing: {path}")
        manifest[relative] = registered.sha256_file(path)
    return manifest


def copy_bf16_reference(repo_root: Path, output_dir: Path) -> Path:
    source = repo_root / BF16_REFERENCE
    if not source.is_file():
        raise FileNotFoundError(f"Validated Batch 5B reference is missing: {source}")
    actual = registered.sha256_file(source)
    if actual != BF16_REFERENCE_SHA256:
        raise RuntimeError(
            f"Batch 5B reference changed: expected {BF16_REFERENCE_SHA256}, got {actual}"
        )
    destination = output_dir / "references" / "rev4_generative_baseline_bf16.csv"
    registered.write_bytes(destination, source.read_bytes())
    return destination


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
        "model_reference_type": "mutable API alias; server-reported model recorded per response",
        "frozen_source_commit": FROZEN_SOURCE_COMMIT,
        "frozen_source_hashes": dict(verified["frozen_source_hashes"]),
        "source_archive_sha256": str(source_manifest["archive_sha256"]),
        "source_member_hashes": {
            key: str(value["sha256"])
            for key, value in dict(source_manifest["members"]).items()
        },
        "input_hashes": dict(verified["input_hashes"]),
        "bf16_reference_sha256": BF16_REFERENCE_SHA256,
        "prompt_sha256": EXPECTED_PROMPT_SHA256,
        "generation_settings": dict(GENERATION_SETTINGS),
        "experiment_code_files": code_files,
        "experiment_code_sha256": registered.canonical_sha256(code_files),
        "changed_factor": "free-form answer model/runtime: Qwen2.5-7B -> OpenAI frontier API",
        "retrieval_policy": "frozen RQ2 v3 Rev. 4 contexts; no live retrieval",
        "gold_policy": "gold excluded from API-visible contexts and used only by offline verifier",
        "api_data_policy": "store=false; no tools; API key read from environment and never recorded",
        "frozen_factors": [
            "36 Rev. 4 questions and ordered evidence windows",
            "free-form generative baseline system and user prompts",
            "JSON extraction, fail-closed normalization, and two parse retries",
            "ASK ODP policy and offline verifier",
        ],
    }
    path = output_dir / "run_config.json"
    current_commit = registered.git_head(repo_root)
    if path.exists():
        stored = json.loads(path.read_text(encoding="utf-8"))
        for key, value in expected.items():
            if stored.get(key) != value:
                if has_api_activity(output_dir):
                    raise RuntimeError(
                        f"Batch 5C configuration changed for {key!r} after API activity. "
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
        registered.write_json(path, stored)
        return stored
    if has_api_activity(output_dir):
        raise RuntimeError(
            "API activity exists without a Batch 5C run_config.json. Use a new output directory."
        )
    config = {
        **expected,
        "repo_commit": current_commit,
        "repo_commits_observed": [current_commit] if current_commit else [],
    }
    registered.write_json(path, config)
    return config


def write_preflight(output_dir: Path, contexts: Sequence[Mapping[str, Any]]) -> None:
    counts = [len(list(context.get("evidence_window", []) or [])) for context in contexts]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "scope": "gold-free frozen-context integrity audit; no API call",
        "framework_version": "rev4",
        "context_rows": len(contexts),
        "context_jsonl_sha256": registered.sha256_file(
            output_dir / "contexts" / "rev4_prepared_contexts.jsonl"
        ),
        "distinct_context_hashes": len({str(row["context_sha256"]) for row in contexts}),
        "distinct_window_hashes": len(
            {
                str((row.get("evidence_window_manifest") or {}).get("sha256", ""))
                for row in contexts
            }
        ),
        "window_record_count": {
            "min": min(counts),
            "mean": sum(counts) / len(counts),
            "max": max(counts),
        },
        "api_calls_performed": 0,
    }
    registered.write_json(output_dir / "preflight" / "summary.json", summary)
    text = "\n".join(
        [
            "# Batch 5C Prepared-Context Audit",
            "",
            "This is a gold-free integrity check, not a completed frontier-model result.",
            "",
            f"- Result identity: `{RESULT_ID}`",
            f"- Frozen Rev. 4 contexts: {len(contexts)}",
            f"- Distinct context hashes: {summary['distinct_context_hashes']}",
            f"- Distinct evidence-window hashes: {summary['distinct_window_hashes']}",
            f"- Context SHA-256: `{summary['context_jsonl_sha256']}`",
            "- API calls performed: no",
            "",
        ]
    )
    (output_dir / "PREPARED_CONTEXTS.md").write_text(text, encoding="utf-8")


def prepare_experiment(
    repo_root: Path, output_dir: Path, archive_path: Path
) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, str]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    verified = registered.verify_inputs(repo_root, archive_path)
    contexts, source_manifest = registered.extract_registered_archive(
        archive_path=archive_path,
        output_dir=output_dir,
    )
    source_manifest["schema_version"] = SCHEMA_VERSION
    source_manifest["result_id"] = RESULT_ID
    registered.write_json(output_dir / "manifests" / "source_archive.json", source_manifest)
    bf16_path = copy_bf16_reference(repo_root, output_dir)
    load_or_create_run_config(
        repo_root=repo_root,
        output_dir=output_dir,
        source_manifest=source_manifest,
        verified=verified,
    )
    gold_rows = registered.load_gold_rows(repo_root / INPUTS["gold"])
    expected_ids = {str(context["query_id"]) for context in contexts}
    if expected_ids != set(gold_rows):
        raise AssertionError("Frozen contexts and registered gold rows have different query ids.")
    reference_paths = [
        output_dir / "references" / "rev4_generative_baseline_4bit.csv",
        output_dir / "references" / "rev4_compliancegpt_4bit.csv",
        bf16_path,
    ]
    for path in reference_paths:
        rows = registered.read_csv_rows(path)
        if len(rows) != EXPECTED_ROWS or set(rows) != expected_ids:
            raise AssertionError(f"Registered reference output is incomplete: {path}")
    write_preflight(output_dir, contexts)
    return contexts, gold_rows


def validate_or_write_api_runtime(output_dir: Path) -> Dict[str, Any]:
    runtime = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "model_id": MODEL_ID,
        "python": platform.python_version(),
        "openai_python": version("openai"),
        "generation_settings": dict(GENERATION_SETTINGS),
        "api_key_source": "OPENAI_API_KEY environment variable; value never recorded",
    }
    path = output_dir / "manifests" / "api_runtime.json"
    if path.exists() and has_api_activity(output_dir):
        stored = json.loads(path.read_text(encoding="utf-8"))
        for key in ("model_id", "python", "openai_python", "generation_settings"):
            if stored.get(key) != runtime.get(key):
                raise RuntimeError(
                    f"API runtime changed for {key!r} after API activity. "
                    "Reconnect with the same runtime or use a new output directory."
                )
        return stored
    registered.write_json(path, runtime)
    return runtime


def validate_generation_contract(system_prompt: str, answerer: Any) -> Dict[str, Any]:
    prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()
    if prompt_hash != EXPECTED_PROMPT_SHA256:
        raise RuntimeError(
            f"Frozen generative prompt changed: expected {EXPECTED_PROMPT_SHA256}, got {prompt_hash}"
        )
    observed = {
        "reasoning_effort": str(answerer.reasoning_effort),
        "max_output_tokens": int(answerer.max_output_tokens),
        "max_parse_retries": int(answerer.max_parse_retries),
        "store": bool(answerer.store),
        "tools_enabled": False,
        "structured_output_enforced": False,
        "sdk_max_retries": GENERATION_SETTINGS["sdk_max_retries"],
        "sdk_timeout_seconds": GENERATION_SETTINGS["sdk_timeout_seconds"],
    }
    if observed != GENERATION_SETTINGS:
        raise RuntimeError(
            f"Registered API generation settings changed: expected {GENERATION_SETTINGS}, got {observed}"
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "prompt_sha256": prompt_hash,
        "prompt_and_parser_source_commit": FROZEN_SOURCE_COMMIT,
        "generation_settings": observed,
        "same_prompt_boundary": (
            "System prompt, context serialization, user prompt, JSON parser, fail-closed "
            "normalization, and retry prompt are inherited from the frozen Qwen baseline."
        ),
    }


def validate_matched_rows(
    frontier: Mapping[str, Mapping[str, str]],
    bf16: Mapping[str, Mapping[str, str]],
    baseline_4bit: Mapping[str, Mapping[str, str]],
    compliance_4bit: Mapping[str, Mapping[str, str]],
) -> Dict[str, Any]:
    mappings = {
        "frontier": frontier,
        "generative_baseline_bf16": bf16,
        "generative_baseline_4bit": baseline_4bit,
        "compliancegpt_4bit": compliance_4bit,
    }
    if any(len(rows) != EXPECTED_ROWS for rows in mappings.values()):
        raise AssertionError("Batch 5C or a registered reference is incomplete.")
    if any(set(rows) != set(frontier) for rows in mappings.values()):
        raise AssertionError("Batch 5C and reference query-id sets do not match.")
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
            "The API request uses a mutable model alias. Every response id and server-reported "
            "model string is retained; the runner rejects a model-string change within one run."
        ),
    }


def audit_api_provenance(output_dir: Path, read_api_call_log: Any, summarize_usage: Any) -> Dict[str, Any]:
    call_log = read_api_call_log(api_log_path(output_dir))
    by_id = {str(row["response_id"]): row for row in call_log}
    rows = registered.read_csv_rows(frontier_csv(output_dir))
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
                raise AssertionError(f"API response is referenced by multiple result rows: {response_id}")
            if dict(call) != by_id[response_id]:
                raise AssertionError(f"API response metadata differs from the append-only log: {response_id}")
            referenced_ids.add(response_id)
            response_models.add(str(call.get("response_model", "") or ""))
        final_output = str(calls[-1].get("output_text", "") or "")
        if hashlib.sha256(final_output.encode("utf-8")).hexdigest() != hashlib.sha256(
            str(raw.get("raw_output", "") or "").encode("utf-8")
        ).hexdigest():
            raise AssertionError(f"Final API output does not match contract raw output: {query_id}")
    response_models.discard("")
    if len(response_models) != 1:
        raise AssertionError(f"Expected exactly one server-reported model: {sorted(response_models)}")
    associated_calls = [row for row in call_log if str(row["response_id"]) in referenced_ids]
    orphaned = [str(row["response_id"]) for row in call_log if str(row["response_id"]) not in referenced_ids]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "response_model": next(iter(response_models)),
        "call_log": str(api_log_path(output_dir)),
        "call_log_sha256": registered.sha256_file(api_log_path(output_dir)),
        "completed_result_rows": len(rows),
        "all_logged_usage": summarize_usage(call_log),
        "result_associated_usage": summarize_usage(associated_calls),
        "parse_retry_rows": sum(count > 1 for count in calls_by_query.values()),
        "calls_by_query": calls_by_query,
        "orphaned_call_count": len(orphaned),
        "orphaned_response_ids": orphaned,
        "interpretation": (
            "Orphaned calls, if any, are billed responses produced before an interrupted row "
            "checkpoint; they are retained for cost and provenance auditing but excluded from results."
        ),
    }
    registered.write_json(output_dir / "manifests" / "api_responses.json", manifest)
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
    registered.write_json(runtime_path, runtime)
    return manifest


def format_rate(value: Mapping[str, Any]) -> str:
    rate = value.get("rate")
    rate_text = "NA" if rate is None else f"{float(rate):.3f}"
    return f"{int(value['count'])}/{int(value['n'])} ({rate_text})"


def write_summary_markdown(path: Path, summary: Mapping[str, Any]) -> None:
    labels = [
        ("generative_frontier_api", "Frontier API baseline"),
        ("generative_baseline_bf16", "Qwen generative baseline, BF16"),
        ("generative_baseline_4bit", "Qwen generative baseline, 4-bit"),
        ("compliancegpt_4bit", "ComplianceGPT, 4-bit"),
    ]
    lines = [
        "# Batch 5C — Rev. 4 Frontier API Baseline",
        "",
        f"Result identity: `{RESULT_ID}`",
        "",
        "All systems use the same 36 questions, ordered evidence windows, ASK policy, and offline verifier. The frontier baseline inherits the frozen free-form prompt and parser without API tools or schema-constrained decoding.",
        "",
        "| System | Strict pass | Full clause coverage | Runtime contract pass | Mean clause precision | Mean selected clauses | ODP sensitivity* |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label in labels:
        metrics = dict(summary["configurations"][key])
        odp = dict(metrics["odp_against_author_labels"])
        lines.append(
            f"| {label} | {format_rate(metrics['strict_pass'])}"
            f" | {format_rate(metrics['full_gold_clause_coverage'])}"
            f" | {format_rate(metrics['runtime_contract_pass'])}"
            f" | {float(metrics['mean_gold_clause_precision']):.3f}"
            f" | {float(metrics['selected_clause_count']['mean']):.2f}"
            f" | {format_rate(odp['params_required_sensitivity'])} |"
        )
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
        ("frontier_vs_bf16_baseline", "Frontier vs Qwen BF16 baseline"),
        ("frontier_vs_4bit_baseline", "Frontier vs Qwen 4-bit baseline"),
        ("frontier_vs_4bit_compliancegpt", "Frontier vs 4-bit ComplianceGPT"),
    ):
        value = summary["paired_strict_pass"][key]
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
    *,
    output_dir: Path,
    gold_rows: Mapping[str, Mapping[str, str]],
    normalize_odp_id: Any,
    api_manifest: Mapping[str, Any],
) -> Dict[str, Any]:
    paths = {
        "generative_frontier_api": frontier_csv(output_dir),
        "generative_baseline_bf16": output_dir / "references" / "rev4_generative_baseline_bf16.csv",
        "generative_baseline_4bit": output_dir / "references" / "rev4_generative_baseline_4bit.csv",
        "compliancegpt_4bit": output_dir / "references" / "rev4_compliancegpt_4bit.csv",
    }
    rows = {name: registered.read_csv_rows(path) for name, path in paths.items()}
    validation = validate_matched_rows(
        rows["generative_frontier_api"],
        rows["generative_baseline_bf16"],
        rows["generative_baseline_4bit"],
        rows["compliancegpt_4bit"],
    )
    configurations: Dict[str, Any] = {}
    for name, values in rows.items():
        aggregate = registered.aggregate_rows(
            rows=values,
            gold_rows=gold_rows,
            normalize_odp_id=normalize_odp_id,
        )
        aggregate.pop("per_row", None)
        configurations[name] = aggregate

    def comparison(right: str) -> Dict[str, Any]:
        return {
            "left": "generative_frontier_api",
            "right": right,
            **registered.paired_strict_pass(rows["generative_frontier_api"], rows[right]),
        }

    summary = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "framework_version": "rev4",
        "n_questions": EXPECTED_ROWS,
        "changed_factor": "free-form answer model/runtime: Qwen2.5-7B -> OpenAI frontier API",
        "matched_input_validation": validation,
        "api_provenance": dict(api_manifest),
        "configurations": configurations,
        "paired_strict_pass": {
            "frontier_vs_bf16_baseline": comparison("generative_baseline_bf16"),
            "frontier_vs_4bit_baseline": comparison("generative_baseline_4bit"),
            "frontier_vs_4bit_compliancegpt": comparison("compliancegpt_4bit"),
        },
        "strict_pass_definition": (
            "The existing gold-based citation-contract endpoint: full expected-clause coverage, "
            "source/revision/verbatim validity, and ODP/status consistency. It permits extra evidence."
        ),
        "interpretation_boundary": (
            "This is a stronger-system baseline, not an isolation of weight precision or architecture. "
            "Questions, model-visible evidence, prompt/parser, ODP policy, and verifier are fixed, but "
            "the API model and serving runtime differ. The requested model is a mutable alias; response "
            "IDs, server-reported model strings, raw outputs, and token usage are retained. API sampling "
            "may not reproduce byte-identical outputs."
        ),
        "file_hashes": {name: registered.sha256_file(path) for name, path in paths.items()},
    }
    registered.write_json(output_dir / "summary.json", summary)
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
            files[relative] = registered.sha256_file(path)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "files": files,
        "files_sha256": registered.canonical_sha256(files),
    }
    registered.write_json(output_dir / "manifests" / "outputs.json", manifest)
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
    print(f"Frozen Batch 5C inputs verified: {len(contexts)} Rev. 4 contexts.")
    if args.prepare_only:
        print(f"Prepared-context audit: {output_dir / 'PREPARED_CONTEXTS.md'}")
        print("No API key was read and no API call was made.")
        return

    api_key = str(os.environ.get("OPENAI_API_KEY", "") or "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. In Colab, add it to Secrets, enable notebook access, "
            "and rerun. The notebook never prints or writes the key."
        )
    validate_or_write_api_runtime(output_dir)

    current_src = repo_root / "src"
    if str(current_src) not in sys.path:
        sys.path.insert(0, str(current_src))
    from answerer_comparison.frontier_api_answerer import (
        make_openai_responses_answerer_class,
        read_api_call_log,
        summarize_usage,
    )
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        max_retries=int(GENERATION_SETTINGS["sdk_max_retries"]),
        timeout=float(GENERATION_SETTINGS["sdk_timeout_seconds"]),
    )

    with tempfile.TemporaryDirectory(prefix="compliancegpt-rq2-frontier-") as temporary:
        frozen_src = registered.extract_frozen_source(repo_root, Path(temporary))
        sys.path.insert(0, str(frozen_src))

        # The frozen pipeline imports local-model and QUR dependencies at module
        # import time even though this prepared-context API path invokes neither.
        # Supply dependency-light import shims only when Transformers is absent,
        # and always suppress the disabled QUR module's import-time stack.  The
        # frozen prompt/parser class itself is still imported from the registered
        # source commit and its hash is checked below.
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
        from generative_answerer.generator import BaselineGenerativeAnswerer, build_system_prompt
        import generative_answerer.pipeline as generative_pipeline_module

        matched.CONTEXT_SCHEMA = registered.EXPECTED_CONTEXT_SCHEMA
        system_prompt = str(build_system_prompt())
        answerer_class = make_openai_responses_answerer_class(BaselineGenerativeAnswerer)
        answerer = answerer_class(
            client=client,
            model_id=MODEL_ID,
            system_prompt=system_prompt,
            query_id_by_question={
                str(context["question"]): str(context["query_id"])
                for context in contexts
            },
            call_log_path=api_log_path(output_dir),
            reasoning_effort=str(GENERATION_SETTINGS["reasoning_effort"]),
            max_output_tokens=int(GENERATION_SETTINGS["max_output_tokens"]),
            max_parse_retries=int(GENERATION_SETTINGS["max_parse_retries"]),
            store=bool(GENERATION_SETTINGS["store"]),
        )
        generation_contract = validate_generation_contract(system_prompt, answerer)
        registered.write_json(
            output_dir / "manifests" / "generation_contract.json",
            generation_contract,
        )

        class PlaceholderModel:
            config = SimpleNamespace(_commit_hash=MODEL_RESOLVED_REVISION_MARKER)

        class PlaceholderTokenizer:
            init_kwargs = {"_commit_hash": TOKENIZER_REVISION_MARKER}

        # These constructors belong to the local-model path and are never used
        # by the prepared-context API answerer.  Replacing them prevents an
        # accidental model download while retaining the exact frozen pipeline.
        compliance_pipeline_module.ComplianceGenerator = lambda *_args, **_kwargs: object()
        generative_pipeline_module.BaselineGenerativeAnswerer = (
            lambda *_args, **_kwargs: answerer
        )
        retriever = matched.FrozenCCSRetriever.from_jsonl(repo_root / INPUTS["ccs"])
        pipeline = generative_pipeline_module.BaselineGenerativeRAGPipeline(
            framework_version="rev4",
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
        run_manifest["api_model_alias"] = MODEL_ID
        run_manifest["local_model_loaded"] = False
        registered.write_json(output_dir / "manifests" / "run.json", run_manifest)
        api_manifest = audit_api_provenance(output_dir, read_api_call_log, summarize_usage)
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
    print(f"Batch 5C completed successfully: {output_dir}")
    print(f"Result archive: {archive}")
    print(f"Result archive SHA-256: {registered.sha256_file(archive)}")


if __name__ == "__main__":
    main()
