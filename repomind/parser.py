from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Dict, List

from repomind.parsers import (
    CFamilyParser,
    CSharpParser,
    JavaParser,
    JavaScriptParser,
    ParserRegistry,
    PythonParser,
    RustParser,
    TreeSitterEngine,
)
from repomind.parsers.normalizers import (
    normalize_java_imports,
    normalize_js_imports,
    normalize_python_imports,
)


_EXT_TO_LANGUAGE: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".hpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hh": "C++",
    ".hxx": "C++",
    ".java": "Java",
    ".cs": "C#",
    ".rs": "Rust",
}


def _normalize_python(imports: List[str], *, file_path: Path, repo_root: Path | None) -> List[str]:
    return normalize_python_imports(imports, file_path=file_path, repo_root=repo_root)


def _normalize_js(imports: List[str], *, file_path: Path, repo_root: Path | None) -> List[str]:
    return normalize_js_imports(imports, file_path=file_path, repo_root=repo_root)


def _normalize_java(imports: List[str], *, file_path: Path, repo_root: Path | None) -> List[str]:
    return normalize_java_imports(imports)


def _normalize_passthrough(imports: List[str], *, file_path: Path, repo_root: Path | None) -> List[str]:
    return [x for x in imports if x]


_NORMALIZE_BY_LANGUAGE: Dict[str, Callable[..., List[str]]] = {
    "Python": _normalize_python,
    "JavaScript": _normalize_js,
    "TypeScript": _normalize_js,
    "Java": _normalize_java,
    "C#": _normalize_passthrough,
    "Rust": _normalize_passthrough,
}


class Parser:
    def __init__(self, registry: ParserRegistry | None = None):
        self.registry = registry or self._build_default_registry()

    def _build_default_registry(self) -> ParserRegistry:
        ts_engine = TreeSitterEngine()

        python_parser = PythonParser()
        js_parser = JavaScriptParser(ts_engine)
        c_parser = CFamilyParser(ts_engine)
        java_parser = JavaParser(ts_engine)
        csharp_parser = CSharpParser(ts_engine)
        rust_parser = RustParser(ts_engine)

        registry = ParserRegistry()
        registry.register_parser("Python", python_parser)
        registry.register_parser("JavaScript", js_parser)
        registry.register_parser("TypeScript", js_parser)
        registry.register_parser("C", c_parser)
        registry.register_parser("C++", c_parser)
        registry.register_parser("Java", java_parser)
        registry.register_parser("C#", csharp_parser)
        registry.register_parser("Rust", rust_parser)
        return registry

    def detect_language(self, file_path: Path) -> str:
        return _EXT_TO_LANGUAGE.get(file_path.suffix.lower(), "Unknown")

    def parse_file(self, file_path: Path, repo_root: Path | None = None) -> Dict[str, Any]:
        language = self.detect_language(file_path)
        parser = self.registry.get_parser(language)

        if not parser:
            return {
                "file": str(file_path),
                "language": language,
                "imports": [],
                "classes": [],
                "functions": [],
                "error": "unsupported_language",
            }

        result = parser.parse(file_path, repo_root=repo_root)

        normalizer = _NORMALIZE_BY_LANGUAGE.get(language)
        if normalizer and not result.get("error"):
            try:
                result["imports"] = normalizer(result.get("imports", []), file_path=file_path, repo_root=repo_root)
            except Exception as e:
                return {
                    "file": str(file_path),
                    "language": result.get("language", language),
                    "imports": [],
                    "classes": [],
                    "functions": [],
                    "error": f"normalize_error: {e}",
                }

        return {
            "file": result["file"],
            "language": result["language"],
            "imports": result["imports"],
            "classes": result["classes"],
            "functions": result["functions"],
            "error": result["error"],
        }

    def parse_repo(self, files: List[Path]) -> List[Dict[str, Any]]:
        if not files:
            return []

        repo_root = Path(os.path.commonpath([str(Path(f).resolve()) for f in files]))
        return [self.parse_file(f, repo_root=repo_root) for f in files]
