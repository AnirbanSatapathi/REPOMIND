import tempfile
import unittest
from pathlib import Path

from repomind.parser import Parser


class TestGoParser(unittest.TestCase):
    def test_go_parser_extracts_functions_imports_and_types(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            go_file = root / "main.go"
            go_file.write_text(
                'package main\n'
                'import "fmt"\n'
                'type Foo struct{}\n'
                'func main() {\n'
                '    fmt.Println("hi")\n'
                '}\n'
                'func helper() int {\n'
                '    return 42\n'
                '}\n',
                encoding="utf-8",
            )

            parser = Parser()
            result = parser.parse_repo([go_file])
            self.assertEqual(len(result), 1)
            r = result[0]

            self.assertEqual(r["language"], "Go")
            self.assertIn("main", r["functions"])
            self.assertIn("helper", r["functions"])
            self.assertIn("fmt", r["imports"])
            self.assertIn("Foo", r["classes"])
            self.assertIsNone(r["error"])


if __name__ == "__main__":
    unittest.main()