#!/usr/bin/env python3
"""Replay the frozen selector path with ODP-statement rescue on and off.

The runner reconstructs the deterministic pre-rescue state from each frozen
RQ2 v3 ComplianceGPT contract.  It never calls retrieval or a language model.
Before measuring any rescue effect, it requires the rescue-on replay to match
the frozen contract on its core evidence, answer, ODP, citation, and scoring
fields.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


RESULT_ID = "rq2_rescue_ablation_v1"
SCHEMA_VERSION = "compliancegpt-rq2-rescue-ablation-v1"
EXPECTED_ROWS = {"rev5": 100, "rev4": 36}
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


def manifest_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


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
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(left_only, right_only) + 1)
    )
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


def source_ids(contract: Mapping[str, Any]) -> List[str]:
    return [
        str(span.get("source_id", "") or "").strip()
        for span in list(contract.get("evidence_spans", []) or [])
        if str(span.get("source_id", "") or "").strip()
    ]


def build_replay_contract(
    *,
    frozen_contract: Mapping[str, Any],
    question: str,
    revision: str,
    ccs: Mapping[str, Mapping[str, Any]],
    odp_registry: Mapping[str, Any],
    param_ids: set[str],
    key_map: Mapping[str, str],
    rescue_enabled: bool,
    extract_control_hints: Any,
    query_allows_enhancements: Any,
    is_enhancement_clause_id: Any,
    rescue_odp_statement_spans: Any,
    apply_odp_policy_to_answer: Any,
    canonicalize_param_list: Any,
    assignment_sentinel: str,
    build_ask_list: Any,
    best_primary_citation: Any,
    build_citation_suffix: Any,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    debug = dict(frozen_contract.get("debug", {}) or {})
    if list(debug.get("hierarchy_added_ids", []) or []):
        raise AssertionError("Frozen contract unexpectedly contains hierarchy additions.")
    if bool(debug.get("secondary_fallback_used", False)):
        raise AssertionError("Frozen contract unexpectedly uses secondary fallback.")

    selector_raw = dict(debug.get("selector_raw", {}) or {})
    raw_ids = source_ids(selector_raw)
    control_hints = list(extract_control_hints(question) or [])
    allow_enhancements = bool(query_allows_enhancements(question)) or any(
        "." in str(control) for control in control_hints
    )
    # In the frozen trace, ``selector_raw`` is the normalized selector contract
    # except on the recorded empty-selector fallback rows, where it is the
    # already-constructed top-window fallback contract.  The enhancement gate
    # precedes that fallback, so applying it a second time would incorrectly
    # erase Rev. 5 query 9's recorded fallback clause.
    if bool(debug.get("fallback_used", False)):
        retained_ids = list(raw_ids)
        window_ids = list(
            dict(debug.get("evidence_window", {}) or {}).get("source_ids", []) or []
        )
        if not retained_ids or not window_ids or retained_ids[0] != str(window_ids[0]):
            raise AssertionError(
                "Recorded fallback does not identify the first frozen evidence-window clause."
            )
    else:
        retained_ids = [
            source_id
            for source_id in raw_ids
            if allow_enhancements or not bool(is_enhancement_clause_id(source_id))
        ]

    pre_rescue_spans: List[Dict[str, str]] = []
    for source_id in retained_ids:
        record = ccs.get(source_id)
        if not isinstance(record, Mapping):
            continue
        kind = str(record.get("kind", "") or "").strip().lower()
        text = str(record.get("text", "") or "").strip()
        if kind not in {"smt", "gdn"} or not text:
            continue
        pre_rescue_spans.append(
            {
                "source_id": str(record.get("id", source_id) or source_id).strip(),
                "span_text": text,
            }
        )
    if not pre_rescue_spans:
        raise AssertionError(
            "Replay produced no valid pre-rescue spans "
            f"(raw_ids={raw_ids!r}, retained_ids={retained_ids!r}, "
            f"allow_enhancements={allow_enhancements!r})."
        )

    winner_control = str(debug.get("winner_control", "") or "").strip()
    if not winner_control:
        raise AssertionError("Frozen contract has no winner_control.")

    if rescue_enabled:
        final_spans, added_ids, rescue_used = rescue_odp_statement_spans(
            filled_spans=pre_rescue_spans,
            winner_control=winner_control,
            record_by_id=dict(ccs),
            resolution_policy="ASK",
            allow_enhancements=allow_enhancements,
            max_add=4,
        )
    else:
        final_spans = [dict(span) for span in pre_rescue_spans]
        added_ids = []
        rescue_used = False

    answer_text = "\n\n".join(span["span_text"] for span in final_spans).strip()
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
    required = canonical_required or list(
        dict.fromkeys(
            str(item).strip()
            for item in raw_required
            if str(item).strip()
        )
    )
    status_text = str(status or "OK").strip().upper() or "OK"
    ask_list = (
        build_ask_list(required, final_spans, dict(odp_registry))
        if status_text == "PARAMS_REQUIRED"
        else []
    )

    citations = source_ids({"evidence_spans": final_spans})
    all_citations = ", ".join(citations)
    retrieval_meta = dict(debug.get("retrieval_meta", {}) or {})
    citation_query = str(
        ((retrieval_meta.get("query_transform") or {}).get("retrieval_query"))
        or question
    )
    primary_citation = best_primary_citation(citation_query, final_spans)
    suffix = build_citation_suffix(revision)
    answer_with_citations = (
        f"{answer_text}\n\nCitations: {all_citations} ({suffix})".strip()
        if all_citations
        else answer_text
    )

    replay_debug = {
        "result_id": RESULT_ID,
        "source_result_id": "rq2_matched_v3",
        "rescue_enabled": bool(rescue_enabled),
        "rescue_used": bool(rescue_used),
        "rescue_added_ids": list(added_ids),
        "pre_rescue_source_ids": source_ids({"evidence_spans": pre_rescue_spans}),
        "winner_control": winner_control,
        "allow_enhancements": bool(allow_enhancements),
        "fallback_used": bool(debug.get("fallback_used", False)),
        "prepared_context_sha256": str(debug.get("prepared_context_sha256", "") or ""),
    }
    contract = {
        "question": question,
        "framework_version": revision,
        "answer_text": answer_text,
        "answer_text_with_citations": answer_with_citations,
        "evidence_spans": final_spans,
        "status": status_text,
        "odp_required_list": required,
        "ask_list": ask_list,
        "primary_citation": primary_citation,
        "all_citations": all_citations,
        "selected_source_ids": citations,
        "debug": replay_debug,
    }
    reconstruction = {
        "raw_selector_source_ids": raw_ids,
        "pre_rescue_source_ids": replay_debug["pre_rescue_source_ids"],
        "rescue_added_ids": list(added_ids),
        "rescue_used": bool(rescue_used),
        "winner_control": winner_control,
        "allow_enhancements": bool(allow_enhancements),
    }
    return contract, reconstruction


def assert_rescue_on_matches_frozen(
    replay: Mapping[str, Any],
    frozen: Mapping[str, Any],
    *,
    revision: str,
    query_id: str,
) -> None:
    comparable_fields = (
        "question",
        "framework_version",
        "answer_text",
        "answer_text_with_citations",
        "status",
        "odp_required_list",
        "ask_list",
        "primary_citation",
        "all_citations",
        "selected_source_ids",
    )
    for field in comparable_fields:
        if replay.get(field) != frozen.get(field):
            raise AssertionError(
                f"Rescue-on replay differs from frozen {revision} query {query_id} field {field}."
            )
    if list(replay.get("evidence_spans", []) or []) != list(
        frozen.get("evidence_spans", []) or []
    ):
        raise AssertionError(
            f"Rescue-on replay evidence differs from frozen {revision} query {query_id}."
        )


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
    selected = [source_id.lower() for source_id in source_ids(contract)]
    selected = list(dict.fromkeys(selected))
    gold = normalized_source_ids(gold_row.get("gold_control_path", ""))
    gold_set = set(gold)
    selected_set = set(selected)
    gold_odps = normalized_odp_ids(gold_row.get("odp_required", ""), normalize_odp_id)
    generated_odps = normalized_odp_ids(
        contract.get("odp_required_list", []),
        normalize_odp_id,
    )
    answer = str(contract.get("answer_text", "") or "")
    citations = str(contract.get("all_citations", "") or "")
    status = str(contract.get("status", "") or "")

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
        "status": status,
        "params_required": status == "PARAMS_REQUIRED",
        "false_complete": bool(gold_odps) and status == "OK",
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

    def count(name: str, subset: Sequence[Mapping[str, Any]] = rows) -> int:
        return sum(bool(row[name]) for row in subset)

    def count_rate(name: str, subset: Sequence[Mapping[str, Any]] = rows) -> Dict[str, float]:
        value = count(name, subset)
        total = len(subset)
        return {"count": value, "rate": value / total if total else float("nan")}

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
            "params_required": count_rate("params_required", odp_rows),
            "false_complete": count_rate("false_complete", odp_rows),
            "exact_odp_list": count_rate("exact_odp_list", odp_rows),
        },
        "non_odp_status_expansion": {
            "n": len(non_odp_rows),
            "params_required": count_rate("params_required", non_odp_rows),
        },
        "review_burden": {
            "selected_clause_count": distribution([float(row["selected_clause_count"]) for row in rows]),
            "additional_evidence_count": distribution([float(row["additional_evidence_count"]) for row in rows]),
            "gold_clause_precision": distribution([float(row["gold_clause_precision"]) for row in rows]),
            "answer_word_count": distribution([float(row["answer_word_count"]) for row in rows]),
            "citation_char_count": distribution([float(row["citation_char_count"]) for row in rows]),
            "generated_odp_count": distribution([float(row["generated_odp_count"]) for row in rows]),
        },
    }


def paired_binary(
    off_rows: Sequence[Mapping[str, Any]],
    on_rows: Sequence[Mapping[str, Any]],
    field: str,
    *,
    odp_only: bool = False,
    non_odp_only: bool = False,
) -> Dict[str, Any]:
    off = {str(row["query_id"]): row for row in off_rows}
    on = {str(row["query_id"]): row for row in on_rows}
    if set(off) != set(on):
        raise AssertionError("Rescue-off and rescue-on row sets differ.")
    ids = sorted(off, key=lambda value: (0, int(value)) if value.isdigit() else (1, value))
    if odp_only:
        ids = [query_id for query_id in ids if int(off[query_id]["gold_odp_count"]) > 0]
    if non_odp_only:
        ids = [query_id for query_id in ids if int(off[query_id]["gold_odp_count"]) == 0]
    on_only = sum(bool(on[qid][field]) and not bool(off[qid][field]) for qid in ids)
    off_only = sum(bool(off[qid][field]) and not bool(on[qid][field]) for qid in ids)
    both = sum(bool(on[qid][field]) and bool(off[qid][field]) for qid in ids)
    neither = len(ids) - on_only - off_only - both
    return {
        "n": len(ids),
        "rescue_on_only": on_only,
        "rescue_off_only": off_only,
        "both": both,
        "neither": neither,
        "exact_mcnemar_two_sided_p": exact_mcnemar(on_only, off_only),
    }


def delta_summary(off: Mapping[str, Any], on: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "offline_strict_pass_rate": on["offline_strict_pass"]["rate"] - off["offline_strict_pass"]["rate"],
        "full_gold_clause_coverage_rate": on["full_gold_clause_coverage"]["rate"] - off["full_gold_clause_coverage"]["rate"],
        "right_control_rate": on["right_control"]["rate"] - off["right_control"]["rate"],
        "odp_params_required_rate": on["odp_subset"]["params_required"]["rate"] - off["odp_subset"]["params_required"]["rate"],
        "odp_false_complete_rate": on["odp_subset"]["false_complete"]["rate"] - off["odp_subset"]["false_complete"]["rate"],
        "exact_odp_list_rate": on["odp_subset"]["exact_odp_list"]["rate"] - off["odp_subset"]["exact_odp_list"]["rate"],
        "non_odp_status_expansion_rate": on["non_odp_status_expansion"]["params_required"]["rate"] - off["non_odp_status_expansion"]["params_required"]["rate"],
        "mean_selected_clause_count": on["review_burden"]["selected_clause_count"]["mean"] - off["review_burden"]["selected_clause_count"]["mean"],
        "mean_additional_evidence_count": on["review_burden"]["additional_evidence_count"]["mean"] - off["review_burden"]["additional_evidence_count"]["mean"],
        "mean_gold_clause_precision": on["review_burden"]["gold_clause_precision"]["mean"] - off["review_burden"]["gold_clause_precision"]["mean"],
        "mean_answer_word_count": on["review_burden"]["answer_word_count"]["mean"] - off["review_burden"]["answer_word_count"]["mean"],
        "mean_generated_odp_count": on["review_burden"]["generated_odp_count"]["mean"] - off["review_burden"]["generated_odp_count"]["mean"],
    }


def render_summary(summary: Mapping[str, Any]) -> str:
    lines = [
        "# RQ2 ODP-Statement Rescue Ablation",
        "",
        f"Result identity: `{RESULT_ID}`",
        "",
        "The replay reconstructs the frozen selector path immediately before bounded ODP-statement rescue. It performs no retrieval or model inference. Every rescue-on replay must reproduce the frozen core contract before an on/off effect is reported.",
        "",
    ]
    for revision in ("rev5", "rev4"):
        block = summary["revisions"][revision]
        off = block["rescue_off"]
        on = block["rescue_on"]
        delta = block["delta_on_minus_off"]
        rescue = block["rescue_activity"]
        lines.extend(
            [
                f"## {revision.upper()}",
                "",
                f"Rescue activates on {rescue['rows_used']}/{off['n_questions']} rows and adds {rescue['identifier_occurrences']} identifier occurrences ({rescue['gold_identifier_occurrences']} expected-gold occurrences).",
                "",
                "| Measure | Rescue off | Rescue on | Delta |",
                "|---|---:|---:|---:|",
                f"| Offline strict pass | {off['offline_strict_pass']['count']}/{off['n_questions']} ({off['offline_strict_pass']['rate']:.3f}) | {on['offline_strict_pass']['count']}/{on['n_questions']} ({on['offline_strict_pass']['rate']:.3f}) | {delta['offline_strict_pass_rate']:+.3f} |",
                f"| Full gold-clause coverage | {off['full_gold_clause_coverage']['count']}/{off['n_questions']} ({off['full_gold_clause_coverage']['rate']:.3f}) | {on['full_gold_clause_coverage']['count']}/{on['n_questions']} ({on['full_gold_clause_coverage']['rate']:.3f}) | {delta['full_gold_clause_coverage_rate']:+.3f} |",
                f"| Right governing control | {off['right_control']['count']}/{off['n_questions']} ({off['right_control']['rate']:.3f}) | {on['right_control']['count']}/{on['n_questions']} ({on['right_control']['rate']:.3f}) | {delta['right_control_rate']:+.3f} |",
                f"| `PARAMS_REQUIRED` on gold ODP rows | {off['odp_subset']['params_required']['count']}/{off['odp_subset']['n']} ({off['odp_subset']['params_required']['rate']:.3f}) | {on['odp_subset']['params_required']['count']}/{on['odp_subset']['n']} ({on['odp_subset']['params_required']['rate']:.3f}) | {delta['odp_params_required_rate']:+.3f} |",
                f"| False complete on gold ODP rows | {off['odp_subset']['false_complete']['count']}/{off['odp_subset']['n']} ({off['odp_subset']['false_complete']['rate']:.3f}) | {on['odp_subset']['false_complete']['count']}/{on['odp_subset']['n']} ({on['odp_subset']['false_complete']['rate']:.3f}) | {delta['odp_false_complete_rate']:+.3f} |",
                f"| Exact ODP-list agreement | {off['odp_subset']['exact_odp_list']['count']}/{off['odp_subset']['n']} ({off['odp_subset']['exact_odp_list']['rate']:.3f}) | {on['odp_subset']['exact_odp_list']['count']}/{on['odp_subset']['n']} ({on['odp_subset']['exact_odp_list']['rate']:.3f}) | {delta['exact_odp_list_rate']:+.3f} |",
                f"| `PARAMS_REQUIRED` on labeled non-ODP rows | {off['non_odp_status_expansion']['params_required']['count']}/{off['non_odp_status_expansion']['n']} ({off['non_odp_status_expansion']['params_required']['rate']:.3f}) | {on['non_odp_status_expansion']['params_required']['count']}/{on['non_odp_status_expansion']['n']} ({on['non_odp_status_expansion']['params_required']['rate']:.3f}) | {delta['non_odp_status_expansion_rate']:+.3f} |",
                f"| Mean selected clauses | {off['review_burden']['selected_clause_count']['mean']:.2f} | {on['review_burden']['selected_clause_count']['mean']:.2f} | {delta['mean_selected_clause_count']:+.2f} |",
                f"| Mean additional clauses | {off['review_burden']['additional_evidence_count']['mean']:.2f} | {on['review_burden']['additional_evidence_count']['mean']:.2f} | {delta['mean_additional_evidence_count']:+.2f} |",
                f"| Mean gold-clause precision | {off['review_burden']['gold_clause_precision']['mean']:.3f} | {on['review_burden']['gold_clause_precision']['mean']:.3f} | {delta['mean_gold_clause_precision']:+.3f} |",
                f"| Mean answer words | {off['review_burden']['answer_word_count']['mean']:.1f} | {on['review_burden']['answer_word_count']['mean']:.1f} | {delta['mean_answer_word_count']:+.1f} |",
                f"| Mean surfaced ODPs | {off['review_burden']['generated_odp_count']['mean']:.2f} | {on['review_burden']['generated_odp_count']['mean']:.2f} | {delta['mean_generated_odp_count']:+.2f} |",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation boundary",
            "",
            "This is a deterministic replay over fixed frozen selector outputs. Non-ODP status expansion is descriptive and is not called a false-positive rate or specificity estimate without independent adjudication.",
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
        _best_primary_citation,
        _build_ask_list,
        _build_citation_suffix,
        _build_param_key_to_canonical,
        _canonicalize_param_list,
        _extract_control_hints,
        _is_enhancement_clause_id,
        _query_allows_enhancements,
        _rescue_odp_statement_spans,
        load_odp_registry,
    )

    if not frozen_archive.is_file():
        raise FileNotFoundError(frozen_archive)
    frozen_hash_before = sha256_file(frozen_archive)

    contexts_by_revision: Dict[str, Dict[str, Dict[str, Any]]] = {}
    frozen_rows_by_revision: Dict[str, Dict[str, Dict[str, str]]] = {}
    member_hashes: Dict[str, str] = {}
    with zipfile.ZipFile(frozen_archive, "r") as archive:
        for revision in ("rev5", "rev4"):
            context_rows, context_hash = read_jsonl_member(
                archive,
                CONTEXT_MEMBERS[revision],
            )
            frozen_rows, contract_hash = read_csv_member(
                archive,
                CONTRACT_MEMBERS[revision],
            )
            if len(context_rows) != EXPECTED_ROWS[revision]:
                raise AssertionError(
                    f"Unexpected {revision} context count: {len(context_rows)}"
                )
            if len(frozen_rows) != EXPECTED_ROWS[revision]:
                raise AssertionError(
                    f"Unexpected {revision} contract count: {len(frozen_rows)}"
                )
            for context in context_rows:
                validate_prepared_context(context)
            contexts_by_revision[revision] = {
                str(context["query_id"]): context for context in context_rows
            }
            frozen_rows_by_revision[revision] = frozen_rows
            member_hashes[CONTEXT_MEMBERS[revision]] = context_hash
            member_hashes[CONTRACT_MEMBERS[revision]] = contract_hash

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
        "condition",
        "result_id",
        "question",
        "context_sha256",
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
        "answer_word_count",
        "citation_char_count",
        "gold_odp_count",
        "generated_odp_count",
        "exact_odp_list",
        "rescue_used",
        "rescue_added_ids",
        "selected_source_ids",
        "odp_required_list",
        "offline_metrics_json",
        "contract_json",
    ]

    for revision in ("rev5", "rev4"):
        gold_path = repo_root / INPUTS[revision]["gold"]
        ccs_path = repo_root / INPUTS[revision]["ccs"]
        registry_path = repo_root / INPUTS[revision]["odp_registry"]
        gold_by_id = load_gold_rows(
            gold_path,
            expected_rows=EXPECTED_ROWS[revision],
        )
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

        off_rows: List[Dict[str, Any]] = []
        on_rows: List[Dict[str, Any]] = []
        contract_rows_by_condition: Dict[str, List[Dict[str, Any]]] = {
            "rescue_off": [],
            "rescue_on": [],
        }
        rescue_rows = 0
        rescue_occurrences = 0
        rescue_gold_occurrences = 0
        rescue_window_occurrences = 0
        replay_matches = 0

        for query_id, frozen_row in sorted(
            frozen_rows_by_revision[revision].items(),
            key=lambda item: (0, int(item[0])) if item[0].isdigit() else (1, item[0]),
        ):
            context = contexts_by_revision[revision][query_id]
            gold_row = gold_by_id[query_id]
            frozen_contract = json.loads(str(frozen_row.get("contract_json", "") or "{}"))
            build_kwargs = {
                "frozen_contract": frozen_contract,
                "question": str(context["question"]),
                "revision": revision,
                "ccs": ccs,
                "odp_registry": odp_registry,
                "param_ids": param_ids,
                "key_map": key_map,
                "extract_control_hints": _extract_control_hints,
                "query_allows_enhancements": _query_allows_enhancements,
                "is_enhancement_clause_id": _is_enhancement_clause_id,
                "rescue_odp_statement_spans": _rescue_odp_statement_spans,
                "apply_odp_policy_to_answer": apply_odp_policy_to_answer,
                "canonicalize_param_list": _canonicalize_param_list,
                "assignment_sentinel": ASSIGNMENT_REQUIRED_SENTINEL,
                "build_ask_list": _build_ask_list,
                "best_primary_citation": _best_primary_citation,
                "build_citation_suffix": _build_citation_suffix,
            }
            off_contract, off_reconstruction = build_replay_contract(
                **build_kwargs,
                rescue_enabled=False,
            )
            on_contract, on_reconstruction = build_replay_contract(
                **build_kwargs,
                rescue_enabled=True,
            )
            assert_rescue_on_matches_frozen(
                on_contract,
                frozen_contract,
                revision=revision,
                query_id=query_id,
            )
            replay_matches += 1

            off_metrics = evaluate_contract(
                contract=off_contract,
                gold_row=gold_row,
                corpus=corpus,
                revision=revision,
                verify_answer=verify_answer,
                verify_contract_validity=verify_contract_validity,
                normalize_odp_id=normalize_odp_id,
            )
            on_metrics = evaluate_contract(
                contract=on_contract,
                gold_row=gold_row,
                corpus=corpus,
                revision=revision,
                verify_answer=verify_answer,
                verify_contract_validity=verify_contract_validity,
                normalize_odp_id=normalize_odp_id,
            )
            recorded_pass = str(frozen_row.get("verifier_pass", "")).strip().lower() == "true"
            if bool(on_metrics["offline_strict_pass"]) != recorded_pass:
                raise AssertionError(
                    f"Rescue-on scorer differs from frozen {revision} query {query_id}."
                )

            off_metrics.update({"query_id": query_id, "question": str(context["question"])})
            on_metrics.update({"query_id": query_id, "question": str(context["question"])})
            off_rows.append(off_metrics)
            on_rows.append(on_metrics)

            added_ids = list(on_reconstruction["rescue_added_ids"])
            if added_ids:
                rescue_rows += 1
            rescue_occurrences += len(added_ids)
            gold_ids = set(normalized_source_ids(gold_row.get("gold_control_path", "")))
            rescue_gold_occurrences += sum(
                source_id.lower() in gold_ids for source_id in added_ids
            )
            window_ids = {
                str(record.get("id", "") or "").strip()
                for record in list(context.get("evidence_window", []) or [])
            }
            rescue_window_occurrences += sum(source_id in window_ids for source_id in added_ids)

            all_pair_rows.append(
                {
                    "framework_version": revision,
                    "query_id": query_id,
                    "question": str(context["question"]),
                    "gold_clause_count": off_metrics["gold_clause_count"],
                    "gold_odp_count": off_metrics["gold_odp_count"],
                    "rescue_used": bool(added_ids),
                    "rescue_added_count": len(added_ids),
                    "rescue_added_ids": "|".join(added_ids),
                    "rescue_added_gold_count": sum(
                        source_id.lower() in gold_ids for source_id in added_ids
                    ),
                    "rescue_added_window_count": sum(
                        source_id in window_ids for source_id in added_ids
                    ),
                    **{
                        f"off_{key}": off_metrics[key]
                        for key in (
                            "offline_strict_pass",
                            "full_gold_clause_coverage",
                            "right_control",
                            "selected_clause_count",
                            "additional_evidence_count",
                            "gold_clause_precision",
                            "answer_word_count",
                            "status",
                            "generated_odp_count",
                            "exact_odp_list",
                        )
                    },
                    **{
                        f"on_{key}": on_metrics[key]
                        for key in (
                            "offline_strict_pass",
                            "full_gold_clause_coverage",
                            "right_control",
                            "selected_clause_count",
                            "additional_evidence_count",
                            "gold_clause_precision",
                            "answer_word_count",
                            "status",
                            "generated_odp_count",
                            "exact_odp_list",
                        )
                    },
                }
            )

            for condition, contract, metrics, reconstruction in (
                ("rescue_off", off_contract, off_metrics, off_reconstruction),
                ("rescue_on", on_contract, on_metrics, on_reconstruction),
            ):
                contract_rows_by_condition[condition].append(
                    {
                        "query_id": query_id,
                        "framework_version": revision,
                        "condition": condition,
                        "result_id": RESULT_ID,
                        "question": str(context["question"]),
                        "context_sha256": str(context["context_sha256"]),
                        "status": metrics["status"],
                        "offline_strict_pass": metrics["offline_strict_pass"],
                        "offline_error_tags": "|".join(metrics["offline_error_tags"]),
                        "runtime_contract_pass": metrics["runtime_contract_pass"],
                        "runtime_error_tags": "|".join(metrics["runtime_error_tags"]),
                        "full_gold_clause_coverage": metrics["full_gold_clause_coverage"],
                        "right_control": metrics["right_control"],
                        "any_gold_clause": metrics["any_gold_clause"],
                        "gold_clause_precision": metrics["gold_clause_precision"],
                        "selected_clause_count": metrics["selected_clause_count"],
                        "gold_clause_count": metrics["gold_clause_count"],
                        "additional_evidence_count": metrics["additional_evidence_count"],
                        "answer_word_count": metrics["answer_word_count"],
                        "citation_char_count": metrics["citation_char_count"],
                        "gold_odp_count": metrics["gold_odp_count"],
                        "generated_odp_count": metrics["generated_odp_count"],
                        "exact_odp_list": metrics["exact_odp_list"],
                        "rescue_used": reconstruction["rescue_used"],
                        "rescue_added_ids": "|".join(reconstruction["rescue_added_ids"]),
                        "selected_source_ids": "|".join(source_ids(contract)),
                        "odp_required_list": "|".join(listish(contract["odp_required_list"])),
                        "offline_metrics_json": json.dumps(metrics["offline_metrics"], sort_keys=True),
                        "contract_json": json.dumps(contract, ensure_ascii=False, sort_keys=True),
                    }
                )

        if replay_matches != EXPECTED_ROWS[revision]:
            raise AssertionError(f"Incomplete rescue-on replay validation for {revision}.")

        for condition in ("rescue_off", "rescue_on"):
            contracts_path = output_dir / "contracts" / f"{revision}_{condition}.csv"
            contracts_path.parent.mkdir(parents=True, exist_ok=True)
            with contracts_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=contract_fields)
                writer.writeheader()
                writer.writerows(contract_rows_by_condition[condition])
            output_hashes[str(contracts_path.relative_to(output_dir))] = sha256_file(contracts_path)

        off_agg = aggregate(off_rows)
        on_agg = aggregate(on_rows)
        summary["revisions"][revision] = {
            "replay_validation": {
                "matched_frozen_core_contracts": replay_matches,
                "expected": EXPECTED_ROWS[revision],
            },
            "rescue_activity": {
                "rows_used": rescue_rows,
                "identifier_occurrences": rescue_occurrences,
                "gold_identifier_occurrences": rescue_gold_occurrences,
                "window_present_identifier_occurrences": rescue_window_occurrences,
            },
            "rescue_off": off_agg,
            "rescue_on": on_agg,
            "delta_on_minus_off": delta_summary(off_agg, on_agg),
            "paired": {
                "offline_strict_pass": paired_binary(off_rows, on_rows, "offline_strict_pass"),
                "full_gold_clause_coverage": paired_binary(off_rows, on_rows, "full_gold_clause_coverage"),
                "odp_params_required": paired_binary(off_rows, on_rows, "params_required", odp_only=True),
                "odp_exact_list": paired_binary(off_rows, on_rows, "exact_odp_list", odp_only=True),
                "non_odp_params_required": paired_binary(off_rows, on_rows, "params_required", non_odp_only=True),
            },
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
        raise AssertionError("Frozen RQ2 v3 archive changed during the rescue replay.")

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
            "retrieval": "none; consume frozen prepared contexts",
            "selector": "none; recover stored normalized selector result",
            "rescue_off": "retain recovered pre-rescue spans",
            "rescue_on": "implemented deterministic ODP-statement rescue, max_add=4",
            "resolution_policy": "ASK with no organization profile",
            "fallback": "reuse the two fallbacks already recorded in frozen selector_raw",
            "secondary_fallback": "required absent",
            "hierarchy_closure": "required absent",
            "gold_during_construction": False,
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
