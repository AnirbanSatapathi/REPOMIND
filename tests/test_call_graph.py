import tempfile
import unittest
from pathlib import Path

from repomind.call_graph import CallGraphExtractor, generate_call_graph_summary


class TestCallGraphExtractor(unittest.TestCase):
    def test_python_call_graph(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            # File A: defines two functions, one calls the other
            a = root / "a.py"
            a.write_text(
                "def helper():\n"
                "    return 42\n\n"
                "def main():\n"
                "    return helper()\n",
                encoding="utf-8",
            )

            parsed = [
                {"file": str(a), "language": "Python", "functions": ["helper", "main"], "classes": [], "error": None},
            ]

            extractor = CallGraphExtractor()
            cg = extractor.extract_call_graph(parsed)

            # main() calls helper() — should be detected
            a_key = str(a.resolve())
            self.assertIn(a_key, cg)
            self.assertTrue(
                any("helper" in callee for callee in cg[a_key]),
                f"Expected helper call in {cg[a_key]}"
            )

    def test_call_graph_summary_generation(self):
        cg = {
            "/repo/a.py": ["/repo/b.py::func_b", "/repo/c.py::func_c"],
            "/repo/b.py": ["/repo/a.py::func_a"],
        }
        summary = generate_call_graph_summary(cg)
        self.assertIn("Total files with function calls: 2", summary)
        self.assertIn("Total function call edges: 3", summary)
        self.assertIn("func_b", summary)

    def test_empty_call_graph_summary(self):
        summary = generate_call_graph_summary({})
        self.assertIn("No function calls detected", summary)

    def test_go_call_graph(self):
        """Test Go call extraction: function calls and selector expressions."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            go_file = root / "main.go"
            go_file.write_text(
                'package main\n'
                'import "fmt"\n'
                'func helper() int {\n'
                '    return 42\n'
                '}\n'
                'func main() {\n'
                '    x := helper()\n'
                '    fmt.Println(x)\n'
                '}\n',
                encoding="utf-8",
            )

            parsed = [
                {
                    "file": str(go_file),
                    "language": "Go",
                    "functions": ["helper", "main"],
                    "classes": [],
                    "imports": ["fmt"],
                    "error": None,
                },
            ]

            extractor = CallGraphExtractor()
            cg = extractor.extract_call_graph(parsed)

            go_key = str(go_file.resolve())
            self.assertIn(go_key, cg)
            self.assertTrue(
                any("helper" in callee for callee in cg[go_key]),
                f"Expected 'helper' call in Go file: {cg.get(go_key, [])}"
            )

    def test_javascript_call_graph(self):
        """Test JS call extraction: function calls and member expressions."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            js_file = root / "app.js"
            js_file.write_text(
                "function greet(name) {\n"
                "    return 'hello ' + name;\n"
                "}\n"
                "function main() {\n"
                "    greet('world');\n"
                "}\n",
                encoding="utf-8",
            )

            parsed = [
                {
                    "file": str(js_file),
                    "language": "JavaScript",
                    "functions": ["greet", "main"],
                    "classes": [],
                    "imports": [],
                    "error": None,
                },
            ]

            extractor = CallGraphExtractor()
            cg = extractor.extract_call_graph(parsed)

            js_key = str(js_file.resolve())
            self.assertIn(js_key, cg)
            self.assertTrue(
                any("greet" in callee for callee in cg[js_key]),
                f"Expected 'greet' call in JS file: {cg.get(js_key, [])}"
            )

    def test_cross_file_python_call_resolution(self):
        """Test that calls across files resolve correctly."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            # File A defines helper
            a = root / "helpers.py"
            a.write_text(
                "def compute():\n"
                "    return 100\n",
                encoding="utf-8",
            )

            # File B calls helper
            b = root / "main.py"
            b.write_text(
                "from helpers import compute\n\n"
                "def run():\n"
                "    return compute()\n",
                encoding="utf-8",
            )

            parsed = [
                {"file": str(a), "language": "Python", "functions": ["compute"], "classes": [], "error": None},
                {"file": str(b), "language": "Python", "functions": ["run"], "classes": [], "error": None},
            ]

            extractor = CallGraphExtractor()
            cg = extractor.extract_call_graph(parsed)

            b_key = str(b.resolve())
            self.assertIn(b_key, cg)
            self.assertTrue(
                any("compute" in callee for callee in cg[b_key]),
                f"Expected cross-file compute call in {cg.get(b_key, [])}"
            )

    def test_error_files_are_skipped(self):
        """Files with errors should not be included in the call graph."""
        parsed = [
            {"file": "/fake/a.py", "language": "Python", "functions": ["foo"], "classes": [], "error": "parse_error"},
        ]
        extractor = CallGraphExtractor()
        cg = extractor.extract_call_graph(parsed)
        self.assertEqual(len(cg), 0)

    def test_java_method_invocation(self):
        """Test Java method_invocation call detection."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            java_file = root / "Main.java"
            java_file.write_text(
                "public class Main {\n"
                "    static int helper() { return 1; }\n"
                "    public static void main(String[] args) {\n"
                "        int x = helper();\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            parsed = [
                {
                    "file": str(java_file),
                    "language": "Java",
                    "functions": ["helper", "main"],
                    "classes": ["Main"],
                    "imports": [],
                    "error": None,
                },
            ]

            extractor = CallGraphExtractor()
            cg = extractor.extract_call_graph(parsed)

            java_key = str(java_file.resolve())
            self.assertIn(java_key, cg)
            self.assertTrue(
                any("helper" in callee for callee in cg[java_key]),
                f"Expected 'helper' call in Java file: {cg.get(java_key, [])}"
            )


if __name__ == "__main__":
    unittest.main()