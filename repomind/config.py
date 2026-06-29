"""
Configuration loader for RepoMind.
Reads settings from .env file with sensible defaults.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _find_env_file() -> Optional[Path]:
    """Find .env file in current directory or parent directories."""
    current = Path.cwd()
    for _ in range(5):  # Search up to 5 levels up
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _load_dotenv() -> None:
    """Load .env file if it exists (simple implementation, no external dep)."""
    env_path = _find_env_file()
    if not env_path:
        return

    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                # Only set if not already set (env vars take precedence)
                if key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass  # Silently fail if .env is malformed


# Load .env on import
_load_dotenv()


def get_embedding_model() -> str:
    """Get the embedding model name from env or default."""
    return os.environ.get("REPOMIND_EMBEDDING_MODEL", "all-MiniLM-L6-v2")


def get_llm_model() -> str:
    """Get the LLM model name from env or default."""
    return os.environ.get("REPOMIND_LLM_MODEL", "llama3.2")


def get_ollama_host() -> str:
    """Get the Ollama host URL from env or default."""
    return os.environ.get("REPOMIND_OLLAMA_HOST", "http://localhost:11434")


def get_index_dir() -> str:
    """Get the index directory from env or default."""
    return os.environ.get("REPOMIND_INDEX_DIR", ".repomind/indexes")


def get_max_chunk_lines() -> int:
    """Get max lines per chunk from env or default."""
    return int(os.environ.get("REPOMIND_MAX_CHUNK_LINES", "100"))


def get_top_k_default() -> int:
    """Get default top-k for search from env or default."""
    return int(os.environ.get("REPOMIND_TOP_K", "5"))


def get_device() -> Optional[str]:
    """Get the device for embeddings (cpu/cuda) from env or default."""
    return os.environ.get("REPOMIND_DEVICE", None)