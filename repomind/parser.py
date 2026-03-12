import ast
from pathlib import Path
from typing import Dict, Any, List

class Parser:
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        language = self.detect_language(file_path)
        if language == "Python":
            return self.parse_python(file_path)
        return {
            "file": str(file_path),
            "language": language,
            "imports": [],
            "classes": [],
            "functions": []
        }
    def detect_language(self, file_path: Path) -> str:
        ext = file_path.suffix.lower()

        mapping = {
            ".py": "Python",
            ".java": "Java",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".go": "Go",
            ".rs": "Rust",
            ".cpp": "C++",
            ".c": "C"
        }
        return mapping.get(ext, "Unknown")

    def parse_python(self, file_path: Path) -> Dict[str, Any]:
        imports: List[str] = []
        classes: List[str] = []
        functions: List[str] = []

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for n in node.names:
                        imports.append(n.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
        except Exception:
            pass
        return {
            "file": str(file_path),
            "language": "Python",
            "imports": imports,
            "classes": classes,
            "functions": functions
        }
    def parse_repo(self, files: List[Path]) -> List[Dict[str, Any]]:
        results = []
        for file in files:
            parsed = self.parse_file(file)
            results.append(parsed)
        return results
