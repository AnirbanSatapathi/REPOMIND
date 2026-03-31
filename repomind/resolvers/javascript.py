from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict

from .base import BaseResolver


class JSResolver(BaseResolver):
    """
    JavaScript/TypeScript import resolution strategy.
    """

    JS_EXT = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json"]

    def __init__(self, language: str = "JavaScript"):
        self._language = language

    @property
    def language(self) -> str:
        return self._language

    def resolve(
        self,
        current_file: Path,
        repo_root: Path,
        imp: str,
        file_index: Dict[str, str],
    ) -> Optional[str]:
        if imp.startswith("."):
            target = (current_file.parent / imp).resolve()
        elif imp.startswith("@/"):
            target = (repo_root / "src" / imp[2:]).resolve()
        else:
            # internal package import inside repo (e.g. next/dist/...)
            target = (repo_root / imp).resolve()

        candidates = []

        for ext in self.JS_EXT:
            candidates.append(target.with_suffix(ext))
            candidates.append(target / f"index{ext}")

        candidates.append(target)

        for c in candidates:
            key = str(c)
            if key in file_index:
                return file_index[key]

            # Extension-less fallback
            key2 = str(c.with_suffix(""))
            if key2 in file_index:
                return file_index[key2]

        return None
