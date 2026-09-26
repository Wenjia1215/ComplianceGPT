#!/usr/bin/env python3
"""Run the no-LLM selector ablation over the frozen RQ2 v3 windows.

The ablation bypasses the selector and retains every clause record in each
immutable evidence window.  It performs no retrieval, model inference,
fallback, rescue, or hierarchy expansion.  The ordinary ASK policy and the
existing gold-aware offline verifier are then applied to the resulting
deterministic citation contract.

This experiment has its own result identity and never edits the frozen RQ2 v3
archive.  It reports both evidence coverage and reviewer-burden measures so a
coverage increase cannot be interpreted without its concision cost.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import shutil
import statistics
import sys
import zipfile
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


RESULT_ID = "rq2_no_selector_v1"
SCHEMA_VERSION = "compliancegpt-rq2-no-selector-v1"
EXPECTED_ROWS = {"rev5": 100, "rev4": 36}
CONTEXT_MEMBERS = {
    "rev5": "contexts/rev5_prepared_contexts.jsonl",
    "rev4": "contexts/rev4_prepared_contexts.jsonl",
}
SELECTOR_MEMBERS = {
    "rev5": "contracts/rev5_compliancegpt.csv",
    "rev4": "contracts/rev4_compliancegpt.csv",
}
INPUTS = {
    "rev5": {
        "gold": "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv",
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl",
    },
    "rev4": {
        "gold": "data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv",
        "ccs": "data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl",
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


def manifest_path(path: Path, repo_root: Path) -> str:
    """Record repository inputs portably and external inputs explicitly."""
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


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


def read_jsonl_member(archive: zipfile.ZipFile, member: str) -> Tuple[List[Dict[str, Any]], str]:
    payload = archive.read(member)
    rows = [json.loads(line) for line in payload.decode("utf-8").splitlines() if line.strip()]
    return rows, sha256_bytes(payload)


def read_csv_member(archive: zipfile.ZipFile, member: str) -> Tuple[Dict[str, Dict[str, str]], str]:
    payload = archive.read(member)
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8"), newline=""))
    rows = {str(row["query_id"]): dict(row) for row in reader}
    return rows, sha256_bytes(payload)


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
    if not values:
        return {
            "min": float("nan"),
            "mean": float("nan"),
            "median": float("nan"),
            "p95": float("nan"),
            "max": float("nan"),
        }
    floats = [float(value) for value in values]
    return {
        "min": min(floats),
        "mean": statistics.fmean(floats),
        "median": statistics.median(floats),
        "p95": percentile(floats, 0.95),
        "max": max(floats),
    }


def exact_mcnemar(left_only: int, right_only: int) -> float:
    discordant = int(left_only) + int(right_only)
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(left_only, right_only) + 1))
    return min(1.0, 2.0 * tail / (2.0**discordant))


def normalized_source_ids(value: Any) -> List[str]:
    return [item.lower() for item in listish(value)]


def normalized_odp_ids(value: Any, normalize_odp_id: Any) -> List[str]:
    return sorted(
        {
            normalized
            for item in listish(value)
            if (normalized := normalize_odp_id(item))
        }
    )


def build_no_selector_contract(
    *,
    context: Mapping[str, Any],
    param_ids: set[str],
    key_map: Mapping[str, str],
    apply_odp_policy_to_answer: Any,
    canonicalize_param_list: Any,
    assignment_sentinel: str,
) -> Dict[str, Any]:
    window = [dict(record) for record in list(context.get("evidence_window", []) or [])]
    if not window:
        raise ValueError(f"Prepared context {context.get('query_id')} has an empty evidence window.")

    spans: List[Dict[str, str]] = []
    seen = set()
    for record in window:
        source_id = str(record.get("id", "") or "").strip()
        text = str(record.get("text", "") or "").strip()
        kind = str(record.get("kind", "") or "").strip().lower()
        if not source_id or not text:
            raise ValueError(f"Window record lacks id or text for query {context.get('query_id')}.")
        if kind not in {"smt", "gdn"}:
            raise ValueError(
                f"No-selector window contains non-clause kind {kind!r} for query {context.get('query_id')}."
            )
        if source_id in seen:
            raise ValueError(f"Duplicate window id {source_id!r} for query {context.get('query_id')}.")
        seen.add(source_id)
        spans.append({"source_id": source_id, "span_text": text})

    answer_text = "\n\n".join(span["span_text"] for span in spans).strip()
    answer_text, raw_required, status = apply_odp_policy_to_answer(
        answer_text=answer_text,
        policy="ASK",
        org_profile={},
    )
    canonical_required = canonicalize_param_list(
        raw_list=list(raw_required),
        param_ids=param_ids,
        key_map=dict(key_map),
        assignment_sentinel=assignment_sentinel,
    )
    required = canonical_required or list(dict.fromkeys(str(item).strip() for item in raw_required if str(item).strip()))
    citations = [span["source_id"] for span in spans]
    citation_text = ", ".join(citations)
    suffix = "NIST SP 800-53 Rev. 5" if str(context["framework_version"]) == "rev5" else "NIST SP 800-53 Rev. 4"

    return {
        "question": str(context["question"]),
        "framework_version": str(context["framework_version"]),
        "answer_text": answer_text,
        "answer_text_with_citations": f"{answer_text}\n\nCitations: {citation_text} ({suffix})",
        "evidence_spans": spans,
        "status": str(status),
        "odp_required_list": required,
        "ask_list": [],
        "primary_citation": citations[0],
        "all_citations": citation_text,
        "selected_source_ids": citations,
        "debug": {
            "result_id": RESULT_ID,
            "selector_policy": "bypassed_retain_entire_frozen_window",
            "selector_called": False,
            "fallback_used": False,
            "rescue_used": False,
            "hierarchy_closure_used": False,
            "prepared_context_sha256": str(context.get("context_sha256", "")),
            "evidence_window": dict(context.get("evidence_window_manifest", {}) or {}),
            "per_identifier_provenance": [
                {"source_id": source_id, "source": "frozen_window"}
                for source_id in citations
            ],
        },
    }


def evaluate_contract(
    *,
    contract: Mapping[str, Any],
    gold_row: Mapping[str, Any],
    corpus: Mapping[str, str],
    revision: str,
    verify_answer: Any,
    verify_contract_validity: Any,
    normalize_odp_id: Any,
) -> Dict[str, Any]:
    verification = verify_answer(
        json_output=dict(contract),
        gold_row=dict(gold_row),
        corpus=dict(corpus),
        org_profile={},
        corpus_version=revision,
        strict_extras=False,
        strict_verbatim=True,
        strict_version=False,
    )
    runtime_pass, runtime_errors = verify_contract_validity(
        dict(contract),
        corpus=dict(corpus),
        org_profile={},
        strict_verbatim=True,
    )
    metrics = dict(verification.metrics)
    selected = [str(span.get("source_id", "")).strip().lower() for span in contract.get("evidence_spans", [])]
    selected = list(dict.fromkeys(item for item in selected if item))
    gold = normalized_source_ids(gold_row.get("gold_control_path", ""))
    gold_set = set(gold)
    selected_set = set(selected)
    gold_odps = normalized_odp_ids(gold_row.get("odp_required", ""), normalize_odp_id)
    generated_odps = normalized_odp_ids(contract.get("odp_required_list", []), normalize_odp_id)
    answer = str(contract.get("answer_text", "") or "")
    citations = str(contract.get("all_citations", "") or "")

    return {
        "offline_strict_pass": bool(verification.is_pass),
        "offline_error_tags": list(verification.error_tags),
        "offline_metrics": metrics,
        "runtime_contract_pass": bool(runtime_pass),
        "runtime_error_tags": list(runtime_errors),
        "full_gold_clause_coverage": float(metrics.get("doc_recall", 0.0) or 0.0) >= 1.0,
        "any_gold_clause": bool(gold_set & selected_set),
        "right_control": float(metrics.get("control_recall", 0.0) or 0.0) >= 1.0,
        "gold_clause_precision": (
            len(gold_set & selected_set) / len(selected_set) if selected_set else 0.0
        ),
        "selected_clause_count": len(selected),
        "gold_clause_count": len(gold_set),
        "additional_evidence_count": len(selected_set - gold_set),
        "answer_char_count": len(answer),
        "answer_word_count": len(answer.split()),
        "citation_char_count": len(citations),
        "status": str(contract.get("status", "") or ""),
        "gold_odp_count": len(gold_odps),
        "generated_odp_count": len(generated_odps),
        "exact_odp_list": set(gold_odps) == set(generated_odps),
        "gold_odps": gold_odps,
        "generated_odps": generated_odps,
    }


def aggregate(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    n = len(rows)
    odp_rows = [row for row in rows if int(row["gold_odp_count"]) > 0]
    non_odp_rows = [row for row in rows if int(row["gold_odp_count"]) == 0]

    def count(name: str) -> int:
        return sum(bool(row[name]) for row in rows)

    def count_rate(name: str) -> Dict[str, float]:
        value = count(name)
        return {"count": value, "rate": value / n if n else float("nan")}

    return {
        "n_questions": n,
        "offline_strict_pass": count_rate("offline_strict_pass"),
        "runtime_contract_pass": count_rate("runtime_contract_pass"),
        "full_gold_clause_coverage": count_rate("full_gold_clause_coverage"),
        "right_control": count_rate("right_control"),
        "any_gold_clause": count_rate("any_gold_clause"),
        "status_counts": dict(sorted(Counter(str(row["status"]) for row in rows).items())),
        "odp_subset": {
            "n": len(odp_rows),
            "params_required_count": sum(row["status"] == "PARAMS_REQUIRED" for row in odp_rows),
            "params_required_rate": (
                sum(row["status"] == "PARAMS_REQUIRED" for row in odp_rows) / len(odp_rows)
                if odp_rows
                else float("nan")
            ),
            "exact_odp_list_count": sum(bool(row["exact_odp_list"]) for row in odp_rows),
            "exact_odp_list_rate": (
                sum(bool(row["exact_odp_list"]) for row in odp_rows) / len(odp_rows)
                if odp_rows
                else float("nan")
            ),
        },
        "non_odp_status_expansion": {
            "n": len(non_odp_rows),
            "params_required_count": sum(row["status"] == "PARAMS_REQUIRED" for row in non_odp_rows),
            "params_required_rate": (
                sum(row["status"] == "PARAMS_REQUIRED" for row in non_odp_rows) / len(non_odp_rows)
                if non_odp_rows
                else float("nan")
            ),
        },
        "review_burden": {
            "selected_clause_count": distribution([float(row["selected_clause_count"]) for row in rows]),
            "additional_evidence_count": distribution([float(row["additional_evidence_count"]) for row in rows]),
            "gold_clause_precision": distribution([float(row["gold_clause_precision"]) for row in rows]),
            "answer_char_count": distribution([float(row["answer_char_count"]) for row in rows]),
            "answer_word_count": distribution([float(row["answer_word_count"]) for row in rows]),
            "citation_char_count": distribution([float(row["citation_char_count"]) for row in rows]),
        },
    }


def paired_summary(
    selector_rows: Sequence[Mapping[str, Any]],
    no_selector_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    selector = {str(row["query_id"]): row for row in selector_rows}
    no_selector = {str(row["query_id"]): row for row in no_selector_rows}
    if set(selector) != set(no_selector):
        raise AssertionError("Selector and no-selector row sets differ.")
    ids = sorted(selector, key=lambda value: (0, int(value)) if value.isdigit() else (1, value))

    def paired(field: str) -> Dict[str, Any]:
        no_only = sum(bool(no_selector[qid][field]) and not bool(selector[qid][field]) for qid in ids)
        selector_only = sum(bool(selector[qid][field]) and not bool(no_selector[qid][field]) for qid in ids)
        both = sum(bool(no_selector[qid][field]) and bool(selector[qid][field]) for qid in ids)
        neither = len(ids) - no_only - selector_only - both
        return {
            "no_selector_only": no_only,
            "selector_only": selector_only,
            "both": both,
            "neither": neither,
            "exact_mcnemar_two_sided_p": exact_mcnemar(no_only, selector_only),
        }

    return {
        "offline_strict_pass": paired("offline_strict_pass"),
        "full_gold_clause_coverage": paired("full_gold_clause_coverage"),
    }


def delta_summary(selector: Mapping[str, Any], no_selector: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "offline_strict_pass_rate": no_selector["offline_strict_pass"]["rate"] - selector["offline_strict_pass"]["rate"],
        "full_gold_clause_coverage_rate": no_selector["full_gold_clause_coverage"]["rate"] - selector["full_gold_clause_coverage"]["rate"],
        "right_control_rate": no_selector["right_control"]["rate"] - selector["right_control"]["rate"],
        "mean_selected_clause_count": no_selector["review_burden"]["selected_clause_count"]["mean"] - selector["review_burden"]["selected_clause_count"]["mean"],
        "mean_additional_evidence_count": no_selector["review_burden"]["additional_evidence_count"]["mean"] - selector["review_burden"]["additional_evidence_count"]["mean"],
        "mean_gold_clause_precision": no_selector["review_burden"]["gold_clause_precision"]["mean"] - selector["review_burden"]["gold_clause_precision"]["mean"],
        "mean_answer_word_count": no_selector["review_burden"]["answer_word_count"]["mean"] - selector["review_burden"]["answer_word_count"]["mean"],
        "mean_citation_char_count": no_selector["review_burden"]["citation_char_count"]["mean"] - selector["review_burden"]["citation_char_count"]["mean"],
        "exact_odp_list_rate": no_selector["odp_subset"]["exact_odp_list_rate"] - selector["odp_subset"]["exact_odp_list_rate"],
        "non_odp_status_expansion_rate": no_selector["non_odp_status_expansion"]["params_required_rate"] - selector["non_odp_status_expansion"]["params_required_rate"],
    }


def fmt_rate(value: Mapping[str, Any]) -> str:
    return f"{int(value['count'])}/{int(value.get('n', 0) or 0)}" if "n" in value else f"{float(value['rate']):.3f}"


def render_summary(summary: Mapping[str, Any]) -> str:
    lines = [
        "# RQ2 No-Selector Ablation",
        "",
        f"Result identity: `{RESULT_ID}`",
        "",
        "The no-selector path retains every record in each frozen RQ2 v3 evidence window. It performs no model inference, fallback, rescue, or hierarchy expansion.",
        "",
    ]
    for revision in ("rev5", "rev4"):
        block = summary["revisions"][revision]
        selector = block["selector_v3"]
        no_selector = block["no_selector_v1"]
        delta = block["delta_no_selector_minus_selector"]
        lines.extend(
            [
                f"## {revision.upper()}",
                "",
                "| Measure | Selector v3 | No selector v1 | Delta |",
                "|---|---:|---:|---:|",
                f"| Offline strict pass | {selector['offline_strict_pass']['count']}/{selector['n_questions']} ({selector['offline_strict_pass']['rate']:.3f}) | {no_selector['offline_strict_pass']['count']}/{no_selector['n_questions']} ({no_selector['offline_strict_pass']['rate']:.3f}) | {delta['offline_strict_pass_rate']:+.3f} |",
                f"| Full gold-clause coverage | {selector['full_gold_clause_coverage']['count']}/{selector['n_questions']} ({selector['full_gold_clause_coverage']['rate']:.3f}) | {no_selector['full_gold_clause_coverage']['count']}/{no_selector['n_questions']} ({no_selector['full_gold_clause_coverage']['rate']:.3f}) | {delta['full_gold_clause_coverage_rate']:+.3f} |",
                f"| Right governing control | {selector['right_control']['count']}/{selector['n_questions']} ({selector['right_control']['rate']:.3f}) | {no_selector['right_control']['count']}/{no_selector['n_questions']} ({no_selector['right_control']['rate']:.3f}) | {delta['right_control_rate']:+.3f} |",
                f"| Mean selected clauses | {selector['review_burden']['selected_clause_count']['mean']:.2f} | {no_selector['review_burden']['selected_clause_count']['mean']:.2f} | {delta['mean_selected_clause_count']:+.2f} |",
                f"| Mean additional clauses | {selector['review_burden']['additional_evidence_count']['mean']:.2f} | {no_selector['review_burden']['additional_evidence_count']['mean']:.2f} | {delta['mean_additional_evidence_count']:+.2f} |",
                f"| Mean gold-clause precision | {selector['review_burden']['gold_clause_precision']['mean']:.3f} | {no_selector['review_burden']['gold_clause_precision']['mean']:.3f} | {delta['mean_gold_clause_precision']:+.3f} |",
                f"| Mean answer words | {selector['review_burden']['answer_word_count']['mean']:.1f} | {no_selector['review_burden']['answer_word_count']['mean']:.1f} | {delta['mean_answer_word_count']:+.1f} |",
                f"| Mean citation characters | {selector['review_burden']['citation_char_count']['mean']:.1f} | {no_selector['review_burden']['citation_char_count']['mean']:.1f} | {delta['mean_citation_char_count']:+.1f} |",
                f"| Exact ODP-list agreement | {selector['odp_subset']['exact_odp_list_count']}/{selector['odp_subset']['n']} ({selector['odp_subset']['exact_odp_list_rate']:.3f}) | {no_selector['odp_subset']['exact_odp_list_count']}/{no_selector['odp_subset']['n']} ({no_selector['odp_subset']['exact_odp_list_rate']:.3f}) | {delta['exact_odp_list_rate']:+.3f} |",
                f"| `PARAMS_REQUIRED` on author-labeled non-ODP rows | {selector['non_odp_status_expansion']['params_required_count']}/{selector['non_odp_status_expansion']['n']} ({selector['non_odp_status_expansion']['params_required_rate']:.3f}) | {no_selector['non_odp_status_expansion']['params_required_count']}/{no_selector['non_odp_status_expansion']['n']} ({no_selector['non_odp_status_expansion']['params_required_rate']:.3f}) | {delta['non_odp_status_expansion_rate']:+.3f} |",
                "",
                f"No-selector p95 selected clauses: {no_selector['review_burden']['selected_clause_count']['p95']:.1f}; p95 answer words: {no_selector['review_burden']['answer_word_count']['p95']:.1f}.",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation boundary",
            "",
            "Higher coverage does not by itself establish a better operational answer. The additional-evidence, precision, and answer-length measures quantify the review burden created by retaining the whole window. Non-ODP status expansion is reported descriptively and is not called a false-positive rate without independent adjudication.",
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
    output_dir.mkdir(parents=True)

    sys.path.insert(0, str(repo_root / "src"))
    from answerer_comparison.matched_window_runner import (  # type: ignore
        load_ccs,
        load_gold_rows,
        validate_prepared_context,
    )
    from compliancegpt.generator.verifier.verifier import (  # type: ignore
        normalize_odp_id,
        verify_answer,
        verify_contract_validity,
    )
    from compliancegpt.pipeline.odp_policy import (  # type: ignore
        ASSIGNMENT_REQUIRED_SENTINEL,
        apply_odp_policy_to_answer,
    )
    from compliancegpt.pipeline.pipeline import (  # type: ignore
        _build_param_key_to_canonical,
        _canonicalize_param_list,
    )

    if not frozen_archive.is_file():
        raise FileNotFoundError(frozen_archive)

    frozen_hash_before = sha256_file(frozen_archive)
    contexts_by_revision: Dict[str, List[Dict[str, Any]]] = {}
    selector_csv_by_revision: Dict[str, Dict[str, Dict[str, str]]] = {}
    member_hashes: Dict[str, str] = {}
    with zipfile.ZipFile(frozen_archive, "r") as archive:
        for revision in ("rev5", "rev4"):
            contexts, context_hash = read_jsonl_member(archive, CONTEXT_MEMBERS[revision])
            selector_rows, selector_hash = read_csv_member(archive, SELECTOR_MEMBERS[revision])
            if len(contexts) != EXPECTED_ROWS[revision]:
                raise AssertionError(f"Unexpected {revision} context count: {len(contexts)}")
            if len(selector_rows) != EXPECTED_ROWS[revision]:
                raise AssertionError(f"Unexpected {revision} selector count: {len(selector_rows)}")
            for context in contexts:
                validate_prepared_context(context)
            contexts_by_revision[revision] = contexts
            selector_csv_by_revision[revision] = selector_rows
            member_hashes[CONTEXT_MEMBERS[revision]] = context_hash
            member_hashes[SELECTOR_MEMBERS[revision]] = selector_hash

    summary: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "revisions": {},
    }
    all_pair_rows: List[Dict[str, Any]] = []
    output_hashes: Dict[str, str] = {}

    contract_fields = [
        "query_id",
        "framework_version",
        "result_id",
        "question",
        "context_sha256",
        "evidence_window_sha256",
        "status",
        "offline_strict_pass",
        "offline_error_tags",
        "runtime_contract_pass",
        "runtime_error_tags",
        "full_gold_clause_coverage",
        "right_control",
        "any_gold_clause",
        "gold_clause_precision",
        "selected_clause_count",
        "gold_clause_count",
        "additional_evidence_count",
        "answer_char_count",
        "answer_word_count",
        "citation_char_count",
        "gold_odp_count",
        "generated_odp_count",
        "exact_odp_list",
        "selected_source_ids",
        "odp_required_list",
        "offline_metrics_json",
        "contract_json",
    ]

    for revision in ("rev5", "rev4"):
        gold_path = repo_root / INPUTS[revision]["gold"]
        ccs_path = repo_root / INPUTS[revision]["ccs"]
        gold_by_id = load_gold_rows(gold_path, expected_rows=EXPECTED_ROWS[revision])
        ccs = load_ccs(ccs_path)
        corpus = {source_id: str(record.get("text", "") or "") for source_id, record in ccs.items()}
        param_ids = {
            source_id
            for source_id, record in ccs.items()
            if str(record.get("kind", "") or "").strip().lower() in {"odp", "prm"}
        }
        key_map = _build_param_key_to_canonical(param_ids)

        no_selector_rows: List[Dict[str, Any]] = []
        selector_rows: List[Dict[str, Any]] = []
        contract_rows: List[Dict[str, Any]] = []
        selector_csv = selector_csv_by_revision[revision]
        for context in contexts_by_revision[revision]:
            query_id = str(context["query_id"])
            gold_row = gold_by_id[query_id]
            no_selector_contract = build_no_selector_contract(
                context=context,
                param_ids=param_ids,
                key_map=key_map,
                apply_odp_policy_to_answer=apply_odp_policy_to_answer,
                canonicalize_param_list=_canonicalize_param_list,
                assignment_sentinel=ASSIGNMENT_REQUIRED_SENTINEL,
            )
            no_metrics = evaluate_contract(
                contract=no_selector_contract,
                gold_row=gold_row,
                corpus=corpus,
                revision=revision,
                verify_answer=verify_answer,
                verify_contract_validity=verify_contract_validity,
                normalize_odp_id=normalize_odp_id,
            )
            no_metrics["query_id"] = query_id
            no_metrics["question"] = str(context["question"])
            no_selector_rows.append(no_metrics)

            original_row = selector_csv[query_id]
            original_contract = json.loads(str(original_row.get("contract_json", "") or "{}"))
            selector_metrics = evaluate_contract(
                contract=original_contract,
                gold_row=gold_row,
                corpus=corpus,
                revision=revision,
                verify_answer=verify_answer,
                verify_contract_validity=verify_contract_validity,
                normalize_odp_id=normalize_odp_id,
            )
            recorded_pass = str(original_row.get("verifier_pass", "")).strip().lower() == "true"
            if bool(selector_metrics["offline_strict_pass"]) != recorded_pass:
                raise AssertionError(f"Recomputed selector pass differs for {revision} query {query_id}.")
            selector_metrics["query_id"] = query_id
            selector_metrics["question"] = str(context["question"])
            selector_rows.append(selector_metrics)

            all_pair_rows.append(
                {
                    "framework_version": revision,
                    "query_id": query_id,
                    "question": str(context["question"]),
                    "gold_clause_count": no_metrics["gold_clause_count"],
                    "gold_odp_count": no_metrics["gold_odp_count"],
                    **{
                        f"selector_{key}": selector_metrics[key]
                        for key in (
                            "offline_strict_pass",
                            "full_gold_clause_coverage",
                            "right_control",
                            "selected_clause_count",
                            "additional_evidence_count",
                            "gold_clause_precision",
                            "answer_word_count",
                            "status",
                            "exact_odp_list",
                        )
                    },
                    **{
                        f"no_selector_{key}": no_metrics[key]
                        for key in (
                            "offline_strict_pass",
                            "full_gold_clause_coverage",
                            "right_control",
                            "selected_clause_count",
                            "additional_evidence_count",
                            "gold_clause_precision",
                            "answer_word_count",
                            "status",
                            "exact_odp_list",
                        )
                    },
                }
            )

            contract_rows.append(
                {
                    "query_id": query_id,
                    "framework_version": revision,
                    "result_id": RESULT_ID,
                    "question": str(context["question"]),
                    "context_sha256": str(context["context_sha256"]),
                    "evidence_window_sha256": str(context["evidence_window_manifest"]["sha256"]),
                    "status": no_metrics["status"],
                    "offline_strict_pass": no_metrics["offline_strict_pass"],
                    "offline_error_tags": "|".join(no_metrics["offline_error_tags"]),
                    "runtime_contract_pass": no_metrics["runtime_contract_pass"],
                    "runtime_error_tags": "|".join(no_metrics["runtime_error_tags"]),
                    "full_gold_clause_coverage": no_metrics["full_gold_clause_coverage"],
                    "right_control": no_metrics["right_control"],
                    "any_gold_clause": no_metrics["any_gold_clause"],
                    "gold_clause_precision": no_metrics["gold_clause_precision"],
                    "selected_clause_count": no_metrics["selected_clause_count"],
                    "gold_clause_count": no_metrics["gold_clause_count"],
                    "additional_evidence_count": no_metrics["additional_evidence_count"],
                    "answer_char_count": no_metrics["answer_char_count"],
                    "answer_word_count": no_metrics["answer_word_count"],
                    "citation_char_count": no_metrics["citation_char_count"],
                    "gold_odp_count": no_metrics["gold_odp_count"],
                    "generated_odp_count": no_metrics["generated_odp_count"],
                    "exact_odp_list": no_metrics["exact_odp_list"],
                    "selected_source_ids": "|".join(no_selector_contract["selected_source_ids"]),
                    "odp_required_list": "|".join(no_selector_contract["odp_required_list"]),
                    "offline_metrics_json": json.dumps(no_metrics["offline_metrics"], sort_keys=True),
                    "contract_json": json.dumps(no_selector_contract, ensure_ascii=False, sort_keys=True),
                }
            )

        expected_selector_pass = 65 if revision == "rev5" else 29
        if sum(bool(row["offline_strict_pass"]) for row in selector_rows) != expected_selector_pass:
            raise AssertionError(f"Frozen selector strict-pass count changed for {revision}.")

        contracts_path = output_dir / "contracts" / f"{revision}_no_selector.csv"
        contracts_path.parent.mkdir(parents=True, exist_ok=True)
        with contracts_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=contract_fields)
            writer.writeheader()
            writer.writerows(contract_rows)
        output_hashes[str(contracts_path.relative_to(output_dir))] = sha256_file(contracts_path)

        selector_agg = aggregate(selector_rows)
        no_selector_agg = aggregate(no_selector_rows)
        summary["revisions"][revision] = {
            "selector_v3": selector_agg,
            "no_selector_v1": no_selector_agg,
            "delta_no_selector_minus_selector": delta_summary(selector_agg, no_selector_agg),
            "paired": paired_summary(selector_rows, no_selector_rows),
        }

    pair_path = output_dir / "per_row_comparison.csv"
    with pair_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(all_pair_rows[0]))
        writer.writeheader()
        writer.writerows(all_pair_rows)
    output_hashes[str(pair_path.relative_to(output_dir))] = sha256_file(pair_path)

    summary_path = output_dir / "summary.json"
    write_json(summary_path, summary)
    output_hashes[str(summary_path.relative_to(output_dir))] = sha256_file(summary_path)

    summary_md_path = output_dir / "SUMMARY.md"
    summary_md_path.write_text(render_summary(summary), encoding="utf-8")
    output_hashes[str(summary_md_path.relative_to(output_dir))] = sha256_file(summary_md_path)

    frozen_hash_after = sha256_file(frozen_archive)
    if frozen_hash_before != frozen_hash_after:
        raise AssertionError("Frozen RQ2 v3 archive changed during the no-selector run.")

    run_config = {
        "schema_version": SCHEMA_VERSION,
        "result_id": RESULT_ID,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": ".",
        "script": str(Path(__file__).resolve().relative_to(repo_root)),
        "script_sha256": sha256_file(Path(__file__).resolve()),
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
            "selector": "bypassed; retain every record in the frozen evidence window",
            "retrieval": "none; consume frozen prepared contexts",
            "resolution_policy": "ASK with no organization profile",
            "fallback": "disabled",
            "rescue": "disabled",
            "hierarchy_closure": "disabled",
            "strict_extras": False,
            "strict_verbatim": True,
        },
        "outputs_sha256": output_hashes,
        "result_summary_sha256": canonical_sha256(summary),
    }
    config_path = output_dir / "run_config.json"
    write_json(config_path, run_config)

    archive_path = Path(
        shutil.make_archive(
            str(output_dir.parent / output_dir.name),
            "zip",
            root_dir=output_dir,
        )
    )
    print(f"Completed {RESULT_ID}: {output_dir}")
    print(f"Result archive: {archive_path}")
    print(render_summary(summary))


if __name__ == "__main__":
    main()
