#!/usr/bin/env python3
"""Audit dissertation source claims against frozen ComplianceGPT evidence.

The dissertation source is intentionally maintained outside this repository.
This tool accepts an extracted Overleaf source directory, recomputes the main
reported quantities from checked-in artifacts, and fails if a required LaTeX
anchor, citation, dependency, file hash, or publication identity is missing or
inconsistent.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


TEX_COMMAND_RE = re.compile(r"\\(?:input|include)\{([^}]+)\}")
FIGURE_RE = re.compile(r"\\includegraphics(?:\[[^]]*\])?\s*\{([^}]+)\}")
CITE_RE = re.compile(r"\\cite[a-zA-Z*]*\{([^}]+)\}")
BIBITEM_RE = re.compile(r"\\bibitem(?:\[[^]]*\])?\{([^}]+)\}")
PATH_HASH_RE = re.compile(
    r"\\path\{([^}]+)\}\s*&\s*\\sha\{([0-9a-f]{64})\}"
)
Z_975 = 1.959963984540054

HISTORICAL_NOTEBOOK_COMMIT = "e00f9cdf77b1ad45a42df0a0bddd338de744266f"
HISTORICAL_NOTEBOOK_SHA256 = (
    "2e96e47c83f4d02e04b992a81d76cb3c8e670cffbc876d3329437637a1247fcc"
)
CURRENT_NOTEBOOK_COMMIT = "487f207edc578930cd66a53ff524e12d8edfbec3"
CURRENT_NOTEBOOK_SHA256 = (
    "d4cafb9d32ddf1e51516bb1b08eb6d1037cc99e05ed5e0ef9894fbb358a751af"
)
NOTEBOOK_SEMANTIC_SHA256 = (
    "a84858d01a08076445c9597902e95a15151d7ebd14e50d4ae43321ee53f1bee0"
)
LOCAL_PRESERVE_PRECOMMIT = "17a76e14a2285c5070b8d8da3c7341e5772d303d"
PUBLIC_PRESERVE_PRECOMMIT = "bb2e382b7428feab4e1804dceb788606d73ac8ce"
PUBLIC_PRESERVE_RESULT = "e00f9cdf77b1ad45a42df0a0bddd338de744266f"


@dataclass
class Check:
    category: str
    name: str
    passed: bool
    expected: Any
    observed: Any
    evidence: str


class Audit:
    def __init__(self) -> None:
        self.checks: list[Check] = []

    def add(
        self,
        category: str,
        name: str,
        passed: bool,
        expected: Any,
        observed: Any,
        evidence: str,
    ) -> None:
        self.checks.append(
            Check(category, name, bool(passed), expected, observed, evidence)
        )

    @property
    def failures(self) -> list[Check]:
        return [item for item in self.checks if not item.passed]

    def report(self) -> dict[str, Any]:
        counts = Counter(item.category for item in self.checks)
        passed = Counter(item.category for item in self.checks if item.passed)
        return {
            "status": "PASS" if not self.failures else "FAIL",
            "checks_total": len(self.checks),
            "checks_passed": len(self.checks) - len(self.failures),
            "checks_failed": len(self.failures),
            "by_category": {
                category: {
                    "total": counts[category],
                    "passed": passed[category],
                    "failed": counts[category] - passed[category],
                }
                for category in sorted(counts)
            },
            "failures": [asdict(item) for item in self.failures],
            "checks": [asdict(item) for item in self.checks],
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def as_rank(value: str) -> int | None:
    value = str(value).strip()
    if not value or value.lower() in {"none", "nan"}:
        return None
    rank = int(float(value))
    return rank if rank > 0 else None


def wilson_interval(successes: int, total: int) -> tuple[float, float]:
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


def exact_mcnemar(left_only: int, right_only: int) -> float:
    discordant = left_only + right_only
    if discordant == 0:
        return 1.0
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(left_only, right_only) + 1)
    )
    return min(1.0, 2 * tail / (2**discordant))


def notebook_projection(document: dict[str, Any]) -> dict[str, Any]:
    cells = []
    for cell in document.get("cells", []):
        cells.append(
            {
                key: cell.get(key)
                for key in (
                    "cell_type",
                    "source",
                    "execution_count",
                    "outputs",
                    "attachments",
                )
                if key in cell
            }
        )
    return {
        "nbformat": document.get("nbformat"),
        "nbformat_minor": document.get("nbformat_minor"),
        "cells": cells,
    }


def semantic_notebook_sha(document: dict[str, Any]) -> str:
    encoded = json.dumps(
        notebook_projection(document),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(encoded)


def git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repo, stderr=subprocess.STDOUT, text=True
    ).strip()


def add_anchor(
    audit: Audit,
    source_name: str,
    source: str,
    name: str,
    expected: str,
    category: str = "manuscript claims",
) -> None:
    normalized_source = normalize_space(source)
    normalized_expected = normalize_space(expected)
    audit.add(
        category,
        name,
        normalized_expected in normalized_source,
        normalized_expected,
        "present" if normalized_expected in normalized_source else "missing",
        source_name,
    )


def audit_tex_structure(
    audit: Audit, manuscript: Path, sources: dict[str, str]
) -> None:
    combined = "\n".join(sources.values())
    missing_inputs: list[str] = []
    missing_figures: list[str] = []
    for name, text in sources.items():
        for target in TEX_COMMAND_RE.findall(text):
            relative = target.strip()
            if not Path(relative).suffix:
                relative += ".tex"
            if not (manuscript / relative).is_file():
                missing_inputs.append(f"{name}: {relative}")
        for target in FIGURE_RE.findall(text):
            relative = target.strip()
            candidates = [manuscript / relative]
            if not Path(relative).suffix:
                candidates.extend(
                    manuscript / f"{relative}{suffix}"
                    for suffix in (".pdf", ".png", ".jpg", ".jpeg")
                )
            if not any(candidate.is_file() for candidate in candidates):
                missing_figures.append(f"{name}: {relative}")
    audit.add(
        "LaTeX structure",
        "all included TeX files exist",
        not missing_inputs,
        [],
        missing_inputs,
        str(manuscript),
    )
    audit.add(
        "LaTeX structure",
        "all included figures exist",
        not missing_figures,
        [],
        missing_figures,
        str(manuscript),
    )

    cited: list[str] = []
    for value in CITE_RE.findall(combined):
        cited.extend(part.strip() for part in value.split(",") if part.strip())
    defined = BIBITEM_RE.findall(sources.get("references.tex", ""))
    citation_result = {
        "cited_unique": len(set(cited)),
        "defined_unique": len(set(defined)),
        "missing": sorted(set(cited) - set(defined)),
        "duplicate_definitions": sorted(
            key for key, count in Counter(defined).items() if count > 1
        ),
        "uncited": sorted(set(defined) - set(cited)),
    }
    citation_ok = (
        citation_result["cited_unique"] == 133
        and citation_result["defined_unique"] == 133
        and not citation_result["missing"]
        and not citation_result["duplicate_definitions"]
        and not citation_result["uncited"]
    )
    audit.add(
        "citations",
        "retained bibliography is one-to-one with citations",
        citation_ok,
        {
            "cited_unique": 133,
            "defined_unique": 133,
            "missing": [],
            "duplicate_definitions": [],
            "uncited": [],
        },
        citation_result,
        "all TeX sources and references.tex",
    )


def audit_explicit_hashes(
    audit: Audit, repo: Path, sources: dict[str, str]
) -> None:
    verified = 0
    failures: list[dict[str, str]] = []
    for source_name, source in sources.items():
        for relative, expected in PATH_HASH_RE.findall(source):
            path = repo / relative
            if not path.is_file():
                failures.append(
                    {
                        "source": source_name,
                        "path": relative,
                        "expected": expected,
                        "actual": "missing",
                    }
                )
                continue
            actual = sha256_file(path)
            if actual != expected:
                failures.append(
                    {
                        "source": source_name,
                        "path": relative,
                        "expected": expected,
                        "actual": actual,
                    }
                )
            else:
                verified += 1
    audit.add(
        "artifact identity",
        "explicit Appendix path/hash pairs",
        verified == 22 and not failures,
        {"verified": 22, "failures": []},
        {"verified": verified, "failures": failures},
        "Appendix path/hash table",
    )


def audit_repo_paths(audit: Audit, repo: Path, appendix: str) -> None:
    required = [
        "EVALUATION_INPUT_CHECKSUMS.md",
        "data/DATA_VERSIONS.md",
        "REPRODUCIBILITY.md",
        "data/ccs/nist800-53/",
        "data/ODP/rev4/",
        "data/ODP/rev5/",
        "src/compliancegpt/QUR_generator/",
        "src/compliancegpt/retriever/retriever_s7.py",
        "src/compliancegpt/pipeline/pipeline.py",
        "src/compliancegpt/generator/generator.py",
        "src/compliancegpt/generator/citation_contract_80053.md",
        "src/compliancegpt/generator/verifier/verifier.py",
        "src/generative_answerer/",
        "src/answerer_comparison/frontier_api_answerer.py",
        "src/answerer_comparison/matched_window_runner.py",
        "experiments/",
    ]
    for relative in required:
        audit.add(
            "repository paths",
            relative,
            (repo / relative).exists() and f"\\path{{{relative}}}" in appendix,
            "exists in repository and is named in Appendix",
            {
                "repo_exists": (repo / relative).exists(),
                "appendix_mentions": f"\\path{{{relative}}}" in appendix,
            },
            "appendix.tex implementation map",
        )


def audit_dataset_and_corpus_claims(
    audit: Audit, repo: Path, chap4: str, chap5: str, chap6: str
) -> None:
    gold: dict[int, list[dict[str, str]]] = {}
    ccs: dict[int, list[dict[str, Any]]] = {}
    registries_csv: dict[int, list[dict[str, str]]] = {}
    registries_json: dict[int, dict[str, Any]] = {}
    raw_catalogs: dict[int, dict[str, Any]] = {}
    for revision, total in ((4, 36), (5, 100)):
        gold_path = (
            repo
            / "data/gold_standard_datasets/nist800-53"
            / f"nist_sp800-53_rev{revision}_gold-set_{total}q.csv"
        )
        gold[revision] = read_csv(gold_path)
        ccs_path = (
            repo
            / "data/ccs/nist800-53"
            / f"NIST_SP-800-53_rev{revision}_catalog.jsonl"
        )
        ccs[revision] = [
            json.loads(line)
            for line in ccs_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        registries_csv[revision] = read_csv(
            repo / f"data/ODP/rev{revision}/odp_registry_rev{revision}.csv"
        )
        registries_json[revision] = read_json(
            repo / f"data/ODP/rev{revision}/odp_registry_rev{revision}.json"
        )
        raw_catalogs[revision] = read_json(
            repo
            / "data/raw/nist800-53"
            / f"NIST_SP-800-53_rev{revision}_catalog.json"
        )

    observed_gold = {
        "rev4_rows": len(gold[4]),
        "rev5_rows": len(gold[5]),
        "total_rows": len(gold[4]) + len(gold[5]),
        "rev4_odp_positive": sum(bool(row["odp_required"].strip()) for row in gold[4]),
        "rev5_odp_positive": sum(bool(row["odp_required"].strip()) for row in gold[5]),
    }
    expected_gold = {
        "rev4_rows": 36,
        "rev5_rows": 100,
        "total_rows": 136,
        "rev4_odp_positive": 19,
        "rev5_odp_positive": 63,
    }
    audit.add(
        "datasets",
        "benchmark and ODP-positive row counts",
        observed_gold == expected_gold,
        expected_gold,
        observed_gold,
        "gold-set CSVs",
    )
    add_anchor(
        audit,
        "chap5.tex",
        chap5,
        "RQ2 benchmark sizes",
        "RQ2 includes all 100 Rev.~5 questions and all 36 Rev.~4 questions.",
    )
    add_anchor(
        audit,
        "chap6.tex",
        chap6,
        "RQ3 ODP-positive sizes",
        "RQ3 uses the 63 Rev.~5 and 19 Rev.~4 gold rows",
    )

    observed_ccs: dict[str, Any] = {}
    for revision in (4, 5):
        kind_counts = Counter(row["kind"] for row in ccs[revision])
        observed_ccs[f"rev{revision}"] = {
            "total": len(ccs[revision]),
            "controls": len(
                {row["control_id"] for row in ccs[revision] if row.get("control_id")}
            ),
            "families": len(
                {
                    row["control_id"].split("-", 1)[0]
                    for row in ccs[revision]
                    if row.get("control_id")
                }
            ),
            "smt": kind_counts["smt"],
            "gdn": kind_counts["gdn"],
            "obj": kind_counts["obj"],
            "prm": kind_counts["prm"],
            "odp": kind_counts["odp"],
            "registry_rows": len(registries_csv[revision]),
            "registry_ids": len(registries_json[revision]),
        }
    expected_ccs = {
        "rev4": {
            "total": 7416,
            "controls": 826,
            "families": 18,
            "smt": 1586,
            "gdn": 695,
            "obj": 4282,
            "prm": 853,
            "odp": 0,
            "registry_rows": 853,
            "registry_ids": 853,
        },
        "rev5": {
            "total": 8423,
            "controls": 1013,
            "families": 20,
            "smt": 2125,
            "gdn": 1011,
            "obj": 3695,
            "prm": 142,
            "odp": 1450,
            "registry_rows": 3010,
            "registry_ids": 1592,
        },
    }
    audit.add(
        "datasets",
        "CCS and ODP registry counts",
        observed_ccs == expected_ccs,
        expected_ccs,
        observed_ccs,
        "CCS JSONL and ODP registry CSV/JSON files",
    )
    for label, fragment in (
        ("CCS total row", "Total records & 7,416 & 8,423 \\"),
        (
            "CCS statement row",
            "Statement records & 1,586 & 2,125 \\",
        ),
        ("CCS guidance row", "Guidance records & 695 & 1,011 \\"),
        ("CCS objective row", "Objective records & 4,282 & 3,695 \\"),
        ("CCS parameter row", "Parameter records & 853 & 142 \\"),
        ("CCS ODP row", "ODP records & 0 & 1,450 \\"),
        (
            "Rev. 4 registry row",
            "Rev.~4 ODP registry & 853 & 853 &",
        ),
        (
            "Rev. 5 registry row",
            "Rev.~5 ODP registry & 3,010 & 1,592 &",
        ),
    ):
        add_anchor(audit, "chap4.tex", chap4, label, fragment)

    metadata_observed = {}
    for revision in (4, 5):
        metadata = raw_catalogs[revision]["catalog"]["metadata"]
        metadata_observed[f"rev{revision}"] = {
            "version": metadata["version"],
            "oscal_version": metadata["oscal-version"],
            "last_modified_date": metadata["last-modified"][:10],
        }
    metadata_expected = {
        "rev4": {
            "version": "2015-01-22",
            "oscal_version": "1.1.1",
            "last_modified_date": "2023-10-12",
        },
        "rev5": {
            "version": "5.1.1+u4",
            "oscal_version": "1.1.2",
            "last_modified_date": "2024-02-04",
        },
    }
    audit.add(
        "upstream metadata",
        "embedded OSCAL catalog metadata",
        metadata_observed == metadata_expected,
        metadata_expected,
        metadata_observed,
        "raw NIST OSCAL catalogs",
    )


def retrieval_metrics(rows: list[dict[str, str]]) -> dict[str, float | int]:
    total = len(rows)
    ranks = [as_rank(row["rank"]) for row in rows]
    return {
        "n": total,
        "s1": sum(as_bool(row["is_hit_at_1"]) for row in rows) / total,
        "s5": sum(as_bool(row["is_hit_at_5"]) for row in rows) / total,
        "s10": sum(as_bool(row["is_hit_at_10"]) for row in rows) / total,
        "mrr10": sum(1 / rank for rank in ranks if rank is not None and rank <= 10)
        / total,
        "ndcg10": sum(
            1 / math.log2(rank + 1)
            for rank in ranks
            if rank is not None and rank <= 10
        )
        / total,
    }


def audit_retrieval_claims(audit: Audit, repo: Path, chap6: str) -> None:
    systems = {
        "S1": ("system_1_bm25", "S1_bm25", "S1 BM25"),
        "S2": ("system_2_dense", "S2_dense", "S2 Dense"),
        "S3": ("system_3_rewrite_only", "S3_rewrite_only", "S3 Rewrite only"),
        "S4": ("system_4_qur_rrf", "S4_qur_rrf", "S4 rewrite plus RRF"),
        "S5": ("system_5_hybrid_rrf", "S5_hybrid_rrf", "S5 Hybrid RRF"),
        "S6": (
            "system_6_hybrid_rerank",
            "S6_hybrid_rerank",
            "S6 Hybrid plus rerank",
        ),
        "S7": (
            "system_7_compliance_gpt",
            "S7_compliance_gpt",
            "S7 ComplianceGPT Retriever",
        ),
    }
    loaded: dict[tuple[str, str], list[dict[str, str]]] = {}
    for revision in ("rev5", "rev4"):
        for system, (directory, prefix, display) in systems.items():
            path = (
                repo
                / "experiments/retriever_ablation/ablation_outputs"
                / directory
                / f"{prefix}_{revision}_results.csv"
            )
            rows = read_csv(path)
            loaded[(revision, system)] = rows
            metric = retrieval_metrics(rows)
            row = (
                f"{display} & {metric['s1']:.4f} & {metric['s5']:.4f} & "
                f"{metric['s10']:.4f} & {metric['mrr10']:.4f} & "
                f"{metric['ndcg10']:.4f} \\\\"
            )
            add_anchor(
                audit,
                "chap6.tex",
                chap6,
                f"primary retrieval row {revision} {system}",
                row,
            )

            counts = [
                sum(as_bool(item[f"is_hit_at_{k}"]) for item in rows)
                for k in (1, 5, 10)
            ]
            cells = []
            for count in counts:
                low, high = wilson_interval(count, len(rows))
                rate = count / len(rows)
                rate_text = f"{rate:.3f}".lstrip("0")
                low_text = f"{low:.3f}".lstrip("0")
                high_text = f"{high:.3f}".lstrip("0")
                cells.append(f"{rate_text} [{low_text}, {high_text}]")
            interval_row = f"{display} & " + " & ".join(cells) + " \\\\"
            add_anchor(
                audit,
                "chap6.tex",
                chap6,
                f"Wilson interval row {revision} {system}",
                interval_row,
            )

            error_path = (
                repo
                / "experiments/retriever_ablation/ablation_outputs"
                / directory
                / f"{prefix}_error_bank_{revision}_results.csv"
            )
            error_metric = retrieval_metrics(read_csv(error_path))
            error_row = (
                f"{display} & {error_metric['s1']:.4f} & "
                f"{error_metric['s5']:.4f} & {error_metric['s10']:.4f} & "
                f"{error_metric['mrr10']:.4f} & "
                f"{error_metric['ndcg10']:.4f} \\\\"
            )
            add_anchor(
                audit,
                "chap6.tex",
                chap6,
                f"ErrorBank retrieval row {revision} {system}",
                error_row,
            )

    for revision, left_name, right_name, row_fragment in (
        ("rev5", "S7", "S5", "Rev.~5 & .900 & S5: .890 & 5 & 4 & 1 & 1.000"),
        ("rev4", "S7", "S2", "Rev.~4 & .917 & S2: .889 & 3 & 2 & 1 & 1.000"),
    ):
        left = {row["question_id"]: row for row in loaded[(revision, left_name)]}
        right = {row["question_id"]: row for row in loaded[(revision, right_name)]}
        left_only = sum(
            as_bool(left[key]["is_hit_at_1"])
            and not as_bool(right[key]["is_hit_at_1"])
            for key in left
        )
        right_only = sum(
            as_bool(right[key]["is_hit_at_1"])
            and not as_bool(left[key]["is_hit_at_1"])
            for key in left
        )
        observed = {
            "left_only": left_only,
            "right_only": right_only,
            "net": left_only - right_only,
            "p": exact_mcnemar(left_only, right_only),
        }
        expected = {
            "left_only": 5 if revision == "rev5" else 3,
            "right_only": 4 if revision == "rev5" else 2,
            "net": 1,
            "p": 1.0,
        }
        audit.add(
            "RQ1 evidence",
            f"paired S@1 audit {revision}",
            observed == expected,
            expected,
            observed,
            "frozen S1-S7 CSVs",
        )
        add_anchor(
            audit,
            "chap6.tex",
            chap6,
            f"paired S@1 manuscript row {revision}",
            row_fragment,
        )


def nested(document: dict[str, Any], *keys: str) -> Any:
    value: Any = document
    for key in keys:
        value = value[key]
    return value


def audit_answerer_claims(audit: Audit, repo: Path, chap6: str, appendix: str) -> None:
    rev5 = read_json(
        repo
        / "experiments/answerer_comparison/rq2_frontier_baseline_rev5/results_v1/summary.json"
    )
    rev4 = read_json(
        repo
        / "experiments/answerer_comparison/rq2_frontier_baseline/results_v1/summary.json"
    )
    no_selector = read_json(
        repo
        / "experiments/answerer_comparison/rq2_no_selector/results_v1/summary.json"
    )
    rescue = read_json(
        repo
        / "experiments/answerer_comparison/rq2_rescue_ablation/results_v1/summary.json"
    )
    provenance = read_json(
        repo
        / "experiments/answerer_comparison/rq2_identifier_provenance/results_v1/summary.json"
    )
    mutation = read_json(
        repo
        / "experiments/answerer_comparison/runtime_verifier_mutation/results_v1/summary.json"
    )
    preserve = read_json(
        repo
        / "experiments/answerer_comparison/rq2_preserve_replay/results_v1/summary.json"
    )
    retest = read_json(
        repo
        / "experiments/annotation_reliability/intra_annotator_retest/reveal/agreement_summary.json"
    )
    gate = read_json(
        repo
        / "experiments/answerer_comparison/rq2_control_gate_width/results_v1/summary.json"
    )
    bf16 = read_json(
        repo
        / "experiments/answerer_comparison/rq2_bf16_baseline/results_v1/summary.json"
    )

    headline_observed = {
        "rev5": {
            "compliancegpt_strict": nested(
                rev5, "configurations", "compliancegpt_4bit", "strict_pass", "count"
            ),
            "gemini_strict": nested(
                rev5,
                "configurations",
                "generative_frontier_api",
                "strict_pass",
                "count",
            ),
            "qwen_strict": nested(
                rev5,
                "configurations",
                "generative_baseline_4bit",
                "strict_pass",
                "count",
            ),
            "paired": nested(
                rev5,
                "paired_strict_pass",
                "compliancegpt_vs_frontier",
            ),
        },
        "rev4": {
            "compliancegpt_strict": nested(
                rev4, "configurations", "compliancegpt_4bit", "strict_pass", "count"
            ),
            "gemini_strict": nested(
                rev4,
                "configurations",
                "generative_frontier_api",
                "strict_pass",
                "count",
            ),
            "qwen_strict": nested(
                rev4,
                "configurations",
                "generative_baseline_4bit",
                "strict_pass",
                "count",
            ),
            "paired": nested(
                rev4,
                "paired_strict_pass",
                "frontier_vs_4bit_compliancegpt",
            ),
        },
    }
    expected_headline = {
        "rev5": {
            "compliancegpt_strict": 65,
            "gemini_strict": 66,
            "qwen_strict": 25,
            "paired": {
                "both_pass": 54,
                "exact_mcnemar_two_sided_p": 1.0,
                "left": "compliancegpt_4bit",
                "left_only": 11,
                "neither_pass": 23,
                "paired_rows": 100,
                "right": "generative_frontier_api",
                "right_only": 12,
            },
        },
        "rev4": {
            "compliancegpt_strict": 29,
            "gemini_strict": 24,
            "qwen_strict": 8,
            "paired": {
                "both_pass": 21,
                "exact_mcnemar_two_sided_p": 0.2265625,
                "left": "generative_frontier_api",
                "left_only": 3,
                "neither_pass": 4,
                "paired_rows": 36,
                "right": "compliancegpt_4bit",
                "right_only": 8,
            },
        },
    }
    audit.add(
        "RQ2 evidence",
        "frontier strict-pass endpoints and paired tests",
        headline_observed == expected_headline,
        expected_headline,
        headline_observed,
        "Batch 5C and 5D summary.json",
    )

    anchors = [
        (
            "frontier endpoint row",
            "Offline strict pass & 65/100 & 66/100 & 29/36 & 24/36",
        ),
        (
            "frontier paired Rev. 5",
            "Rev.~5 & 100 & 11 & 12 & 1.000",
        ),
        (
            "frontier paired Rev. 4",
            "Rev.~4 & 36 & 8 & 3 & 0.2266",
        ),
        (
            "gate endpoints",
            "Adaptive v3 & 65/100 & 97/100 & 29/36 & 36/36",
        ),
        (
            "fixed top-two endpoints",
            "Fixed top 2 & 65/100 & 99/100 & 29/36 & 36/36",
        ),
        (
            "no-selector endpoints",
            "Offline strict pass & 65/100 & 92/100 & 29/36 & 35/36",
        ),
        (
            "rescue endpoints",
            "Offline strict pass & 59/100 & 65/100 & 29/36 & 29/36",
        ),
        (
            "ODP operating points",
            "ComplianceGPT & 63/63 (1.000) & 17/37 (0.459) & 63/83 (0.759) & 19/19 (1.000) & 8/17 (0.471) & 19/28 (0.679)",
        ),
        (
            "mutation ODP removal",
            "Remove one ODP-list entry & 111 & 41 & 0.3694",
        ),
        (
            "test-retest control row",
            "Control exact agreement & 29/30 (0.9667) & 8/8 (1.0000) & 21/22 (0.9545)",
        ),
        (
            "test-retest clause row",
            "Clause-set exact agreement & 16/30 (0.5333) & 4/8 (0.5000) & 12/22 (0.5455)",
        ),
        (
            "test-retest ODP row",
            "ODP-set exact agreement & 26/30 (0.8667) & 7/8 (0.8750) & 19/22 (0.8636)",
        ),
    ]
    for name, fragment in anchors:
        add_anchor(audit, "chap6.tex", chap6, name, fragment)

    evidence_observed = {
        "gate": {
            revision: {
                condition: {
                    "strict": gate["configurations"][f"{revision}_{condition}"][
                        "strict_pass"
                    ]["count"],
                    "control": gate["configurations"][f"{revision}_{condition}"][
                        "right_governing_control"
                    ]["count"],
                }
                for condition in ("adaptive_v3", "top2")
            }
            for revision in ("rev5", "rev4")
        },
        "bf16": {
            "strict": bf16["configurations"]["generative_baseline_bf16"][
                "strict_pass"
            ]["count"],
            "coverage": bf16["configurations"]["generative_baseline_bf16"][
                "full_gold_clause_coverage"
            ]["count"],
            "runtime": bf16["configurations"]["generative_baseline_bf16"][
                "runtime_contract_pass"
            ]["count"],
        },
        "no_selector": {
            revision: no_selector["revisions"][revision]["no_selector_v1"][
                "offline_strict_pass"
            ]["count"]
            for revision in ("rev5", "rev4")
        },
        "rescue": {
            revision: {
                state: rescue["revisions"][revision][state]["offline_strict_pass"][
                    "count"
                ]
                for state in ("rescue_off", "rescue_on")
            }
            for revision in ("rev5", "rev4")
        },
        "provenance": {
            "contracts": provenance["combined"]["contracts"],
            "occurrences": provenance["combined"]["identifier_occurrences"],
            "selector": provenance["combined"]["by_origin"]["selector"][
                "identifier_occurrences"
            ],
            "fallback": provenance["combined"]["by_origin"]["fallback"][
                "identifier_occurrences"
            ],
            "rescue": provenance["combined"]["by_origin"]["rescue"][
                "identifier_occurrences"
            ],
            "hierarchy": provenance["combined"]["by_origin"]["hierarchy"][
                "identifier_occurrences"
            ],
        },
        "mutation": {
            "planned": mutation["planned_operator_cells"],
            "attempted": mutation["total_attempted_mutations"],
            "detected": mutation["total_detected_mutations"],
            "odp_attempted": mutation["operators"]["drop_odp_entry"]["attempted"],
            "odp_detected": mutation["operators"]["drop_odp_entry"]["detected"],
        },
        "preserve": {
            "rows": preserve["row_count"],
            "runtime": preserve["counts"]["runtime_contract_valid"],
            "offline": preserve["counts"]["offline_verifier_pass"],
            "accepted": preserve["accepted"],
        },
        "retest": retest["summary"]["overall"],
    }
    evidence_expected = {
        "gate": {
            "rev5": {
                "adaptive_v3": {"strict": 65, "control": 97},
                "top2": {"strict": 65, "control": 99},
            },
            "rev4": {
                "adaptive_v3": {"strict": 29, "control": 36},
                "top2": {"strict": 29, "control": 36},
            },
        },
        "bf16": {"strict": 8, "coverage": 20, "runtime": 14},
        "no_selector": {"rev5": 92, "rev4": 35},
        "rescue": {
            "rev5": {"rescue_off": 59, "rescue_on": 65},
            "rev4": {"rescue_off": 29, "rescue_on": 29},
        },
        "provenance": {
            "contracts": 136,
            "occurrences": 582,
            "selector": 530,
            "fallback": 2,
            "rescue": 50,
            "hierarchy": 0,
        },
        "mutation": {
            "planned": 680,
            "attempted": 619,
            "detected": 549,
            "odp_attempted": 111,
            "odp_detected": 41,
        },
        "preserve": {"rows": 8, "runtime": 8, "offline": 5, "accepted": True},
        "retest": {
            "all_components_exact_count": 16,
            "all_components_exact_rate": 0.5333333333333333,
            "clause_mean_jaccard": 0.795515873015873,
            "clause_set_exact_count": 16,
            "clause_set_exact_rate": 0.5333333333333333,
            "control_cohens_kappa": 0.9653979238754326,
            "control_exact_count": 29,
            "control_exact_rate": 0.9666666666666667,
            "n": 30,
            "odp_mean_jaccard": 0.8866666666666667,
            "odp_set_exact_count": 26,
            "odp_set_exact_rate": 0.8666666666666667,
            "rows_with_any_disagreement": 14,
        },
    }
    audit.add(
        "experiment evidence",
        "follow-on experiment endpoint census",
        evidence_observed == evidence_expected,
        evidence_expected,
        evidence_observed,
        "checked-in machine-readable summaries",
    )
    add_anchor(
        audit,
        "appendix.tex",
        appendix,
        "PRESERVE public precommit",
        PUBLIC_PRESERVE_PRECOMMIT,
        "publication identity",
    )
    add_anchor(
        audit,
        "appendix.tex",
        appendix,
        "PRESERVE public result commit",
        PUBLIC_PRESERVE_RESULT,
        "publication identity",
    )


def audit_notebook_and_git_identity(
    audit: Audit, repo: Path, appendix: str
) -> None:
    relative = (
        "experiments/answerer_comparison/rq2_frontier_baseline_rev5/"
        "Batch_5D_Rev5_Frontier_API_Baseline.ipynb"
    )
    current_path = repo / relative
    current_bytes = current_path.read_bytes()
    historical_bytes = subprocess.check_output(
        ["git", "show", f"{HISTORICAL_NOTEBOOK_COMMIT}:{relative}"], cwd=repo
    )
    current_document = json.loads(current_bytes)
    historical_document = json.loads(historical_bytes)
    observed = {
        "historical_file_sha256": sha256_bytes(historical_bytes),
        "current_file_sha256": sha256_bytes(current_bytes),
        "historical_semantic_sha256": semantic_notebook_sha(historical_document),
        "current_semantic_sha256": semantic_notebook_sha(current_document),
        "historical_cells": len(historical_document["cells"]),
        "current_cells": len(current_document["cells"]),
        "historical_output_blocks": sum(
            len(cell.get("outputs", [])) for cell in historical_document["cells"]
        ),
        "current_output_blocks": sum(
            len(cell.get("outputs", [])) for cell in current_document["cells"]
        ),
    }
    expected = {
        "historical_file_sha256": HISTORICAL_NOTEBOOK_SHA256,
        "current_file_sha256": CURRENT_NOTEBOOK_SHA256,
        "historical_semantic_sha256": NOTEBOOK_SEMANTIC_SHA256,
        "current_semantic_sha256": NOTEBOOK_SEMANTIC_SHA256,
        "historical_cells": 13,
        "current_cells": 13,
        "historical_output_blocks": 11,
        "current_output_blocks": 11,
    }
    audit.add(
        "publication identity",
        "Batch 5D historical/current notebook identity",
        observed == expected,
        expected,
        observed,
        relative,
    )
    for name, digest in (
        ("historical Batch 5D notebook hash", HISTORICAL_NOTEBOOK_SHA256),
        ("current Batch 5D notebook hash", CURRENT_NOTEBOOK_SHA256),
        ("Batch 5D notebook semantic hash", NOTEBOOK_SEMANTIC_SHA256),
        ("historical Batch 5D public commit", HISTORICAL_NOTEBOOK_COMMIT),
        ("current Batch 5D public commit", CURRENT_NOTEBOOK_COMMIT),
    ):
        add_anchor(
            audit,
            "appendix.tex",
            appendix,
            name,
            digest,
            "publication identity",
        )

    local_tree = git_output(repo, "rev-parse", f"{LOCAL_PRESERVE_PRECOMMIT}^{{tree}}")
    public_tree = git_output(
        repo, "rev-parse", f"{PUBLIC_PRESERVE_PRECOMMIT}^{{tree}}"
    )
    final_tree = git_output(repo, "rev-parse", f"{PUBLIC_PRESERVE_RESULT}^{{tree}}")
    git_observed = {
        "local_precommit_tree": local_tree,
        "public_precommit_tree": public_tree,
        "public_final_tree": final_tree,
    }
    git_expected = {
        "local_precommit_tree": "f62d667917fe84855506752dbfb55649b0956c96",
        "public_precommit_tree": "f62d667917fe84855506752dbfb55649b0956c96",
        "public_final_tree": "e58ba15d5ab9e7c98c6e500a696018d10eefb35b",
    }
    audit.add(
        "publication identity",
        "PRESERVE local/public commit tree mapping",
        git_observed == git_expected,
        git_expected,
        git_observed,
        "Git object database",
    )


def audit_stale_claims(audit: Audit, sources: dict[str, str]) -> None:
    patterns = {
        "Recall@ terminology": r"(?<![A-Za-z])Recall@",
        "unqualified accuracy superiority": (
            r"(?i)ComplianceGPT[^.\n]{0,120}(?:outperform|superior|more accurate)"
        ),
        "old 67-reference inventory": r"(?i)\b67 references\b",
    }
    for label, pattern in patterns.items():
        matches: list[str] = []
        regex = re.compile(pattern)
        for name, source in sources.items():
            for match in regex.finditer(source):
                line = source.count("\n", 0, match.start()) + 1
                snippet = normalize_space(match.group(0))
                matches.append(f"{name}:{line}: {snippet}")
        audit.add(
            "claim boundaries",
            f"no stale {label}",
            not matches,
            [],
            matches,
            "all TeX sources",
        )
    preserve_matches = []
    regex = re.compile(
        r"(?i)PRESERVE[^.\n]{0,180}returns?\s+\\texttt\{OK\}"
    )
    for name, source in sources.items():
        for match in regex.finditer(source):
            context_start = max(0, match.start() - 120)
            context = normalize_space(source[context_start : match.end()])
            if "cannot return \\texttt{ok}" in context.lower():
                continue
            if not any(
                qualifier in context.lower()
                for qualifier in ("frozen version", "historical", "v1.0")
            ):
                line = source.count("\n", 0, match.start()) + 1
                preserve_matches.append(f"{name}:{line}: {context}")
    audit.add(
        "claim boundaries",
        "PRESERVE OK wording is historically qualified",
        not preserve_matches,
        [],
        preserve_matches,
        "all TeX sources",
    )


def markdown_report(report: dict[str, Any], manuscript: Path, repo: Path) -> str:
    lines = [
        "# Manuscript consistency audit",
        "",
        f"Status: **{report['status']}**",
        "",
        f"- Manuscript source: `{manuscript}`",
        f"- Repository: `{repo}`",
        f"- Checks passed: {report['checks_passed']}/{report['checks_total']}",
        f"- Checks failed: {report['checks_failed']}",
        "",
        "## Check groups",
        "",
        "| Group | Passed | Total |",
        "|---|---:|---:|",
    ]
    for category, values in report["by_category"].items():
        lines.append(f"| {category} | {values['passed']} | {values['total']} |")
    lines.extend(["", "## Failures", ""])
    if not report["failures"]:
        lines.append("None.")
    else:
        for failure in report["failures"]:
            lines.append(
                f"- **{failure['category']} / {failure['name']}** — "
                f"expected `{failure['expected']}`; observed `{failure['observed']}`; "
                f"evidence: `{failure['evidence']}`"
            )
    lines.extend(
        [
            "",
            "## Scope boundary",
            "",
            "This audit checks internal traceability from the manuscript to the "
            "frozen repository evidence. It does not independently validate legal "
            "sufficiency, benchmark labels, or external factual claims beyond the "
            "pinned source records.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manuscript_dir", type=Path)
    parser.add_argument(
        "--repo-dir", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    args = parser.parse_args()

    manuscript = args.manuscript_dir.resolve()
    repo = args.repo_dir.resolve()
    sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(manuscript.glob("*.tex"))
    }
    audit = Audit()
    audit.add(
        "LaTeX structure",
        "expected manuscript source inventory",
        len(sources) == 15,
        15,
        len(sources),
        str(manuscript),
    )
    audit_tex_structure(audit, manuscript, sources)
    audit_explicit_hashes(audit, repo, sources)
    appendix = sources.get("appendix.tex", "")
    audit_repo_paths(audit, repo, appendix)
    audit_dataset_and_corpus_claims(
        audit,
        repo,
        sources.get("chap4.tex", ""),
        sources.get("chap5.tex", ""),
        sources.get("chap6.tex", ""),
    )
    audit_retrieval_claims(audit, repo, sources.get("chap6.tex", ""))
    audit_answerer_claims(
        audit, repo, sources.get("chap6.tex", ""), appendix
    )
    audit_notebook_and_git_identity(audit, repo, appendix)
    audit_stale_claims(audit, sources)

    report = audit.report()
    if args.json_out:
        args.json_out.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if args.markdown_out:
        args.markdown_out.write_text(
            markdown_report(report, manuscript, repo), encoding="utf-8"
        )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
