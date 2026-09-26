"""Recompute the Batch 2 retrieval uncertainty and adoption-gate audit.

The stored CSV schema calls the binary query hit indicator ``is_hit_at_k``.
The dissertation reports that quantity as Success@k because each question has
one labeled governing control rather than an exhaustively judged relevance set.
This script reads the frozen CSVs without modifying them.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent / "ablation_outputs"
SYSTEMS = {
    "S1": ("system_1_bm25", "S1_bm25"),
    "S2": ("system_2_dense", "S2_dense"),
    "S3": ("system_3_rewrite_only", "S3_rewrite_only"),
    "S4": ("system_4_qur_rrf", "S4_qur_rrf"),
    "S5": ("system_5_hybrid_rrf", "S5_hybrid_rrf"),
    "S6": ("system_6_hybrid_rerank", "S6_hybrid_rerank"),
    "S7": ("system_7_compliance_gpt", "S7_compliance_gpt"),
}
Z_975 = 1.959963984540054


def load_rows(system: str, revision: str) -> list[dict[str, str]]:
    directory, prefix = SYSTEMS[system]
    path = ROOT / directory / f"{prefix}_{revision}_results.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("total must be positive")
    proportion = successes / total
    z2 = Z_975**2
    denominator = 1 + z2 / total
    center = (proportion + z2 / (2 * total)) / denominator
    half_width = (
        Z_975
        * math.sqrt(
            proportion * (1 - proportion) / total + z2 / (4 * total**2)
        )
        / denominator
    )
    return center - half_width, center + half_width


def exact_mcnemar(b: int, c: int) -> float:
    discordant = b + c
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, j) for j in range(min(b, c) + 1))
    return min(1.0, 2 * tail / (2**discordant))


def success_summary() -> dict[str, Any]:
    output: dict[str, Any] = {}
    for revision in ("rev5", "rev4"):
        output[revision] = {}
        for system in SYSTEMS:
            rows = load_rows(system, revision)
            entry: dict[str, Any] = {"n": len(rows)}
            for k in (1, 5, 10):
                count = sum(as_bool(row[f"is_hit_at_{k}"]) for row in rows)
                low, high = wilson_interval(count, len(rows))
                entry[f"success_at_{k}"] = {
                    "count": count,
                    "rate": count / len(rows),
                    "wilson_95": [low, high],
                }
            output[revision][system] = entry
    return output


def paired_top1() -> dict[str, Any]:
    comparisons = {"rev5": ("S7", "S5"), "rev4": ("S7", "S2")}
    output: dict[str, Any] = {}
    for revision, (left_name, right_name) in comparisons.items():
        left = {row["question_id"]: row for row in load_rows(left_name, revision)}
        right = {row["question_id"]: row for row in load_rows(right_name, revision)}
        if left.keys() != right.keys():
            raise ValueError(f"paired query IDs differ for {revision}")
        left_only = right_only = 0
        for query_id in sorted(left):
            left_hit = as_bool(left[query_id]["is_hit_at_1"])
            right_hit = as_bool(right[query_id]["is_hit_at_1"])
            left_only += left_hit and not right_hit
            right_only += right_hit and not left_hit
        output[revision] = {
            "comparison": f"{left_name}_vs_{right_name}",
            "left_only": left_only,
            "right_only": right_only,
            "net": left_only - right_only,
            "exact_mcnemar_two_sided_p": exact_mcnemar(left_only, right_only),
        }
    return output


def rerank_gate_audit() -> dict[str, Any]:
    output: dict[str, Any] = {}
    for revision in ("rev5", "rev4"):
        rejected = prevented_error = blocked_correction = 0
        query_ids: list[str] = []
        for row in load_rows("S7", revision):
            metadata = json.loads(row["system_meta"])
            base = str(metadata.get("base_top1", "")).upper()
            reranked = str(metadata.get("rerank_top1", "")).upper()
            final = str(metadata.get("final_top1", "")).upper()
            changed = bool(base and reranked and base != reranked)
            gate_rejected = (
                as_bool(metadata.get("reranker_called"))
                and changed
                and not as_bool(metadata.get("rerank_applied"))
                and final == base
            )
            if not gate_rejected:
                continue
            rejected += 1
            query_ids.append(row["question_id"])
            gold = row["gold_control_id"].upper()
            prevented_error += base == gold and reranked != gold
            blocked_correction += base != gold and reranked == gold
        output[revision] = {
            "rejected_changed_top": rejected,
            "prevented_error": prevented_error,
            "blocked_correction": blocked_correction,
            "question_ids": query_ids,
        }
    return output


def main() -> None:
    report = {
        "success_intervals": success_summary(),
        "paired_top1": paired_top1(),
        "rerank_adoption_gate": rerank_gate_audit(),
    }
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
