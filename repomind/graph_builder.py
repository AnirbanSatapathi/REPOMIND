from pathlib import Path
from typing import List, Dict, Any
import os

from repomind.resolvers import (
    CFamilyResolver,
    CSharpResolver,
    JavaResolver,
    JSResolver,
    PythonResolver,
    ResolverRegistry,
    RustResolver,
)


class GraphBuilder:
    """
    Builds a dependency graph from parsed files by delegating language-specific 
    import resolution to the ResolverRegistry.
    """

    def __init__(self, registry: ResolverRegistry | None = None):
        self.registry = registry or self._build_default_registry()

    def _build_default_registry(self) -> ResolverRegistry:
        registry = ResolverRegistry()
        registry.register_resolver("Python", PythonResolver())
        registry.register_resolver("JavaScript", JSResolver("JavaScript"))
        registry.register_resolver("TypeScript", JSResolver("TypeScript"))
        registry.register_resolver("C", CFamilyResolver("C"))
        registry.register_resolver("C++", CFamilyResolver("C++"))
        registry.register_resolver("Java", JavaResolver())
        registry.register_resolver("C#", CSharpResolver())
        registry.register_resolver("Rust", RustResolver())
        return registry

    # ---------------- ROOT ----------------
    def _get_repo_root(self, parsed_files: List[Dict[str, Any]]) -> Path:
        if not parsed_files:
            raise ValueError("empty_parsed_files")

        paths = [Path(item["file"]).resolve() for item in parsed_files]
        return Path(os.path.commonpath(paths))

    # ---------------- FILE INDEX ----------------
    def _build_file_index(self, parsed_files: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Builds a map of file paths and stems to their full path.
        Used by resolvers to quickly check existence.
        """
        index: Dict[str, str] = {}

        for item in parsed_files:
            path = Path(item["file"]).resolve()
            resolved = str(path)

            index[resolved] = resolved
            index[str(path.with_suffix(""))] = resolved

            # JS index resolution (e.g. index.js maps to parent directory)
            if path.name.startswith("index."):
                index[str(path.parent.resolve())] = resolved

        return index

    # ---------------- MAIN ----------------
    def build_graph(self, parsed_files: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        if not parsed_files:
            return {}

        graph: Dict[str, set] = {}

        repo_root = self._get_repo_root(parsed_files)
        file_index = self._build_file_index(parsed_files)

        # Prepare all resolvers (build local filename indices, etc.)
        self.registry.prepare_all(repo_root, file_index, parsed_files)

        for item in parsed_files:
            file_path_obj = Path(item["file"]).resolve()
            file_path = str(file_path_obj)

            language = item.get("language", "")
            imports = item.get("imports", [])

            graph[file_path] = set()
            resolver = self.registry.get_resolver(language)

            if not resolver:
                continue

            for imp in imports:
                if not imp:
                    continue

                resolved = resolver.resolve(file_path_obj, repo_root, imp, file_index)

                # Avoid self-loops and only add if resolution succeeded
                if resolved and resolved != file_path:
                    graph[file_path].add(resolved)

        return {k: list(v) for k, v in graph.items()}
