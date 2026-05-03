"""
Hybrid retrieval: FAISS dense search + BM25 keyword search, merged with RRF.

Architecture
------------
- Dense:  BAAI/bge-small-en-v1.5 via fastembed ONNX (384-dim, retrieval-optimised)
          query_embed() for queries, embed() for passages (asymmetric)
- Sparse: BM25Okapi (rank-bm25) rebuilt from saved chunk text on load
- Fusion: Reciprocal Rank Fusion (k=60) — no score normalisation needed
- Index:  FAISS IndexFlatIP over L2-normalised passage vectors
- Persistence: storage/{session_id}/index.faiss + chunks.json
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import faiss
import numpy as np
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi

from config import EMBEDDING_MODEL, STORAGE_DIR

_model: Optional[TextEmbedding] = None


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(EMBEDDING_MODEL)
    return _model


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


# ---------------------------------------------------------------------------
# FAISSStore
# ---------------------------------------------------------------------------

class FAISSStore:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.session_dir = os.path.join(STORAGE_DIR, session_id)
        self._index: Optional[faiss.IndexFlatIP] = None
        self._chunks: list[dict] = []
        self._bm25: Optional[BM25Okapi] = None

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build(self, chunks: list[dict]) -> None:
        model = _get_model()
        texts = [c["text"] for c in chunks]

        # Dense: passage embeddings (L2-normalised by fastembed)
        embeddings = np.array(list(model.embed(texts)), dtype=np.float32)
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)

        self._chunks = [dict(c) for c in chunks]

        # Sparse: BM25 over tokenised chunk text
        self._bm25 = BM25Okapi([_tokenize(t) for t in texts])

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        os.makedirs(self.session_dir, exist_ok=True)
        faiss.write_index(self._index, self._index_path())
        with open(self._chunks_path(), "w", encoding="utf-8") as f:
            json.dump(self._chunks, f, ensure_ascii=False)

    @classmethod
    def load(cls, session_id: str) -> "FAISSStore":
        store = cls(session_id)
        store._index = faiss.read_index(store._index_path())
        with open(store._chunks_path(), "r", encoding="utf-8") as f:
            store._chunks = json.load(f)
        # BM25 is cheap to rebuild from saved chunk text
        store._bm25 = BM25Okapi([_tokenize(c["text"]) for c in store._chunks])
        return store

    @classmethod
    def exists(cls, session_id: str) -> bool:
        store = cls(session_id)
        return os.path.isfile(store._index_path()) and os.path.isfile(
            store._chunks_path()
        )

    def delete(self) -> None:
        import shutil
        if os.path.isdir(self.session_dir):
            shutil.rmtree(self.session_dir)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5) -> list[tuple[dict, float]]:
        """
        Hybrid search: FAISS + BM25 merged with Reciprocal Rank Fusion.

        Returns top_k (chunk, dense_score) pairs sorted by RRF score.
        dense_score is kept for compatibility with the similarity threshold gate.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        n = self._index.ntotal
        fetch_k = min(top_k * 3, n)  # cast a wider net before merging

        # --- Dense retrieval ---
        model = _get_model()
        query_emb = np.array(list(model.query_embed([query])), dtype=np.float32)
        scores, indices = self._index.search(query_emb, fetch_k)
        dense_ranked: list[tuple[int, float]] = [
            (int(idx), float(score))
            for score, idx in zip(scores[0], indices[0])
            if idx >= 0
        ]

        # --- Sparse retrieval (BM25) ---
        bm25_scores = self._bm25.get_scores(_tokenize(query))
        sparse_ranked: list[tuple[int, float]] = [
            (int(idx), float(bm25_scores[idx]))
            for idx in np.argsort(bm25_scores)[::-1][:fetch_k]
        ]

        # --- Reciprocal Rank Fusion ---
        RRF_K = 60
        rrf: dict[int, float] = {}
        for rank, (idx, _) in enumerate(dense_ranked):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)
        for rank, (idx, _) in enumerate(sparse_ranked):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (RRF_K + rank + 1)

        top_indices = sorted(rrf, key=rrf.__getitem__, reverse=True)[:top_k]

        dense_score_map = {idx: score for idx, score in dense_ranked}
        results = [
            (self._chunks[idx], dense_score_map.get(idx, 0.0))
            for idx in top_indices
        ]
        # Sort by dense score so the threshold gate sees the best dense score first
        return sorted(results, key=lambda x: x[1], reverse=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _index_path(self) -> str:
        return os.path.join(self.session_dir, "index.faiss")

    def _chunks_path(self) -> str:
        return os.path.join(self.session_dir, "chunks.json")
