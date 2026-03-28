from pathlib import Path
from typing import Dict, Any
import os
try:
    import pathspec
except ImportError:
    pathspec = None


class Scanner:
    DEFAULT_IGNORE = {
        ".git",
        "node_modules",
        "venv",
        ".venv",
        "dist",
        "build",
        "target",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".idea",
        ".vscode",
        ".next",
        ".nuxt",
        ".gradle",
        "out",
        ".terraform",
        ".uv-cache",
        ".repomind",
        "repomind.egg-info",
    }

    CODE_EXTENSIONS = {
        ".py": "Python",
        ".java": "Java",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".jsx": "JavaScript",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
        ".h": "C",
        ".hpp": "C++",
        ".cs": "C#",
        ".kt": "Kotlin",
    }

    CONFIG_EXTENSIONS = {
        ".yaml", ".yml", ".toml", ".ini",
        ".env", ".cfg", ".json",
    }

    DOC_EXTENSIONS = {
        ".md", ".txt", ".rst",
    }

    INFRA_FILES = {
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
    }

    INFRA_DIRS = {
        "k8s",
        "kubernetes",
        "helm",
        "terraform",
    }

    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

    def _load_gitignore(self, repo_path: Path):
        if not pathspec:
            return None

        gitignore = repo_path / ".gitignore"
        if not gitignore.exists():
            return None

        with open(gitignore) as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)

    def _is_binary(self, file_path: Path) -> bool:
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                return b"\x00" in chunk
        except Exception:
            return True  # treat unknown as binary (safe fallback)

    def scan_repo(self, repo_path: Path) -> Dict[str, Any]:
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path not found: {repo_path}")

        gitignore_spec = self._load_gitignore(repo_path)

        languages_count = {}
        files_category = {
            "code": [],
            "config": [],
            "infra": [],
            "docs": [],
            "unknown": [],
        }

        for root, dirs, files in os.walk(repo_path):

            # Filter ignored directories
            dirs[:] = [
                d for d in dirs
                if d not in self.DEFAULT_IGNORE
            ]

            root_path = Path(root)

            # Precise infra dir check
            is_infra_dir = root_path.name in self.INFRA_DIRS

            for file in files:
                file_path = root_path / file

                # Gitignore filtering
                if gitignore_spec:
                    rel_path = file_path.relative_to(repo_path)
                    if gitignore_spec.match_file(str(rel_path)):
                        continue

                # Safe file size check
                try:
                    if file_path.stat().st_size > self.MAX_FILE_SIZE:
                        continue
                except Exception:
                    continue

                # Skip binary files
                if self._is_binary(file_path):
                    continue

                ext = file_path.suffix.lower()
                name_lower = file.lower()

                is_infra_file = name_lower in self.INFRA_FILES

                if is_infra_dir or is_infra_file:
                    files_category["infra"].append(file_path)

                elif ext in self.CODE_EXTENSIONS:
                    lang = self.CODE_EXTENSIONS[ext]
                    files_category["code"].append(file_path)
                    languages_count[lang] = languages_count.get(lang, 0) + 1

                elif ext in self.CONFIG_EXTENSIONS:
                    files_category["config"].append(file_path)

                elif ext in self.DOC_EXTENSIONS:
                    files_category["docs"].append(file_path)

                else:
                    files_category["unknown"].append(file_path)

        all_files = (
            files_category["code"]
            + files_category["config"]
            + files_category["infra"]
            + files_category["docs"]
        )

        return {
            "files": all_files,
            "code_files": files_category["code"],
            "config_files": files_category["config"],
            "infra_files": files_category["infra"],
            "doc_files": files_category["docs"],
            "unknown_files": files_category["unknown"],
            "languages": languages_count,
            "detected_languages": list(languages_count.keys()),
            "total_files": len(all_files),
            "stats": {
                "code_files": len(files_category["code"]),
                "config_files": len(files_category["config"]),
                "infra_files": len(files_category["infra"]),
                "docs": len(files_category["docs"]),
                "unknown_files": len(files_category["unknown"]),
            },
        }