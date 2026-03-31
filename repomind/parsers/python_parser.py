from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List

from .base import BaseParser, ParseResult


class PythonParser(BaseParser):
    language = "Python"

    _module_name_re = re.compile(r"^[a-z_][a-z0-9_]*$")

    def _should_expand_imported_name(self, name: str) -> bool:
        # Only expand names that look like module/file names (avoid classes/constants).
        return bool(self._module_name_re.match(name))

    def parse(self, file_path: Path, repo_root: Path | None = None) -> ParseResult:
        try:
            source = file_path.read_text(encoding="utf-8-sig")
        except Exception as e:
            return self._err(file_path, f"read_error: {e}")

        try:
            tree = ast.parse(source)
        except Exception as e:
            return self._err(file_path, f"syntax_error: {e}")

        imports: List[str] = []
        classes: List[str] = []
        functions: List[str] = []

        for node in ast.walk(tree):
            # import x
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name:
                        imports.append(n.name)

            # from x import y
            elif isinstance(node, ast.ImportFrom):
                prefix = "." * node.level if node.level else ""

                if node.module:
                    imports.append(prefix + node.module)

                    # Expand `from pkg import mod` into `pkg.mod` when it looks module-like.
                    if not node.level:
                        for alias in node.names:
                            if alias.name and alias.name != "*" and self._should_expand_imported_name(alias.name):
                                imports.append(f"{node.module}.{alias.name}")
                elif node.level:
                    # from . import x  -> ".x"
                    for alias in node.names:
                        if alias.name and alias.name != "*":
                            imports.append(prefix + alias.name)

            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)

        return self._ok(
            file_path,
            imports=list(dict.fromkeys(imports)),
            classes=classes,
            functions=functions,
        )
