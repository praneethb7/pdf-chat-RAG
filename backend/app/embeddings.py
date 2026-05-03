"""
BM25 retrieval store — no local ML model, no ONNX, no PyTorch.

Why BM25 over dense embeddings for this deployment:
- Render free tier (512 MB) cannot fit any ONNX/PyTorch model at runtime
- BM25 uses ~5 MB of RAM regardless of document size
- For technical PDFs with precise terminology, BM25 retrieval quality matches
  or exceeds generic sentence-embedding models (exact term matching beats
  semantic approximation for domain-specific vocabulary)
- The Groq LLM at Layer 2 supplies the semantic reasoning over retrieved chunks

Scoring: raw BM25 scores normalised to [0, 1] by dividing by the max score in
the result set. A score of 0 means no query term matched any chunk.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import numpy as np
from rank_bm25 import BM25Okapi

from config import STORAGE_DIR


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class FAISSStore:
    """
    Drop-in replacement for the previous FAISS vector store.
    Internally uses BM25 for retrieval; the public interface is identical.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.session_dir = os.path.join(STORAGE_DIR, session_id)
        self._chunks: list[dict] = []
        self._bm25: Optional[BM25Okapi] = None

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build(self, chunks: list[dict]) -> None:
        self._chunks = [dict(c) for c in chunks]
        self._bm25 = BM25Okapi([_tokenize(c["text"]) for c in self._chunks])

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        os.makedirs(self.session_dir, exist_ok=True)
        with open(self._chunks_path(), "w", encoding="utf-8") as f:
            json.dump(self._chunks, f, ensure_ascii=False)

    @classmethod
    def load(cls, session_id: str) -> "FAISSStore":
        store = cls(session_id)
        with open(store._chunks_path(), "r", encoding="utf-8") as f:
            store._chunks = json.load(f)
        store._bm25 = BM25Okapi([_tokenize(c["text"]) for c in store._chunks])
        return store

    @classmethod
    def exists(cls, session_id: str) -> bool:
        store = cls(session_id)
        return os.path.isfile(store._chunks_path())

    def delete(self) -> None:
        import shutil
        if os.path.isdir(self.session_dir):
            shutil.rmtree(self.session_dir)

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5) -> list[tuple[dict, float]]:
        """
        Return the top_k most relevant chunks with normalised BM25 scores [0, 1].
        Score of 0 means no query term appears in any chunk (truly out-of-scope).
        """
        if not self._chunks:
            return []

        scores = self._bm25.get_scores(_tokenize(query))
        top_indices = np.argsort(scores)[::-1][:top_k]

        max_score = float(scores[top_indices[0]]) if len(top_indices) > 0 else 0.0
        if max_score == 0.0:
            return []

        results = [
            (self._chunks[int(i)], float(scores[i]) / max_score)
            for i in top_indices
            if scores[i] > 0
        ]
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _chunks_path(self) -> str:
        return os.path.join(self.session_dir, "chunks.json")
