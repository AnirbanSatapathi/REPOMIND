"""
Call graph extraction: traces function-to-function calls within and across files.
Supports Python via AST and other languages via Tree-sitter.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from repomind.parsers.treesitter_engine import TreeSitterEngine


class CallGraphExtractor:
    """
    Extracts function/method call relationships from source code.
    Uses AST for Python, Tree-sitter for JS/TS/C/C++/Java/C#/Rust/Go.
    """

    # Languages that use Tree-sitter for call extraction
    TS_LANGUAGES = {
        "JavaScript": "javascript",
        "TypeScript": "typescript",
        "C": "c",
        "C++": "cpp",
        "Java": "java",
        "C#": "c_sharp",
        "Rust": "rust",
        "Go": "go",
    }

    def __init__(self):
        self._builtins: Set[str] = set(dir(__builtins__)) if hasattr(__builtins__, '__dict__') else set()
        self._ts_engine = TreeSitterEngine()

    def extract_call_graph(self, parsed_files: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Extract function-to-function call edges from parsed files.
        Returns a dict: caller_full_path -> [callee_full_path, ...]
        """
        call_graph: Dict[str, set] = {}
        all_files_data: Dict[str, Dict[str, Any]] = {item["file"]: item for item in parsed_files if not item.get("error")}

        for item in parsed_files:
            if item.get("error"):
                continue

            fp = item["file"]
            lang = item.get("language", "")
            file_path = Path(fp)

            if lang == "Python":
                edges = self._extract_python_calls(file_path, item, all_files_data)
            elif lang in self.TS_LANGUAGES:
                edges = self._extract_ts_calls(file_path, lang, item, all_files_data)
            else:
                continue

            if edges:
                call_graph[str(file_path.resolve())] = sorted(edges)

        return call_graph

    def _get_local_symbols(self, item: Dict[str, Any]) -> Set[str]:
        """Get all local symbol names from a parsed item."""
        return set(item.get("functions", [])) | set(item.get("classes", []))

    def _resolve_callee(
        self,
        callee: str,
        current_fp: str,
        all_files_data: Dict[str, Dict[str, Any]],
    ) -> Set[str]:
        """Resolve a callee name to (file_path::name) entries."""
        results: Set[str] = set()

        # Check current file first
        current_item = all_files_data.get(current_fp)
        if current_item and callee in self._get_local_symbols(current_item):
            results.add(f"{current_fp}::{callee}")
            return results

        # Check all other files
        for fp, item in all_files_data.items():
            if fp == current_fp:
                continue
            if callee in self._get_local_symbols(item):
                results.add(f"{fp}::{callee}")

            # Handle obj.method()
            if "." in callee:
                parts = callee.split(".")
                if len(parts) == 2:
                    class_name, method_name = parts
                    if class_name in set(item.get("classes", [])):
                        results.add((f"{fp}::{callee}"))

        return results

    def _extract_python_calls(
        self,
        file_path: Path,
        item: Dict[str, Any],
        all_files_data: Dict[str, Dict[str, Any]],
    ) -> Set[str]:
        """Extract calls from Python files using AST."""
        fp = item["file"]
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except Exception:
            return set()

        local_names = self._get_local_symbols(item)
        function_bodies: List[ast.FunctionDef] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_bodies.append(node)

        calls_in_file: Dict[str, Set[str]] = {}

        for func_node in function_bodies:
            caller_name = func_node.name
            callees: Set[str] = set()

            for child in ast.walk(func_node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        callee = child.func.id
                        if callee not in self._builtins and callee != caller_name:
                            callees.add(callee)
                    elif isinstance(child.func, ast.Attribute):
                        if isinstance(child.func.value, ast.Name):
                            callees.add(f"{child.func.value.id}.{child.func.attr}")

                elif isinstance(child, ast.Await):
                    if isinstance(child.value, ast.Call):
                        if isinstance(child.value.func, ast.Name):
                            callee = child.value.func.id
                            if callee not in self._builtins and callee != caller_name:
                                callees.add(callee)

            calls_in_file[caller_name] = callees

        edges: Set[str] = set()
        for caller, callees in calls_in_file.items():
            for callee in callees:
                resolved = self._resolve_callee(callee, fp, all_files_data)
                edges.update(resolved)

        return edges

    def _text(self, source_bytes: bytes, node) -> str:
        return source_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def _extract_ts_calls(
        self,
        file_path: Path,
        language: str,
        item: Dict[str, Any],
        all_files_data: Dict[str, Dict[str, Any]],
    ) -> Set[str]:
        """Extract calls from non-Python files using Tree-sitter.

        Handles language-specific call patterns:
        - JS/TS: call_expression → identifier | member_expression
        - Go: call_expression → identifier | selector_expression
        - Java: method_invocation → name | object.name
        - C#: invocation_expression → identifier | member_access_expression
        - Rust: call_expression + macro_invocation
        - C/C++: call_expression → identifier | field_expression
        """
        fp = item["file"]
        ts_lang = self.TS_LANGUAGES[language]

        try:
            source_bytes = file_path.read_bytes()
            parser = self._ts_engine.get_parser(ts_lang)
            tree = parser.parse(source_bytes)
            root = tree.root_node
        except Exception:
            return set()

        # Find all function/method definitions
        function_names: Set[str] = set(item.get("functions", []))

        # Language-specific call node types
        call_types = {"call_expression"}
        if language == "Java":
            call_types.add("method_invocation")
        elif language == "C#":
            call_types.add("invocation_expression")

        edges: Set[str] = set()
        stack = [root]

        while stack:
            node = stack.pop()
            stack.extend(reversed(node.children))

            # --- Rust macro invocations (e.g. println!, vec!) ---
            if language == "Rust" and node.type == "macro_invocation":
                macro_node = node.child_by_field_name("macro")
                if macro_node:
                    callee = self._text(source_bytes, macro_node).rstrip("!")
                    if callee in function_names:
                        resolved = self._resolve_callee(callee, fp, all_files_data)
                        edges.update(resolved)
                continue

            # Skip non-call nodes
            if node.type not in call_types:
                continue

            # --- Java method_invocation ---
            if node.type == "method_invocation":
                name_node = node.child_by_field_name("name")
                if name_node:
                    callee = self._text(source_bytes, name_node)
                    resolved = self._resolve_callee(callee, fp, all_files_data)
                    edges.update(resolved)
                continue

            # --- C# invocation_expression ---
            if node.type == "invocation_expression":
                fn_node = node.children[0] if node.children else None
                if fn_node:
                    if fn_node.type == "identifier":
                        callee = self._text(source_bytes, fn_node)
                        if callee in function_names:
                            resolved = self._resolve_callee(callee, fp, all_files_data)
                            edges.update(resolved)
                    elif fn_node.type == "member_access_expression":
                        name_node = fn_node.child_by_field_name("name")
                        if name_node:
                            callee = self._text(source_bytes, name_node)
                            resolved = self._resolve_callee(callee, fp, all_files_data)
                            edges.update(resolved)
                continue

            # --- call_expression (JS/TS, Go, C/C++, Rust) ---
            fn_node = node.child_by_field_name("function")
            if not fn_node:
                # Some grammars don't use 'function' field —
                # try first child as the callee
                if node.children:
                    fn_node = node.children[0]
                else:
                    continue

            # Simple identifier call: foo()
            if fn_node.type == "identifier":
                callee = self._text(source_bytes, fn_node)
                if callee in function_names:
                    resolved = self._resolve_callee(callee, fp, all_files_data)
                    edges.update(resolved)

            # JS/TS member_expression: obj.foo()
            elif fn_node.type == "member_expression":
                prop_node = fn_node.child_by_field_name("property")
                if prop_node:
                    callee = self._text(source_bytes, prop_node)
                    resolved = self._resolve_callee(callee, fp, all_files_data)
                    edges.update(resolved)

            # C/C++ field_expression: obj.foo() or obj->foo()
            elif fn_node.type == "field_expression":
                method_node = fn_node.child_by_field_name("field")
                if method_node:
                    callee = self._text(source_bytes, method_node)
                    resolved = self._resolve_callee(callee, fp, all_files_data)
                    edges.update(resolved)

            # Go selector_expression: pkg.Func() or obj.Method()
            elif fn_node.type == "selector_expression":
                field_node = fn_node.child_by_field_name("field")
                if field_node:
                    callee = self._text(source_bytes, field_node)
                    resolved = self._resolve_callee(callee, fp, all_files_data)
                    edges.update(resolved)

            # Rust scoped call: foo::bar()
            elif fn_node.type == "scoped_identifier":
                name_node = fn_node.child_by_field_name("name")
                if name_node:
                    callee = self._text(source_bytes, name_node)
                    resolved = self._resolve_callee(callee, fp, all_files_data)
                    edges.update(resolved)

        return edges


def generate_call_graph_summary(call_graph: Dict[str, List[str]]) -> str:
    """Generate a human-readable summary of the call graph."""
    if not call_graph:
        return "## Call Graph Summary\n\nNo function calls detected.\n"

    total_calls = sum(len(callees) for callees in call_graph.values())
    lines = [
        "## Call Graph Summary\n",
        f"Total files with function calls: {len(call_graph)}",
        f"Total function call edges: {total_calls}\n",
    ]

    # Top callers (files with most outgoing calls)
    sorted_files = sorted(call_graph.items(), key=lambda x: len(x[1]), reverse=True)[:15]
    if sorted_files:
        lines.append("### Top Callers\n")
        for fp, callees in sorted_files:
            lines.append(f"- `{Path(fp).name}` → {len(callees)} calls")
        lines.append("")

    # Show sample entries
    lines.append("### Sample Call Edges\n")
    count = 0
    for fp, callees in sorted_files[:5]:
        for callee in callees[:5]:
            caller_name = Path(fp).stem
            callee_name = callee.split("::")[-1] if "::" in callee else callee
            lines.append(f"- `{caller_name}` → `{callee_name}`")
            count += 1
            if count >= 20:
                break
        if count >= 20:
            break
    lines.append("")

    return "\n".join(lines)