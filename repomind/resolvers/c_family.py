from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseResolver


class CFamilyResolver(BaseResolver):
    """
    C/C++ include resolution strategy.
    """

    C_EXT = {".h", ".hpp", ".c", ".cpp", ".cc", ".cxx", ".hh", ".hxx"}

    def __init__(self, language: str = "C"):
        self._language = language
        self._c_filename_index: Dict[str, str] = {}

    @property
    def language(self) -> str:
        return self._language

    def prepare(
        self,
        repo_root: Path,
        file_index: Dict[str, str],
        parsed_files: List[Dict[str, Any]],
    ) -> None:
        """
        Builds a basic mapping of bare filename -> full path for C-family headers/sources.
        """
        self._c_filename_index = {}

        for root, _, files in os.walk(repo_root):
            for f in files:
                suffix = Path(f).suffix.lower()
                if suffix not in self.C_EXT:
                    continue

                p = (Path(root) / f).resolve()
                k = str(p)

                # Store mapping if file is part of our parsed set
                if k in file_index and f not in self._c_filename_index:
                    self._c_filename_index[f] = file_index[k]

    def resolve(
        self,
        current_file: Path,
        repo_root: Path,
        imp: Any,
        file_index: Dict[str, str],
    ) -> Optional[str]:
        if isinstance(imp, dict):
            imp = imp.get("value", "")

        if not isinstance(imp, str):
            return None

        # remove <> or ""
        imp = imp.strip("<>\"")

        # try the full relative path from repo root
        candidate = (repo_root / imp).resolve()

        # direct match
        key = str(candidate)
        if key in file_index:
            return file_index[key]

        # extension fallback
        if not candidate.suffix:
            # We don't know the intended extension, but we can try common ones
            for ext in (".h", ".hpp", ".c", ".cpp"):
                p = candidate.with_suffix(ext)
                k = str(p)
                if k in file_index:
                    return file_index[k]

        # filename fallback (weak but common for C headers)
        name = Path(imp).name
        if name in self._c_filename_index:
            return self._c_filename_index[name]

        return None
