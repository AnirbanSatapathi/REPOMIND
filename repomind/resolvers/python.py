from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict

from .base import BaseResolver


class PythonResolver(BaseResolver):
    """
    Python import resolution strategy.
    """

    @property
    def language(self) -> str:
        return "Python"

    def resolve(
        self,
        current_file: Path,
        repo_root: Path,
        imp: str,
        file_index: Dict[str, str],
    ) -> Optional[str]:
        # handle relative imports
        if imp.startswith("."):
            levels = len(imp) - len(imp.lstrip("."))
            base = current_file.parent

            for _ in range(levels - 1):
                base = base.parent

            rest = imp.lstrip(".")
            if rest:
                base = base / Path(*rest.split("."))

            candidates = [
                base.with_suffix(".py"),
                base / "__init__.py",
            ]

        else:
            base = repo_root / Path(*imp.split("."))
            candidates = [
                base.with_suffix(".py"),
                base / "__init__.py",
            ]

        for c in candidates:
            key = str(c.resolve())
            if key in file_index:
                return file_index[key]

        return None
