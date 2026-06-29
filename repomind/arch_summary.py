"""
Architecture-level summary generator.
Produces high-level textual descriptions of the codebase structure.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Set


def _find_repo_root(paths: List[Path]) -> Path:
    """
    Find the common root directory from a list of file paths.
    """
    if not paths:
        return Path(".")
    common = os.path.commonpath([str(p.resolve()) for p in paths])
    common_path = Path(common)
    if not common_path.is_dir():
        common_path = common_path.parent
    return common_path


def _to_relative(file_path: str, repo_root: Path) -> str:
    """Convert an absolute file path to a repo-relative path string."""
    try:
        return str(Path(file_path).resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return Path(file_path).name


def generate_architecture_summary(
    parsed_files: List[Dict[str, Any]],
    dependency_graph: Dict[str, List[str]],
    call_graph: Dict[str, List[str]],
) -> str:
    """
    Generate a high-level architecture summary from parsed data,
    dependency graph, and call graph.
    """
    lines: List[str] = []
    lines.append("# Architecture Summary")
    lines.append("")

    # --- Module Overview ---
    lines.append("## Module Overview")
    lines.append("")

    # Group files by top-level directory (relative to common root)
    # Find common root from all file paths
    all_paths = [Path(item["file"]) for item in parsed_files if not item.get("error")]
    if not all_paths:
        return "No valid parsed files."

    # Use first file's parent chain to determine repo root heuristically
    repo_root = _find_repo_root(all_paths)

    dirs: Dict[str, List[str]] = {}
    for item in parsed_files:
        if item.get("error"):
            continue
        fp = Path(item["file"])
        try:
            rel = fp.resolve().relative_to(repo_root.resolve())
            top_dir = rel.parts[0] if len(rel.parts) > 1 else "."
        except ValueError:
            top_dir = "."
        if top_dir not in dirs:
            dirs[top_dir] = []
        dirs[top_dir].append(item["file"])

    for dir_name, files in sorted(dirs.items()):
        lines.append(f"### `{dir_name}/` ({len(files)} files)")
        # Count types in this directory
        funcs = 0
        classes = 0
        for item in parsed_files:
            if item.get("error"):
                continue
            if item["file"] in files:
                funcs += len(item.get("functions", []))
                classes += len(item.get("classes", []))
        lines.append(f"- Functions: {funcs}")
        lines.append(f"- Classes: {classes}")
        lines.append("")

    # --- Dependency Analysis ---
    lines.append("## Dependency Analysis")
    lines.append("")

    if dependency_graph:
        # Find most depended-upon files (hub nodes)
        dep_count: Dict[str, int] = {}
        for source, targets in dependency_graph.items():
            for target in targets:
                dep_count[target] = dep_count.get(target, 0) + 1

        top_deps = sorted(dep_count.items(), key=lambda x: x[1], reverse=True)[:10]
        if top_deps:
            lines.append("### Most Depended-Upon Files (Hubs)")
            lines.append("")
            for fp, count in top_deps:
                rel_path = _to_relative(fp, repo_root)
                lines.append(f"- `{rel_path}` — imported by {count} files")
            lines.append("")

        # Find files with most dependencies
        top_importers = sorted(
            dependency_graph.items(), key=lambda x: len(x[1]), reverse=True
        )[:10]
        if top_importers:
            lines.append("### Files with Most Dependencies")
            lines.append("")
            for fp, deps in top_importers:
                rel_path = _to_relative(fp, repo_root)
                lines.append(f"- `{rel_path}` → {len(deps)} dependencies")
            lines.append("")

    # --- Call Graph Analysis ---
    lines.append("## Call Graph Analysis")
    lines.append("")

    if call_graph:
        total_calls = sum(len(callees) for callees in call_graph.values())
        lines.append(f"- Total call edges: {total_calls}")
        lines.append(f"- Files with function calls: {len(call_graph)}")
        lines.append("")

        # Top callers
        top_callers = sorted(
            call_graph.items(), key=lambda x: len(x[1]), reverse=True
        )[:5]
        if top_callers:
            lines.append("### Top Callers (Files)")
            lines.append("")
            for fp, callees in top_callers:
                lines.append(f"- `{Path(fp).name}` → {len(callees)} calls")
            lines.append("")
    else:
        lines.append("No call graph data available.")
        lines.append("")

    # --- Language Breakdown ---
    lines.append("## Language Breakdown")
    lines.append("")

    lang_counts: Dict[str, int] = {}
    for item in parsed_files:
        lang = item.get("language", "Unknown")
        if lang != "Unknown" and not item.get("error"):
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

    for lang, count in sorted(lang_counts.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- **{lang}**: {count} files")

    lines.append("")
    lines.append("---")
    lines.append("*Generated by RepoMind*")

    return "\n".join(lines)