#!/usr/bin/env python3
"""Replay the corrected PRESERVE path on the eight applicable frozen RQ2 rows.

The replay reuses the immutable prepared contexts and the exact frozen selector
outputs from RQ2 matched-window v3.  It executes the current deterministic
pipeline from evidence filling through ODP policy, contract construction, and
both runtime and offline verification.  It performs no live retrieval and no
new model inference.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import os
import platform
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from answerer_comparison.matched_window_runner import (
    FrozenCCSRetriever,
    file_sha256,
    load_gold_rows,
    run_prepared_contexts,
    validate_prepared_context,
)
from compliancegpt.pipeline.odp_policy import (
    ODP_POLICY_PATCH_ID,
    ODP_POLICY_VERSION,
    extract_odp_ids,
)
from compliancegpt.pipeline.pipeline import ComplianceGPTPipeline


RESULT_ID = "rq2_preserve_replay_v1"
SCHEMA_VERSION = "compliancegpt-rq2-preserve-replay-v1"
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MODEL_REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
FROZEN_RUNTIME_COMMIT = "be862bcadfa61b474d795303e01ce9394909fdcc"
EXPECTED_POLICY_VERSION = "1.1"
EXPECTED_PATCH_ID = "2026-10-03-preserve-status-v1.1"
EXPECTED_QUERY_IDS = {
    "rev4": ("21", "30"),
    "rev5": ("1", "11", "20", "30", "69", "93"),
}

ARCHIVE_RELATIVE = (
    "experiments/answerer_comparison/rq2_matched/results_v3/"
    "compliancegpt_rq2_matched_v3.zip"
)
ARCHIVE_SHA256 = "56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328"
ARCHIVE_MEMBER_SHA256 = {
    "contexts/rev4_prepared_contexts.jsonl": (
        "4f1ca834993a34c22bb4b61fa9a984d32382b5e84e3473656a22af688412d7a6"
    ),
    "contexts/rev5_prepared_contexts.jsonl": (
        "b47e58c17ce6d0aca1d8519941f52c3c21e393d9187fcf113de7bfec68cfc473"
    ),
    "contracts/rev4_compliancegpt.csv": (
        "cb8d49cdff4b1ebcd68f0010b4fbecafd457352cb9e963856b03ef1a0aae50f9"
    ),
    "contracts/rev5_compliancegpt.csv": (
        "9440fd02c25e30b4b3fe39890fadb3ec3e120dfd8af9e82ea23fab6f87167cc9"
    ),
    "run_config.json": (
        "9f87e66c19c8a066aa6d87350eca2b959a3c2315bc7b602eac75f3f13b23acf5"
    ),
}
REPO_INPUTS = {
    "rev4": {
        "gold": (
            "data/gold_standard_datasets/nist800-53/"
            "nist_sp800-53_rev4_gold-set_36q.csv"
        ),
        "gold_sha256": (
            "80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2"
        ),
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl",
        "ccs_sha256": (
            "500bb5d1f265080752710c2f0ae84b8044b67a1e2118cd5e166353b6fc3ab726"
        ),
        "odp_registry": "data/ODP/rev4/odp_registry_rev4.json",
    },
    "rev5": {
        "gold": (
            "data/gold_standard_datasets/nist800-53/"
            "nist_sp800-53_rev5_gold-set_100q.csv"
        ),
        "gold_sha256": (
            "f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5"
        ),
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl",
        "ccs_sha256": (
            "71057ba79c54b8c1f0d171198a6ccb60b4c8818acbd2062e7f7c74ee11242e08"
        ),
        "odp_registry": "data/ODP/rev5/odp_registry_rev5.json",
    },
}
CODE_PATHS = (
    "experiments/answerer_comparison/rq2_preserve_replay/run_preserve_replay.py",
    "src/answerer_comparison/matched_window_runner.py",
    "src/compliancegpt/pipeline/evidence_window.py",
    "src/compliancegpt/pipeline/odp_policy.py",
    "src/compliancegpt/pipeline/pipeline.py",
    "src/compliancegpt/generator/generator.py",
    "src/compliancegpt/generator/verifier/verifier.py",
    "tests/test_odp_policy.py",
    "tests/test_pipeline_generator_injection.py",
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")


def _git_head(repo_root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def _assert_sha256(path: Path, expected: str) -> None:
    actual = file_sha256(path)
    if actual != expected:
        raise AssertionError(f"SHA-256 mismatch for {path}: {actual} != {expected}")


def _read_jsonl_bytes(payload: bytes) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line_number, raw in enumerate(payload.decode("utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        if not isinstance(row, dict):
            raise ValueError(f"JSONL row {line_number} is not an object.")
        validate_prepared_context(row)
        rows.append(row)
    return rows


def _read_csv_bytes(payload: bytes) -> List[Dict[str, str]]:
    text = payload.decode("utf-8-sig")
    return [dict(row) for row in csv.DictReader(io.StringIO(text))]


def _read_contract(row: Mapping[str, str]) -> Dict[str, Any]:
    value = json.loads(str(row.get("contract_json", "") or "{}"))
    if not isinstance(value, dict):
        raise ValueError("Frozen contract_json is not an object.")
    return value


class _DummyConfig:
    _commit_hash = MODEL_REVISION


class _FrozenModelIdentity:
    config = _DummyConfig()


class _FrozenTokenizerIdentity:
    pad_token_id = 0
    eos_token_id = 1
    init_kwargs = {"_commit_hash": MODEL_REVISION}


class FrozenSelectorGenerator:
    """Return the exact selector contract recorded in matched-window v3."""

    def __init__(self, entries: Sequence[Mapping[str, Any]]) -> None:
        self._by_question: Dict[str, Dict[str, Any]] = {}
        for entry in entries:
            question = str(entry["question"])
            if question in self._by_question:
                raise AssertionError("Frozen selector questions are not unique.")
            self._by_question[question] = dict(entry)

    def generate(
        self,
        question: str,
        docs: Sequence[Mapping[str, Any]],
        _profile: Mapping[str, Any],
    ) -> Dict[str, Any]:
        entry = self._by_question.get(str(question))
        if entry is None:
            raise KeyError("No frozen selector output for question.")
        actual_ids = [str(doc.get("id", "") or "") for doc in docs]
        expected_ids = list(entry["evidence_window_source_ids"])
        if actual_ids != expected_ids:
            raise AssertionError(
                f"Evidence window changed for query {entry['query_id']}: "
                f"{actual_ids} != {expected_ids}"
            )
        return copy.deepcopy(dict(entry["selector_raw"]))


def _load_and_validate_inputs(repo_root: Path) -> Dict[str, Any]:
    if ODP_POLICY_VERSION != EXPECTED_POLICY_VERSION:
        raise AssertionError(
            f"Expected PRESERVE policy v{EXPECTED_POLICY_VERSION}, got v{ODP_POLICY_VERSION}."
        )
    if ODP_POLICY_PATCH_ID != EXPECTED_PATCH_ID:
        raise AssertionError(f"Unexpected ODP patch ID: {ODP_POLICY_PATCH_ID}")

    archive = repo_root / ARCHIVE_RELATIVE
    _assert_sha256(archive, ARCHIVE_SHA256)

    loaded: Dict[str, Any] = {
        "archive": archive,
        "revisions": {},
        "archive_member_hashes": {},
    }
    with zipfile.ZipFile(archive) as bundle:
        for member, expected in ARCHIVE_MEMBER_SHA256.items():
            payload = bundle.read(member)
            actual = _sha256_bytes(payload)
            if actual != expected:
                raise AssertionError(f"Archive member hash changed for {member}.")
            loaded["archive_member_hashes"][member] = actual

        frozen_config = json.loads(bundle.read("run_config.json"))
        if frozen_config.get("repo_commit") != FROZEN_RUNTIME_COMMIT:
            raise AssertionError("Frozen matched-window runtime commit changed.")
        if frozen_config.get("model_id") != MODEL_ID:
            raise AssertionError("Frozen model ID changed.")
        if frozen_config.get("model_revision") != MODEL_REVISION:
            raise AssertionError("Frozen model revision changed.")

        for revision in ("rev4", "rev5"):
            spec = REPO_INPUTS[revision]
            gold_path = repo_root / spec["gold"]
            ccs_path = repo_root / spec["ccs"]
            odp_path = repo_root / spec["odp_registry"]
            _assert_sha256(gold_path, spec["gold_sha256"])
            _assert_sha256(ccs_path, spec["ccs_sha256"])
            if not odp_path.is_file():
                raise FileNotFoundError(odp_path)

            expected_total = 36 if revision == "rev4" else 100
            gold_by_id = load_gold_rows(gold_path, expected_rows=expected_total)
            applicable_ids = tuple(
                query_id
                for query_id, row in gold_by_id.items()
                if str(row.get("resolution_policy", "") or "").strip().upper()
                == "PRESERVE"
            )
            if applicable_ids != EXPECTED_QUERY_IDS[revision]:
                raise AssertionError(
                    f"Applicable {revision} IDs changed: {applicable_ids}"
                )

            context_member = f"contexts/{revision}_prepared_contexts.jsonl"
            contract_member = f"contracts/{revision}_compliancegpt.csv"
            all_contexts = _read_jsonl_bytes(bundle.read(context_member))
            all_contract_rows = _read_csv_bytes(bundle.read(contract_member))
            context_by_id = {str(row["query_id"]): row for row in all_contexts}
            contract_by_id = {str(row["query_id"]): row for row in all_contract_rows}
            if len(context_by_id) != expected_total or len(contract_by_id) != expected_total:
                raise AssertionError(f"Frozen {revision} row count changed.")

            contexts: List[Dict[str, Any]] = []
            selector_entries: List[Dict[str, Any]] = []
            for query_id in applicable_ids:
                context = dict(context_by_id[query_id])
                contract_row = dict(contract_by_id[query_id])
                contract = _read_contract(contract_row)
                selector_raw = dict(
                    ((contract.get("debug") or {}).get("selector_raw") or {})
                )
                if not selector_raw:
                    raise AssertionError(f"Missing frozen selector output: {revision}/{query_id}")
                question = str(gold_by_id[query_id].get("question", "") or "")
                if question != str(context.get("question", "") or ""):
                    raise AssertionError(f"Question changed: {revision}/{query_id}")
                if question != str(contract_row.get("question", "") or ""):
                    raise AssertionError(f"Contract question changed: {revision}/{query_id}")

                window_ids = list(
                    (context.get("evidence_window_manifest") or {}).get("source_ids", [])
                    or []
                )
                selector_ids = [
                    str(span.get("source_id", "") or "")
                    for span in list(selector_raw.get("evidence_spans", []) or [])
                    if isinstance(span, dict)
                ]
                if not selector_ids or any(source_id not in window_ids for source_id in selector_ids):
                    raise AssertionError(
                        f"Frozen selector IDs are empty or outside the window: {revision}/{query_id}"
                    )

                contexts.append(context)
                selector_entries.append(
                    {
                        "revision": revision,
                        "query_id": query_id,
                        "question": question,
                        "context_sha256": str(context["context_sha256"]),
                        "evidence_window_sha256": str(
                            (context["evidence_window_manifest"] or {})["sha256"]
                        ),
                        "evidence_window_source_ids": window_ids,
                        "selector_raw": selector_raw,
                        "selector_raw_sha256": _canonical_sha256(selector_raw),
                        "selector_source_ids": selector_ids,
                    }
                )

            loaded["revisions"][revision] = {
                "gold_path": gold_path,
                "ccs_path": ccs_path,
                "odp_registry_path": odp_path,
                "gold_by_id": {query_id: gold_by_id[query_id] for query_id in applicable_ids},
                "contexts": contexts,
                "selector_entries": selector_entries,
            }
    return loaded


def _build_pipeline(revision: str, spec: Mapping[str, Any]) -> ComplianceGPTPipeline:
    retriever = FrozenCCSRetriever.from_jsonl(spec["ccs_path"])
    generator = FrozenSelectorGenerator(spec["selector_entries"])
    return ComplianceGPTPipeline(
        framework_version=revision,
        model_id=MODEL_ID,
        model_revision=MODEL_REVISION,
        shared_model=_FrozenModelIdentity(),
        shared_tokenizer=_FrozenTokenizerIdentity(),
        generator_instance=generator,
        retriever_instance=retriever,
        use_qur=False,
        doc_filter_mode="prefer_smt_keep_params",
        ccs_path=str(spec["ccs_path"]),
        odp_registry_path=str(spec["odp_registry_path"]),
        strict_ccs_assert=True,
        resolution_policy="PRESERVE",
        enable_hierarchy_closure=False,
    )


def _code_manifest(repo_root: Path) -> Dict[str, str]:
    manifest: Dict[str, str] = {}
    for relative in CODE_PATHS:
        path = repo_root / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        manifest[relative] = file_sha256(path)
    return manifest


def _analyze_rows(
    revision: str,
    output_csv: Path,
    selector_entries: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    expected_by_id = {str(entry["query_id"]): dict(entry) for entry in selector_entries}
    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if tuple(row["query_id"] for row in rows) != EXPECTED_QUERY_IDS[revision]:
        raise AssertionError(f"Output order or row identity changed for {revision}.")

    audits: List[Dict[str, Any]] = []
    contracts: List[Dict[str, Any]] = []
    for row in rows:
        query_id = str(row["query_id"])
        expected = expected_by_id[query_id]
        contract = _read_contract(row)
        contracts.append(contract)
        selector_raw = dict(((contract.get("debug") or {}).get("selector_raw") or {}))
        selector_hash = _canonical_sha256(selector_raw)
        answer_text = str(contract.get("answer_text", "") or "")
        visible_ids, has_assignment = extract_odp_ids(answer_text)
        visible_markers = bool(visible_ids or has_assignment)
        evidence_spans = list(contract.get("evidence_spans", []) or [])
        reconstructed = "\n\n".join(
            str(span.get("span_text", "") or "")
            for span in evidence_spans
            if isinstance(span, dict)
        ).strip()
        final_ids = [
            str(span.get("source_id", "") or "")
            for span in evidence_spans
            if isinstance(span, dict)
        ]
        window_ids = list(expected["evidence_window_source_ids"])
        validity = dict(contract.get("validity_check", {}) or {})
        odp_required = list(contract.get("odp_required_list", []) or [])
        status = str(contract.get("status", "") or "")
        audit = {
            "revision": revision,
            "query_id": query_id,
            "context_sha256": str(row["context_sha256"]),
            "evidence_window_sha256": str(row["evidence_window_sha256"]),
            "selector_raw_sha256": selector_hash,
            "selector_unchanged": selector_hash == expected["selector_raw_sha256"],
            "selector_source_ids": list(expected["selector_source_ids"]),
            "final_source_ids": final_ids,
            "final_ids_within_frozen_window": all(source_id in window_ids for source_id in final_ids),
            "visible_odp_ids": visible_ids,
            "visible_assignment_marker": has_assignment,
            "visible_unresolved_marker": visible_markers,
            "status": status,
            "params_required_for_visible_marker": (
                visible_markers and status == "PARAMS_REQUIRED"
            ),
            "no_ok_with_visible_marker": not (visible_markers and status == "OK"),
            "odp_required_list": odp_required,
            "nonempty_required_list": bool(odp_required),
            "literal_placeholders_preserved": answer_text == reconstructed,
            "ask_list_empty": list(contract.get("ask_list", []) or []) == [],
            "runtime_contract_valid": bool(validity.get("is_pass", False)),
            "runtime_contract_errors": list(validity.get("errors", []) or []),
            "offline_verifier_pass": bool(contract.get("verifier_pass", False)),
            "offline_verifier_errors": list(contract.get("verifier_errors", []) or []),
            "contract_sha256": _canonical_sha256(contract),
        }
        if audit["context_sha256"] != expected["context_sha256"]:
            raise AssertionError(f"Context hash changed: {revision}/{query_id}")
        if audit["evidence_window_sha256"] != expected["evidence_window_sha256"]:
            raise AssertionError(f"Evidence-window hash changed: {revision}/{query_id}")
        audits.append(audit)
    return audits, contracts


def _acceptance_summary(audits: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    total = len(audits)

    def count(field: str) -> int:
        return sum(bool(row.get(field)) for row in audits)

    checks = {
        "row_count_is_8": total == 8,
        "all_rows_exercise_visible_preserve_markers": count("visible_unresolved_marker") == total,
        "all_visible_marker_rows_are_params_required": (
            count("params_required_for_visible_marker") == total
        ),
        "no_ok_contract_has_a_visible_marker": count("no_ok_with_visible_marker") == total,
        "all_required_lists_are_nonempty": count("nonempty_required_list") == total,
        "all_placeholders_are_literal": count("literal_placeholders_preserved") == total,
        "all_ask_lists_are_empty": count("ask_list_empty") == total,
        "all_runtime_contracts_are_valid": count("runtime_contract_valid") == total,
        "all_selectors_are_unchanged": count("selector_unchanged") == total,
        "all_final_ids_are_in_frozen_windows": count("final_ids_within_frozen_window") == total,
    }
    return {
        "row_count": total,
        "counts": {
            field: count(field)
            for field in (
                "visible_unresolved_marker",
                "params_required_for_visible_marker",
                "no_ok_with_visible_marker",
                "nonempty_required_list",
                "literal_placeholders_preserved",
                "ask_list_empty",
                "runtime_contract_valid",
                "offline_verifier_pass",
                "selector_unchanged",
                "final_ids_within_frozen_window",
            )
        },
        "acceptance_checks": checks,
        "accepted": all(checks.values()),
    }


def _write_audit_csv(path: Path, audits: Sequence[Mapping[str, Any]]) -> None:
    fieldnames = [
        "revision",
        "query_id",
        "context_sha256",
        "evidence_window_sha256",
        "selector_raw_sha256",
        "selector_unchanged",
        "visible_unresolved_marker",
        "visible_odp_ids",
        "visible_assignment_marker",
        "status",
        "params_required_for_visible_marker",
        "no_ok_with_visible_marker",
        "odp_required_list",
        "nonempty_required_list",
        "literal_placeholders_preserved",
        "ask_list_empty",
        "runtime_contract_valid",
        "runtime_contract_errors",
        "offline_verifier_pass",
        "offline_verifier_errors",
        "final_ids_within_frozen_window",
        "selector_source_ids",
        "final_source_ids",
        "contract_sha256",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for audit in audits:
            row = dict(audit)
            for key in (
                "visible_odp_ids",
                "odp_required_list",
                "runtime_contract_errors",
                "offline_verifier_errors",
                "selector_source_ids",
                "final_source_ids",
            ):
                row[key] = "|".join(str(item) for item in list(row.get(key, []) or []))
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _summary_markdown(summary: Mapping[str, Any]) -> str:
    counts = dict(summary["counts"])
    total = int(summary["row_count"])
    accepted = bool(summary["accepted"])
    return f"""# RQ2 PRESERVE End-to-End Replay

Result identity: `{RESULT_ID}`  
PRESERVE policy artifact: `v{ODP_POLICY_VERSION}` (`{ODP_POLICY_PATCH_ID}`)

The replay processed all eight gold rows whose registered resolution policy is
`PRESERVE`: six Revision 5 rows and two Revision 4 rows. It reused the frozen
prepared contexts and exact selector outputs from matched-window v3, then ran
the corrected deterministic pipeline through evidence filling, PRESERVE policy,
contract construction, Runtime Verifier, and offline verifier. It used no live
retrieval and no new model inference.

| Acceptance measure | Result |
|---|---:|
| Applicable rows completed | {total}/8 |
| Rows with visible unresolved markers | {counts['visible_unresolved_marker']}/{total} |
| Visible-marker rows returning `PARAMS_REQUIRED` | {counts['params_required_for_visible_marker']}/{total} |
| Rows preserving literal placeholder text | {counts['literal_placeholders_preserved']}/{total} |
| Rows with empty `ask_list` under PRESERVE | {counts['ask_list_empty']}/{total} |
| Runtime-valid contracts | {counts['runtime_contract_valid']}/{total} |
| Frozen selector outputs unchanged | {counts['selector_unchanged']}/{total} |
| Final identifiers contained in frozen windows | {counts['final_ids_within_frozen_window']}/{total} |
| Offline strict-verifier passes | {counts['offline_verifier_pass']}/{total} |

Registered acceptance result: **{'PASS' if accepted else 'FAIL'}**.

## Interpretation boundary

This is a frozen-selector, prepared-context end-to-end replay of the corrected
deterministic PRESERVE path. It directly evaluates the branch that previously
retained placeholders while returning `OK`; it is not a new retrieval study or
a new stochastic model run. The original matched RQ2 and RQ3 results remain
unchanged because those reported runs used `ASK`.
"""


def _audit_markdown(summary: Mapping[str, Any], run_config: Mapping[str, Any]) -> str:
    lines = [
        "# Audit Record",
        "",
        f"- Result identity: `{RESULT_ID}`",
        f"- Formal execution time (UTC): `{run_config['executed_at_utc']}`",
        f"- Execution commit: `{run_config['execution_repo_commit']}`",
        f"- Frozen defective runtime commit: `{FROZEN_RUNTIME_COMMIT}`",
        f"- Frozen matched archive SHA-256: `{ARCHIVE_SHA256}`",
        f"- Policy version: `{ODP_POLICY_VERSION}`",
        f"- Patch identity: `{ODP_POLICY_PATCH_ID}`",
        "- Live retrieval: disabled",
        "- New model inference: disabled",
        "- Selector outputs: exact frozen matched-window v3 values",
        "- Gold use: row selection and post-construction verification only",
        f"- Registered acceptance: `{'PASS' if summary['accepted'] else 'FAIL'}`",
        "",
        "Every output contract, row-level condition, input identity, code hash, and",
        "archive hash is retained in this directory. No row was excluded after the",
        "formal replay began.",
        "",
    ]
    return "\n".join(lines)


def _write_sha256sums(output_dir: Path, filename: str = "SHA256SUMS") -> None:
    target = output_dir / filename
    paths = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file()
        and path != target
        and not path.name.endswith(".zip")
        and path.name != "ARCHIVE_SHA256SUMS"
    )
    target.write_text(
        "".join(f"{file_sha256(path)}  {path.relative_to(output_dir).as_posix()}\n" for path in paths),
        encoding="utf-8",
    )


def _write_deterministic_zip(output_dir: Path) -> Path:
    archive = output_dir / f"{RESULT_ID}.zip"
    members = sorted(
        path
        for path in output_dir.rglob("*")
        if path.is_file() and path != archive and path.name != "ARCHIVE_SHA256SUMS"
    )
    with zipfile.ZipFile(
        archive,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as bundle:
        for path in members:
            relative = path.relative_to(output_dir).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 10, 3, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes())
    (output_dir / "ARCHIVE_SHA256SUMS").write_text(
        f"{file_sha256(archive)}  {archive.name}\n",
        encoding="utf-8",
    )
    return archive


def _ensure_new_output_dir(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(
            f"Refusing to mix or overwrite a frozen result directory: {path}"
        )
    path.mkdir(parents=True, exist_ok=True)


def run_formal(repo_root: Path, output_dir: Path, loaded: Mapping[str, Any]) -> Dict[str, Any]:
    _ensure_new_output_dir(output_dir)
    all_audits: List[Dict[str, Any]] = []
    run_details: Dict[str, Any] = {}

    inputs_dir = output_dir / "applicable_inputs"
    contracts_dir = output_dir / "contracts"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    contracts_dir.mkdir(parents=True, exist_ok=True)

    for revision in ("rev4", "rev5"):
        spec = loaded["revisions"][revision]
        _write_jsonl(inputs_dir / f"{revision}_prepared_contexts.jsonl", spec["contexts"])
        _write_jsonl(inputs_dir / f"{revision}_frozen_selectors.jsonl", spec["selector_entries"])
        pipeline = _build_pipeline(revision, spec)
        output_csv = contracts_dir / f"{revision}_preserve_replay.csv"
        run_details[revision] = run_prepared_contexts(
            pipeline=pipeline,
            contexts=spec["contexts"],
            gold_rows_by_id=spec["gold_by_id"],
            system_name="compliancegpt_preserve_v1.1_frozen_selector_replay",
            output_csv=output_csv,
            top_k=12,
            resume=False,
            progress_every=1,
        )
        audits, contracts = _analyze_rows(revision, output_csv, spec["selector_entries"])
        all_audits.extend(audits)
        _write_jsonl(contracts_dir / f"{revision}_contracts.jsonl", contracts)

    summary = _acceptance_summary(all_audits)
    _write_audit_csv(output_dir / "per_row_audit.csv", all_audits)

    code_hashes = _code_manifest(repo_root)
    executed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    run_config = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "executed_at_utc": executed_at,
        "execution_repo_commit": _git_head(repo_root),
        "frozen_defective_runtime_commit": FROZEN_RUNTIME_COMMIT,
        "policy_version": ODP_POLICY_VERSION,
        "policy_patch_id": ODP_POLICY_PATCH_ID,
        "resolution_policy": "PRESERVE",
        "sample_rule": "all gold rows with resolution_policy=PRESERVE",
        "query_ids": {key: list(value) for key, value in EXPECTED_QUERY_IDS.items()},
        "row_count": 8,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_inference": "none; exact frozen selector outputs replayed",
        "retrieval": "none; immutable prepared contexts replayed",
        "gold_use": "sample identification and post-construction verifier only",
        "frozen_archive": {
            "path": ARCHIVE_RELATIVE,
            "sha256": ARCHIVE_SHA256,
            "members": dict(loaded["archive_member_hashes"]),
        },
        "repository_inputs": {
            revision: {
                "gold_path": REPO_INPUTS[revision]["gold"],
                "gold_sha256": REPO_INPUTS[revision]["gold_sha256"],
                "ccs_path": REPO_INPUTS[revision]["ccs"],
                "ccs_sha256": REPO_INPUTS[revision]["ccs_sha256"],
                "odp_registry_path": REPO_INPUTS[revision]["odp_registry"],
                "odp_registry_sha256": file_sha256(
                    repo_root / REPO_INPUTS[revision]["odp_registry"]
                ),
            }
            for revision in ("rev4", "rev5")
        },
        "code_sha256": code_hashes,
        "code_manifest_sha256": _canonical_sha256(code_hashes),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "per_revision_run_details": run_details,
        "registered_acceptance_checks": list(summary["acceptance_checks"]),
    }
    _write_json(output_dir / "run_config.json", run_config)
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "SUMMARY.md").write_text(_summary_markdown(summary), encoding="utf-8")
    (output_dir / "AUDIT.md").write_text(
        _audit_markdown(summary, run_config), encoding="utf-8"
    )
    (output_dir / "README.md").write_text(_summary_markdown(summary), encoding="utf-8")
    _write_sha256sums(output_dir)
    archive = _write_deterministic_zip(output_dir)

    if not summary["accepted"]:
        raise AssertionError(
            f"Formal replay failed registered acceptance; preserved at {output_dir}"
        )
    return {
        "result_id": RESULT_ID,
        "accepted": True,
        "summary": summary,
        "archive": str(archive),
        "archive_sha256": file_sha256(archive),
    }


def parse_args() -> argparse.Namespace:
    default_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=default_root
        / "experiments/answerer_comparison/rq2_preserve_replay/results_v1",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Validate frozen identities and pipeline construction without producing contracts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    loaded = _load_and_validate_inputs(repo_root)
    for revision in ("rev4", "rev5"):
        _build_pipeline(revision, loaded["revisions"][revision])
    if args.preflight:
        print(
            json.dumps(
                {
                    "preflight": "PASS",
                    "result_id": RESULT_ID,
                    "policy_version": ODP_POLICY_VERSION,
                    "patch_id": ODP_POLICY_PATCH_ID,
                    "applicable_rows": sum(len(ids) for ids in EXPECTED_QUERY_IDS.values()),
                    "formal_outputs_written": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    result = run_formal(repo_root, args.output_dir.resolve(), loaded)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
