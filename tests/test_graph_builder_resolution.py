import tempfile
import unittest
from pathlib import Path

from repomind.graph_builder import GraphBuilder


class TestGraphBuilderResolution(unittest.TestCase):
    def test_alias_and_internal_package_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            (root / "src" / "lib").mkdir(parents=True)
            (root / "next" / "dist" / "util").mkdir(parents=True)
            (root / "pages").mkdir(parents=True)

            foo = root / "src" / "lib" / "foo.tsx"
            foo.write_text("export const x = 1;\n", encoding="utf-8")

            logger = root / "next" / "dist" / "util" / "logger.js"
            logger.write_text("export const y = 2;\n", encoding="utf-8")

            entry = root / "pages" / "a.ts"
            entry.write_text("import x from '@/lib/foo'\nimport y from 'next/dist/util/logger'\n", encoding="utf-8")

            parsed_files = [
                {"file": str(entry), "language": "TypeScript", "imports": ["@/lib/foo", "next/dist/util/logger"]},
                {"file": str(foo), "language": "TypeScript", "imports": []},
                {"file": str(logger), "language": "JavaScript", "imports": []},
            ]

            gb = GraphBuilder()
            graph = gb.build_graph(parsed_files)

            deps = set(graph[str(entry.resolve())])
            self.assertIn(str(foo.resolve()), deps)
            self.assertIn(str(logger.resolve()), deps)


if __name__ == "__main__":
    unittest.main()
