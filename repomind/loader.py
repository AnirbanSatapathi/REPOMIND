from pathlib import Path
import shutil

from git import Repo, GitCommandError, InvalidGitRepositoryError


class Loader:
    def __init__(self, base_storage: str = ".repomind/repos"):
        self.base_storage = Path(base_storage)
        self.prepare_storage()

    def prepare_storage(self):
        self.base_storage.mkdir(parents=True, exist_ok=True)

    def get_repo_name(self, url: str) -> str:
        name = url.rstrip("/").split("/")[-1]
        if name.endswith(".git"):
            name = name[:-4]
        return name

    def _is_incomplete_repo(self, repo_path: Path) -> bool:
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return True

        try:
            repo = Repo(repo_path)
            head_valid = repo.head.is_valid()
        except (InvalidGitRepositoryError, Exception):
            head_valid = False

        has_working_tree_files = any(p.name != ".git" for p in repo_path.iterdir())
        return (not head_valid) or (not has_working_tree_files)

    def _remove_stale_lock(self, repo_path: Path) -> None:
        lock_path = repo_path / ".git" / "index.lock"
        if lock_path.exists():
            try:
                lock_path.unlink()
            except Exception as e:
                raise RuntimeError(f"Failed to remove git lock file {lock_path}: {e}")

    def clone_repo(self, repo_url: str) -> Path:
        repo_name = self.get_repo_name(repo_url)
        target_path = self.base_storage / repo_name

        if target_path.exists():
            self._remove_stale_lock(target_path)
            if not self._is_incomplete_repo(target_path):
                return target_path

            try:
                shutil.rmtree(target_path)
            except Exception as e:
                raise RuntimeError(f"Existing repo checkout is incomplete and could not be removed: {e}")

        try:
            Repo.clone_from(
                repo_url,
                target_path,
                depth=1,
            #    multi_options=["-c", "core.longpaths=true"],
            )
        except GitCommandError as e:
            raise RuntimeError(f"Failed to clone repository: {e}")

        self._remove_stale_lock(target_path)
        if self._is_incomplete_repo(target_path):
            raise RuntimeError(
                "Repository clone completed but working tree is empty/incomplete. "
                "This is commonly caused by Windows long-path issues or an interrupted checkout."
            )
        return target_path

    def load_local_repo(self, path: str) -> Path:
        local_path = Path(path).resolve()
        if not local_path.exists():
            raise FileNotFoundError(f"Local path does not exist: {local_path}")
        if not (local_path / ".git").exists():
            raise ValueError(f"Not a valid git repository: {local_path}")
        return local_path
