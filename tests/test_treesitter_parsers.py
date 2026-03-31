import tempfile
import unittest
from pathlib import Path


try:
    from repomind.parser import Parser
except Exception:  # pragma: no cover
    Parser = None


@unittest.skipIf(Parser is None, "Parser import failed")
class TestTreeSitterParsers(unittest.TestCase):
    def test_javascript_imports_classes_functions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "utils").mkdir(parents=True)

            js_file = root / "index.js"
            js_file.write_text(
                "\n".join(
                    [
                        "import x from './utils/helper';",
                        "const y = require('./pkg');",
                        "export * from './reexport';",
                        "class A {}",
                        "function f() {}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            (root / "utils" / "helper.js").write_text("export const x = 1;\n", encoding="utf-8")
            (root / "pkg.js").write_text("module.exports = {};\n", encoding="utf-8")
            (root / "reexport.js").write_text("export const y = 2;\n", encoding="utf-8")

            parser = Parser()
            parsed = parser.parse_repo([js_file, root / "utils" / "helper.js", root / "pkg.js", root / "reexport.js"])
            result = next(item for item in parsed if item["file"].endswith("index.js"))

            self.assertEqual(result["language"], "JavaScript")
            expected = {
                str((root / "utils" / "helper").resolve()),
                str((root / "pkg").resolve()),
                str((root / "reexport").resolve()),
            }
            self.assertTrue(expected.issubset(set(result["imports"])))
            self.assertIn("A", result["classes"])
            self.assertIn("f", result["functions"])


if __name__ == "__main__":
    unittest.main()
