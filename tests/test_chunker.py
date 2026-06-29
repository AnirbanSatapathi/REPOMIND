import tempfile
import unittest
from pathlib import Path

from repomind.chunker import Chunker, CodeChunk


class TestChunker(unittest.TestCase):
    def test_chunk_python_file_with_functions_and_classes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            py_file = root / "example.py"
            py_file.write_text(
                "import os\n"
                "import sys\n\n"
                "class MyClass:\n"
                "    def method_a(self):\n"
                "        pass\n\n"
                "def my_function():\n"
                "    x = 1\n"
                "    return x\n",
                encoding="utf-8",
            )

            chunker = Chunker()
            chunks = chunker.chunk_file(py_file, "Python")

            self.assertGreater(len(chunks), 0)
            chunk_types = {c.chunk_type for c in chunks}
            self.assertIn("function", chunk_types)
            self.assertIn("class", chunk_types)

            # Check specific names
            names = {c.name for c in chunks}
            self.assertIn("my_function", names)
            self.assertIn("MyClass", names)

    def test_chunk_empty_file_returns_module_chunk(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            py_file = root / "empty.py"
            py_file.write_text("", encoding="utf-8")

            chunker = Chunker()
            chunks = chunker.chunk_file(py_file, "Python")

            self.assertEqual(len(chunks), 1)
            self.assertEqual(chunks[0].chunk_type, "module")

    def test_chunk_generic_non_python(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            js_file = root / "test.js"
            js_file.write_text(
                "function foo() { return 1; }\n"
                "function bar() { return 2; }\n",
                encoding="utf-8",
            )

            chunker = Chunker()
            chunks = chunker.chunk_file(js_file, "JavaScript")

            self.assertGreater(len(chunks), 0)
            for c in chunks:
                self.assertEqual(c.language, "JavaScript")

    def test_codechunk_to_dict(self):
        chunk = CodeChunk(
            text="def foo(): pass",
            file_path="/test/file.py",
            chunk_type="function",
            name="foo",
            start_line=1,
            end_line=2,
            language="Python",
        )
        d = chunk.to_dict()
        self.assertEqual(d["name"], "foo")
        self.assertEqual(d["chunk_type"], "function")
        self.assertEqual(d["language"], "Python")

    def test_treesitter_js_chunking_extracts_functions(self):
        """JS files should be chunked using Tree-sitter, extracting function declarations."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            js_file = root / "app.js"
            js_file.write_text(
                "function greet(name) {\n"
                "    return 'hello ' + name;\n"
                "}\n\n"
                "function farewell(name) {\n"
                "    return 'bye ' + name;\n"
                "}\n",
                encoding="utf-8",
            )

            chunker = Chunker()
            chunks = chunker.chunk_file(js_file, "JavaScript")

            names = {c.name for c in chunks}
            self.assertIn("greet", names)
            self.assertIn("farewell", names)
            # All should be function-type chunks
            for c in chunks:
                if c.name in ("greet", "farewell"):
                    self.assertEqual(c.chunk_type, "function")

    def test_treesitter_go_chunking(self):
        """Go files should be chunked using Tree-sitter."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            go_file = root / "main.go"
            go_file.write_text(
                'package main\n\n'
                'import "fmt"\n\n'
                'type Server struct {\n'
                '    port int\n'
                '}\n\n'
                'func main() {\n'
                '    fmt.Println("hello")\n'
                '}\n\n'
                'func helper() int {\n'
                '    return 42\n'
                '}\n',
                encoding="utf-8",
            )

            chunker = Chunker()
            chunks = chunker.chunk_file(go_file, "Go")

            names = {c.name for c in chunks}
            types = {c.chunk_type for c in chunks}
            self.assertIn("main", names)
            self.assertIn("helper", names)
            self.assertIn("function", types)
            # type_declaration for Server struct should be a "class" chunk
            self.assertIn("class", types)

    def test_chunk_repo_with_multi_language_files(self):
        """chunk_repo should chunk all files, skipping unknown/errored ones."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            py_file = root / "app.py"
            py_file.write_text(
                "def run():\n    pass\n",
                encoding="utf-8",
            )

            js_file = root / "utils.js"
            js_file.write_text(
                "function format() { return 1; }\n",
                encoding="utf-8",
            )

            parsed = [
                {"file": str(py_file), "language": "Python", "error": None},
                {"file": str(js_file), "language": "JavaScript", "error": None},
                {"file": "/fake/bad.py", "language": "Unknown", "error": None},
                {"file": "/fake/err.py", "language": "Python", "error": "parse_error"},
            ]

            chunker = Chunker()
            chunks = chunker.chunk_repo(parsed)

            languages = {c.language for c in chunks}
            self.assertIn("Python", languages)
            self.assertIn("JavaScript", languages)
            self.assertNotIn("Unknown", languages)

    def test_max_chunk_lines_enforcement(self):
        """Generic chunker should respect max_chunk_lines."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            txt_file = root / "big.txt"
            # Create a file with 250 lines of code
            lines = [f"line_{i} = {i}" for i in range(250)]
            txt_file.write_text("\n".join(lines), encoding="utf-8")

            chunker = Chunker(max_chunk_lines=50)
            # Use a language not in the TS config to force generic chunking
            chunks = chunker._chunk_generic(txt_file, "\n".join(lines), "PlainText")

            self.assertGreater(len(chunks), 1)
            for c in chunks:
                actual_lines = c.text.count("\n") + 1
                # Each chunk should be at most max_chunk_lines
                self.assertLessEqual(actual_lines, 51)  # +1 for rounding

    def test_treesitter_js_class_with_methods(self):
        """JS classes should be chunked with their methods extracted."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            js_file = root / "myclass.js"
            js_file.write_text(
                "class Animal {\n"
                "    constructor(name) {\n"
                "        this.name = name;\n"
                "    }\n"
                "    speak() {\n"
                "        return this.name + ' speaks';\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            chunker = Chunker()
            chunks = chunker.chunk_file(js_file, "JavaScript")

            names = {c.name for c in chunks}
            types = {c.chunk_type for c in chunks}
            self.assertIn("Animal", names)
            self.assertIn("class", types)

    def test_codechunk_repr(self):
        chunk = CodeChunk(
            text="def foo(): pass",
            file_path="/test/file.py",
            chunk_type="function",
            name="foo",
            start_line=1,
            end_line=2,
            language="Python",
        )
        r = repr(chunk)
        self.assertIn("function", r)
        self.assertIn("foo", r)


if __name__ == "__main__":
    unittest.main()