#!/usr/bin/env python3
"""Run the matched S4/S4b and S7/S7a diagnostic retrieval study.

S4b and S7a use the gold control to select one of the existing query rewrites.
They are diagnostic variants, not deployable retrieval systems.  This runner
uses the same model IDs, corpus construction, rewrite filtering, RRF weights,
rerank blend, and gates as the frozen S1--S7 ablation notebook.  It also reruns
S4 and S7 in the same process so every reported contrast is matched.
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
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd


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


def control_id_aliases(control_id: str) -> str:
    canonical = normalize_control_id(control_id)
    aliases = {canonical, canonical.replace("-", ""), canonical.replace("-", " ")}
    match = CONTROL_ID_PAREN_RE.match(canonical)
    if match:
        dot = f"{match.group(1)}.{match.group(2)}"
        aliases.update({dot, dot.replace("-", ""), dot.replace("-", " ")})
    return " ".join(sorted(aliases))


def strict_key(text: object) -> str:
    return "".join(character.lower() for character in str(text) if character.isalnum())


def jaccard_overlap(left: str, right: str) -> float:
    left_tokens = set(tokenize(normalize_text(left)))
    right_tokens = set(tokenize(normalize_text(right)))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / float(len(left_tokens | right_tokens))


def load_clause_records(path: Path) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            source = json.loads(line)
            kind = str(source.get("kind", "")).lower()
            text = str(source.get("text", "")).strip()
            if kind not in {"smt", "gdn"} or not text:
                continue
            records.append(
                {
                    "clause_id": str(source.get("id", "")).strip(),
                    "control_id": normalize_control_id(source.get("control_id") or source.get("control") or ""),
                    "title": str(source.get("title", "")).strip(),
                    "text": text,
                    "kind": kind,
                }
            )
    if not records:
        raise ValueError(f"No statement or guidance clauses found in {path}")
    return records


def build_control_docs(records: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    texts: dict[str, list[str]] = defaultdict(list)
    titles: dict[str, str] = {}
    for record in records:
        control = record["control_id"]
        if not control:
            continue
        texts[control].append(record["text"])
        if record["title"]:
            titles[control] = record["title"]
    documents = []
    for control, parts in texts.items():
        header = [control_id_aliases(control)]
        if titles.get(control):
            header.append(titles[control])
        documents.append({"control_id": control, "text": "\n".join(header + parts)})
    return documents


def build_fallback_texts(records: Iterable[dict[str, str]]) -> dict[str, str]:
    by_control: dict[str, list[str]] = defaultdict(list)
    for record in records:
        if record["control_id"]:
            by_control[record["control_id"]].append(record["text"])
    return {control: "\n".join(parts[:8]) for control, parts in by_control.items()}


class BM25Okapi:
    def __init__(self, corpus_tokens: list[list[str]], k1: float = BM25_K1, b: float = BM25_B):
        self.k1 = float(k1)
        self.b = float(b)
        self.size = len(corpus_tokens)
        self.doc_len = np.array([len(document) for document in corpus_tokens], dtype=np.float32)
        self.avgdl = float(self.doc_len.mean()) if self.size else 0.0
        self.term_frequencies: list[dict[str, int]] = []
        document_frequencies: dict[str, int] = {}
        for document in corpus_tokens:
            frequencies: dict[str, int] = {}
            for term in document:
                frequencies[term] = frequencies.get(term, 0) + 1
            self.term_frequencies.append(frequencies)
            for term in frequencies:
                document_frequencies[term] = document_frequencies.get(term, 0) + 1
        self.idf = {
            term: math.log((self.size - frequency + 0.5) / (frequency + 0.5) + 1)
            for term, frequency in document_frequencies.items()
        }

    def get_scores(self, query_tokens: list[str]) -> np.ndarray:
        scores = np.zeros(self.size, dtype=np.float32)
        for term in query_tokens:
            if term not in self.idf:
                continue
            for index, frequencies in enumerate(self.term_frequencies):
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                numerator = frequency * (self.k1 + 1.0)
                denominator = frequency + self.k1 * (
                    1.0 - self.b + self.b * (self.doc_len[index] / max(self.avgdl, 1e-9))
                )
                scores[index] += float(self.idf[term]) * float(numerator / denominator)
        return scores

    def get_top_n(self, query_tokens: list[str], n: int) -> list[int]:
        scores = self.get_scores(query_tokens)
        if n >= len(scores):
            return np.argsort(-scores).tolist()
        indices = np.argpartition(-scores, n - 1)[:n]
        return indices[np.argsort(-scores[indices])].tolist()


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
        clause_text: dict[str, str],
    ):
        self.index = dense_index
        self.clause_to_control = clause_to_control
        self.clause_text = clause_text
        self.cache: dict[tuple[str, int], tuple[list[tuple[str, float]], dict[str, str]]] = {}

    def search(self, query: str, top_k: int = CANDIDATE_SET_SIZE) -> list[tuple[str, float]]:
        key = (query, int(top_k))
        if key not in self.cache:
            best_scores: dict[str, float] = {}
            best_clauses: dict[str, str] = {}
            for clause_id, score in self.index.search(query, top_k=int(top_k) * 5):
                control = normalize_control_id(self.clause_to_control.get(clause_id, ""))
                if control and score > best_scores.get(control, -1.0):
                    best_scores[control] = score
                    best_clauses[control] = clause_id
            ranked = sorted(best_scores.items(), key=lambda item: item[1], reverse=True)[: int(top_k)]
            self.cache[key] = (ranked, best_clauses)
        return list(self.cache[key][0])

    def best_clause_text(self, query: str, control_id: str, top_k: int = CANDIDATE_SET_SIZE) -> str:
        key = (query, int(top_k))
        if key not in self.cache:
            self.search(query, top_k=top_k)
        clause_id = self.cache[key][1].get(normalize_control_id(control_id), "")
        return self.clause_text.get(clause_id, "")


@dataclass
class RetrievalResources:
    bm25: BM25Okapi
    control_ids: list[str]
    dense: ClauseDenseControlAdapter
    reranker: Any
    fallback_text: dict[str, str]


def build_resources(catalog_path: Path) -> RetrievalResources:
    from sentence_transformers import CrossEncoder
    import torch

    records = load_clause_records(catalog_path)
    documents = build_control_docs(records)
    bm25 = BM25Okapi([tokenize(normalize_text(document["text"])) for document in documents])
    control_ids = [document["control_id"] for document in documents]

    clause_ids: list[str] = []
    dense_texts: list[str] = []
    clause_to_control: dict[str, str] = {}
    clause_text: dict[str, str] = {}
    for record in records:
        packed = f"{record['control_id']} {record['title']} ({record['kind']})\n{record['text']}"
        clause_ids.append(record["clause_id"])
        dense_texts.append(f"passage: {packed}")
        clause_to_control[record["clause_id"]] = record["control_id"]
        clause_text[record["clause_id"]] = packed

    dense_index = DenseIndex(DENSE_MODEL_ID)
    dense_index.build(dense_texts, clause_ids)
    dense = ClauseDenseControlAdapter(dense_index, clause_to_control, clause_text)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    reranker = CrossEncoder(RERANKER_MODEL_ID, device=device)
    return RetrievalResources(bm25, control_ids, dense, reranker, build_fallback_texts(records))


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


def prepare_hybrid(resources: RetrievalResources, variants: list[str]) -> dict[str, Any]:
    weights = [1.0] + [REWRITE_WEIGHT] * (len(variants) - 1)
    scores: dict[str, float] = defaultdict(float)
    best_text: dict[str, str] = {}
    bm25_top1 = ""
    dense_top1 = ""
    for variant_index, (variant, weight) in enumerate(zip(variants, weights)):
        indices = resources.bm25.get_top_n(tokenize(normalize_text(variant)), n=CANDIDATE_SET_SIZE)
        if variant_index == 0 and indices:
            bm25_top1 = normalize_control_id(resources.control_ids[indices[0]])
        for rank, index in enumerate(indices, start=1):
            control = normalize_control_id(resources.control_ids[index])
            scores[control] += float(weight) / float(RRF_K + rank)
            best_text.setdefault(control, resources.fallback_text.get(control, ""))

        dense_hits = resources.dense.search(variant, top_k=CANDIDATE_SET_SIZE)
        if variant_index == 0 and dense_hits:
            dense_top1 = normalize_control_id(dense_hits[0][0])
        for rank, (control_id, _) in enumerate(dense_hits, start=1):
            control = normalize_control_id(control_id)
            scores[control] += float(weight) / float(RRF_K + rank)
            clause_text = resources.dense.best_clause_text(variant, control)
            if clause_text:
                best_text[control] = clause_text

    fused = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:CANDIDATE_SET_SIZE]
    return {
        "controls": [control for control, _ in fused],
        "scores": dict(scores),
        "best_text": best_text,
        "bm25_top1": bm25_top1,
        "dense_top1": dense_top1,
        "num_variants": len(variants),
    }


def normalize_scores(values: np.ndarray) -> np.ndarray:
    if values.size == 0:
        return values
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    if maximum - minimum < 1e-12:
        return np.zeros_like(values, dtype=np.float32)
    return ((values - minimum) / (maximum - minimum)).astype(np.float32)


def rerank_prepared(
    resources: RetrievalResources,
    prepared: dict[str, Any],
    rerank_query: str,
) -> tuple[list[str], dict[str, Any]]:
    candidates = list(prepared["controls"])
    if not candidates:
        return [], {"reranker_called": False, "rerank_applied": False, "skip_reason": "no_candidates"}

    valid_controls: list[str] = []
    pairs: list[list[str]] = []
    for control in candidates:
        text = prepared["best_text"].get(control) or resources.fallback_text.get(control, "")
        if text:
            pairs.append([rerank_query, text])
            valid_controls.append(control)
    base_controls = valid_controls if valid_controls else candidates
    scores = prepared["scores"]
    base_values = np.asarray([scores.get(control, 0.0) for control in base_controls], dtype=np.float32)
    base_normalized = normalize_scores(base_values)
    if len(base_controls) >= 2:
        first = float(scores.get(base_controls[0], 0.0))
        second = float(scores.get(base_controls[1], 0.0))
        base_margin = (first - second) / max(first, 1e-9)
    else:
        base_margin = 1.0
    base_top1 = base_controls[0] if base_controls else ""

    common_meta = {
        "num_variants": int(prepared["num_variants"]),
        "bm25_top1": prepared["bm25_top1"],
        "dense_top1": prepared["dense_top1"],
        "base_top1": base_top1,
        "base_margin_ratio": float(base_margin),
        "rerank_alpha": RERANK_ALPHA,
        "rerank_apply_min_margin_ratio": RERANK_APPLY_MIN_MARGIN_RATIO,
        "rerank_skip_min_base_margin_ratio": RERANK_SKIP_MIN_BASE_MARGIN_RATIO,
    }
    if base_margin >= RERANK_SKIP_MIN_BASE_MARGIN_RATIO:
        return base_controls, {
            **common_meta,
            "reranker_called": False,
            "rerank_applied": False,
            "skip_reason": "base_confident",
            "final_top1": base_top1,
        }
    if not pairs:
        return candidates, {
            **common_meta,
            "reranker_called": False,
            "rerank_applied": False,
            "skip_reason": "no_text_for_rerank",
            "final_top1": candidates[0],
        }

    predictions = resources.reranker.predict(
        pairs,
        batch_size=32,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    rerank_normalized = normalize_scores(np.asarray(predictions, dtype=np.float32))
    final_scores = RERANK_ALPHA * base_normalized[: len(rerank_normalized)] + (
        1.0 - RERANK_ALPHA
    ) * rerank_normalized
    order = np.argsort(-final_scores)
    reranked = [valid_controls[int(index)] for index in order]
    if len(order) >= 2:
        first = float(final_scores[int(order[0])])
        second = float(final_scores[int(order[1])])
        rerank_margin = (first - second) / max(first, 1e-9)
    else:
        rerank_margin = 1.0
    rerank_top1 = reranked[0] if reranked else ""
    applied = not (rerank_top1 != base_top1 and rerank_margin < RERANK_APPLY_MIN_MARGIN_RATIO)
    final = reranked if applied else base_controls
    return final, {
        **common_meta,
        "reranker_called": True,
        "rerank_applied": bool(applied),
        "skip_reason": None,
        "rerank_top1": rerank_top1,
        "rerank_margin_ratio": float(rerank_margin),
        "final_top1": final[0] if final else "",
    }


def select_gold_informed_rewrite(
    resources: RetrievalResources,
    query: str,
    gold_control: str,
    rewrites: list[str],
) -> Optional[str]:
    best_rewrite: Optional[str] = None
    best_rank: Optional[int] = None
    for rewrite in rewrites[:S7_MAX_REWRITES]:
        prepared = prepare_hybrid(resources, [query, rewrite])
        candidate_rank = rank_of(gold_control, prepared["controls"], CANDIDATE_SET_SIZE)
        if candidate_rank and (best_rank is None or candidate_rank < best_rank):
            best_rank = candidate_rank
            best_rewrite = rewrite
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
    rewrites_s7 = rewrites_s4[:S7_MAX_REWRITES]
    selected = select_gold_informed_rewrite(resources, query, gold, rewrites_s7)

    s4_ranked = bm25_rrf(resources, [query] + rewrites_s4)
    s4b_ranked = bm25_rrf(resources, [query] + ([selected] if selected else []))
    prepared = prepare_hybrid(resources, [query] + rewrites_s7)
    s7_ranked, s7_meta = rerank_prepared(resources, prepared, query)
    s7a_ranked, s7a_meta = rerank_prepared(resources, prepared, selected or query)

    systems = [
        ("S4", s4_ranked, {"sys": "S4", "n_vars": 1 + len(rewrites_s4)}),
        (
            "S4b",
            s4b_ranked,
            {"sys": "S4b", "n_vars": 2 if selected else 1, "gold_informed_rewrite_used": bool(selected)},
        ),
        ("S7", s7_ranked, {**s7_meta, "sys": "S7"}),
        (
            "S7a",
            s7a_ranked,
            {**s7a_meta, "sys": "S7a", "gold_informed_rewrite_used": bool(selected)},
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
                "selected_rewrite": selected or "",
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
