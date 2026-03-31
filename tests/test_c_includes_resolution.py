import tempfile
import unittest
from pathlib import Path

from repomind.graph_builder import GraphBuilder
from repomind.parser import Parser


class TestCIncludesResolution(unittest.TestCase):
    def test_c_parser_extracts_only_include_path_and_graph_resolves(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "include" / "dir").mkdir(parents=True)
            (root / "src").mkdir(parents=True)

            header = root / "include" / "dir" / "utils.h"
            header.write_text("#pragma once\n", encoding="utf-8")

            c_file = root / "src" / "main.c"
            c_file.write_text(
                '#include "dir/utils.h"\n#include <stdio.h>\nint f(){return 1;}\n',
                encoding="utf-8",
            )

            parser = Parser()
            parsed = parser.parse_repo([c_file, header])
            main_item = next(x for x in parsed if x["file"].endswith("main.c"))

            # Parser returns only extracted include path (no raw "#include ...")
            self.assertIn("dir/utils.h", main_item["imports"])
            self.assertIn("stdio.h", main_item["imports"])
            self.assertTrue(all(not s.strip().startswith("#include") for s in main_item["imports"]))

            gb = GraphBuilder()
            graph = gb.build_graph(parsed)
            deps = set(graph[str(c_file.resolve())])

            # Repo header resolves; system header should miss.
            self.assertIn(str(header.resolve()), deps)


if __name__ == "__main__":
    unittest.main()

