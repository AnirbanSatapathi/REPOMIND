from __future__ import annotations

from pathlib import Path
from typing import List

from .base import BaseParser, ParseResult
from .treesitter_engine import TreeSitterEngine


class JavaScriptParser(BaseParser):
    language = "JavaScript"

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

        ext = file_path.suffix.lower()
        ts_language = "javascript"
        language_label = "JavaScript"

        if ext in (".ts", ".tsx"):
            ts_language = "typescript"
            language_label = "TypeScript"

        imports: List[str] = []
        classes: List[str] = []
        functions: List[str] = []

        try:
            parser = self._ts.get_parser(ts_language)
            tree = parser.parse(source_bytes)
            root = tree.root_node

            stack = [root]

            while stack:
                node = stack.pop()

                # --------------------
                # IMPORTS
                # --------------------
                if node.type == "import_statement":
                    source_node = node.child_by_field_name("source")
                    if source_node:
                        val = self._text(source_bytes, source_node).strip("'\"")
                        if not val.endswith(".css"):  # filter junk
                            imports.append(val)

                elif node.type == "export_statement":
                    source_node = node.child_by_field_name("source")
                    if source_node:
                        val = self._text(source_bytes, source_node).strip("'\"")
                        imports.append(val)

                # require()
                elif node.type == "call_expression":
                    fn = node.child_by_field_name("function")

                    # require("x")
                    if fn and fn.type == "identifier":
                        fn_name = self._text(source_bytes, fn)
                        if fn_name == "require":
                            args = node.child_by_field_name("arguments")
                            if args:
                                for arg in args.children:
                                    if arg.type == "string":
                                        imports.append(
                                            self._text(source_bytes, arg).strip("'\"")
                                        )

                    # dynamic import("x")
                    if fn and fn.type == "import":
                        args = node.child_by_field_name("arguments")
                        if args:
                            for arg in args.children:
                                if arg.type == "string":
                                    imports.append(
                                        self._text(source_bytes, arg).strip("'\"")
                                    )

                # --------------------
                # CLASSES
                # --------------------
                elif node.type == "class_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        classes.append(self._text(source_bytes, name_node))

                # --------------------
                # FUNCTIONS
                # --------------------
                elif node.type == "function_declaration":
                    name_node = node.child_by_field_name("name")
                    if name_node:
                        functions.append(self._text(source_bytes, name_node))

                # const fn = () => {}
                elif node.type == "variable_declarator":
                    name_node = node.child_by_field_name("name")
                    value_node = node.child_by_field_name("value")

                    if name_node and value_node:
                        if value_node.type in ("arrow_function", "function"):
                            functions.append(
                                self._text(source_bytes, name_node)
                            )

                stack.extend(reversed(node.children))

        except Exception as e:
            return self._err(file_path, f"parse_error: {e}")

        return {
            "file": str(file_path),
            "language": language_label,
            "imports": list(dict.fromkeys(imports)),
            "classes": classes,
            "functions": functions,
            "error": None,
        }