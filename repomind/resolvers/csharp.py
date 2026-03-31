from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseResolver


class CSharpResolver(BaseResolver):
    """
    C# (using) resolution strategy.
    """

    def __init__(self):
        self._cs_filename_index: Dict[str, str] = {}

    @property
    def language(self) -> str:
        return "C#"

    def prepare(
        self,
        repo_root: Path,
        file_index: Dict[str, str],
        parsed_files: List[Dict[str, Any]],
    ) -> None:
        """
        Maps bare C# filename (e.g. 'Foo.cs') -> resolved path.
        """
        self._cs_filename_index = {}
        for item in parsed_files:
            if item.get("language") != "C#":
                continue
            path = Path(item["file"]).resolve()
            name = path.name
            if name not in self._cs_filename_index:
                self._cs_filename_index[name] = str(path)

    def resolve(
        self,
        current_file: Path,
        repo_root: Path,
        imp: str,
        file_index: Dict[str, str],
    ) -> Optional[str]:
        if not imp:
            return None

        parts = imp.split(".")

        # Strategy 1: Full namespace path as file
        rel_path = Path(*parts).with_suffix(".cs")
        candidates = [
            repo_root / rel_path,
        ]

        # Strateg 2: Try without leading project name segments (common convention)
        if len(parts) > 1:
            for start in range(1, min(len(parts), 3)):
                sub_parts = parts[start:]
                if sub_parts:
                    candidates.append(repo_root / Path(*sub_parts).with_suffix(".cs"))

        for c in candidates:
            path_res = c.resolve()
            key = str(path_res)
            if key in file_index:
                return file_index[key]
            key2 = str(path_res.with_suffix("").resolve())
            if key2 in file_index:
                return file_index[key2]

        # Strategy 3: Last segment as filename
        class_name = parts[-1] + ".cs"
        if class_name in self._cs_filename_index:
            return self._cs_filename_index[class_name]

        return None
