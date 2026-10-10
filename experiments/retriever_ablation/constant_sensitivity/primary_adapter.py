"""Use the historical primary notebook definitions without changing their logic."""
from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import re
import typing
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

NOTEBOOK = "experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb"
DEFINITIONS = {
    5: ("PUNCT_RE", "WS_RE", "TOKEN_RE", "_CONTROL_ID_DOT_RE", "_CONTROL_ID_PAREN_RE",
        "normalize_text", "tokenize", "normalize_control_id", "control_id_aliases",
        "load_clause_records_jsonl", "build_control_docs_from_clauses", "build_control_fallback_text_map"),
    6: ("BM25Okapi", "build_bm25"),
    7: ("DenseIndex", "ClauseDenseControlAdapter", "build_dense_retriever"),
    9: ("find_rank", "strict_clean", "jaccard_overlap", "normalize_scores_minmax",
        "get_qur_variants_filtered", "s7_heavy_retrieve_details"),
}
BASELINE = {"candidate_set_size": 50, "rrf_k": 60, "max_rewrites": 3,
            "rewrite_weight": 0.25, "rewrite_jaccard_min": 0.15,
            "rerank_alpha": 0.65, "rerank_apply_min_margin_ratio": 0.15,
            "rerank_skip_enabled": True, "rerank_skip_min_base_margin_ratio": 0.10,
            "rerank_skip_require_top1_agreement": False}
CONDITIONS = {"baseline": {}, "alpha_minus20": {"rerank_alpha": 0.52},
              "alpha_plus20": {"rerank_alpha": 0.78},
              "adoption_minus20": {"rerank_apply_min_margin_ratio": 0.12},
              "adoption_plus20": {"rerank_apply_min_margin_ratio": 0.18},
              "skip_minus20": {"rerank_skip_min_base_margin_ratio": 0.08},
              "skip_plus20": {"rerank_skip_min_base_margin_ratio": 0.12}}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def definitions(repo):
    notebook = json.loads((repo / NOTEBOOK).read_text())
    sources = {}
    for cell_index, names in DEFINITIONS.items():
        source = "".join(notebook["cells"][cell_index]["source"])
        # Only an installation magic outside the selected definitions is removed.
        source = "\n".join((" " * (len(line) - len(line.lstrip())) + "pass")
                            if line.lstrip().startswith("!") else line
                            for line in source.splitlines())
        nodes = {}
        for node in ast.parse(source).body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                nodes[node.name] = node
            elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                nodes[node.targets[0].id] = node
        for name in names:
            if name not in nodes:
                raise AssertionError(f"Missing primary notebook definition: {name}")
            sources[name] = ast.get_source_segment(source, nodes[name])
    return sources


def load_primary(repo):
    namespace = {"__name__": "primary_rq1_notebook", "np": np, "pd": pd,
                 "math": math, "json": json, "re": re, "defaultdict": defaultdict,
                 "BM25_K1": 1.5, "BM25_B": 0.75, "DENSE_MODEL_ID": "intfloat/e5-small-v2"}
    namespace.update({name: getattr(typing, name) for name in ("Any", "Dict", "List", "Tuple", "Optional", "Iterable")})
    for name, source in definitions(repo).items():
        exec(compile(source, f"{NOTEBOOK}:{name}", "exec"), namespace)
    return namespace


def config(condition):
    return dict(BASELINE, **CONDITIONS[condition])


def rewrites_frame(rewrites, question):
    return pd.DataFrame({"original_query": [question] * len(rewrites), "rewritten_query": rewrites})


class CaptureBM25:
    def __init__(self, base):
        self.base, self.calls = base, []

    def get_top_n(self, tokens, n=10):
        indices = self.base.get_top_n(tokens, n=n)
        self.calls.append({"tokens": list(tokens), "n": n, "indices": indices,
                           "scores": self.base.get_scores(tokens).astype(np.float32).tolist()})
        return indices


class CaptureDense:
    def __init__(self, base):
        self.base, self.calls = base, []

    def search(self, query, top_k=50):
        hits = self.base.search(query, top_k=top_k)
        texts = {cid: self.base.best_clause_text_for_control(cid) for cid, _ in hits}
        self.calls.append({"query": query, "top_k": top_k, "hits": hits,
                           "best_clause_ids": copy.deepcopy(self.base.last_best_clause), "texts": texts})
        return hits

    def best_clause_text_for_control(self, cid):
        return self.base.best_clause_text_for_control(cid)


class CaptureCrossEncoder:
    def __init__(self, base):
        self.base, self.calls = base, []

    def predict(self, pairs, show_progress_bar=False):
        scores = np.asarray(self.base.predict(pairs, show_progress_bar=show_progress_bar), dtype=np.float32)
        if scores.ndim != 1 or len(scores) != len(pairs) or not np.isfinite(scores).all():
            raise AssertionError("Cross-encoder must supply one finite score per pair")
        self.calls.append({"pairs": copy.deepcopy(pairs), "pairs_sha256": digest(pairs), "scores": scores.tolist()})
        return scores


class ReplayBM25:
    def __init__(self, calls):
        self.calls, self.cursor = calls, 0

    def get_top_n(self, tokens, n=10):
        if self.cursor >= len(self.calls):
            raise AssertionError("Unregistered lexical call")
        row = self.calls[self.cursor]
        if list(tokens) != row["tokens"] or n != row["n"]:
            raise AssertionError("Lexical call differs from captured input")
        self.cursor += 1
        return list(row["indices"])


class ReplayDense:
    def __init__(self, calls):
        self.calls, self.cursor, self.errors = calls, 0, []

    def search(self, query, top_k=50):
        if self.cursor >= len(self.calls):
            self.errors.append("Unregistered dense call")
            raise AssertionError(self.errors[-1])
        row = self.calls[self.cursor]
        if query != row["query"] or top_k != row["top_k"]:
            self.errors.append("Dense call differs from captured input")
            raise AssertionError(self.errors[-1])
        self.cursor += 1
        return copy.deepcopy(row["hits"])

    def best_clause_text_for_control(self, cid):
        if not self.cursor:
            raise AssertionError("Dense text requested before search")
        return self.calls[self.cursor - 1]["texts"].get(cid)


class ReplayCrossEncoder:
    def __init__(self, calls):
        self.calls, self.cursor = calls, 0

    def predict(self, pairs, show_progress_bar=False):
        if self.cursor >= len(self.calls):
            raise AssertionError("Unregistered cross-encoder call")
        row = self.calls[self.cursor]
        if pairs != row["pairs"] or digest(pairs) != row["pairs_sha256"]:
            raise AssertionError("Cross-encoder pairs differ from captured input")
        self.cursor += 1
        return np.asarray(row["scores"], dtype=np.float32)


def invoke(namespace, question, rewrites, lexical, dense, cross_encoder, control_ids, fallback_texts, settings):
    return namespace["s7_heavy_retrieve_details"](
        question, lexical, dense, control_ids, cross_encoder, fallback_texts,
        rewrites_frame(rewrites, question), **settings)


def capture(namespace, case, bm25, dense, cross_encoder, control_ids, fallback_texts):
    lexical, dense_proxy, cross = CaptureBM25(bm25), CaptureDense(dense), CaptureCrossEncoder(cross_encoder)
    settings = dict(BASELINE, rerank_skip_enabled=False, rerank_apply_min_margin_ratio=0.0)
    result = invoke(namespace, case["question"], case["rewrites"], lexical, dense_proxy, cross,
                    control_ids, fallback_texts, settings)
    if len(cross.calls) != 1 or len(lexical.calls) != len(case["accepted_variants"]) or len(dense_proxy.calls) != len(lexical.calls):
        raise AssertionError("Incomplete primary channel capture")
    if [row["query"] for row in dense_proxy.calls] != case["accepted_variants"]:
        raise AssertionError("Primary rewrite filtering differs from registration")
    trace = {"schema": "primary-rq1-channel-cache-v1", "revision": case["revision"],
             "query_id": case["query_id"], "question": case["question"], "rewrites": case["rewrites"],
             "accepted_variants": case["accepted_variants"], "lexical_calls": lexical.calls,
             "dense_calls": dense_proxy.calls, "cross_encoder_calls": cross.calls,
             "ungated_probe": result}
    replayed = replay(namespace, trace, control_ids, fallback_texts, settings)
    if replayed != result:
        raise AssertionError("Captured primary result cannot be reproduced exactly")
    return trace


def replay(namespace, trace, control_ids, fallback_texts, settings):
    if trace.get("schema") != "primary-rq1-channel-cache-v1":
        raise AssertionError("Unsupported channel-cache schema")
    lexical, dense, cross = ReplayBM25(trace["lexical_calls"]), ReplayDense(trace["dense_calls"]), ReplayCrossEncoder(trace["cross_encoder_calls"])
    result = invoke(namespace, trace["question"], trace["rewrites"], lexical, dense, cross,
                    control_ids, fallback_texts, settings)
    if lexical.cursor != len(lexical.calls) or dense.cursor != len(dense.calls) or dense.errors:
        raise AssertionError("Incomplete or altered channel replay")
    expected_cross_calls = int(bool(result["meta"].get("reranker_called")))
    if cross.cursor != expected_cross_calls:
        raise AssertionError("Cross-encoder replay does not match the logical gate")
    return result
