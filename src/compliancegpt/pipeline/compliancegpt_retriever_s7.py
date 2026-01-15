# -*- coding: utf-8 -*-
"""
compliancegpt_retriever_s7.py

Clean, inference-oriented implementation of the ComplianceGPT "System 7" retriever.

Responsibilities
----------------
- Load a CCS JSONL catalog (e.g., NIST SP 800-53 Rev4/Rev5).
- Build:
    * BM25 index (lexical)
    * Dense index (E5-small-v2 + FAISS)
    * Cross-Encoder reranker (MS MARCO MiniLM)
- Expose a simple API:

    retriever = ComplianceGPTRetriever(catalog_path)
    docs = retriever.retrieve(query, top_k=5, rewrites=[...])
"""

from __future__ import annotations

import json
import math
import re
import os
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple, Set, Any
from collections import defaultdict

import numpy as np
import torch


# =======================================================================
# 1. Text + CCS utilities
# =======================================================================

def normalize_text(text: str) -> str:
    text = str(text).lower()
    text = text.replace("-", " ")
    text = re.sub(r"[^0-9a-z\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> List[str]:
    return normalize_text(text).split()


@dataclass
class RetrievalConfig:
    bm25_k1: float = 0.5
    bm25_b: float = 0.75
    alpha_lex: float = 1.0
    alpha_sem: float = 4.0
    rrf_k: int = 60
    dense_topk: int = 20
    lex_topk: int = 20
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"


# =======================================================================
# 2. Dense Index (FAISS + E5)
# =======================================================================

class DenseIndex:
    def __init__(self, texts: List[str], model_name: str = "intfloat/e5-small-v2"):
        if not texts:
            raise ValueError("DenseIndex received empty text list.")

        try:
            import faiss
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("DenseIndex requires 'faiss-cpu' and 'sentence-transformers'.")

        self.model = SentenceTransformer(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

        prefixed = [f"passage: {t}" for t in texts]
        print(f"[Retriever] Building Dense index ({model_name}) over {len(texts)} docs...")
        
        embeddings = self.model.encode(
            prefixed,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        d = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(d)
        self.index.add(embeddings)

    def search(self, query: str, top_k: int = 20) -> Tuple[List[int], List[float]]:
        q_text = f"query: {query}"
        q_emb = self.model.encode(
            [q_text],
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        scores, indices = self.index.search(q_emb, top_k)
        return indices[0].tolist(), scores[0].tolist()


# =======================================================================
# 3. BM25 Index (Lexical)
# =======================================================================

class BM25Index:
    def __init__(self, corpus: List[str], k1: float = 0.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.avgdl = 0.0
        self.doc_freqs: List[Dict[str, int]] = []
        self.idf: Dict[str, float] = {}
        self.doc_len: List[int] = []

        print(f"[Retriever] Building BM25 index over {self.corpus_size} docs...")
        total_len = 0
        df_counts = defaultdict(int)

        for text in corpus:
            tokens = tokenize(text)
            length = len(tokens)
            self.doc_len.append(length)
            total_len += length

            freqs = defaultdict(int)
            for t in tokens:
                freqs[t] += 1
            self.doc_freqs.append(freqs)

            for t in freqs:
                df_counts[t] += 1

        self.avgdl = total_len / self.corpus_size if self.corpus_size else 0

        for token, freq in df_counts.items():
            self.idf[token] = math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def search(self, query: str, top_k: int = 20) -> List[Tuple[int, float]]:
        q_tokens = tokenize(query)
        scores = []
        for idx in range(self.corpus_size):
            score = 0.0
            doc_len = self.doc_len[idx]
            freqs = self.doc_freqs[idx]
            for qt in q_tokens:
                if qt not in freqs:
                    continue
                f = freqs[qt]
                numerator = self.idf[qt] * f * (self.k1 + 1)
                denominator = f + self.k1 * (1 - self.b + self.b * (doc_len / self.avgdl))
                score += numerator / denominator
            if score > 0:
                scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# =======================================================================
# 4. Main Retriever Class (S7)
# =======================================================================

class ComplianceGPTRetriever:
    def __init__(self, catalog_path: str, config: RetrievalConfig = None):
        if config is None:
            config = RetrievalConfig()
        self.cfg = config
        
        self.ids: List[str] = []
        self.texts: List[str] = []
        self.docs_map: Dict[str, str] = {}
        
        # Regex for header cleaning
        self.req_start_re = re.compile(
            r"\b(the organization|enforce|establish|implement|configure|ensure|provide|develop|define|document|maintain|monitor|review|update|restrict|prohibit|verify|if)\b",
            re.IGNORECASE
        )

        self._load_catalog(catalog_path)
        
        if not self.texts:
            raise ValueError(f"[FATAL] No documents loaded from: {catalog_path}. The file parses but no 'text' content was found.")

        # Build Indices
        self.bm25 = BM25Index(self.texts, k1=self.cfg.bm25_k1, b=self.cfg.bm25_b)
        self.dense = DenseIndex(self.texts)
        
        print("[Retriever] Loading Cross-Encoder for reranking...")
        from sentence_transformers import CrossEncoder
        self.reranker = CrossEncoder(self.cfg.rerank_model)

    def _extract_recursive_text(self, node: Any) -> List[str]:
        """
        Recursively extract 'prose' or 'text' fields from nested JSON structures (e.g. parts).
        """
        acc = []
        if isinstance(node, dict):
            # Check for direct text fields
            if "prose" in node and isinstance(node["prose"], str):
                acc.append(node["prose"])
            elif "text" in node and isinstance(node["text"], str):
                acc.append(node["text"])
            
            # Recurse into children
            for key, val in node.items():
                if isinstance(val, (dict, list)):
                    acc.extend(self._extract_recursive_text(val))
        
        elif isinstance(node, list):
            for item in node:
                acc.extend(self._extract_recursive_text(item))
        
        return acc

    def _load_catalog(self, path: str):
        if not os.path.exists(path):
            print(f"[ERROR] Catalog file not found: {path}")
            return

        print(f"[Retriever] Loading catalog from: {path}")
        count = 0
        missing_text = 0
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                try:
                    obj = json.loads(line)
                    cid = obj.get("id") or obj.get("control_id")
                    
                    # 1. Try direct text
                    txt = obj.get("text", "")
                    
                    # 2. If missing, try recursive extraction from 'parts'
                    if not txt:
                        parts_text = self._extract_recursive_text(obj.get("parts", []))
                        if parts_text:
                            # Prepend title if available for context
                            title = obj.get("title", "")
                            joined_parts = " ".join(parts_text)
                            txt = f"{cid} {title} {joined_parts}" if title else joined_parts
                    
                    # Clean whitespace
                    txt = txt.replace("\n", " ").strip()
                    
                    if cid and txt:
                        self.ids.append(cid)
                        self.texts.append(txt)
                        self.docs_map[cid] = txt
                        count += 1
                    else:
                        missing_text += 1
                        
                except json.JSONDecodeError:
                    continue
                    
        print(f"[Retriever] Successfully loaded {count} documents.")
        if count == 0 and missing_text > 0:
            print(f"[Retriever] WARN: {missing_text} lines parsed but had no text content.")

    def _rrf_score(self, rankings_list: List[List[str]], k: int = 60) -> Dict[str, float]:
        rrf_map = defaultdict(float)
        for ranking in rankings_list:
            for rank, cid in enumerate(ranking):
                rrf_map[cid] += 1.0 / (k + rank + 1)
        return rrf_map

    def _superhybrid_rrf(self, query: str, rewrites: Optional[List[str]]) -> List[str]:
        all_rankings = []
        d_idxs, _ = self.dense.search(query, top_k=self.cfg.dense_topk)
        all_rankings.append([self.ids[i] for i in d_idxs])

        l_pairs = self.bm25.search(query, top_k=self.cfg.lex_topk)
        all_rankings.append([self.ids[i] for i, _ in l_pairs])

        if rewrites:
            for rw in rewrites:
                d_idxs_r, _ = self.dense.search(rw, top_k=self.cfg.dense_topk)
                all_rankings.append([self.ids[i] for i in d_idxs_r])
                l_pairs_r = self.bm25.search(rw, top_k=self.cfg.lex_topk)
                all_rankings.append([self.ids[i] for i, _ in l_pairs_r])

        rrf_scores = self._rrf_score(all_rankings, k=self.cfg.rrf_k)
        sorted_ids = sorted(rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True)
        return sorted_ids[:50]

    def _rerank(self, query: str, candidate_ids: List[str]) -> List[Tuple[str, float]]:
        if not candidate_ids: return []
        texts = []
        valid_cids = []
        for cid in candidate_ids:
            txt = self.docs_map.get(cid)
            if txt:
                valid_cids.append(cid)
                texts.append(txt)

        if not valid_cids: return []

        pairs = [[query, t] for t in texts]
        scores = self.reranker.predict(pairs)
        scored = []
        for cid, sc in zip(valid_cids, scores):
            scored.append((cid, float(sc)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _clean_header(self, text: str) -> str:
        """
        Strips header junk from the start of the string for cleaner LLM context.
        """
        match = self.req_start_re.search(text)
        if match:
            # Only slice if the start is reasonably close to the beginning
            if match.start() < 200: 
                return text[match.start():].strip()
        
        # Fallback: Split by newline if it looks like a title header
        if "\n" in text:
            return text.split("\n", 1)[1].strip()
            
        return text

    def retrieve(self, query: str, top_k: int = 5, rewrites: Optional[List[str]] = None) -> List[Dict[str, object]]:
        candidate_ids = self._superhybrid_rrf(query, rewrites=rewrites)
        reranked = self._rerank(query, candidate_ids)
        results = []
        for cid, score in reranked[:top_k]:
            raw_text = self.docs_map.get(cid, "")
            
            # Use cleaned text for the pipeline/LLM
            clean_text = self._clean_header(raw_text)
            
            results.append({
                "id": cid,
                "text": clean_text,
                "raw_text": raw_text,
                "score": float(score)
            })
        return results