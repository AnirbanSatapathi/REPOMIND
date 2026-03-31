from __future__ import annotations

from pathlib import Path
from typing import List


def _dedupe(items: List[str]) -> List[str]:
    return list(dict.fromkeys([x for x in items if x]))


def _path_to_module(path: Path, repo_root: Path) -> str | None:
    try:
        rel = path.resolve().relative_to(repo_root.resolve())
    except Exception:
        return None
    parts = rel.with_suffix("").parts
    if not parts:
        return None
    return ".".join(parts)


def normalize_python_imports(
    imports: List[str],
    *,
    file_path: Path,
    repo_root: Path | None,
) -> List[str]:

    if not repo_root:
        return _dedupe(imports)

    current_module = _path_to_module(file_path, repo_root)
    if not current_module:
        return _dedupe(imports)

    current_parts = current_module.split(".")
    normalized: List[str] = []

    for imp in imports:
        if not imp:
            continue

        if imp.startswith("."):
            level = len(imp) - len(imp.lstrip("."))
            remainder = imp[level:]

            if level > len(current_parts):
                # invalid relative import → skip
                continue

            base_parts = current_parts[:-level]

            if remainder:
                base_parts += remainder.split(".")

            if base_parts:
                normalized.append(".".join(base_parts))

        else:
            normalized.append(imp)

    return _dedupe(normalized)


_JS_EXTS = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")


def _strip_js_ext(spec: str) -> str:
    for ext in _JS_EXTS:
        if spec.endswith(ext):
            return spec[: -len(ext)]
    return spec


def _resolve_js_relative_spec(spec: str, *, file_path: Path) -> Path:
    # Strip any extension before attempting resolution.
    spec_no_ext = _strip_js_ext(spec)
    candidate = (file_path.parent / spec_no_ext).resolve()

    # Directory import -> index.*
    if candidate.exists() and candidate.is_dir():
        for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            index_path = candidate / f"index{ext}"
            if index_path.exists():
                return index_path
        return candidate

    # Exact file path
    if candidate.exists() and candidate.is_file():
        return candidate

    # Extension fallback
    for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
        p = Path(str(candidate) + ext)
        if p.exists():
            return p.resolve()

    return candidate


def normalize_js_imports(imports: List[str], *, file_path: Path, repo_root: Path | None) -> List[str]:
    normalized: List[str] = []

    for imp in imports:
        if not imp:
            continue

        # Node-style relative
        if imp.startswith("./") or imp.startswith("../") or imp == "." or imp == "..":
            resolved = _resolve_js_relative_spec(imp, file_path=file_path)
            if resolved.suffix:
                resolved = resolved.with_suffix("")
            normalized.append(str(resolved.resolve()))
            continue

        # Strip common JS extensions for non-relative specifiers too.
        normalized.append(_strip_js_ext(imp))

    return _dedupe(normalized)


def normalize_java_imports(imports: List[str]) -> List[str]:
    normalized: List[str] = []
    for imp in imports:
        if not imp:
            continue
        s = imp.strip()
        if s.startswith("import "):
            s = s[len("import ") :].strip()
        if s.endswith(";"):
            s = s[:-1].strip()
        normalized.append(s)
    return _dedupe(normalized)
