from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict

from .base import BaseResolver


class GoResolver(BaseResolver):
    """
    Go import resolution strategy.
    Resolves local Go imports (within the same module) by matching
    import paths to file paths in the repository.
    """

    @property
    def language(self) -> str:
        return "Go"

    def resolve(
        self,
        current_file: Path,
        repo_root: Path,
        imp: str,
        file_index: Dict[str, str],
    ) -> Optional[str]:
        if not imp:
            return None

        # Skip standard library and external packages (contain dots or known prefixes)
        # Go std lib packages don't have dots: "fmt", "os", "net/http"
        # External packages have dots: "github.com/...", "golang.org/..."
        if "." in imp:
            return None

        # Try to resolve as a local package import
        # e.g. "internal/parser" -> repo_root / "internal/parser"
        candidate = (repo_root / imp).resolve()

        # Try directory-based resolution (Go packages are directories)
        candidates = [
            candidate / "main.go",
            candidate / f"{candidate.name}.go",
        ]

        for c in candidates:
            key = str(c)
            if key in file_index:
                return file_index[key]

        # Try as a single file in the same directory
        # e.g. "utils" -> ./utils.go
        same_dir = (current_file.parent / f"{imp}.go").resolve()
        key = str(same_dir)
        if key in file_index:
            return file_index[key]

        return None