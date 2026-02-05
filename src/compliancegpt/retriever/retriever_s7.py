"""
retriever_s7.py — S7 retriever component for ComplianceGPT pipeline

Pipeline-compatible API:
    from retriever_s7 import ComplianceGPTRetriever, RetrievalConfig
    r = ComplianceGPTRetriever(catalog_path=..., config=RetrievalConfig())
    docs = r.retrieve(query, top_k=..., rewrites=rewrites)

This module:
- Keeps the S7 ranking idea (weighted RRF fusion + safe rerank blending + no-harm gate)
- Adds only the integration glue required by pipeline.py:
  * exposes ComplianceGPTRetriever + RetrievalConfig
  * supports `rewrites=` kwarg
  * sets `self.ids` to CCS clause ids so pipeline CCS sanity check passes
  * returns clause-level doc dicts (id/control_id/kind/text/title)

Dependencies:
- sentence-transformers
- faiss-cpu (or faiss-gpu)
- torch
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


# ==========================================================
# 1) Text utils / normalization
# ==========================================================
_PUNCT_RE = re.compile(r"[^0-9A-Za-z_\s]+")
_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    s = text.lower().replace("-", " ")
    s = _PUNCT_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(str(text))]


def normalize_control_id(control_id: str) -> str:
    if not isinstance(control_id, str):
        return ""
    return control_id.strip().upper().replace("_", "-")


def control_id_aliases(control_id: str) -> str:
    cid = normalize_control_id(control_id)
    return f"{cid} {cid.replace('-', '')} {cid.replace('-', ' ')}"


def strict_clean(s: str) -> str:
    return "".join(c.lower() for c in str(s) if c.isalnum())


def jaccard_overlap(a: str, b: str) -> float:
    A = set(tokenize(normalize_text(a)))
    B = set(tokenize(normalize_text(b)))
    if not A or not B:
        return 0.0
    return len(A & B) / float(len(A | B))


def normalize_scores_minmax(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    mn, mx = float(np.min(x)), float(np.max(x))
    if mx - mn < 1e-12:
        return np.zeros_like(x, dtype=np.float32)
    return ((x - mn) / (mx - mn)).astype(np.float32)


# ==========================================================
# 2) CCS JSONL loader (clause-level)
# ==========================================================
def load_clause_records_jsonl(
    jsonl_path: str,
    keep_kinds: Iterable[str] = ("smt", "gdn"),
) -> List[Dict[str, Any]]:
    keep = set(k.lower() for k in keep_kinds) if keep_kinds else set()
    out: List[Dict[str, Any]] = []

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)

            kind = str(rec.get("kind", "other")).lower()
            if keep and kind not in keep:
                continue

            txt = str(rec.get("text", "")).strip()
            if not txt:
                continue

            clause_id = str(rec.get("id", "")).strip()
            if not clause_id:
                continue

            out.append(
                {
                    "id": clause_id,
                    "control_id": normalize_control_id(rec.get("control_id") or rec.get("control") or ""),
                    "title": str(rec.get("title", "")).strip(),
                    "text": txt,
                    "kind": kind,
                }
            )
    return out


def build_control_docs_from_clauses(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    by_ctl: Dict[str, List[str]] = defaultdict(list)
    titles: Dict[str, str] = {}
    for r in records:
        cid = r.get("control_id", "")
        if not cid:
            continue
        by_ctl[cid].append(r.get("text", ""))
        if r.get("title"):
            titles[cid] = r["title"]

    docs: List[Dict[str, str]] = []
    for cid, parts in by_ctl.items():
        header = [control_id_aliases(cid)]
        if titles.get(cid):
            header.append(titles[cid])
        docs.append({"control_id": cid, "text": "\n".join(header + parts)})
    return docs


def build_control_fallback_text_map(records: List[Dict[str, Any]]) -> Dict[str, str]:
    by_ctl: Dict[str, List[str]] = defaultdict(list)
    for r in records:
        cid = r.get("control_id", "")
        if cid:
            by_ctl[cid].append(r.get("text", ""))
    return {normalize_control_id(k).upper(): "\n".join(v[:8]) for k, v in by_ctl.items()}


# ==========================================================
# 3) BM25
# ==========================================================
class BM25Okapi:
    def __init__(self, corpus_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = float(k1)
        self.b = float(b)
        self.N = len(corpus_tokens)
        self.doc_len = np.array([len(d) for d in corpus_tokens], dtype=np.float32)
        self.avgdl = float(self.doc_len.mean()) if self.N else 0.0

        self.tf: List[Dict[str, int]] = []
        df: Dict[str, int] = {}
        for doc in corpus_tokens:
            tf_doc: Dict[str, int] = {}
            for t in doc:
                tf_doc[t] = tf_doc.get(t, 0) + 1
            self.tf.append(tf_doc)
            for t in tf_doc:
                df[t] = df.get(t, 0) + 1

        self.idf = {t: math.log((self.N - freq + 0.5) / (freq + 0.5) + 1) for t, freq in df.items()}

    def get_scores(self, query_tokens: List[str]) -> np.ndarray:
        scores = np.zeros(self.N, dtype=np.float32)
        for t in query_tokens:
            if t not in self.idf:
                continue
            idf = self.idf[t]
            for i, tf_doc in enumerate(self.tf):
                f = tf_doc.get(t, 0)
                if not f:
                    continue
                num = f * (self.k1 + 1.0)
                den = f + self.k1 * (1.0 - self.b + self.b * (self.doc_len[i] / max(self.avgdl, 1e-9)))
                scores[i] += float(idf) * float(num / den)
        return scores

    def get_top_n(self, query_tokens: List[str], n: int = 10) -> List[int]:
        scores = self.get_scores(query_tokens)
        if n >= len(scores):
            return np.argsort(-scores).tolist()
        idx = np.argpartition(-scores, n - 1)[:n]
        return idx[np.argsort(-scores[idx])].tolist()


def build_bm25(docs: List[Dict[str, str]], k1: float, b: float) -> Tuple[BM25Okapi, List[str]]:
    ids = [d["control_id"] for d in docs]
    toks = [tokenize(normalize_text(d["text"])) for d in docs]
    return BM25Okapi(toks, k1=k1, b=b), ids


# ==========================================================
# 4) Dense index + clause→control adapter
# ==========================================================
class DenseIndex:
    """Exposed for debugging/introspection."""
    def __init__(self, model_id: str):
        try:
            import torch  # noqa: F401
            from sentence_transformers import SentenceTransformer  # noqa: F401
            import faiss  # noqa: F401
        except Exception as e:
            raise ImportError(
                "DenseIndex requires sentence-transformers + faiss. "
                "Install: pip install sentence-transformers faiss-cpu"
            ) from e

        import torch
        from sentence_transformers import SentenceTransformer

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id = model_id
        self.model = SentenceTransformer(model_id, device=self.device)
        self.index = None
        self.ids: List[str] = []

    def build(self, texts: List[str], ids: List[str]) -> None:
        import faiss

        self.ids = list(ids)
        emb = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        self.index = faiss.IndexFlatIP(emb.shape[1])
        self.index.add(emb)

    def search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        if self.index is None:
            return []
        q_emb = self.model.encode([query], normalize_embeddings=True)
        scores, idxs = self.index.search(q_emb, top_k)
        out: List[Tuple[str, float]] = []
        for i, s in zip(idxs[0], scores[0]):
            if i == -1:
                continue
            out.append((self.ids[int(i)], float(s)))
        return out


class ClauseDenseControlAdapter:
    """Clause search → compress to control by max clause score."""
    def __init__(self, dense_idx: DenseIndex, clause_to_control: Dict[str, str]):
        self.idx = dense_idx
        self.cmap = clause_to_control

    def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        hits = self.idx.search(query, top_k=top_k * 5)
        best_score: Dict[str, float] = {}
        for clause_id, score in hits:
            ctl = self.cmap.get(clause_id)
            if not ctl:
                continue
            ctl = normalize_control_id(ctl)
            if score > best_score.get(ctl, -1.0):
                best_score[ctl] = float(score)
        ranked = sorted(best_score.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


def build_dense_retriever(
    records: List[Dict[str, Any]],
    dense_model_id: str,
) -> Tuple[ClauseDenseControlAdapter, Dict[str, str], Dict[str, str]]:
    clause_ids: List[str] = []
    texts: List[str] = []
    clause_to_control: Dict[str, str] = {}
    clause_id_to_text: Dict[str, str] = {}

    for r in records:
        cid = r["control_id"]
        title = r.get("title", "")
        kind = r.get("kind", "other")
        header = f"{cid} {title} ({kind})".strip()
        packed = f"{header}\n{r['text']}".strip()

        clause_id = r["id"]
        clause_ids.append(clause_id)
        texts.append(f"passage: {packed}")  # e5
        clause_to_control[clause_id] = cid
        clause_id_to_text[clause_id] = packed

    idx = DenseIndex(dense_model_id)
    idx.build(texts, clause_ids)
    return ClauseDenseControlAdapter(idx, clause_to_control), clause_id_to_text, clause_to_control


def build_reranker(model_id: str):
    try:
        import torch  # noqa: F401
        from sentence_transformers import CrossEncoder  # noqa: F401
    except Exception as e:
        raise ImportError("Reranker requires sentence-transformers.") from e

    import torch
    from sentence_transformers import CrossEncoder

    device = "cuda" if torch.cuda.is_available() else "cpu"
    return CrossEncoder(model_id, device=device)


# ==========================================================
# 5) Rewrite handling (pipeline rewrites OR QUR df)
# ==========================================================
def _coerce_rewrite_list(rewrites: Any) -> List[str]:
    if not rewrites:
        return []
    out: List[str] = []
    if isinstance(rewrites, (list, tuple)):
        for r in rewrites:
            if isinstance(r, str):
                out.append(r)
            elif isinstance(r, dict):
                out.append(r.get("rewrite") or r.get("text") or "")
            else:
                out.append(str(r))
    else:
        out.append(str(rewrites))
    return [x.strip() for x in out if isinstance(x, str) and x.strip()]


def _variants_from_pipeline_rewrites(original_query: str, rewrites: List[str], max_rewrites: int, jaccard_min: float) -> List[str]:
    variants = [original_query]
    for r in rewrites:
        if len(r) < 6:
            continue
        if jaccard_overlap(original_query, r) < float(jaccard_min):
            continue
        variants.append(r)
        if len(variants) >= 1 + int(max_rewrites):
            break
    return list(dict.fromkeys(variants))


def _variants_from_qur_df(original_query: str, qur_df: Optional[pd.DataFrame], max_rewrites: int, jaccard_min: float) -> List[str]:
    variants = [original_query]
    if qur_df is None or qur_df.empty:
        return variants

    df = qur_df
    if "strict_key" not in df.columns and "original_query" in df.columns:
        df = df.copy()
        df["strict_key"] = df["original_query"].apply(strict_clean)

    q_key = strict_clean(original_query)
    matches = df[df["strict_key"] == q_key] if "strict_key" in df.columns else pd.DataFrame()

    if matches.empty or "rewritten_query" not in matches.columns:
        return variants

    rewrites: List[str] = []
    for r in matches["rewritten_query"].tolist():
        r = str(r).strip()
        if len(r) < 6:
            continue
        if jaccard_overlap(original_query, r) < float(jaccard_min):
            continue
        rewrites.append(r)

    variants.extend(rewrites[: int(max_rewrites)])
    return list(dict.fromkeys(variants))


# ==========================================================
# 6) S7 ranking core (controls)
# ==========================================================
def s7_rank_controls(
    original_query: str,
    variants: List[str],
    bm25_retriever: BM25Okapi,
    bm25_control_ids: List[str],
    dense_adapter: ClauseDenseControlAdapter,
    reranker,
    id_to_text_map: Dict[str, str],
    candidate_set_size: int,
    rrf_k: int,
    rewrite_weight: float,
    rerank_alpha: float,
    rerank_apply_min_margin_ratio: float,
) -> Tuple[List[str], Dict[str, Any]]:
    weights = [1.0] + [float(rewrite_weight)] * (len(variants) - 1)

    rrf_scores: Dict[str, float] = defaultdict(float)
    best_text_cache: Dict[str, str] = {}

    for q, w in zip(variants, weights):
        # BM25 (control-level)
        q_toks = tokenize(normalize_text(q))
        idxs = bm25_retriever.get_top_n(q_toks, n=int(candidate_set_size))
        for rank, i in enumerate(idxs, 1):
            cid = normalize_control_id(bm25_control_ids[int(i)]).upper()
            rrf_scores[cid] += float(w) * (1.0 / (float(rrf_k) + float(rank)))
            if cid not in best_text_cache:
                best_text_cache[cid] = id_to_text_map.get(cid, "")

        # Dense (control-level via adapter)
        hits = dense_adapter.search(q, top_k=int(candidate_set_size))
        for rank, (raw_cid, _) in enumerate(hits, 1):
            cid = normalize_control_id(str(raw_cid)).upper()
            rrf_scores[cid] += float(w) * (1.0 / (float(rrf_k) + float(rank)))

    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[: int(candidate_set_size)]
    cids = [c for c, _ in fused]
    if not cids:
        return [], {"note": "no_candidates", "rerank_applied": False, "num_variants": len(variants)}

    # Reranker pairs using fallback control text
    pairs: List[List[str]] = []
    valid_cids: List[str] = []
    for cid in cids:
        txt = best_text_cache.get(cid) or id_to_text_map.get(cid, "")
        if txt:
            pairs.append([original_query, txt])
            valid_cids.append(cid)

    base_ranked = valid_cids[:]
    if not pairs:
        return cids, {"note": "no_text_for_rerank", "rerank_applied": False, "num_variants": len(variants)}

    pred = reranker.predict(pairs, show_progress_bar=False)

    base = np.array([rrf_scores.get(c, 0.0) for c in valid_cids], dtype=np.float32)
    base_n = normalize_scores_minmax(base)
    pred_n = normalize_scores_minmax(np.array(pred, dtype=np.float32))

    ra = float(rerank_alpha)
    final_scores = ra * base_n + (1.0 - ra) * pred_n
    order = np.argsort(-final_scores)
    reranked = [valid_cids[int(i)] for i in order]

    if len(order) >= 2:
        fs1 = float(final_scores[int(order[0])])
        fs2 = float(final_scores[int(order[1])])
        rerank_margin_ratio = (fs1 - fs2) / max(fs1, 1e-9)
    else:
        rerank_margin_ratio = 1.0

    base_top1 = base_ranked[0] if base_ranked else ""
    rerank_top1 = reranked[0] if reranked else ""

    rerank_applied = True
    final_ranked = reranked
    if (rerank_top1 != base_top1) and (rerank_margin_ratio < float(rerank_apply_min_margin_ratio)):
        rerank_applied = False
        final_ranked = base_ranked

    meta = {
        "num_variants": len(variants),
        "rerank_applied": rerank_applied,
        "rerank_alpha": float(rerank_alpha),
        "rerank_apply_min_margin_ratio": float(rerank_apply_min_margin_ratio),
        "base_top1": base_top1,
        "rerank_top1": rerank_top1,
        "final_top1": final_ranked[0] if final_ranked else "",
        "rerank_margin_ratio": float(rerank_margin_ratio),
    }
    return final_ranked, meta


# ==========================================================
# 7) Config + retriever (pipeline-compatible)
# ==========================================================
@dataclass
class S7Config:
    keep_kinds: Tuple[str, ...] = ("smt", "gdn")

    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    dense_model_id: str = "intfloat/e5-small-v2"
    reranker_model_id: str = "BAAI/bge-reranker-base"

    candidate_set_size: int = 50
    rrf_k: int = 60

    max_rewrites: int = 3
    rewrite_weight: float = 0.25
    rewrite_jaccard_min: float = 0.15

    rerank_alpha: float = 0.65
    rerank_apply_min_margin_ratio: float = 0.15


RetrievalConfig = S7Config


class ComplianceGPTRetriever:
    """
    Pipeline-facing retriever.

    - __init__(catalog_path=..., config=RetrievalConfig())
    - retrieve(query, top_k=..., rewrites=rewrites) -> list[doc_dict]
    - ids: clause ids (for pipeline CCS sanity check)
    """
    def __init__(self, *, catalog_path: str, config: RetrievalConfig = RetrievalConfig(), qur_df: Optional[pd.DataFrame] = None, **kwargs):
        self.config = config
        self.qur_df = qur_df

        # Load CCS clause records
        self.records = load_clause_records_jsonl(catalog_path, keep_kinds=config.keep_kinds)
        self.record_by_id = {r["id"]: r for r in self.records}

        # Clause ids for CCS sanity check
        self.ids = [r["id"] for r in self.records]

        # Control->clauses map (fallback selection)
        self.control_to_clause_ids: Dict[str, List[str]] = defaultdict(list)
        for r in self.records:
            ctl = normalize_control_id(r.get("control_id", "")).upper()
            if ctl:
                self.control_to_clause_ids[ctl].append(r["id"])

        # Build BM25 on control-level aggregated docs
        ctl_docs = build_control_docs_from_clauses(self.records)
        self.bm25, self.bm25_control_ids = build_bm25(ctl_docs, k1=config.bm25_k1, b=config.bm25_b)

        # Dense clause index + adapter
        self.dense_adapter, self.clause_id_to_text, self.clause_to_control = build_dense_retriever(self.records, dense_model_id=config.dense_model_id)

        # Reranker
        self.reranker = build_reranker(config.reranker_model_id)

        # Fallback control text for reranker
        self.id_to_text_map = build_control_fallback_text_map(self.records)

    def set_qur_df(self, qur_df: pd.DataFrame) -> None:
        self.qur_df = qur_df

    def _pick_clause_for_controls(self, query: str, controls: List[str]) -> Dict[str, str]:
        """
        Pick one representative clause id per control, using dense clause hits for the query.
        """
        controls_set = set(controls)
        best: Dict[str, Tuple[str, float]] = {}

        clause_hits = self.dense_adapter.idx.search(query, top_k=self.config.candidate_set_size * 10)
        for clause_id, score in clause_hits:
            ctl = normalize_control_id(self.clause_to_control.get(clause_id, "")).upper()
            if ctl in controls_set:
                prev = best.get(ctl)
                if prev is None or float(score) > prev[1]:
                    best[ctl] = (clause_id, float(score))

        out: Dict[str, str] = {}
        for ctl in controls:
            if ctl in best:
                out[ctl] = best[ctl][0]
            else:
                cands = self.control_to_clause_ids.get(ctl, [])
                if cands:
                    out[ctl] = cands[0]
        return out

    def retrieve(self, query: str, top_k: int = 10, rewrites=None, **kwargs) -> List[Dict[str, Any]]:
        """
        Returns clause-level doc dicts for pipeline:
          {id, control_id, kind, title, text}
        Accepts `rewrites=` (pipeline passes this).
        """
        # Variants
        rewrite_list = _coerce_rewrite_list(rewrites)
        if rewrite_list:
            variants = _variants_from_pipeline_rewrites(
                query, rewrite_list, max_rewrites=self.config.max_rewrites, jaccard_min=self.config.rewrite_jaccard_min
            )
        else:
            variants = _variants_from_qur_df(
                query, self.qur_df, max_rewrites=self.config.max_rewrites, jaccard_min=self.config.rewrite_jaccard_min
            )

        # Rank controls
        ranked_controls, _meta = s7_rank_controls(
            original_query=query,
            variants=variants,
            bm25_retriever=self.bm25,
            bm25_control_ids=self.bm25_control_ids,
            dense_adapter=self.dense_adapter,
            reranker=self.reranker,
            id_to_text_map=self.id_to_text_map,
            candidate_set_size=self.config.candidate_set_size,
            rrf_k=self.config.rrf_k,
            rewrite_weight=self.config.rewrite_weight,
            rerank_alpha=self.config.rerank_alpha,
            rerank_apply_min_margin_ratio=self.config.rerank_apply_min_margin_ratio,
        )

        controls = [normalize_control_id(c).upper() for c in ranked_controls][: int(top_k)]
        if not controls:
            return []

        # Convert to clause docs
        ctl_to_clause = self._pick_clause_for_controls(query, controls)
        docs: List[Dict[str, Any]] = []
        for ctl in controls:
            clause_id = ctl_to_clause.get(ctl)
            if not clause_id:
                continue
            rec = self.record_by_id.get(clause_id)
            if not rec:
                continue
            docs.append(
                {
                    "id": rec["id"],
                    "control_id": normalize_control_id(rec.get("control_id", "")),
                    "kind": rec.get("kind", "other"),
                    "title": rec.get("title", ""),
                    "text": rec.get("text", ""),
                }
            )
        return docs
