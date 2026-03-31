from __future__ import annotations

from pathlib import Path
from typing import List

from .base import BaseParser, ParseResult
from .treesitter_engine import TreeSitterEngine


class CSharpParser(BaseParser):
    language = "C#"

    def __init__(self, ts_engine: TreeSitterEngine):
        self._ts = ts_engine

    def _text(self, source_bytes: bytes, node) -> str:
        """Extract text using byte offsets (safe with BOM / multi-byte chars)."""
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def parse(self, file_path: Path, repo_root: Path | None = None) -> ParseResult:
        try:
            source_bytes = file_path.read_bytes()
        except Exception as e:
            return self._err(file_path, f"read_error: {e}")

        imports: List[str] = []
        classes: List[str] = []
        functions: List[str] = []

        try:
            parser = self._ts.get_parser("c_sharp")
            tree = parser.parse(source_bytes)
            root = tree.root_node

            stack = [root]
            while stack:
                node = stack.pop()

                # -------- USING DIRECTIVES --------
                if node.type == "using_directive":
                    name_node = node.child_by_field_name("name")
                    if not name_node:
                        for child in node.children:
                            if child.type in {
                                "qualified_name",
                                "identifier",
                                "alias_qualified_name",
                            }:
                                name_node = child
                                break
                    if name_node:
                        imports.append(self._text(source_bytes, name_node))

                # -------- CLASSES / STRUCTS / INTERFACES / RECORDS --------
                elif node.type in {
                    "class_declaration",
                    "struct_declaration",
                    "interface_declaration",
                    "record_declaration",
                }:
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        classes.append(self._text(source_bytes, name_node))

                # -------- METHODS --------
                elif node.type == "method_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        functions.append(self._text(source_bytes, name_node))

                # -------- CONSTRUCTORS --------
                elif node.type == "constructor_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        functions.append(self._text(source_bytes, name_node))

                stack.extend(reversed(node.children))

        except Exception as e:
            return self._err(file_path, f"parse_error: {e}")

        return {
            "file": str(file_path),
            "language": "C#",
            "imports": list(dict.fromkeys(imports)),
            "classes": classes,
            "functions": functions,
            "error": None,
        }
