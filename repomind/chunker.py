"""
Logical code chunker that splits source files into function/class-level units
while preserving metadata for embedding and retrieval.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class CodeChunk:
    """A single logical chunk of code with metadata."""

    def __init__(
        self,
        text: str,
        file_path: str,
        chunk_type: str,
        name: str,
        start_line: int,
        end_line: int,
        language: str,
    ):
        self.text = text
        self.file_path = file_path
        self.chunk_type = chunk_type  # 'function', 'class', 'module'
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.language = language

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "file_path": self.file_path,
            "chunk_type": self.chunk_type,
            "name": self.name,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "language": self.language,
        }

    def __repr__(self) -> str:
        return f"CodeChunk({self.chunk_type}={self.name} @ {self.file_path}:{self.start_line})"


# Tree-sitter language names and their function/class node types
_TS_CHUNK_CONFIG: Dict[str, Dict[str, Any]] = {
    "JavaScript": {
        "ts_lang": "javascript",
        "function_nodes": {
            "function_declaration",
            "method_definition",
            "arrow_function",
            "generator_function_declaration",
        },
        "class_nodes": {"class_declaration"},
    },
    "TypeScript": {
        "ts_lang": "typescript",
        "function_nodes": {
            "function_declaration",
            "method_definition",
            "arrow_function",
            "generator_function_declaration",
        },
        "class_nodes": {"class_declaration", "interface_declaration"},
    },
    "Go": {
        "ts_lang": "go",
        "function_nodes": {"function_declaration", "method_declaration"},
        "class_nodes": {"type_declaration"},
    },
    "Java": {
        "ts_lang": "java",
        "function_nodes": {"method_declaration", "constructor_declaration"},
        "class_nodes": {"class_declaration", "interface_declaration", "enum_declaration"},
    },
    "C": {
        "ts_lang": "c",
        "function_nodes": {"function_definition"},
        "class_nodes": {"struct_specifier", "enum_specifier"},
    },
    "C++": {
        "ts_lang": "cpp",
        "function_nodes": {"function_definition"},
        "class_nodes": {"class_specifier", "struct_specifier", "enum_specifier"},
    },
    "C#": {
        "ts_lang": "c_sharp",
        "function_nodes": {"method_declaration", "constructor_declaration"},
        "class_nodes": {"class_declaration", "interface_declaration", "struct_declaration"},
    },
    "Rust": {
        "ts_lang": "rust",
        "function_nodes": {"function_item"},
        "class_nodes": {"struct_item", "enum_item", "impl_item", "trait_item"},
    },
}


class Chunker:
    """
    Splits source files into logical chunks (functions, classes, module-level).
    Uses Python AST for Python, Tree-sitter for other supported languages,
    and line-based fallback for unsupported languages.
    """

    PYTHON_FUNC_RE = re.compile(
        r"^(\s*)(?:async\s+)?def\s+(\w+)\s*\("
    )
    PYTHON_CLASS_RE = re.compile(
        r"^(\s*)class\s+(\w+)\s*[\(:]"
    )

    def __init__(self, max_chunk_lines: int = 100):
        self.max_chunk_lines = max_chunk_lines

    def chunk_file(self, file_path: Path, language: str) -> List[CodeChunk]:
        """
        Chunk a single file into logical units.
        """
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            raise RuntimeError(f"Failed to read {file_path}: {e}")

        if language == "Python":
            return self._chunk_python(file_path, source)
        elif language in _TS_CHUNK_CONFIG:
            try:
                return self._chunk_treesitter(file_path, source, language)
            except Exception:
                return self._chunk_generic(file_path, source, language)
        else:
            return self._chunk_generic(file_path, source, language)

    def _chunk_python(self, file_path: Path, source: str) -> List[CodeChunk]:
        """Chunk Python files using the AST."""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            # Fallback to line-based chunking
            return self._chunk_generic(file_path, source, "Python")

        chunks: List[CodeChunk] = []
        lines = source.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not getattr(node, "body", None):
                    continue
                start = node.lineno - 1  # 0-indexed
                end = node.end_lineno or start
                text = "\n".join(lines[start:end])
                if len(text.strip()) < 3:
                    continue
                chunks.append(CodeChunk(
                    text=text,
                    file_path=str(file_path),
                    chunk_type="function",
                    name=node.name,
                    start_line=start + 1,
                    end_line=end,
                    language="Python",
                ))

            elif isinstance(node, ast.ClassDef):
                if not getattr(node, "body", None):
                    continue
                start = node.lineno - 1
                end = node.end_lineno or start
                text = "\n".join(lines[start:end])
                if len(text.strip()) < 3:
                    continue
                chunks.append(CodeChunk(
                    text=text,
                    file_path=str(file_path),
                    chunk_type="class",
                    name=node.name,
                    start_line=start + 1,
                    end_line=end,
                    language="Python",
                ))

        # If no chunks found, add the whole file as a module chunk
        if not chunks:
            chunks.append(CodeChunk(
                text=source,
                file_path=str(file_path),
                chunk_type="module",
                name=file_path.stem,
                start_line=1,
                end_line=len(lines),
                language="Python",
            ))

        return chunks

    def _chunk_treesitter(
        self, file_path: Path, source: str, language: str
    ) -> List[CodeChunk]:
        """
        Chunk non-Python files using Tree-sitter AST.
        Extracts functions, classes, structs, and methods as individual chunks.
        """
        from repomind.parsers.treesitter_engine import TreeSitterEngine

        config = _TS_CHUNK_CONFIG[language]
        ts_engine = TreeSitterEngine()
        source_bytes = source.encode("utf-8")
        parser = ts_engine.get_parser(config["ts_lang"])
        tree = parser.parse(source_bytes)
        root = tree.root_node
        lines = source.splitlines()

        chunks: List[CodeChunk] = []
        func_nodes = config["function_nodes"]
        class_nodes = config["class_nodes"]

        # Walk only top-level and second-level children (methods inside classes)
        for child in root.children:
            if child.type in func_nodes:
                name = self._ts_get_name(source_bytes, child, language)
                start = child.start_point[0]  # 0-indexed line
                end = child.end_point[0] + 1
                text = "\n".join(lines[start:end])
                if text.strip():
                    chunks.append(CodeChunk(
                        text=text,
                        file_path=str(file_path),
                        chunk_type="function",
                        name=name,
                        start_line=start + 1,
                        end_line=end,
                        language=language,
                    ))

            elif child.type in class_nodes:
                name = self._ts_get_name(source_bytes, child, language)
                start = child.start_point[0]
                end = child.end_point[0] + 1
                text = "\n".join(lines[start:end])
                if text.strip():
                    chunks.append(CodeChunk(
                        text=text,
                        file_path=str(file_path),
                        chunk_type="class",
                        name=name,
                        start_line=start + 1,
                        end_line=end,
                        language=language,
                    ))

                # Also extract methods inside the class
                for sub in child.children:
                    if sub.type in func_nodes:
                        method_name = self._ts_get_name(source_bytes, sub, language)
                        m_start = sub.start_point[0]
                        m_end = sub.end_point[0] + 1
                        m_text = "\n".join(lines[m_start:m_end])
                        if m_text.strip():
                            chunks.append(CodeChunk(
                                text=m_text,
                                file_path=str(file_path),
                                chunk_type="function",
                                name=f"{name}.{method_name}",
                                start_line=m_start + 1,
                                end_line=m_end,
                                language=language,
                            ))

        # If Tree-sitter didn't find any chunks, fall back to module-level
        if not chunks:
            if source.strip():
                chunks.append(CodeChunk(
                    text=source,
                    file_path=str(file_path),
                    chunk_type="module",
                    name=file_path.stem,
                    start_line=1,
                    end_line=len(lines),
                    language=language,
                ))

        return chunks

    def _ts_get_name(self, source_bytes: bytes, node, language: str) -> str:
        """Extract the name from a Tree-sitter AST node."""
        # Try common field names
        for field in ("name", "declarator"):
            name_node = node.child_by_field_name(field)
            if name_node:
                name_text = source_bytes[name_node.start_byte:name_node.end_byte].decode(
                    "utf-8", errors="replace"
                )
                # For C/C++ declarators like "int foo()" the declarator may be
                # a function_declarator; extract the inner identifier
                if name_node.type in ("function_declarator",):
                    inner = name_node.child_by_field_name("declarator")
                    if inner:
                        return source_bytes[inner.start_byte:inner.end_byte].decode(
                            "utf-8", errors="replace"
                        )
                return name_text

        # Fallback: first identifier child
        for child in node.children:
            if child.type in ("identifier", "type_identifier"):
                return source_bytes[child.start_byte:child.end_byte].decode(
                    "utf-8", errors="replace"
                )

        # For Go type_declaration: find the type_spec → name
        if node.type == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    name_node = child.child_by_field_name("name")
                    if name_node:
                        return source_bytes[name_node.start_byte:name_node.end_byte].decode(
                            "utf-8", errors="replace"
                        )

        return f"anonymous_{node.start_point[0]}"

    def _chunk_generic(self, file_path: Path, source: str, language: str) -> List[CodeChunk]:
        """
        Generic line-based chunking for non-Python languages.
        Splits by top-level functions/classes detected via simple regex patterns,
        or falls back to line-count chunks.
        """
        lines = source.splitlines()
        if not lines:
            return []

        chunks: List[CodeChunk] = []
        chunk_start = 0
        chunk_lines: List[str] = []

        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*", "```")):
                chunk_lines.append(line)
                continue

            chunk_lines.append(line)

            # Flush chunk when exceeding max lines
            if len(chunk_lines) >= self.max_chunk_lines:
                text = "\n".join(chunk_lines)
                if text.strip():
                    chunks.append(CodeChunk(
                        text=text,
                        file_path=str(file_path),
                        chunk_type="module",
                        name=f"{file_path.stem}_part{len(chunks)+1}",
                        start_line=chunk_start + 1,
                        end_line=i + 1,
                        language=language,
                    ))
                chunk_lines = []
                chunk_start = i + 1

        # Flush remaining lines
        if chunk_lines:
            text = "\n".join(chunk_lines)
            if text.strip():
                chunks.append(CodeChunk(
                    text=text,
                    file_path=str(file_path),
                    chunk_type="module",
                    name=f"{file_path.stem}_part{len(chunks)+1}",
                    start_line=chunk_start + 1,
                    end_line=len(lines),
                    language=language,
                ))

        return chunks

    def chunk_repo(
        self,
        parsed_files: List[Dict[str, Any]],
    ) -> List[CodeChunk]:
        """Chunk all parsed files in a repository scan result."""
        all_chunks: List[CodeChunk] = []
        for item in parsed_files:
            file_path = Path(item["file"])
            language = item.get("language", "Unknown")
            if language == "Unknown" or item.get("error"):
                continue
            try:
                chunks = self.chunk_file(file_path, language)
                all_chunks.extend(chunks)
            except Exception:
                continue
        return all_chunks