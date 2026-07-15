#!/usr/bin/env python3
"""Run the matched S4/S4b and S7/S7a diagnostic retrieval study.

S4b and S7a use the gold control to select one of the existing query rewrites.
They are diagnostic variants, not deployable retrieval systems.  This runner
imports the canonical S7 query planner, fusion, scope adjustment, and guard
logic from ``src/compliancegpt/retriever/retriever_s7.py``.  It also reruns S4
and S7 in the same process so every reported contrast is matched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from compliancegpt.retriever import retriever_s7 as canonical_s7


TOP_N = 10
BM25_K1 = 1.5
BM25_B = 0.75
DENSE_MODEL_ID = "intfloat/e5-small-v2"
RERANKER_MODEL_ID = "BAAI/bge-reranker-base"
CANDIDATE_SET_SIZE = 50
RRF_K = 60
S4_MAX_REWRITES = 5
S7_MAX_REWRITES = 3
REWRITE_WEIGHT = 0.25
REWRITE_JACCARD_MIN = 0.15
RERANK_ALPHA = 0.65
RERANK_APPLY_MIN_MARGIN_RATIO = 0.15
RERANK_SKIP_MIN_BASE_MARGIN_RATIO = 0.10
SCOPE_MATCH_BIAS_RATIO = 0.08
SCOPE_MISMATCH_PENALTY_RATIO = 0.06

PUNCT_RE = re.compile(r"[^0-9A-Za-z_\s]+")
WS_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[A-Za-z0-9]+")
CONTROL_ID_DOT_RE = re.compile(r"^([A-Z]{2,3}-\d+)\.(\d+)$")
CONTROL_ID_PAREN_RE = re.compile(r"^([A-Z]{2,3}-\d+)\((\d+)\)$")


def normalize_text(text: object) -> str:
    value = "" if pd.isna(text) else str(text)
    value = value.lower().replace("-", " ")
    return WS_RE.sub(" ", PUNCT_RE.sub(" ", value)).strip()


def tokenize(text: object) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(str(text))]


def normalize_control_id(control_id: object) -> str:
    if not isinstance(control_id, str):
        return ""
    value = control_id.strip().upper().replace("_", "-")
    match = CONTROL_ID_DOT_RE.match(value)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    match = CONTROL_ID_PAREN_RE.match(value)
    if match:
        return f"{match.group(1)}({match.group(2)})"
    return value


def strict_key(text: object) -> str:
    return "".join(character.lower() for character in str(text) if character.isalnum())


def jaccard_overlap(left: str, right: str) -> float:
    left_tokens = set(tokenize(normalize_text(left)))
    right_tokens = set(tokenize(normalize_text(right)))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / float(len(left_tokens | right_tokens))


class DenseIndex:
    def __init__(self, model_id: str):
        import torch
        from sentence_transformers import SentenceTransformer

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(model_id, device=self.device)
        self.ids: list[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self.query_cache: dict[str, np.ndarray] = {}

    def build(self, texts: list[str], ids: list[str]) -> None:
        self.ids = list(ids)
        embeddings = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        self.embeddings = np.asarray(embeddings, dtype=np.float32)

    def search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        if self.embeddings is None:
            raise RuntimeError("Dense index has not been built")
        if query not in self.query_cache:
            encoded = self.model.encode([query], normalize_embeddings=True, show_progress_bar=False)
            self.query_cache[query] = np.asarray(encoded, dtype=np.float32)[0]
        scores = self.embeddings @ self.query_cache[query]
        count = min(int(top_k), len(scores))
        if count == len(scores):
            indices = np.argsort(-scores)
        else:
            part = np.argpartition(-scores, count - 1)[:count]
            indices = part[np.argsort(-scores[part])]
        return [(self.ids[int(index)], float(scores[int(index)])) for index in indices[:count]]


class ClauseDenseControlAdapter:
    def __init__(
        self,
        dense_index: DenseIndex,
        clause_to_control: dict[str, str],
    ):
        self.index = dense_index
        self.clause_to_control = clause_to_control
        self.cache: dict[tuple[str, int], list[tuple[str, float]]] = {}

    def search(self, query: str, top_k: int = CANDIDATE_SET_SIZE) -> list[tuple[str, float]]:
        key = (query, int(top_k))
        if key not in self.cache:
            best_scores: dict[str, float] = {}
            for clause_id, score in self.index.search(query, top_k=int(top_k) * 5):
                control = normalize_control_id(self.clause_to_control.get(clause_id, ""))
                if control and score > best_scores.get(control, -1.0):
                    best_scores[control] = score
            ranked = sorted(best_scores.items(), key=lambda item: item[1], reverse=True)[: int(top_k)]
            self.cache[key] = ranked
        return list(self.cache[key])


@dataclass
class RetrievalResources:
    bm25: Any
    control_ids: list[str]
    dense: ClauseDenseControlAdapter
    reranker: Any
    fallback_text: dict[str, str]


def build_resources(catalog_path: Path) -> RetrievalResources:
    from sentence_transformers import CrossEncoder
    import torch

    records = canonical_s7.load_clause_records_jsonl(str(catalog_path), keep_kinds={"smt", "gdn"})
    documents = canonical_s7.build_control_docs_from_clauses(records)
    bm25, control_ids = canonical_s7.build_bm25(documents, k1=BM25_K1, b=BM25_B)

    clause_ids: list[str] = []
    dense_texts: list[str] = []
    clause_to_control: dict[str, str] = {}
    for record in records:
        packed = f"{record['control_id']} {record['title']} ({record['kind']})\n{record['text']}"
        clause_ids.append(record["id"])
        dense_texts.append(f"passage: {packed}")
        clause_to_control[record["id"]] = record["control_id"]

    dense_index = DenseIndex(DENSE_MODEL_ID)
    dense_index.build(dense_texts, clause_ids)
    dense = ClauseDenseControlAdapter(dense_index, clause_to_control)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    reranker = CrossEncoder(RERANKER_MODEL_ID, device=device)
    fallback_text = canonical_s7.build_control_fallback_text_map(records)
    return RetrievalResources(bm25, control_ids, dense, reranker, fallback_text)


def get_rewrites(query: str, rewrite_frame: pd.DataFrame, max_rewrites: int) -> list[str]:
    matches = rewrite_frame.loc[rewrite_frame["strict_key"].eq(strict_key(query))]
    rewrites: list[str] = []
    for value in matches["rewritten_query"].tolist():
        rewrite = str(value).strip()
        if len(rewrite) < 6 or jaccard_overlap(query, rewrite) < REWRITE_JACCARD_MIN:
            continue
        if rewrite not in rewrites:
            rewrites.append(rewrite)
    return rewrites[: int(max_rewrites)]


def get_stored_rewrites(query: str, rewrite_frame: pd.DataFrame) -> list[str]:
    """Return unique stored rewrites before canonical S7 planning and filtering."""
    matches = rewrite_frame.loc[rewrite_frame["strict_key"].eq(strict_key(query))]
    rewrites: list[str] = []
    for value in matches["rewritten_query"].tolist():
        rewrite = str(value).strip()
        if len(rewrite) >= 6 and rewrite not in rewrites:
            rewrites.append(rewrite)
    return rewrites


def prepare_s7_plan(query: str, rewrite_frame: pd.DataFrame) -> dict[str, Any]:
    """Mirror ``ComplianceGPTRetriever._prepare_retrieval_plan`` with rewrite provenance."""
    retrieval_query, query_meta = canonical_s7.build_retrieval_query(
        query,
        strip_meta=True,
        expand_scope_terms=True,
    )
    transformed_pairs: list[dict[str, str]] = []
    seen = {retrieval_query} if retrieval_query else set()
    for raw_rewrite in get_stored_rewrites(query, rewrite_frame):
        transformed, _ = canonical_s7.build_retrieval_query(
            raw_rewrite,
            strip_meta=True,
            expand_scope_terms=True,
        )
        if transformed and transformed not in seen:
            seen.add(transformed)
            transformed_pairs.append({"raw": raw_rewrite, "transformed": transformed})

    query_tokens = set(canonical_s7.tokenize(retrieval_query))
    accepted_pairs: list[dict[str, str]] = []
    for pair in transformed_pairs:
        rewrite_tokens = set(canonical_s7.tokenize(pair["transformed"]))
        if query_tokens and rewrite_tokens:
            union = query_tokens | rewrite_tokens
            overlap = len(query_tokens & rewrite_tokens) / float(len(union)) if union else 0.0
            if overlap < REWRITE_JACCARD_MIN:
                continue
        accepted_pairs.append(pair)
        if len(accepted_pairs) >= S7_MAX_REWRITES:
            break

    variants = canonical_s7.build_query_variants(
        retrieval_query,
        [pair["transformed"] for pair in transformed_pairs],
        max_rewrites=S7_MAX_REWRITES,
        jaccard_min=REWRITE_JACCARD_MIN,
    )
    return {
        "raw_query": query,
        "retrieval_query": retrieval_query,
        "query_scope": str(query_meta.get("scope") or "neutral"),
        "accepted_rewrites": accepted_pairs,
        "variants": variants,
    }


def rrf_fuse(ranked_lists: list[list[str]], weights: list[float]) -> tuple[list[str], dict[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    for weight, ranked in zip(weights, ranked_lists):
        for rank, control in enumerate(ranked, start=1):
            canonical = normalize_control_id(control)
            scores[canonical] += float(weight) / float(RRF_K + rank)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    return [control for control, _ in ordered], dict(scores)


def rank_of(gold: str, ranked: list[str], limit: int = TOP_N) -> int:
    canonical_gold = normalize_control_id(gold)
    for rank, control in enumerate(ranked[: int(limit)], start=1):
        if normalize_control_id(control) == canonical_gold:
            return rank
    return 0


def bm25_rrf(resources: RetrievalResources, variants: list[str], top_n: int = TOP_N) -> list[str]:
    lists = []
    for variant in variants:
        indices = resources.bm25.get_top_n(tokenize(normalize_text(variant)), n=int(top_n))
        lists.append([resources.control_ids[index] for index in indices])
    weights = [1.0] + [REWRITE_WEIGHT] * (len(variants) - 1)
    ranked, _ = rrf_fuse(lists, weights)
    return ranked[: int(top_n)]


def rank_current_s7(
    resources: RetrievalResources,
    retrieval_query: str,
    variants: list[str],
    query_scope: str,
    *,
    rerank_query: Optional[str] = None,
    force_base_order: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    """Call the repository's canonical S7 control-ranking implementation."""
    ranked, metadata = canonical_s7.s7_rank_controls(
        original_query=rerank_query or retrieval_query,
        variants=variants,
        bm25_retriever=resources.bm25,
        bm25_control_ids=resources.control_ids,
        dense_adapter=resources.dense,
        reranker=resources.reranker,
        reranker_text_by_control=resources.fallback_text,
        candidate_set_size=CANDIDATE_SET_SIZE,
        rrf_k=RRF_K,
        rewrite_weight=REWRITE_WEIGHT,
        rerank_alpha=RERANK_ALPHA,
        rerank_apply_min_margin_ratio=RERANK_APPLY_MIN_MARGIN_RATIO,
        rerank_skip_enabled=True,
        rerank_skip_min_base_margin_ratio=(0.0 if force_base_order else RERANK_SKIP_MIN_BASE_MARGIN_RATIO),
        rerank_skip_require_top1_agreement=False,
        query_scope=query_scope,
        scope_match_bias_ratio=SCOPE_MATCH_BIAS_RATIO,
        scope_mismatch_penalty_ratio=SCOPE_MISMATCH_PENALTY_RATIO,
    )
    return ranked, metadata


def select_gold_informed_rewrite(
    resources: RetrievalResources,
    retrieval_query: str,
    query_scope: str,
    gold_control: str,
    rewrite_pairs: list[dict[str, str]],
) -> Optional[dict[str, str]]:
    best_rewrite: Optional[dict[str, str]] = None
    best_rank: Optional[int] = None
    for pair in rewrite_pairs:
        variants = canonical_s7.build_query_variants(
            retrieval_query,
            [pair["transformed"]],
            max_rewrites=1,
            jaccard_min=REWRITE_JACCARD_MIN,
        )
        ranked, _ = rank_current_s7(
            resources,
            retrieval_query,
            variants,
            query_scope,
            force_base_order=True,
        )
        candidate_rank = rank_of(gold_control, ranked, CANDIDATE_SET_SIZE)
        if candidate_rank and (best_rank is None or candidate_rank < best_rank):
            best_rank = candidate_rank
            best_rewrite = pair
    return best_rewrite


def evaluate_row(
    resources: RetrievalResources,
    row: pd.Series,
    rewrite_frame: pd.DataFrame,
    dataset: str,
    gold_column: str,
    id_column: str,
) -> list[dict[str, Any]]:
    query = str(row["question"])
    gold = normalize_control_id(row[gold_column])
    rewrites_s4 = get_rewrites(query, rewrite_frame, S4_MAX_REWRITES)
    plan = prepare_s7_plan(query, rewrite_frame)
    selected = select_gold_informed_rewrite(
        resources,
        plan["retrieval_query"],
        plan["query_scope"],
        gold,
        plan["accepted_rewrites"],
    )
    selected_raw = selected["raw"] if selected else ""
    selected_transformed = selected["transformed"] if selected else ""

    s4_ranked = bm25_rrf(resources, [query] + rewrites_s4)
    s4b_ranked = bm25_rrf(resources, [query] + ([selected_raw] if selected else []))
    s7_ranked, s7_meta = rank_current_s7(
        resources,
        plan["retrieval_query"],
        plan["variants"],
        plan["query_scope"],
    )
    s7a_ranked, s7a_meta = rank_current_s7(
        resources,
        plan["retrieval_query"],
        plan["variants"],
        plan["query_scope"],
        rerank_query=selected_transformed or plan["retrieval_query"],
    )

    common_s7_meta = {
        "retrieval_query": plan["retrieval_query"],
        "query_scope": plan["query_scope"],
    }

    systems = [
        ("S4", s4_ranked, {"sys": "S4", "n_vars": 1 + len(rewrites_s4)}),
        (
            "S4b",
            s4b_ranked,
            {"sys": "S4b", "n_vars": 2 if selected else 1, "gold_informed_rewrite_used": bool(selected)},
        ),
        ("S7", s7_ranked, {**s7_meta, **common_s7_meta, "sys": "S7"}),
        (
            "S7a",
            s7a_ranked,
            {
                **s7a_meta,
                **common_s7_meta,
                "sys": "S7a",
                "gold_informed_rewrite_used": bool(selected),
            },
        ),
    ]
    results = []
    for system, ranked, metadata in systems:
        top = [normalize_control_id(control) for control in ranked[:TOP_N]]
        rank = rank_of(gold, top, TOP_N)
        results.append(
            {
                "dataset": dataset,
                "system": system,
                "question_id": int(row[id_column]),
                "question": query,
                "gold_control_id": gold,
                "rank": rank,
                "is_hit_at_1": rank == 1,
                "is_hit_at_5": 1 <= rank <= 5,
                "is_hit_at_10": 1 <= rank <= 10,
                "mrr@10": 1.0 / rank if rank else 0.0,
                "ndcg@10": 1.0 / math.log2(rank + 1) if rank else 0.0,
                "top_1_hit": top[0] if top else "",
                "retrieved_control_ids": json.dumps(top),
                "selected_rewrite": selected_raw,
                "selected_retrieval_rewrite": selected_transformed,
                "system_meta": json.dumps(metadata, sort_keys=True),
            }
        )
    return results


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_versions() -> dict[str, str]:
    from importlib.metadata import version

    packages = ["numpy", "pandas", "torch", "sentence-transformers", "transformers", "huggingface-hub"]
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = version(package)
        except Exception:
            versions[package] = "unavailable"
    return versions


def model_revision(model_id: str) -> str:
    try:
        from huggingface_hub import model_info

        return str(model_info(model_id).sha)
    except Exception as error:
        return f"unavailable: {type(error).__name__}"


def run_revision(repo_root: Path, revision: str, parts_root: Path) -> None:
    catalog = repo_root / f"data/ccs/nist800-53/NIST_SP-800-53_{revision}_catalog.jsonl"
    gold_filename = {
        "rev5": "nist_sp800-53_rev5_gold-set_100q.csv",
        "rev4": "nist_sp800-53_rev4_gold-set_36q.csv",
    }[revision]
    gold_path = repo_root / "data/gold_standard_datasets/nist800-53" / gold_filename
    error_path = repo_root / "data/error_bank/error_bank_v1.csv"
    gold_rewrites_path = repo_root / f"data/qur_outputs/qur_rewrites_{revision}.csv"
    error_rewrites_path = repo_root / "data/qur_outputs/qur_rewrites_error_bank.csv"

    resources = build_resources(catalog)
    gold = pd.read_csv(gold_path, encoding="ISO-8859-1")
    error_bank = pd.read_csv(error_path, encoding="ISO-8859-1")
    error_bank = error_bank.loc[error_bank["version"].astype(str).str.lower().eq(revision)].copy()
    gold_rewrites = pd.read_csv(gold_rewrites_path, encoding="ISO-8859-1")
    error_rewrites = pd.read_csv(error_rewrites_path, encoding="ISO-8859-1")
    for frame in (gold_rewrites, error_rewrites):
        frame["strict_key"] = frame["original_query"].map(strict_key)

    output_dir = parts_root / revision
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_specs = [
        (f"{revision}_gold", gold, gold_rewrites, "control_id", "id"),
        (f"error_bank_{revision}", error_bank, error_rewrites, "gold_control_id", "question_id"),
    ]
    for dataset, frame, rewrites, gold_column, id_column in dataset_specs:
        rows: list[dict[str, Any]] = []
        for ordinal, (_, row) in enumerate(frame.iterrows(), start=1):
            print(f"[{revision}] {dataset}: {ordinal}/{len(frame)}", flush=True)
            rows.extend(evaluate_row(resources, row, rewrites, dataset, gold_column, id_column))
        result = pd.DataFrame(rows)
        result.to_csv(output_dir / f"{dataset}.csv", index=False, float_format="%.8f")

    metadata = {
        "revision": revision,
        "python": sys.version,
        "platform": platform.platform(),
        "packages": package_versions(),
        "canonical_retriever": {
            "path": "src/compliancegpt/retriever/retriever_s7.py",
            "sha256": sha256_file(repo_root / "src/compliancegpt/retriever/retriever_s7.py"),
        },
        "models": {
            "dense": {"id": DENSE_MODEL_ID, "revision": model_revision(DENSE_MODEL_ID)},
            "reranker": {"id": RERANKER_MODEL_ID, "revision": model_revision(RERANKER_MODEL_ID)},
        },
        "inputs": {
            str(path.relative_to(repo_root)): sha256_file(path)
            for path in (catalog, gold_path, error_path, gold_rewrites_path, error_rewrites_path)
        },
        "configuration": {
            "top_n": TOP_N,
            "candidate_set_size": CANDIDATE_SET_SIZE,
            "rrf_k": RRF_K,
            "rewrite_weight": REWRITE_WEIGHT,
            "rewrite_jaccard_min": REWRITE_JACCARD_MIN,
            "s4_max_rewrites": S4_MAX_REWRITES,
            "s7_max_rewrites": S7_MAX_REWRITES,
            "strip_meta_instructions_for_retrieval": True,
            "expand_scope_terms_for_retrieval": True,
            "scope_match_bias_ratio": SCOPE_MATCH_BIAS_RATIO,
            "scope_mismatch_penalty_ratio": SCOPE_MISMATCH_PENALTY_RATIO,
            "rerank_alpha": RERANK_ALPHA,
            "rerank_apply_min_margin_ratio": RERANK_APPLY_MIN_MARGIN_RATIO,
            "rerank_skip_min_base_margin_ratio": RERANK_SKIP_MIN_BASE_MARGIN_RATIO,
        },
    }
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def frozen_result_path(repo_root: Path, system: str, dataset: str) -> Path:
    revision = "rev5" if "rev5" in dataset else "rev4"
    error_fragment = "_error_bank" if dataset.startswith("error_bank") else ""
    if system == "S4":
        return repo_root / (
            "experiments/retriever_ablation/ablation_outputs/system_4_qur_rrf/"
            f"S4_qur_rrf{error_fragment}_{revision}_results.csv"
        )
    return repo_root / (
        "experiments/retriever_ablation/ablation_outputs/system_7_compliance_gpt/"
        f"S7_compliance_gpt{error_fragment}_{revision}_results.csv"
    )


def aggregate(repo_root: Path, parts_root: Path, output_dir: Path) -> None:
    part_paths = sorted(parts_root.glob("rev[45]/*.csv"))
    if len(part_paths) != 4:
        raise FileNotFoundError(f"Expected four revision/dataset part files; found {part_paths}")
    combined = pd.concat([pd.read_csv(path) for path in part_paths], ignore_index=True)
    expected_datasets = {"rev5_gold": 100, "rev4_gold": 36, "error_bank_rev5": 24, "error_bank_rev4": 13}
    for system in ("S4", "S4b", "S7", "S7a"):
        system_rows = combined.loc[combined["system"].eq(system)].copy()
        counts = system_rows.groupby("dataset").size().to_dict()
        if counts != expected_datasets:
            raise AssertionError(f"Unexpected {system} dataset counts: {counts}")
        if system_rows.duplicated(["dataset", "question_id"]).any():
            raise AssertionError(f"Duplicate {system} dataset/question rows")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_names = {
        "S4": "S4_matched_ALL.csv",
        "S4b": "S4b_rrf_best_ALL.csv",
        "S7": "S7_matched_ALL.csv",
        "S7a": "S7a_rerank_best_ALL.csv",
    }
    for system, name in output_names.items():
        combined.loc[combined["system"].eq(system)].to_csv(
            output_dir / name,
            index=False,
            float_format="%.8f",
        )

    summary = (
        combined.groupby(["dataset", "system"], sort=False)
        .agg(
            N=("question_id", "size"),
            Recall_at_1=("is_hit_at_1", "mean"),
            Recall_at_5=("is_hit_at_5", "mean"),
            Recall_at_10=("is_hit_at_10", "mean"),
            MRR_at_10=("mrr@10", "mean"),
            nDCG_at_10=("ndcg@10", "mean"),
        )
        .reset_index()
    )
    summary.to_csv(output_dir / "micro_ablation_summary.csv", index=False, float_format="%.6f")

    validation_rows = []
    for system in ("S4", "S7"):
        for dataset in expected_datasets:
            rerun = combined.loc[
                combined["system"].eq(system) & combined["dataset"].eq(dataset),
                ["question_id", "rank", "top_1_hit"],
            ].copy()
            frozen = pd.read_csv(frozen_result_path(repo_root, system, dataset))[
                ["question_id", "rank", "top_1_hit"]
            ].copy()
            rerun["question_id"] = pd.to_numeric(rerun["question_id"], errors="raise").astype(int)
            frozen["question_id"] = pd.to_numeric(frozen["question_id"], errors="raise").astype(int)
            check = rerun.merge(frozen, on="question_id", suffixes=("_rerun", "_frozen"), validate="one_to_one")
            if len(check) != expected_datasets[dataset]:
                raise AssertionError(f"Incomplete frozen comparison for {system} {dataset}")
            validation_rows.append(
                {
                    "system": system,
                    "dataset": dataset,
                    "N": len(check),
                    "rank_exact_match_rate": float(check["rank_rerun"].eq(check["rank_frozen"]).mean()),
                    "top1_exact_match_rate": float(
                        check["top_1_hit_rerun"].fillna("").eq(check["top_1_hit_frozen"].fillna("")).mean()
                    ),
                    "rerun_MRR@10": float(check["rank_rerun"].map(lambda rank: 1.0 / rank if rank else 0.0).mean()),
                    "frozen_MRR@10": float(check["rank_frozen"].map(lambda rank: 1.0 / rank if rank else 0.0).mean()),
                }
            )
    validation = pd.DataFrame(validation_rows)
    validation.to_csv(output_dir / "baseline_validation.csv", index=False, float_format="%.6f")

    metadata_paths = sorted(parts_root.glob("rev[45]/run_metadata.json"))
    metadata = {
        "study": "matched gold-informed rewrite diagnostic",
        "warning": "S4b and S7a use gold labels for rewrite selection and are not deployable systems.",
        "runs": [json.loads(path.read_text(encoding="utf-8")) for path in metadata_paths],
        "output_sha256": {
            name: sha256_file(output_dir / name)
            for name in [*output_names.values(), "micro_ablation_summary.csv", "baseline_validation.csv"]
        },
    }
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(summary.to_string(index=False))
    print("\nFrozen baseline validation:\n" + validation.to_string(index=False))


def main() -> None:
    default_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument("--revision", choices=("rev4", "rev5"))
    parser.add_argument("--parts-root", type=Path, required=True)
    parser.add_argument("--aggregate-only", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    if args.aggregate_only:
        output_dir = args.output_dir or (repo_root / "experiments/micro_ablations")
        aggregate(repo_root, args.parts_root.resolve(), output_dir.resolve())
    else:
        if not args.revision:
            parser.error("--revision is required unless --aggregate-only is set")
        run_revision(repo_root, args.revision, args.parts_root.resolve())


if __name__ == "__main__":
    main()
