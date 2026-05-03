"""
Generate embeddings with sentence-transformers and store/query via FAISS.

Architecture
------------
- Model: all-MiniLM-L6-v2 (384-dim, runs fully local, ~90MB download once)
- Index: IndexFlatIP (inner-product) over L2-normalised vectors → cosine similarity
- Persistence: each session's index + chunk metadata lives in storage/{session_id}/

Cosine similarity scores are in [0, 1] for normalised vectors.
"""

from __future__ import annotations

import json
import os
from typing import Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL, STORAGE_DIR

# Loaded once at import time; subsequent calls reuse the same object
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


# ---------------------------------------------------------------------------
# FAISSStore
# ---------------------------------------------------------------------------

class FAISSStore:
    """
    Wraps a FAISS IndexFlatIP and a parallel list of chunk metadata.

    Usage
    -----
    # Build from chunks and persist
    store = FAISSStore(session_id)
    store.build(chunks)
    store.save()

    # Reload on a future request
    store = FAISSStore.load(session_id)
    results = store.search(query, top_k=5)
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.session_dir = os.path.join(STORAGE_DIR, session_id)
        self._index: Optional[faiss.IndexFlatIP] = None
        self._chunks: list[dict] = []

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build(self, chunks: list[dict]) -> None:
        """Encode all chunks and populate the FAISS index."""
        model = _get_model()
        texts = [c["text"] for c in chunks]

        embeddings = model.encode(
            texts,
            normalize_embeddings=True,  # L2-normalise → inner product = cosine
            batch_size=64,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype(np.float32)

        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)
        self._chunks = [dict(c) for c in chunks]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Write index and metadata to disk so the session survives restarts."""
        os.makedirs(self.session_dir, exist_ok=True)
        faiss.write_index(self._index, self._index_path())
        with open(self._chunks_path(), "w", encoding="utf-8") as f:
            json.dump(self._chunks, f, ensure_ascii=False)

    @classmethod
    def load(cls, session_id: str) -> "FAISSStore":
        """Reload a previously saved store. Raises FileNotFoundError if absent."""
        store = cls(session_id)
        store._index = faiss.read_index(store._index_path())
        with open(store._chunks_path(), "r", encoding="utf-8") as f:
            store._chunks = json.load(f)
        return store

    @classmethod
    def exists(cls, session_id: str) -> bool:
        store = cls(session_id)
        return os.path.isfile(store._index_path()) and os.path.isfile(
            store._chunks_path()
        )

    def delete(self) -> None:
        """Remove all files for this session from disk."""
        import shutil

        if os.path.isdir(self.session_dir):
            shutil.rmtree(self.session_dir)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5) -> list[tuple[dict, float]]:
        """
        Return the top_k most similar chunks with their cosine similarity scores.

        Returns:
            List of (chunk_dict, score) sorted by descending score.
            score is in [0, 1] (1 = identical).
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        model = _get_model()
        query_emb = model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).astype(np.float32)

        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_emb, k)

        results: list[tuple[dict, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append((self._chunks[idx], float(score)))

        return results  # already sorted descending by FAISS

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _index_path(self) -> str:
        return os.path.join(self.session_dir, "index.faiss")

    def _chunks_path(self) -> str:
        return os.path.join(self.session_dir, "chunks.json")
