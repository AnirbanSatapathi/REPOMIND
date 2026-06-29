"""
FAISS-based vector store for semantic code search.
Supports persistence to disk for reuse across sessions.
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class VectorStore:
    """
    Stores and searches code chunk embeddings using FAISS.
    """

    def __init__(self, dimension: int, index_path: Optional[Path] = None):
        self.dimension = dimension
        self._index_path = index_path
        self._index = None
        self._chunks: List[Dict[str, Any]] = []  # metadata for each vector

    def _lazy_init_index(self):
        if self._index is not None:
            return
        import faiss
        # Use IndexFlatIP for inner product (cosine sim with normalized vectors)
        self._index = faiss.IndexFlatIP(self.dimension)

    def add_chunks(
        self,
        embeddings: List[List[float]],
        chunks: List[Dict[str, Any]],
    ) -> None:
        """
        Add chunk embeddings and their metadata to the store.
        """
        self._lazy_init_index()
        if not embeddings:
            return

        vectors = np.array(embeddings, dtype=np.float32)
        if vectors.ndim != 2:
            raise ValueError(f"Expected 2D array, got shape {vectors.shape}")

        self._index.add(vectors)
        self._chunks.extend(chunks)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Search the store for the top_k most similar chunks.
        Returns list of (score, chunk_metadata) tuples.
        """
        self._lazy_init_index()
        if self._index.ntotal == 0:
            return []

        query = np.array([query_embedding], dtype=np.float32)
        scores, indices = self._index.search(query, min(top_k, self._index.ntotal))

        results: List[Tuple[float, Dict[str, Any]]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._chunks):
                continue
            results.append((float(score), self._chunks[idx]))

        return results

    @property
    def count(self) -> int:
        if self._index is None:
            return 0
        return self._index.ntotal if hasattr(self._index, "ntotal") else len(self._chunks)

    def save(self, path: Optional[Path] = None) -> None:
        """Persist the index and metadata to disk."""
        save_path = path or self._index_path
        if save_path is None:
            raise ValueError("No save path provided")

        import faiss

        save_path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self._index, str(save_path / "index.faiss"))

        # Save chunk metadata as JSON
        meta_path = save_path / "chunks.json"
        meta_path.write_text(json.dumps(self._chunks, indent=2), encoding="utf-8")

    def load(self, path: Optional[Path] = None) -> None:
        """Load a previously saved index and metadata."""
        import faiss

        load_path = path or self._index_path
        if load_path is None:
            raise ValueError("No load path provided")

        index_file = load_path / "index.faiss"
        meta_file = load_path / "chunks.json"

        if not index_file.exists() or not meta_file.exists():
            raise FileNotFoundError(f"Index not found at {load_path}")

        self._index = faiss.read_index(str(index_file))
        self._chunks = json.loads(meta_file.read_text(encoding="utf-8"))

    def clear(self) -> None:
        """Clear all stored vectors and chunks."""
        self._index = None
        self._chunks = []