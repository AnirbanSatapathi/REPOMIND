"""
Local embedding engine using sentence-transformers for code understanding.
"""
from __future__ import annotations

import warnings
from typing import List, Optional

import numpy as np


class EmbeddingEngine:
    """
    Generates embeddings for code chunks using sentence-transformers.
    Uses the lightweight all-MiniLM-L6-v2 model by default.
    """

    # Model names that work well for code
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    CODE_MODELS = {
        "all-MiniLM-L6-v2",  # Good general-purpose, small (<100MB)
        "all-mpnet-base-v2",  # Better quality, larger (~400MB)
    }

    def __init__(self, model_name: str = DEFAULT_MODEL, device: Optional[str] = None):
        self.model_name = model_name
        self.device = device
        self._model = None

    def _lazy_load(self):
        if self._model is not None:
            return
        from sentence_transformers import SentenceTransformer
        kwargs = {}
        if self.device:
            kwargs["device"] = self.device
        self._model = SentenceTransformer(self.model_name, **kwargs)

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        Returns a list of floats (normalized vector).
        """
        self._lazy_load()
        vec = self._model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    def embed_chunks(
        self, texts: List[str], show_progress: bool = False
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        Returns list of float vectors.
        """
        self._lazy_load()
        if not texts:
            return []
        embeddings = self._model.encode(
            texts, normalize_embeddings=True, show_progress_bar=show_progress
        )
        return [v.tolist() for v in embeddings]

    @property
    def dimension(self) -> int:
        """Return the embedding dimension of the model."""
        self._lazy_load()
        return self._model.get_sentence_embedding_dimension()