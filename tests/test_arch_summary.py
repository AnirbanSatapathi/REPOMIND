import tempfile
import unittest
from pathlib import Path

from repomind.arch_summary import generate_architecture_summary


class TestArchSummary(unittest.TestCase):
    def _make_parsed_files(self, root: Path):
        """Create sample parsed file data for testing."""
        return [
            {
                "file": str(root / "src" / "main.py"),
                "language": "Python",
                "functions": ["main", "setup", "run"],
                "classes": ["App"],
                "imports": ["os", "sys"],
                "error": None,
            },
            {
                "file": str(root / "src" / "utils.py"),
                "language": "Python",
                "functions": ["helper", "format_output"],
                "classes": [],
                "imports": [],
                "error": None,
            },
            {
                "file": str(root / "lib" / "core.js"),
                "language": "JavaScript",
                "functions": ["init", "process"],
                "classes": ["Engine"],
                "imports": [],
                "error": None,
            },
        ]

    def test_generates_summary_with_all_sections(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "lib").mkdir()

            parsed = self._make_parsed_files(root)
            dep_graph = {
                str(root / "src" / "main.py"): [str(root / "src" / "utils.py")],
                str(root / "lib" / "core.js"): [],
            }
            call_graph = {
                str(root / "src" / "main.py"): [
                    f"{root / 'src' / 'utils.py'}::helper",
                ],
            }

            summary = generate_architecture_summary(parsed, dep_graph, call_graph)

            self.assertIn("# Architecture Summary", summary)
            self.assertIn("## Module Overview", summary)
            self.assertIn("## Dependency Analysis", summary)
            self.assertIn("## Call Graph Analysis", summary)
            self.assertIn("## Language Breakdown", summary)

    def test_language_breakdown_counts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "lib").mkdir()

            parsed = self._make_parsed_files(root)
            summary = generate_architecture_summary(parsed, {}, {})

            self.assertIn("**Python**: 2 files", summary)
            self.assertIn("**JavaScript**: 1 files", summary)

    def test_dependency_hub_analysis(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()
            (root / "lib").mkdir()

            parsed = self._make_parsed_files(root)
            # utils.py is imported by main.py — should be a "hub"
            dep_graph = {
                str(root / "src" / "main.py"): [str(root / "src" / "utils.py")],
                str(root / "lib" / "core.js"): [str(root / "src" / "utils.py")],
            }

            summary = generate_architecture_summary(parsed, dep_graph, {})

            self.assertIn("Most Depended-Upon Files", summary)
            self.assertIn("utils.py", summary)
            self.assertIn("imported by 2 files", summary)

    def test_empty_parsed_files(self):
        result = generate_architecture_summary([], {}, {})
        self.assertEqual(result, "No valid parsed files.")

    def test_files_with_errors_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()

            parsed = [
                {
                    "file": str(root / "src" / "good.py"),
                    "language": "Python",
                    "functions": ["foo"],
                    "classes": [],
                    "imports": [],
                    "error": None,
                },
                {
                    "file": str(root / "src" / "bad.py"),
                    "language": "Python",
                    "functions": [],
                    "classes": [],
                    "imports": [],
                    "error": "parse_error",
                },
            ]

            summary = generate_architecture_summary(parsed, {}, {})

            self.assertIn("**Python**: 1 files", summary)

    def test_call_graph_analysis_section(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()

            parsed = self._make_parsed_files(root)
            call_graph = {
                str(root / "src" / "main.py"): [
                    f"{root / 'src' / 'utils.py'}::helper",
                    f"{root / 'src' / 'utils.py'}::format_output",
                ],
            }

            summary = generate_architecture_summary(parsed, {}, call_graph)

            self.assertIn("Total call edges: 2", summary)
            self.assertIn("Files with function calls: 1", summary)

    def test_no_call_graph_shows_message(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "src").mkdir()

            parsed = [
                {
                    "file": str(root / "src" / "main.py"),
                    "language": "Python",
                    "functions": [],
                    "classes": [],
                    "imports": [],
                    "error": None,
                },
            ]
            summary = generate_architecture_summary(parsed, {}, {})
            self.assertIn("No call graph data available", summary)


if __name__ == "__main__":
    unittest.main()
