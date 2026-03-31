from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from .base import BaseResolver


class RustResolver(BaseResolver):
    """
    Rust import resolution strategy.
    """

    @property
    def language(self) -> str:
        return "Rust"

    def resolve(
        self,
        current_file: Path,
        repo_root: Path,
        imp: str,
        file_index: Dict[str, str],
    ) -> Optional[str]:
        if not imp:
            return None

        # -------- `mod foo;` (plain module name, no ::) --------
        if "::" not in imp and not imp.startswith("self") and not imp.startswith("super"):
            candidates = [
                current_file.parent / f"{imp}.rs",
                current_file.parent / imp / "mod.rs",
            ]
            for c in candidates:
                key = str(c.resolve())
                if key in file_index:
                    return file_index[key]
            return None

        # -------- Parse use path --------
        segments = imp.split("::")

        # Strip trailing wildcard or braced groups
        if segments and (segments[-1] == "*" or segments[-1].startswith("{")):
            segments = segments[:-1]

        if not segments:
            return None

        root_segment = segments[0].strip()

        # -------- crate:: --------
        if root_segment == "crate":
            path_parts = segments[1:]
            if not path_parts:
                return None

            # Find crate root: try src/ directory
            crate_root = repo_root / "src"
            if not crate_root.exists():
                crate_root = repo_root

            return self._resolve_rust_path(crate_root, path_parts, file_index)

        # -------- super:: --------
        elif root_segment == "super":
            base = current_file.parent.parent
            path_parts = segments[1:]
            if not path_parts:
                return None
            return self._resolve_rust_path(base, path_parts, file_index)

        # -------- self:: --------
        elif root_segment == "self":
            base = current_file.parent
            path_parts = segments[1:]
            if not path_parts:
                return None
            return self._resolve_rust_path(base, path_parts, file_index)

        # -------- external crate (std, serde, etc.) → skip --------
        return None

    def _resolve_rust_path(
        self,
        base: Path,
        path_parts: List[str],
        file_index: Dict[str, str],
    ) -> str | None:
        """Try to resolve a Rust module path from a base directory."""
        path_parts = [p.strip() for p in path_parts if p.strip()]
        if not path_parts:
            return None

        # Build filesystem path from segments
        target = base
        for part in path_parts:
            target = target / part

        candidates = [
            target.with_suffix(".rs"),
            target / "mod.rs",
        ]

        for c in candidates:
            path_res = c.resolve()
            key = str(path_res)
            if key in file_index:
                return file_index[key]

        # Try resolving just the first N-1 segments (last might be a symbol, not module)
        if len(path_parts) > 1:
            target2 = base
            for part in path_parts[:-1]:
                target2 = target2 / part

            candidates2 = [
                target2.with_suffix(".rs"),
                target2 / "mod.rs",
            ]

            for c in candidates2:
                path_res2 = c.resolve()
                key = str(path_res2)
                if key in file_index:
                    return file_index[key]

        return None
