from __future__ import annotations

import re
from pathlib import Path
from typing import List

from .base import BaseParser, ParseResult
from .treesitter_engine import TreeSitterEngine


class CFamilyParser(BaseParser):
    language = "C"

    _include_re = re.compile(r'#include\s*[<"]([^">]+)[">]')

    def __init__(self, ts_engine: TreeSitterEngine):
        self._ts = ts_engine

    def _text(self, source_bytes: bytes, node) -> str:
        """Extract text using byte offsets (safe with BOM / multi-byte chars)."""
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    # -------- function name extraction (basic but safe) --------
    def _extract_function_name(self, node, source_bytes: bytes) -> str | None:
        stack = [node]

        last_identifier = None

        while stack:
            n = stack.pop()

            if n.type == "identifier":
                last_identifier = self._text(source_bytes, n)

            stack.extend(reversed(n.children))

        return last_identifier

    # -------- main parse --------
    def parse(self, file_path: Path, repo_root: Path | None = None) -> ParseResult:
        try:
            source_bytes = file_path.read_bytes()
        except Exception as e:
            return self._err(file_path, f"read_error: {e}")

        ext = file_path.suffix.lower()
        is_cpp = ext in {".cpp", ".hpp", ".cc", ".cxx", ".hh", ".hxx"}

        ts_language = "cpp" if is_cpp else "c"
        language_label = "C++" if is_cpp else "C"

        imports: List[str] = []
        functions: List[str] = []

        try:
            parser = self._ts.get_parser(ts_language)
            tree = parser.parse(source_bytes)
            root = tree.root_node

            stack = [root]

            while stack:
                node = stack.pop()

                # -------- INCLUDE PARSING --------
                if node.type == "preproc_include":
                    include_text = self._text(source_bytes, node)

                    match = self._include_re.search(include_text)
                    if match:
                        imports.append(match.group(1).strip())

                # -------- FUNCTION PARSING --------
                elif node.type == "function_definition":
                    declarator = node.child_by_field_name("declarator")
                    if declarator:
                        name = self._extract_function_name(declarator, source_bytes)
                        if name:
                            functions.append(name)

                stack.extend(reversed(node.children))

        except Exception as e:
            return self._err(file_path, f"parse_error: {e}")

        return {
            "file": str(file_path),
            "language": language_label,
            "imports": list(dict.fromkeys(imports)),
            "classes": [],
            "functions": list(dict.fromkeys(functions)),
            "error": None,
        }
