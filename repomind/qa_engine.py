"""
QA Engine: RAG pipeline that uses Ollama for local LLM inference
to answer questions about a codebase.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from repomind.chunker import Chunker
from repomind.embedding_engine import EmbeddingEngine
from repomind.vector_store import VectorStore


SYSTEM_PROMPT = """You are an expert software engineer analyzing a codebase. 
Use the provided code context to answer the user's question accurately and concisely.

Code Context:
{context}

Answer the question based on the code context above. If the context doesn't contain 
enough information, say so clearly. Reference specific files and line numbers when possible."""


class QAEngine:
    """
    RAG pipeline: embeds codebase chunks, retrieves relevant context,
    and queries a local Ollama LLM for answers.
    """

    def __init__(
        self,
        embedding_model: Optional[str] = None,
        llm_model: Optional[str] = None,
        index_dir: Optional[str] = None,
    ):
        from repomind.config import get_embedding_model, get_llm_model, get_index_dir
        actual_embedding = embedding_model or get_embedding_model()
        self.llm_model = llm_model or get_llm_model()
        self.index_dir = index_dir or get_index_dir()
        self.embedder = EmbeddingEngine(model_name=actual_embedding)
        self._vector_store: Optional[VectorStore] = None
        self._chunker = Chunker()

    def _ensure_ollama_running(self) -> bool:
        """Check if Ollama is available. Returns True if reachable."""
        try:
            import ollama
            ollama.list()
            return True
        except Exception:
            return False

    def index_repo(self, parsed_files: List[Dict[str, Any]]) -> None:
        """
        Index a repository: chunk files, embed, store in vector DB.
        """
        from pathlib import Path

        # Chunk files
        chunks = self._chunker.chunk_repo(parsed_files)
        if not chunks:
            raise ValueError("No chunks generated from parsed files")

        # Get texts and metadata
        texts = [c.text for c in chunks]
        metadata = [c.to_dict() for c in chunks]

        # Compute embeddings
        print(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedder.embed_chunks(texts, show_progress=True)

        # Build vector store
        dim = self.embedder.dimension
        index_path = Path(self.index_dir)
        self._vector_store = VectorStore(dimension=dim, index_path=index_path)
        self._vector_store.add_chunks(embeddings, metadata)

        # Persist to disk
        self._vector_store.save()
        print(f"Index saved to {index_path} ({len(chunks)} chunks)")

    def load_index(self) -> bool:
        """
        Load a previously saved index from disk.
        Returns True if loaded successfully.
        """
        from pathlib import Path
        index_path = Path(self.index_dir)
        if not (index_path / "index.faiss").exists():
            return False

        dim = self.embedder.dimension
        self._vector_store = VectorStore(dimension=dim, index_path=index_path)
        try:
            self._vector_store.load()
            return True
        except Exception:
            return False

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search the indexed codebase for relevant chunks."""
        if self._vector_store is None:
            if not self.load_index():
                raise RuntimeError(
                    "No index found. Run indexing first via `repomind index <path>`"
                )

        query_emb = self.embedder.embed_text(query)
        results = self._vector_store.search(query_emb, top_k=top_k)
        return [{"score": score, **meta} for score, meta in results]

    def ask(self, question: str, top_k: int = 5) -> str:
        """
        Ask a question about the codebase and get an AI-generated answer.
        Uses RAG: retrieves relevant chunks, then queries Ollama.
        """
        if not self._ensure_ollama_running():
            raise RuntimeError(
                "Ollama is not running. Please start Ollama first "
                "(https://ollama.ai/) and pull a model like llama3.2"
            )

        # Retrieve relevant context
        results = self.search(question, top_k=top_k)
        if not results:
            return "No relevant code context found in the indexed codebase."

        # Format context
        context_parts = []
        for r in results:
            context_parts.append(
                f"File: {r['file_path']} ({r['chunk_type']}: {r['name']}, "
                f"lines {r['start_line']}-{r['end_line']})\n"
                f"```\n{r['text']}\n```"
            )

        context = "\n\n".join(context_parts)
        prompt = SYSTEM_PROMPT.format(context=context)

        # Query Ollama
        import ollama

        response = ollama.chat(
            model=self.llm_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": question},
            ],
            options={"temperature": 0.1},
        )

        answer = response["message"]["content"]
        return answer

    @property
    def is_indexed(self) -> bool:
        """Check if an index exists on disk."""
        from pathlib import Path
        return (Path(self.index_dir) / "index.faiss").exists()