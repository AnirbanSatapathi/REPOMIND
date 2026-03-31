from __future__ import annotations

from pathlib import Path
from typing import List

from .base import BaseParser, ParseResult
from .treesitter_engine import TreeSitterEngine


class RustParser(BaseParser):
    language = "Rust"

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
            parser = self._ts.get_parser("rust")
            tree = parser.parse(source_bytes)
            root = tree.root_node

            stack = [root]
            while stack:
                node = stack.pop()

                # -------- USE DECLARATIONS --------
                if node.type == "use_declaration":
                    arg_node = node.child_by_field_name("argument")
                    if arg_node:
                        use_path = self._text(source_bytes, arg_node)
                        imports.append(use_path)

                # -------- MOD DECLARATIONS --------
                elif node.type == "mod_item":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        mod_name = self._text(source_bytes, name_node)
                        has_body = node.child_by_field_name("body") is not None
                        if not has_body:
                            imports.append(mod_name)

                # -------- EXTERN CRATE --------
                elif node.type == "extern_crate_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        imports.append(self._text(source_bytes, name_node))

                # -------- STRUCTS / ENUMS / TRAITS (class-like) --------
                elif node.type in {
                    "struct_item",
                    "enum_item",
                    "trait_item",
                    "impl_item",
                }:
                    name_node = node.child_by_field_name("name")
                    if not name_node and node.type == "impl_item":
                        name_node = node.child_by_field_name("type")
                    if name_node:
                        classes.append(self._text(source_bytes, name_node))

                # -------- FUNCTIONS --------
                elif node.type == "function_item":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        functions.append(self._text(source_bytes, name_node))

                stack.extend(reversed(node.children))

        except Exception as e:
            return self._err(file_path, f"parse_error: {e}")

        return {
            "file": str(file_path),
            "language": "Rust",
            "imports": list(dict.fromkeys(imports)),
            "classes": classes,
            "functions": functions,
            "error": None,
        }
