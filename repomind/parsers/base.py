from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, TypedDict


class ParseResult(TypedDict):
    file: str
    language: str
    imports: List[str]
    classes: List[str]
    functions: List[str]
    error: Optional[str]


class BaseParser(ABC):
    language: str

    @abstractmethod
    def parse(self, file_path: Path, repo_root: Path | None = None) -> ParseResult:
        raise NotImplementedError

    def _ok(
        self,
        file_path: Path,
        *,
        imports: List[str] | None = None,
        classes: List[str] | None = None,
        functions: List[str] | None = None,
    ) -> ParseResult:
        return {
            "file": str(file_path),
            "language": self.language,
            "imports": imports or [],
            "classes": classes or [],
            "functions": functions or [],
            "error": None,
        }

    def _err(self, file_path: Path, error: str) -> ParseResult:
        return {
            "file": str(file_path),
            "language": self.language,
            "imports": [],
            "classes": [],
            "functions": [],
            "error": error,
        }

