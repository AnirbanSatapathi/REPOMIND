from __future__ import annotations

from pathlib import Path
from typing import List

from .base import BaseParser, ParseResult
from .treesitter_engine import TreeSitterEngine


class GoParser(BaseParser):
    language = "Go"

    def __init__(self, ts_engine: TreeSitterEngine):
        self._ts = ts_engine

    def _text(self, source_bytes: bytes, node) -> str:
        """Extract text using byte offsets (safe with multi-byte chars)."""
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def parse(self, file_path: Path, repo_root: Path | None = None) -> ParseResult:
        try:
            source_bytes = file_path.read_bytes()
        except Exception as e:
            return self._err(file_path, f"read_error: {e}")

        imports: List[str] = []
        functions: List[str] = []
        types: List[str] = []

        try:
            parser = self._ts.get_parser("go")
            tree = parser.parse(source_bytes)
            root = tree.root_node

            stack = [root]
            while stack:
                node = stack.pop()

                # -------- IMPORT STATEMENTS --------
                if node.type == "import_declaration":
                    for child in node.children:
                        # import "fmt"
                        if child.type == "import_spec":
                            for gc in child.children:
                                if gc.type == "interpreted_string_literal":
                                    imports.append(self._text(source_bytes, gc).strip('"'))
                        # import ( "fmt" "os" )
                        elif child.type == "import_spec_list":
                            for spec in child.children:
                                if spec.type == "import_spec":
                                    for gc in spec.children:
                                        if gc.type == "interpreted_string_literal":
                                            imports.append(self._text(source_bytes, gc).strip('"'))

                # -------- FUNCTION DECLARATIONS --------
                elif node.type == "function_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        functions.append(self._text(source_bytes, name_node))

                # -------- METHOD DECLARATIONS --------
                elif node.type == "method_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        functions.append(self._text(source_bytes, name_node))

                # -------- TYPE DECLARATIONS (struct, interface) --------
                elif node.type == "type_declaration":
                    for child in node.children:
                        if child.type == "type_spec":
                            name_node = child.child_by_field_name("name")
                            if name_node:
                                types.append(self._text(source_bytes, name_node))

                stack.extend(reversed(node.children))

        except Exception as e:
            return self._err(file_path, f"parse_error: {e}")

        return {
            "file": str(file_path),
            "language": "Go",
            "imports": list(dict.fromkeys(imports)),
            "classes": types,
            "functions": functions,
            "error": None,
        }