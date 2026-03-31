import tempfile
import unittest
from pathlib import Path

from repomind.parser import Parser


class TestPythonRelativeImports(unittest.TestCase):
    def test_resolves_relative_import_to_absolute_module(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            (root / "fastapi").mkdir(parents=True)
            (root / "fastapi" / "routing.py").write_text(
                "from .dependencies import Dependant\n"
                "from . import security\n",
                encoding="utf-8",
            )
            (root / "fastapi" / "dependencies.py").write_text(
                "class Dependant: pass\n",
                encoding="utf-8",
            )
            (root / "fastapi" / "security.py").write_text(
                "x = 1\n",
                encoding="utf-8",
            )

            # Ensure the repo-root heuristic picks `root`, not `root/fastapi`.
            (root / "other.py").write_text("x = 1\n", encoding="utf-8")

            parser = Parser()
            parsed = parser.parse_repo(
                [
                    root / "fastapi" / "routing.py",
                    root / "fastapi" / "dependencies.py",
                    root / "fastapi" / "security.py",
                    root / "other.py",
                ]
            )

            routing = next(item for item in parsed if item["file"].endswith("routing.py"))
            self.assertIn("fastapi.dependencies", routing["imports"])
            self.assertIn("fastapi.security", routing["imports"])
            # Avoid expanding class-like names (e.g. Dependant) into fake modules.
            self.assertNotIn("fastapi.dependencies.Dependant", routing["imports"])

    def test_resolves_parent_relative_import(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            (root / "fastapi" / "subpkg").mkdir(parents=True)
            (root / "fastapi" / "subpkg" / "module.py").write_text(
                "from ..dependencies import Dependant\n",
                encoding="utf-8",
            )
            (root / "fastapi" / "dependencies.py").write_text(
                "class Dependant: pass\n",
                encoding="utf-8",
            )
            (root / "other.py").write_text("x = 1\n", encoding="utf-8")

            parser = Parser()
            parsed = parser.parse_repo(
                [
                    root / "fastapi" / "subpkg" / "module.py",
                    root / "fastapi" / "dependencies.py",
                    root / "other.py",
                ]
            )

            module = next(item for item in parsed if item["file"].endswith("module.py"))
            self.assertIn("fastapi.dependencies", module["imports"])

    def test_expands_from_import_name_when_it_looks_like_module(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            (root / "fastapi").mkdir(parents=True)
            (root / "fastapi" / "app.py").write_text(
                "from fastapi import routing\n",
                encoding="utf-8",
            )
            (root / "fastapi" / "routing.py").write_text("x = 1\n", encoding="utf-8")
            (root / "other.py").write_text("x = 1\n", encoding="utf-8")

            parser = Parser()
            parsed = parser.parse_repo([root / "fastapi" / "app.py", root / "fastapi" / "routing.py", root / "other.py"])

            app = next(item for item in parsed if item["file"].endswith("app.py"))
            self.assertIn("fastapi", app["imports"])
            self.assertIn("fastapi.routing", app["imports"])


if __name__ == "__main__":
    unittest.main()
