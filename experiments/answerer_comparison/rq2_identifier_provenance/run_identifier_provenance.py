#!/usr/bin/env python3
"""Emit and verify positive per-identifier provenance for frozen RQ2 contracts.

The run consumes the frozen RQ2 v3 prepared contexts and ComplianceGPT
contracts. It performs no retrieval or model inference. It deterministically
replays the implemented pre-rescue and rescue path, requires the replayed core
contract to match the frozen contract, and emits one of selector, fallback,
hierarchy, or rescue for every final source identifier.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


RESULT_ID = "rq2_identifier_provenance_v1"
SCHEMA_VERSION = "compliancegpt-rq2-identifier-provenance-v1"
SOURCE_RESULT_ID = "rq2_matched_v3"
EXPECTED_ROWS = {"rev5": 100, "rev4": 36}
ORIGINS = ("selector", "fallback", "rescue", "hierarchy")
CONTEXT_MEMBERS = {
    "rev5": "contexts/rev5_prepared_contexts.jsonl",
    "rev4": "contexts/rev4_prepared_contexts.jsonl",
}
CONTRACT_MEMBERS = {
    "rev5": "contracts/rev5_compliancegpt.csv",
    "rev4": "contracts/rev4_compliancegpt.csv",
}
INPUTS = {
    "rev5": {
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl",
        "odp_registry": "data/ODP/rev5/odp_registry_rev5.json",
    },
    "rev4": {
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl",
        "odp_registry": "data/ODP/rev4/odp_registry_rev4.json",
    },
}


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
    return parser.parse_args()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
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


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields))
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def read_jsonl_member(
    archive: zipfile.ZipFile,
    member: str,
) -> Tuple[List[Dict[str, Any]], str]:
    payload = archive.read(member)
    rows = [
        json.loads(line)
        for line in payload.decode("utf-8").splitlines()
        if line.strip()
    ]
    return rows, sha256_bytes(payload)


def read_csv_member(
    archive: zipfile.ZipFile,
    member: str,
) -> Tuple[Dict[str, Dict[str, str]], str]:
    payload = archive.read(member)
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8"), newline=""))
    rows = {str(row["query_id"]): dict(row) for row in reader}
    return rows, sha256_bytes(payload)


def source_ids(contract: Mapping[str, Any]) -> List[str]:
    return [
        str(span.get("source_id", "") or "").strip()
        for span in list(contract.get("evidence_spans", []) or [])
        if str(span.get("source_id", "") or "").strip()
    ]


def manifest_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def load_rescue_runner(repo_root: Path) -> Any:
    path = (
        repo_root
        / "experiments"
        / "answerer_comparison"
        / "rq2_rescue_ablation"
        / "run_rescue_ablation.py"
    )
    spec = importlib.util.spec_from_file_location("batch3d_rescue_replay", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load rescue replay runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def deterministic_zip(source_dir: Path, output_path: Path) -> None:
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in source_dir.rglob("*") if item.is_file()):
            relative = path.relative_to(source_dir).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def origin_summary(
    identifier_rows: Sequence[Mapping[str, Any]],
    contract_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for origin in ORIGINS:
        occurrences = [row for row in identifier_rows if row["origin"] == origin]
        row_keys = {
            (str(row["framework_version"]), str(row["query_id"]))
            for row in occurrences
        }
        unique_ids = {str(row["source_id"]) for row in occurrences}
        contained = sum(bool(row["in_evidence_window"]) for row in occurrences)
        result[origin] = {
            "identifier_occurrences": len(occurrences),
            "unique_identifiers": len(unique_ids),
            "contracts_with_origin": len(row_keys),
            "window_present_occurrences": contained,
            "window_containment_rate": contained / len(occurrences) if occurrences else None,
        }
    all_contained = sum(bool(row["in_evidence_window"]) for row in identifier_rows)
    return {
        "contracts": len(contract_rows),
        "identifier_occurrences": len(identifier_rows),
        "window_present_occurrences": all_contained,
        "window_containment_rate": (
            all_contained / len(identifier_rows) if identifier_rows else None
        ),
        "contracts_all_identifiers_in_window": sum(
            bool(row["all_identifiers_in_window"]) for row in contract_rows
        ),
        "contracts_complete_provenance": sum(
            bool(row["provenance_complete"]) for row in contract_rows
        ),
        "contracts_matching_frozen_core": sum(
            bool(row["core_contract_match"]) for row in contract_rows
        ),
        "runtime_contract_pass": sum(
            bool(row["runtime_contract_pass"]) for row in contract_rows
        ),
        "by_origin": result,
    }


def render_summary(summary: Mapping[str, Any]) -> str:
    lines = [
        "# RQ2 Per-Identifier Runtime Provenance",
        "",
        f"Result identity: `{RESULT_ID}`",
        "",
        "The run deterministically reconstructs all frozen ComplianceGPT contracts and emits one positive origin for every final source identifier. It performs no retrieval, model inference, or gold-guided construction.",
        "",
    ]
    for revision in ("rev5", "rev4", "combined"):
        block = summary["revisions"][revision] if revision != "combined" else summary["combined"]
        label = revision.upper() if revision != "combined" else "Combined"
        lines.extend(
            [
                f"## {label}",
                "",
                f"All {block['contracts']} contracts have complete provenance, match their frozen core contracts, and pass the gold-independent Runtime Verifier.",
                "",
                "| Origin | Identifier occurrences | Contracts | In shared window | Rate |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for origin in ORIGINS:
            item = block["by_origin"][origin]
            rate = "not applicable" if item["window_containment_rate"] is None else f"{item['window_containment_rate']:.4f}"
            lines.append(
                f"| `{origin}` | {item['identifier_occurrences']} | {item['contracts_with_origin']} | {item['window_present_occurrences']}/{item['identifier_occurrences']} | {rate} |"
            )
        lines.extend(
            [
                "",
                f"Overall containment: {block['window_present_occurrences']}/{block['identifier_occurrences']} final identifier occurrences; {block['contracts_all_identifiers_in_window']}/{block['contracts']} contracts have every final identifier in the frozen shared window.",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation boundary",
            "",
            "The observed run contains no hierarchy additions because hierarchy closure was disabled in the frozen RQ2 configuration. This is a direct zero count, not evidence about enabled hierarchy-closure behavior. The rescue containment result is direct per-identifier runtime evidence: every rescue-added identifier is enumerated in the contract provenance field and checked against that question's frozen evidence window.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    frozen_archive = args.frozen_archive.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(
            f"Output directory already exists: {output_dir}. Use a new path to preserve result identity."
        )
    if not frozen_archive.is_file():
        raise FileNotFoundError(frozen_archive)
    output_dir.mkdir(parents=True)

    sys.path.insert(0, str(repo_root / "src"))
    from answerer_comparison.matched_window_runner import load_ccs, validate_prepared_context
    from compliancegpt.generator.verifier.verifier import verify_contract_validity
    from compliancegpt.pipeline.odp_policy import (
        ASSIGNMENT_REQUIRED_SENTINEL,
        apply_odp_policy_to_answer,
    )
    from compliancegpt.pipeline.pipeline import (
        _best_primary_citation,
        _build_ask_list,
        _build_citation_suffix,
        _build_identifier_provenance,
        _build_param_key_to_canonical,
        _canonicalize_param_list,
        _extract_control_hints,
        _is_enhancement_clause_id,
        _query_allows_enhancements,
        _rescue_odp_statement_spans,
        load_odp_registry,
    )

    rescue_runner = load_rescue_runner(repo_root)
    frozen_hash_before = sha256_file(frozen_archive)
    member_hashes: Dict[str, str] = {}
    contexts_by_revision: Dict[str, Dict[str, Dict[str, Any]]] = {}
    frozen_rows_by_revision: Dict[str, Dict[str, Dict[str, str]]] = {}
    with zipfile.ZipFile(frozen_archive, "r") as archive:
        for revision in ("rev5", "rev4"):
            context_rows, context_hash = read_jsonl_member(archive, CONTEXT_MEMBERS[revision])
            frozen_rows, contract_hash = read_csv_member(archive, CONTRACT_MEMBERS[revision])
            if len(context_rows) != EXPECTED_ROWS[revision]:
                raise AssertionError(f"Unexpected {revision} context count: {len(context_rows)}")
            if len(frozen_rows) != EXPECTED_ROWS[revision]:
                raise AssertionError(f"Unexpected {revision} contract count: {len(frozen_rows)}")
            for context in context_rows:
                validate_prepared_context(context)
            contexts_by_revision[revision] = {
                str(context["query_id"]): context for context in context_rows
            }
            frozen_rows_by_revision[revision] = frozen_rows
            member_hashes[CONTEXT_MEMBERS[revision]] = context_hash
            member_hashes[CONTRACT_MEMBERS[revision]] = contract_hash

    identifier_rows_by_revision: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    contract_rows_by_revision: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    contract_json_rows: List[Dict[str, Any]] = []

    for revision in ("rev5", "rev4"):
        ccs_path = repo_root / INPUTS[revision]["ccs"]
        registry_path = repo_root / INPUTS[revision]["odp_registry"]
        ccs = load_ccs(ccs_path)
        odp_registry = load_odp_registry(str(registry_path))
        corpus = {
            source_id: str(record.get("text", "") or "")
            for source_id, record in ccs.items()
        }
        param_ids = {
            source_id
            for source_id, record in ccs.items()
            if str(record.get("kind", "") or "").strip().lower() in {"odp", "prm"}
        }
        key_map = _build_param_key_to_canonical(param_ids)

        for query_id, frozen_row in sorted(
            frozen_rows_by_revision[revision].items(),
            key=lambda item: (0, int(item[0])) if item[0].isdigit() else (1, item[0]),
        ):
            context = contexts_by_revision[revision][query_id]
            frozen_contract = json.loads(str(frozen_row.get("contract_json", "") or "{}"))
            frozen_debug = dict(frozen_contract.get("debug", {}) or {})
            hierarchy_ids = list(frozen_debug.get("hierarchy_added_ids", []) or [])
            if hierarchy_ids:
                raise AssertionError(
                    f"Frozen {revision} query {query_id} unexpectedly contains hierarchy additions."
                )
            if bool(frozen_debug.get("secondary_fallback_used", False)):
                raise AssertionError(
                    f"Frozen {revision} query {query_id} unexpectedly uses secondary fallback."
                )

            replay_contract, reconstruction = rescue_runner.build_replay_contract(
                frozen_contract=frozen_contract,
                question=str(context["question"]),
                revision=revision,
                ccs=ccs,
                odp_registry=odp_registry,
                param_ids=param_ids,
                key_map=key_map,
                rescue_enabled=True,
                extract_control_hints=_extract_control_hints,
                query_allows_enhancements=_query_allows_enhancements,
                is_enhancement_clause_id=_is_enhancement_clause_id,
                rescue_odp_statement_spans=_rescue_odp_statement_spans,
                apply_odp_policy_to_answer=apply_odp_policy_to_answer,
                canonicalize_param_list=_canonicalize_param_list,
                assignment_sentinel=ASSIGNMENT_REQUIRED_SENTINEL,
                build_ask_list=_build_ask_list,
                best_primary_citation=_best_primary_citation,
                build_citation_suffix=_build_citation_suffix,
            )
            rescue_runner.assert_rescue_on_matches_frozen(
                replay_contract,
                frozen_contract,
                revision=revision,
                query_id=query_id,
            )

            window_ids = [
                str(record.get("id", "") or "").strip()
                for record in list(context.get("evidence_window", []) or [])
                if str(record.get("id", "") or "").strip()
            ]
            debug_window_ids = list(
                dict(frozen_debug.get("evidence_window", {}) or {}).get("source_ids", []) or []
            )
            if window_ids != debug_window_ids:
                raise AssertionError(
                    f"Frozen evidence-window manifest differs for {revision} query {query_id}."
                )

            pre_rescue_ids = list(reconstruction["pre_rescue_source_ids"])
            rescue_ids = list(reconstruction["rescue_added_ids"])
            fallback_used = bool(frozen_debug.get("fallback_used", False))
            selector_ids = [] if fallback_used else pre_rescue_ids
            fallback_ids = pre_rescue_ids if fallback_used else []
            if fallback_used:
                if not fallback_ids or not window_ids or fallback_ids[0] != window_ids[0]:
                    raise AssertionError(
                        f"Fallback is not the first shared-window identifier for {revision} query {query_id}."
                    )

            provenance = _build_identifier_provenance(
                final_spans=list(replay_contract.get("evidence_spans", []) or []),
                selector_ids=selector_ids,
                fallback_ids=fallback_ids,
                hierarchy_ids=hierarchy_ids,
                rescue_ids=rescue_ids,
                evidence_window_ids=window_ids,
            )
            final_ids = source_ids(replay_contract)
            provenance_ids = [str(record["source_id"]) for record in provenance]
            if provenance_ids != final_ids:
                raise AssertionError(
                    f"Provenance order differs from final identifiers for {revision} query {query_id}."
                )
            if len(set(provenance_ids)) != len(provenance_ids):
                raise AssertionError(
                    f"Duplicate final identifier for {revision} query {query_id}."
                )
            observed_by_origin = {
                origin: [
                    str(record["source_id"])
                    for record in provenance
                    if record["origin"] == origin
                ]
                for origin in ORIGINS
            }
            expected_by_origin = {
                "selector": selector_ids,
                "fallback": fallback_ids,
                "rescue": rescue_ids,
                "hierarchy": hierarchy_ids,
            }
            if observed_by_origin != expected_by_origin:
                raise AssertionError(
                    f"Stage attribution differs for {revision} query {query_id}: "
                    f"{observed_by_origin!r} != {expected_by_origin!r}"
                )

            for position, (span, record) in enumerate(
                zip(replay_contract["evidence_spans"], provenance),
                start=1,
            ):
                source_id = str(record["source_id"])
                ccs_record = ccs.get(source_id)
                if not isinstance(ccs_record, Mapping):
                    raise AssertionError(f"Unknown active-CCS source identifier: {source_id}")
                span_text = str(span.get("span_text", "") or "")
                ccs_text = str(ccs_record.get("text", "") or "").strip()
                span_verbatim = span_text == ccs_text
                if not span_verbatim:
                    raise AssertionError(
                        f"Non-verbatim span for {revision} query {query_id}: {source_id}"
                    )
                identifier_rows_by_revision[revision].append(
                    {
                        "framework_version": revision,
                        "query_id": query_id,
                        "position": position,
                        "source_id": source_id,
                        "origin": str(record["origin"]),
                        "in_evidence_window": bool(record["in_evidence_window"]),
                        "span_verbatim": span_verbatim,
                        "span_sha256": sha256_bytes(span_text.encode("utf-8")),
                        "context_sha256": str(context["context_sha256"]),
                    }
                )

            instrumented_contract = copy.deepcopy(frozen_contract)
            instrumented_contract["provenance"] = provenance
            runtime_pass, runtime_errors = verify_contract_validity(
                instrumented_contract,
                corpus=corpus,
                org_profile={},
                strict_verbatim=True,
            )
            if not runtime_pass:
                raise AssertionError(
                    f"Instrumented contract fails Runtime Verifier for {revision} query {query_id}: "
                    f"{runtime_errors!r}"
                )

            counts = Counter(str(record["origin"]) for record in provenance)
            all_in_window = all(bool(record["in_evidence_window"]) for record in provenance)
            provenance_complete = len(provenance) == len(final_ids)
            contract_rows_by_revision[revision].append(
                {
                    "framework_version": revision,
                    "query_id": query_id,
                    "question": str(context["question"]),
                    "identifier_count": len(final_ids),
                    "selector_count": counts["selector"],
                    "fallback_count": counts["fallback"],
                    "rescue_count": counts["rescue"],
                    "hierarchy_count": counts["hierarchy"],
                    "in_window_count": sum(
                        bool(record["in_evidence_window"]) for record in provenance
                    ),
                    "all_identifiers_in_window": all_in_window,
                    "provenance_complete": provenance_complete,
                    "core_contract_match": True,
                    "runtime_contract_pass": bool(runtime_pass),
                    "runtime_error_tags": "|".join(runtime_errors),
                    "context_sha256": str(context["context_sha256"]),
                    "final_source_ids": "|".join(final_ids),
                    "selector_ids": "|".join(observed_by_origin["selector"]),
                    "fallback_ids": "|".join(observed_by_origin["fallback"]),
                    "rescue_ids": "|".join(observed_by_origin["rescue"]),
                    "hierarchy_ids": "|".join(observed_by_origin["hierarchy"]),
                    "provenance_json": json.dumps(provenance, sort_keys=True),
                }
            )
            contract_json_rows.append(
                {
                    "result_id": RESULT_ID,
                    "source_result_id": SOURCE_RESULT_ID,
                    "framework_version": revision,
                    "query_id": query_id,
                    "context_sha256": str(context["context_sha256"]),
                    "contract": instrumented_contract,
                }
            )

    identifier_fields = [
        "framework_version",
        "query_id",
        "position",
        "source_id",
        "origin",
        "in_evidence_window",
        "span_verbatim",
        "span_sha256",
        "context_sha256",
    ]
    contract_fields = [
        "framework_version",
        "query_id",
        "question",
        "identifier_count",
        "selector_count",
        "fallback_count",
        "rescue_count",
        "hierarchy_count",
        "in_window_count",
        "all_identifiers_in_window",
        "provenance_complete",
        "core_contract_match",
        "runtime_contract_pass",
        "runtime_error_tags",
        "context_sha256",
        "final_source_ids",
        "selector_ids",
        "fallback_ids",
        "rescue_ids",
        "hierarchy_ids",
        "provenance_json",
    ]
    all_identifier_rows = identifier_rows_by_revision["rev5"] + identifier_rows_by_revision["rev4"]
    all_contract_rows = contract_rows_by_revision["rev5"] + contract_rows_by_revision["rev4"]
    write_csv(output_dir / "identifier_provenance.csv", all_identifier_rows, identifier_fields)
    write_csv(output_dir / "per_contract_provenance.csv", all_contract_rows, contract_fields)
    write_jsonl(output_dir / "contracts_with_provenance.jsonl", contract_json_rows)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "source_result_id": SOURCE_RESULT_ID,
        "revisions": {
            revision: origin_summary(
                identifier_rows_by_revision[revision],
                contract_rows_by_revision[revision],
            )
            for revision in ("rev5", "rev4")
        },
        "combined": origin_summary(all_identifier_rows, all_contract_rows),
        "interpretation_boundary": {
            "gold_used_for_provenance": False,
            "retrieval_or_model_inference": False,
            "hierarchy_closure_enabled_in_frozen_run": False,
            "zero_hierarchy_additions_interpretation": (
                "No hierarchy additions were observed because hierarchy closure was disabled; "
                "this does not evaluate enabled hierarchy behavior."
            ),
        },
    }
    write_json(output_dir / "summary.json", summary)
    (output_dir / "SUMMARY.md").write_text(render_summary(summary), encoding="utf-8")

    frozen_hash_after = sha256_file(frozen_archive)
    if frozen_hash_before != frozen_hash_after:
        raise AssertionError("Frozen RQ2 v3 archive changed during provenance replay.")

    tracked_outputs = [
        "SUMMARY.md",
        "contracts_with_provenance.jsonl",
        "identifier_provenance.csv",
        "per_contract_provenance.csv",
        "summary.json",
    ]
    rescue_runner_path = (
        repo_root
        / "experiments"
        / "answerer_comparison"
        / "rq2_rescue_ablation"
        / "run_rescue_ablation.py"
    )
    pipeline_path = repo_root / "src" / "compliancegpt" / "pipeline" / "pipeline.py"
    run_config = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "source_result_id": SOURCE_RESULT_ID,
        "repo_root": ".",
        "script": str(Path(__file__).resolve().relative_to(repo_root)),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "runtime_pipeline_sha256": sha256_file(pipeline_path),
        "rescue_replay_runner_sha256": sha256_file(rescue_runner_path),
        "frozen_archive": manifest_path(frozen_archive, repo_root),
        "frozen_archive_sha256_before": frozen_hash_before,
        "frozen_archive_sha256_after": frozen_hash_after,
        "frozen_member_sha256": member_hashes,
        "input_sha256": {
            revision: {
                key: sha256_file(repo_root / relative)
                for key, relative in INPUTS[revision].items()
            }
            for revision in ("rev5", "rev4")
        },
        "policy": {
            "retrieval": "none; consume frozen prepared contexts",
            "selector": "none; replay frozen normalized selector output",
            "rescue": "implemented deterministic ODP-statement rescue, max_add=4",
            "fallback": "reuse recorded deterministic fallback state",
            "hierarchy_closure": "disabled in frozen RQ2 configuration",
            "gold_during_construction_or_attribution": False,
            "provenance_origins": list(ORIGINS),
            "containment_reference": "question-specific frozen shared evidence window",
        },
        "outputs_sha256": {
            name: sha256_file(output_dir / name) for name in tracked_outputs
        },
        "result_summary_sha256": canonical_sha256(summary),
    }
    write_json(output_dir / "run_config.json", run_config)

    archive_path = output_dir.parent / f"{output_dir.name}.zip"
    deterministic_zip(output_dir, archive_path)
    print(f"Completed {RESULT_ID}: {output_dir}")
    print(f"Result archive: {archive_path}")
    print(render_summary(summary))


if __name__ == "__main__":
    main()
