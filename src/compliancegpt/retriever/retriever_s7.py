"""
retriever_s7.py — S7 retriever component for ComplianceGPT

Design goals (clean + pipeline-friendly)
- Single, unambiguous path name: `ccs_path` (NO catalog_path/ccs_path duality).
- Single retriever class: `ComplianceGPTRetriever`.
- Single config class: `RetrievalConfig`.
- Output docs are clause-level dicts the Generator can consume directly:
    { "id", "control_id", "kind", "title", "text" }

Retrieval idea
- Control ranking: weighted RRF fusion over BM25(control) + Dense(control via clause adapter)
- Optional rerank: cross-encoder scoring + "safe blending" + "no-harm gate"
- Evidence selection: return multiple clause snippets per top control (statement + guidance, etc.)

Dependencies (same as before)
- numpy
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


# ==========================================================
# 1) Text utils / normalization
# ==========================================================
_PUNCT_RE = re.compile(r"[^0-9A-Za-z_\s]+")
_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

# Control ID normalization helpers
_CONTROL_ID_DOT_RE = re.compile(r"^([A-Z]{2,3}-\d+)\.(\d+)$")
_CONTROL_ID_PAREN_RE = re.compile(r"^([A-Z]{2,3}-\d+)\((\d+)\)$")


def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    s = text.lower().replace("-", " ")
    s = _PUNCT_RE.sub(" ", s)
    return _WS_RE.sub(" ", s).strip()


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(str(text))]


def normalize_control_id(control_id: str) -> str:
    """Normalize control IDs to a canonical form.

    Canonicalization rules:
      - Upper-case, '_' -> '-'
      - Enhancement dot form (e.g., 'AC-2.1') is converted to parentheses form ('AC-2(1)')
    """
    if not isinstance(control_id, str):
        return ""
    cid = control_id.strip().upper().replace("_", "-")

    m_dot = _CONTROL_ID_DOT_RE.match(cid)
    if m_dot:
        return f"{m_dot.group(1)}({m_dot.group(2)})"

    if _CONTROL_ID_PAREN_RE.match(cid):
        return cid

    return cid


def control_id_aliases(control_id: str) -> str:
    """Return a space-separated set of ID aliases for indexing/matching.

    Includes:
      - canonical form
      - hyphenless and spaced variants
      - dot/parentheses enhancement variants (both directions)
    """
    cid = normalize_control_id(control_id)
    aliases: set[str] = set()

    def _add(x: str) -> None:
        if not x:
            return
        aliases.add(x)
        aliases.add(x.replace("-", ""))
        aliases.add(x.replace("-", " "))

    _add(cid)

    m_paren = _CONTROL_ID_PAREN_RE.match(cid)
    if m_paren:
        dot = f"{m_paren.group(1)}.{m_paren.group(2)}"
        _add(dot)
    else:
        m_dot = _CONTROL_ID_DOT_RE.match(cid)
        if m_dot:
            paren = f"{m_dot.group(1)}({m_dot.group(2)})"
            _add(paren)

    return " ".join(sorted(aliases))


def jaccard_overlap(a: str, b: str) -> float:
    A = set(tokenize(normalize_text(a)))
    B = set(tokenize(normalize_text(b)))
    if not A or not B:
        return 0.0
    return len(A & B) / float(len(A | B))


def normalize_scores_minmax(x: np.ndarray) -> np.ndarray:
    """Map scores to [0,1] robustly (flat -> zeros)."""
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
    ccs_path: str,
    keep_kinds: Iterable[str] = ("smt", "gdn"),
) -> List[Dict[str, Any]]:
    """
    Expected CCS line schema (minimum):
        {
          "id": "...",           # clause id (unique)
          "control_id": "AC-1",  # normalized to AC-1
          "text": "...",         # clause text
          "kind": "smt|gdn|..."  # optional; filtered by keep_kinds
          "title": "..."         # optional
        }
    """
    keep = set(k.lower() for k in keep_kinds) if keep_kinds else set()
    out: List[Dict[str, Any]] = []

    with open(ccs_path, "r", encoding="utf-8") as f:
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


def load_all_records_by_id_jsonl(ccs_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load ALL CCS records into an id->record map (including params like odp/prm).

    Important: retrieval corpora should still be built from clause-only kinds
    (e.g., smt/gdn) via load_clause_records_jsonl(). This function is for
    inventory/verification/canonicalization purposes only.
    """
    out: Dict[str, Dict[str, Any]] = {}
    with open(ccs_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if not isinstance(rec, dict):
                continue

            rid = str(rec.get("id", "")).strip()
            if not rid:
                continue

            kind = str(rec.get("kind", "other")).lower().strip()
            txt = str(rec.get("text", "")).strip()

            # Normalize control id when present (some records may not have one)
            ctl_raw = rec.get("control_id") or rec.get("control") or ""
            ctl = normalize_control_id(ctl_raw)

            # Keep original fields but ensure canonical keys exist
            merged = dict(rec)
            merged["id"] = rid
            merged["kind"] = kind
            merged["text"] = txt
            merged["title"] = str(rec.get("title", "")).strip()
            merged["control_id"] = ctl

            out[rid] = merged

    return out


def build_control_docs_from_clauses(records: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Control-level pseudo-docs for BM25:
    - prepend control id aliases + title
    - append all clause texts for that control
    """
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


def build_control_fallback_text_map(records: List[Dict[str, Any]], max_parts: int = 8) -> Dict[str, str]:
    """
    Short-ish control text for reranker input (avoid feeding huge control docs).
    """
    by_ctl: Dict[str, List[str]] = defaultdict(list)
    for r in records:
        cid = r.get("control_id", "")
        if cid:
            by_ctl[cid].append(r.get("text", ""))
    return {normalize_control_id(k).upper(): "\n".join(v[:max_parts]) for k, v in by_ctl.items()}


# ==========================================================
# 3) BM25 (tiny local implementation)
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
    """Clause-level dense retrieval (cosine/IP with normalized embeddings).

    This implementation prefers faiss when available, but can fall back to a
    brute-force numpy inner-product search if faiss is not installed.
    """

    def __init__(self, model_id: str):
        try:
            import torch  # noqa: F401
            from sentence_transformers import SentenceTransformer  # noqa: F401
        except Exception as e:
            raise ImportError(
                "DenseIndex requires sentence-transformers and torch."
            ) from e

        import torch
        from sentence_transformers import SentenceTransformer

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_id = model_id
        self.model = SentenceTransformer(model_id, device=self.device)

        # faiss is optional
        self._faiss = None
        try:
            import faiss  # type: ignore
            self._faiss = faiss
        except Exception:
            self._faiss = None

        self.index = None
        self.embeddings: Optional[np.ndarray] = None
        self.ids: List[str] = []

    def build(self, texts: List[str], ids: List[str]) -> None:
        self.ids = list(ids)
        emb = self.model.encode(
            texts,
            batch_size=64,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        emb_np = np.asarray(emb, dtype=np.float32)

        if self._faiss is not None:
            self.index = self._faiss.IndexFlatIP(int(emb_np.shape[1]))
            self.index.add(emb_np)
            self.embeddings = None
            return

        # Numpy fallback (slower, but dependency-light)
        self.index = None
        self.embeddings = emb_np

    def search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        if top_k <= 0:
            return []

        q_emb = self.model.encode([query], normalize_embeddings=True)
        q = np.asarray(q_emb, dtype=np.float32)[0]

        if self.index is not None and self._faiss is not None:
            scores, idxs = self.index.search(q.reshape(1, -1), int(top_k))
            out: List[Tuple[str, float]] = []
            for i, s in zip(idxs[0], scores[0]):
                if int(i) == -1:
                    continue
                out.append((self.ids[int(i)], float(s)))
            return out

        if self.embeddings is None or self.embeddings.size == 0:
            return []

        scores_vec = self.embeddings @ q
        n = int(min(int(top_k), int(scores_vec.shape[0])))
        if n <= 0:
            return []

        if n >= int(scores_vec.shape[0]):
            idxs = np.argsort(-scores_vec)
        else:
            part = np.argpartition(-scores_vec, n - 1)[:n]
            idxs = part[np.argsort(-scores_vec[part])]

        out = [(self.ids[int(i)], float(scores_vec[int(i)])) for i in idxs[:n]]
        return out


class ClauseDenseControlAdapter:

    """Clause search → compress to control by max clause score."""

    def __init__(self, dense_idx: DenseIndex, clause_to_control: Dict[str, str]):
        self.idx = dense_idx
        self.cmap = clause_to_control

    def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        # search more clauses than needed, then compress per-control
        hits = self.idx.search(query, top_k=max(10, top_k) * 5)
        best_score: Dict[str, float] = {}
        for clause_id, score in hits:
            ctl = self.cmap.get(clause_id)
            if not ctl:
                continue
            ctl = normalize_control_id(ctl).upper()
            if score > best_score.get(ctl, -1.0):
                best_score[ctl] = float(score)
        ranked = sorted(best_score.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


def build_dense_retriever(
    records: List[Dict[str, Any]],
    dense_model_id: str,
) -> Tuple[ClauseDenseControlAdapter, Dict[str, str], Dict[str, str], DenseIndex]:
    clause_ids: List[str] = []
    texts: List[str] = []
    clause_to_control: Dict[str, str] = {}
    clause_id_to_packed_text: Dict[str, str] = {}

    for r in records:
        cid = r["control_id"]
        title = r.get("title", "")
        kind = r.get("kind", "other")
        header = f"{control_id_aliases(cid)} {title} ({kind})".strip()
        packed = f"{header}\n{r['text']}".strip()

        clause_id = r["id"]
        clause_ids.append(clause_id)
        texts.append(f"passage: {packed}")  # e5 expects "passage: ..."
        clause_to_control[clause_id] = cid
        clause_id_to_packed_text[clause_id] = packed

    idx = DenseIndex(dense_model_id)
    idx.build(texts, clause_ids)
    return ClauseDenseControlAdapter(idx, clause_to_control), clause_id_to_packed_text, clause_to_control, idx


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
# 5) Rewrite handling (pipeline-only, no QUR df here)
# ==========================================================
def _coerce_rewrite_list(rewrites: Any) -> List[str]:
    """
    Accept:
      - list[str]
      - list[dict] with keys rewrite/text
      - single str
    """
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


def build_query_variants(original_query: str, rewrites: List[str], max_rewrites: int, jaccard_min: float) -> List[str]:
    variants = [original_query]
    for r in rewrites:
        if len(r) < 6:
            continue
        if jaccard_overlap(original_query, r) < float(jaccard_min):
            continue
        variants.append(r)
        if len(variants) >= 1 + int(max_rewrites):
            break
    # dedupe while preserving order
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
    reranker_text_by_control: Dict[str, str],
    candidate_set_size: int,
    rrf_k: int,
    rewrite_weight: float,
    rerank_alpha: float,
    rerank_apply_min_margin_ratio: float,
    rerank_skip_enabled: bool = True,
    rerank_skip_min_base_margin_ratio: float = 0.10,
    rerank_skip_require_top1_agreement: bool = False,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Returns:
      (ranked_control_ids, meta)

    Meta includes:
      - reranker_called: whether cross-encoder was executed (performance proof)
      - rerank_applied: whether reranked order was applied (no-harm gate outcome)
      - skip_reason: why reranking was skipped (if skipped)
      - base_margin_ratio: confidence of base fused top-1 vs top-2 (raw RRF)
      - rerank_margin_ratio: confidence of reranked top-1 vs top-2 (blended score space)
    """
    weights = [1.0] + [float(rewrite_weight)] * (len(variants) - 1)
    rrf_scores: Dict[str, float] = defaultdict(float)

    # 1) Weighted RRF fusion of BM25 + Dense (both at control granularity)
    for q, w in zip(variants, weights):
        # BM25 (control-level)
        q_toks = tokenize(normalize_text(q))
        idxs = bm25_retriever.get_top_n(q_toks, n=int(candidate_set_size))
        for rank, i in enumerate(idxs, 1):
            cid = normalize_control_id(bm25_control_ids[int(i)]).upper()
            rrf_scores[cid] += float(w) * (1.0 / (float(rrf_k) + float(rank)))

        # Dense (control-level via clause adapter)
        hits = dense_adapter.search(q, top_k=int(candidate_set_size))
        for rank, (raw_cid, _) in enumerate(hits, 1):
            cid = normalize_control_id(str(raw_cid)).upper()
            rrf_scores[cid] += float(w) * (1.0 / (float(rrf_k) + float(rank)))

    fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[: int(candidate_set_size)]
    cids_all = [c for c, _ in fused]

    if not cids_all:
        return [], {
            "note": "no_candidates",
            "reranker_called": False,
            "rerank_applied": False,
            "skip_reason": "no_candidates",
            "num_variants": len(variants),
        }

    # Base confidence signal (raw RRF margin ratio).
    base_top1 = cids_all[0]
    base_top2 = cids_all[1] if len(cids_all) >= 2 else ""
    if len(cids_all) >= 2:
        s1 = float(rrf_scores.get(base_top1, 0.0))
        s2 = float(rrf_scores.get(base_top2, 0.0))
        base_margin_ratio = (s1 - s2) / max(s1, 1e-9)
    else:
        base_margin_ratio = 1.0


    # Effective apply threshold for the no-harm gate.
    # In uncertain base-ranking scenarios, allow a slightly lower margin requirement so the reranker
    # can correct control-id mistakes without being overly constrained.
    effective_apply_min = float(rerank_apply_min_margin_ratio)
    try:
        if float(base_margin_ratio) < float(rerank_skip_min_base_margin_ratio):
            effective_apply_min = min(effective_apply_min, 0.10)
    except Exception:
        effective_apply_min = float(rerank_apply_min_margin_ratio)

    # Optional agreement signal using original query only (cheap but conservative).
    top1_agree = False
    bm25_top1 = ""
    dense_top1 = ""
    if bool(rerank_skip_require_top1_agreement):
        try:
            q_toks = tokenize(normalize_text(original_query))
            idxs = bm25_retriever.get_top_n(q_toks, n=1)
            if idxs:
                bm25_top1 = normalize_control_id(bm25_control_ids[int(idxs[0])]).upper()
        except Exception:
            bm25_top1 = ""
        try:
            hits = dense_adapter.search(original_query, top_k=1)
            if hits:
                dense_top1 = normalize_control_id(str(hits[0][0])).upper()
        except Exception:
            dense_top1 = ""
        if bm25_top1 and dense_top1 and (base_top1 == bm25_top1 == dense_top1):
            top1_agree = True

    # 2) Pre-rerank skip gate (performance + accuracy)
    if bool(rerank_skip_enabled):
        if base_margin_ratio >= float(rerank_skip_min_base_margin_ratio):
            if (not bool(rerank_skip_require_top1_agreement)) or top1_agree:
                meta = {
                    "num_variants": len(variants),
                    "reranker_called": False,
                    "rerank_applied": False,
                    "skip_reason": "base_confident",
                    "base_top1": base_top1,
                    "base_top2": base_top2,
                    "base_margin_ratio": float(base_margin_ratio),
                    "top1_agree": bool(top1_agree) if bool(rerank_skip_require_top1_agreement) else None,
                    "bm25_top1": bm25_top1 if bool(rerank_skip_require_top1_agreement) else None,
                    "dense_top1": dense_top1 if bool(rerank_skip_require_top1_agreement) else None,
                    "rerank_alpha": float(rerank_alpha),
                    "rerank_apply_min_margin_ratio": float(rerank_apply_min_margin_ratio),
        "rerank_effective_apply_min_margin_ratio": float(effective_apply_min),
                    "rerank_skip_min_base_margin_ratio": float(rerank_skip_min_base_margin_ratio),
                    "rerank_skip_require_top1_agreement": bool(rerank_skip_require_top1_agreement),
                    "final_top1": base_top1,
                    "final_margin_ratio": float(base_margin_ratio),
                    "rerank_margin_ratio": None,
                    "rerank_top1": None,
                    "top_candidates": [],
                }
                return cids_all, meta

    # 3) Rerank (safe blend + no-harm gate)
    pairs: List[List[str]] = []
    valid_cids: List[str] = []
    missing_text_cids: List[str] = []
    for cid in cids_all:
        txt = reranker_text_by_control.get(cid, "")
        if txt:
            pairs.append([original_query, txt])
            valid_cids.append(cid)
        else:
            missing_text_cids.append(cid)

    missing_text_set = set(missing_text_cids)

    if not pairs:
        return cids_all, {
            "note": "no_text_for_rerank",
            "reranker_called": False,
            "rerank_applied": False,
            "skip_reason": "no_text_for_rerank",
            "num_variants": len(variants),
            "base_top1": base_top1,
            "base_top2": base_top2,
            "base_margin_ratio": float(base_margin_ratio),
            "rerank_alpha": float(rerank_alpha),
            "rerank_apply_min_margin_ratio": float(rerank_apply_min_margin_ratio),
        "rerank_effective_apply_min_margin_ratio": float(effective_apply_min),
            "rerank_skip_min_base_margin_ratio": float(rerank_skip_min_base_margin_ratio),
            "rerank_skip_require_top1_agreement": bool(rerank_skip_require_top1_agreement),
            "final_top1": base_top1,
            "final_margin_ratio": float(base_margin_ratio),
        }

    pred = reranker.predict(pairs, show_progress_bar=False)

    base_raw = np.array([rrf_scores.get(c, 0.0) for c in valid_cids], dtype=np.float32)
    base_n = normalize_scores_minmax(base_raw)
    pred_n = normalize_scores_minmax(np.array(pred, dtype=np.float32))

    ra = float(rerank_alpha)
    final_scores = ra * base_n + (1.0 - ra) * pred_n
    order = np.argsort(-final_scores)
    reranked_valid = [valid_cids[int(i)] for i in order]

    # Preserve controls without reranker text (append in base order).
    reranked_full = reranked_valid + [c for c in cids_all if c in missing_text_set]

    if len(order) >= 2:
        fs1 = float(final_scores[int(order[0])])
        fs2 = float(final_scores[int(order[1])])
        rerank_margin_ratio = (fs1 - fs2) / max(fs1, 1e-9)
    else:
        rerank_margin_ratio = 1.0

    rerank_top1 = reranked_full[0] if reranked_full else ""

    # No-harm gate: if reranker changes top1 but with weak margin, keep base ordering.
    # Patch (rerankgate_v1): when the base fused ranking is low-confidence, relax the apply threshold modestly.
    rerank_applied = True
    final_ranked = reranked_full

    effective_apply_min = float(rerank_apply_min_margin_ratio)
    base_uncertain_thr = 0.08
    if float(base_margin_ratio) < float(base_uncertain_thr):
        effective_apply_min = min(effective_apply_min, 0.10)

    if (rerank_top1 != base_top1) and (rerank_margin_ratio < float(effective_apply_min)):
        rerank_applied = False
        final_ranked = cids_all

    final_top1 = final_ranked[0] if final_ranked else ""
    if rerank_applied:
        final_margin_ratio = float(rerank_margin_ratio)
    else:
        final_margin_ratio = float(base_margin_ratio)

    # Debug: capture fused vs rerank vs final details for the top candidates (no effect on ranking)
    debug_top: List[Dict[str, Any]] = []
    try:
        base_rank_map = {c: i + 1 for i, c in enumerate(cids_all)}
        rerank_rank_map = {c: i + 1 for i, c in enumerate(reranked_full)}
        final_rank_map = {c: i + 1 for i, c in enumerate(final_ranked)}
        lim = int(min(20, len(cids_all)))
        valid_idx_map = {c: i for i, c in enumerate(valid_cids)}
        for i in range(lim):
            cid = cids_all[i]
            v_idx = valid_idx_map.get(cid)
            debug_top.append(
                {
                    "control_id": cid,
                    "rrf_score": float(rrf_scores.get(cid, 0.0)),
                    "base_rank": int(base_rank_map.get(cid, 0)),
                    "rerank_rank": int(rerank_rank_map.get(cid, 0)),
                    "final_rank": int(final_rank_map.get(cid, 0)),
                    "base_score_norm": float(base_n[int(v_idx)]) if v_idx is not None and int(v_idx) < len(base_n) else None,
                    "rerank_score_raw": float(pred[int(v_idx)]) if v_idx is not None and int(v_idx) < len(pred) else None,
                    "rerank_score_norm": float(pred_n[int(v_idx)]) if v_idx is not None and int(v_idx) < len(pred_n) else None,
                    "final_score": float(final_scores[int(v_idx)]) if v_idx is not None and int(v_idx) < len(final_scores) else None,
                }
            )
    except Exception:
        debug_top = []

    meta = {
        "num_variants": len(variants),
        "top_candidates": debug_top,
        "reranker_called": True,
        "rerank_applied": rerank_applied,
        "skip_reason": None,
        "rerank_alpha": float(rerank_alpha),
        "rerank_apply_min_margin_ratio": float(rerank_apply_min_margin_ratio),
        "rerank_effective_apply_min_margin_ratio": float(effective_apply_min),
        "rerank_skip_min_base_margin_ratio": float(rerank_skip_min_base_margin_ratio),
        "rerank_skip_require_top1_agreement": bool(rerank_skip_require_top1_agreement),
        "base_top1": base_top1,
        "base_top2": base_top2,
        "base_margin_ratio": float(base_margin_ratio),
        "bm25_top1": bm25_top1 if bool(rerank_skip_require_top1_agreement) else None,
        "dense_top1": dense_top1 if bool(rerank_skip_require_top1_agreement) else None,
        "top1_agree": bool(top1_agree) if bool(rerank_skip_require_top1_agreement) else None,
        "rerank_top1": rerank_top1,
        "final_top1": final_top1,
        "rerank_margin_ratio": float(rerank_margin_ratio),
        "final_margin_ratio": float(final_margin_ratio),
    }
    return final_ranked, meta


# ==========================================================
# 7) Config + retriever (pipeline-facing)
# ==========================================================
@dataclass(frozen=True)
class RetrievalConfig:
    # CCS filtering
    keep_kinds: Tuple[str, ...] = ("smt", "gdn")

    # BM25 params
    bm25_k1: float = 1.5
    bm25_b: float = 0.75

    # Dense / rerank models
    dense_model_id: str = "intfloat/e5-small-v2"
    reranker_model_id: str = "BAAI/bge-reranker-base"

    # Ranking params
    candidate_set_size: int = 50
    rrf_k: int = 60

    # Rewrite params
    max_rewrites: int = 3
    rewrite_weight: float = 0.25
    rewrite_jaccard_min: float = 0.15

    # Safe rerank blending + no-harm gate
    rerank_alpha: float = 0.65
    rerank_apply_min_margin_ratio: float = 0.15

    # Pre-rerank skip gate (performance + accuracy)
    rerank_skip_enabled: bool = True
    rerank_skip_min_base_margin_ratio: float = 0.10
    rerank_skip_require_top1_agreement: bool = False

    # Evidence selection
    clauses_per_control: int = 3
    kind_priority: Tuple[str, ...] = ("smt", "gdn")  # fill missing evidence in this order

    # Evidence gating (keep params in CCS, but avoid citing them as evidence)
    evidence_kinds: Tuple[str, ...] = ("smt", "gdn")

    # Prefer more specific statement subclauses (e.g., *_smt.a) over top-level statements
    prefer_depth1_subclauses: bool = True


class ComplianceGPTRetriever:
    """
    Pipeline-facing retriever.

    Canonical API (use these names everywhere):
      - __init__(ccs_path=..., config=RetrievalConfig())
      - retrieve(query, top_k=..., rewrites=...) -> list[doc_dict]
      - ids: clause ids (for pipeline CCS sanity checks)
    """

    def __init__(self, *, ccs_path: str, config: RetrievalConfig = RetrievalConfig(), **kwargs):
        self.config = config

        # 1) Load CCS
        #    - self.records: retrieval corpus (clause-only kinds)
        #    - self.record_by_id: full CCS inventory (includes odp/prm for canonicalization)
        self.records = load_clause_records_jsonl(ccs_path, keep_kinds=config.keep_kinds)
        self.record_by_id = load_all_records_by_id_jsonl(ccs_path)
        # Ensure clause records used in retrieval are stored in canonical, normalized form
        for r in self.records:
            self.record_by_id[r["id"]] = r

        # clause ids for CCS sanity check
        self.ids = [r["id"] for r in self.records]

        # 2) Build control→clauses maps (for evidence selection fallback)
        self.control_to_clause_ids: Dict[str, List[str]] = defaultdict(list)
        self.control_to_clause_ids_by_kind: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        for r in self.records:
            ctl = normalize_control_id(r.get("control_id", "")).upper()
            if not ctl:
                continue
            self.control_to_clause_ids[ctl].append(r["id"])
            self.control_to_clause_ids_by_kind[ctl][str(r.get("kind", "other")).lower()].append(r["id"])

        # 3) BM25 on control-level aggregated docs
        ctl_docs = build_control_docs_from_clauses(self.records)
        self.bm25, self.bm25_control_ids = build_bm25(ctl_docs, k1=config.bm25_k1, b=config.bm25_b)

        # 4) Dense clause index + control adapter
        self.dense_adapter, self.clause_id_to_packed_text, self.clause_to_control, self.dense_index = build_dense_retriever(
            self.records, dense_model_id=config.dense_model_id
        )

        # 5) Reranker
        self.reranker = build_reranker(config.reranker_model_id)

        # 6) Control fallback text for reranker inputs
        self.reranker_text_by_control = build_control_fallback_text_map(self.records)

    def _select_clauses_for_controls(self, query: str, controls: List[str]) -> Dict[str, List[str]]:
        """
        Select up to `clauses_per_control` clause ids per control.

        Strategy:
          1) Take top dense clause hits for the query; bucket by control; keep best scores.
          2) For each control, if we still need more evidence, fill from kind_priority
             (statement first, then guidance, etc.)
        """
        controls_set = set(controls)
        per_ctl: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

        # Dense clause hits
        clause_hits = self.dense_index.search(query, top_k=max(100, self.config.candidate_set_size * 20))
        allowed_kinds = set(k.lower() for k in (self.config.evidence_kinds or ()))
        for clause_id, score in clause_hits:
            rec = self.record_by_id.get(clause_id)
            if not rec:
                continue
            kind = str(rec.get("kind", "")).lower()
            if allowed_kinds and kind not in allowed_kinds:
                continue

            ctl = normalize_control_id(self.clause_to_control.get(clause_id, "")).upper()
            if ctl not in controls_set:
                continue
            per_ctl[ctl].append((clause_id, float(score)))

        def _depth_bucket(cid: str) -> int:
            s = str(cid).lower()
            rem = ""
            for suf in ("_smt", "_gdn", "_obj"):
                if suf in s:
                    rem = s.split(suf, 1)[1]
                    break
            depth = rem.count(".") if rem else 0
            if not self.config.prefer_depth1_subclauses:
                return 0
            if depth == 1:
                return 0
            if depth == 2:
                return 1
            if depth >= 3:
                return 2
            return 3

        # Keep best unique clause ids per control (depth-aware, then score)
        selected: Dict[str, List[str]] = {}
        for ctl in controls:
            hits = per_ctl.get(ctl, [])
            if hits:
                hits_sorted = sorted(hits, key=lambda x: (_depth_bucket(x[0]), -x[1]))
                seen = set()
                best_ids: List[str] = []
                for cid, _ in hits_sorted:
                    if cid in seen:
                        continue
                    best_ids.append(cid)
                    seen.add(cid)
                    if len(best_ids) >= int(self.config.clauses_per_control):
                        break
                selected[ctl] = best_ids
            else:
                selected[ctl] = []

            # Fill remaining from kind_priority
            need = int(self.config.clauses_per_control) - len(selected[ctl])
            if need > 0:
                for kind in self.config.kind_priority:
                    kind_ids = self.control_to_clause_ids_by_kind.get(ctl, {}).get(kind, [])
                    if kind_ids and self.config.prefer_depth1_subclauses:
                        kind_ids = sorted(kind_ids, key=_depth_bucket)
                    for cid in kind_ids:
                        if cid not in selected[ctl]:
                            selected[ctl].append(cid)
                            need -= 1
                            if need <= 0:
                                break
                    if need <= 0:
                        break

            # If still short, fill from any clauses for the control
            need = int(self.config.clauses_per_control) - len(selected[ctl])
            if need > 0:
                for cid in self.control_to_clause_ids.get(ctl, []):
                    if cid not in selected[ctl]:
                        selected[ctl].append(cid)
                        need -= 1
                        if need <= 0:
                            break

        return selected

    def retrieve(self, query: str, top_k: int = 10, rewrites: Any = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Returns clause-level doc dicts:
          {id, control_id, kind, title, text}

        - `top_k` is the number of top *controls* to return evidence for.
        - total returned docs ~= top_k * clauses_per_control (minus missing).
        """
        rewrite_list = _coerce_rewrite_list(rewrites)
        variants = build_query_variants(
            query, rewrite_list, max_rewrites=self.config.max_rewrites, jaccard_min=self.config.rewrite_jaccard_min
        )

        ranked_controls, _meta = s7_rank_controls(
            original_query=query,
            variants=variants,
            bm25_retriever=self.bm25,
            bm25_control_ids=self.bm25_control_ids,
            dense_adapter=self.dense_adapter,
            reranker=self.reranker,
            reranker_text_by_control=self.reranker_text_by_control,
            candidate_set_size=self.config.candidate_set_size,
            rrf_k=self.config.rrf_k,
            rewrite_weight=self.config.rewrite_weight,
            rerank_alpha=self.config.rerank_alpha,
            rerank_apply_min_margin_ratio=self.config.rerank_apply_min_margin_ratio,
            rerank_skip_enabled=self.config.rerank_skip_enabled,
            rerank_skip_min_base_margin_ratio=self.config.rerank_skip_min_base_margin_ratio,
            rerank_skip_require_top1_agreement=self.config.rerank_skip_require_top1_agreement,
        )


        # Expose last retrieval diagnostics for pipeline-level debugging (no effect on ranking)
        try:
            self.last_meta = dict(_meta or {})
            self.last_ranked_controls = list(ranked_controls or [])
            self.last_variants = list(variants or [])
        except Exception:
            self.last_meta = {}
            self.last_ranked_controls = []
            self.last_variants = list(variants or [])

        controls = [normalize_control_id(c).upper() for c in ranked_controls][: int(top_k)]
        if not controls:
            return []

        ctl_to_clause_ids = self._select_clauses_for_controls(query, controls)

        docs: List[Dict[str, Any]] = []
        for ctl in controls:
            for clause_id in ctl_to_clause_ids.get(ctl, []):
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

    def retrieve_debug(self, query: str, top_k: int = 10, rewrites: Any = None, **kwargs) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Debug-friendly retrieval.

        Returns:
          (docs, meta)

        - docs: same as `retrieve()`
        - meta: includes ranking diagnostics (control ranking + rerank gate info) and how clauses were selected.
        """
        rewrite_list = _coerce_rewrite_list(rewrites)
        variants = build_query_variants(
            query, rewrite_list, max_rewrites=self.config.max_rewrites, jaccard_min=self.config.rewrite_jaccard_min
        )

        ranked_controls, meta = s7_rank_controls(
            original_query=query,
            variants=variants,
            bm25_retriever=self.bm25,
            bm25_control_ids=self.bm25_control_ids,
            dense_adapter=self.dense_adapter,
            reranker=self.reranker,
            reranker_text_by_control=self.reranker_text_by_control,
            candidate_set_size=self.config.candidate_set_size,
            rrf_k=self.config.rrf_k,
            rewrite_weight=self.config.rewrite_weight,
            rerank_alpha=self.config.rerank_alpha,
            rerank_apply_min_margin_ratio=self.config.rerank_apply_min_margin_ratio,
            rerank_skip_enabled=self.config.rerank_skip_enabled,
            rerank_skip_min_base_margin_ratio=self.config.rerank_skip_min_base_margin_ratio,
            rerank_skip_require_top1_agreement=self.config.rerank_skip_require_top1_agreement,
        )

        controls = [normalize_control_id(c).upper() for c in ranked_controls][: int(top_k)]
        if not controls:
            meta = dict(meta or {})
            meta.update({"variants": variants, "ranked_controls": ranked_controls, "selected_controls": []})
            return [], meta

        ctl_to_clause_ids = self._select_clauses_for_controls(query, controls)

        docs: List[Dict[str, Any]] = []
        for ctl in controls:
            for clause_id in ctl_to_clause_ids.get(ctl, []):
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

        meta = dict(meta or {})
        meta.update(
            {
                "variants": variants,
                "ranked_controls": ranked_controls,
                "selected_controls": controls,
                "selected_clause_ids_by_control": {k: list(v) for k, v in (ctl_to_clause_ids or {}).items()},
                "n_docs": len(docs),
            }
        )
        return docs, meta
