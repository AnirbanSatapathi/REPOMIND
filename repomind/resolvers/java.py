from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseResolver


class JavaResolver(BaseResolver):
    """
    Java import resolution strategy.
    """

    def __init__(self):
        self._java_filename_index: Dict[str, str] = {}

    @property
    def language(self) -> str:
        return "Java"

    def prepare(
        self,
        repo_root: Path,
        file_index: Dict[str, str],
        parsed_files: List[Dict[str, Any]],
    ) -> None:
        """
        Maps bare Java filename (e.g. 'Foo.java') -> resolved path.
        """
        self._java_filename_index = {}
        for _, resolved in file_index.items():
            if resolved.endswith(".java"):
                name = Path(resolved).name
                if name not in self._java_filename_index:
                    self._java_filename_index[name] = resolved

    def resolve(
        self,
        current_file: Path,
        repo_root: Path,
        imp: str,
        file_index: Dict[str, str],
    ) -> Optional[str]:
        if not imp:
            return None

        # Strip wildcard imports: `com.example.util.*` -> `com.example.util`
        if imp.endswith(".*"):
            imp = imp[:-2]

        parts = imp.split(".")
        # The last part is typically the class name
        rel_path = Path(*parts).with_suffix(".java")

        # Try various source roots
        candidates = [
            repo_root / rel_path,
        ]

        # Common Java source root patterns
        for src_root in ("src/main/java", "src", "app/src/main/java", "src/main", "app/src"):
            candidates.append(repo_root / src_root / rel_path)

        for c in candidates:
            path_res = c.resolve()
            key = str(path_res)
            if key in file_index:
                return file_index[key]

            # In some cases the index holds the stem path
            key2 = str(path_res.with_suffix(""))
            if key2 in file_index:
                return file_index[key2]

        # Filename fallback: ClassName.java
        class_name = parts[-1] + ".java"
        if class_name in self._java_filename_index:
            return self._java_filename_index[class_name]

        return None
