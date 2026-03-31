from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional


class BaseResolver(ABC):
    """
    Base class for language-specific import resolvers.
    """

    @property
    @abstractmethod
    def language(self) -> str:
        """Language name (e.g., 'Python', 'Java', 'C#')."""
        raise NotImplementedError

    def prepare(
        self,
        repo_root: Path,
        file_index: Dict[str, str],
        parsed_files: List[Dict[str, Any]],
    ) -> None:
        """
        Optional step to pre-calculate language-specific indices 
        (like C/C++ filename indices or Java class source root maps).
        """
        pass

    @abstractmethod
    def resolve(
        self,
        current_file: Path,
        repo_root: Path,
        imp: str,
        file_index: Dict[str, str],
    ) -> Optional[str]:
        """
        Resolves an import string to a file path within the repository.
        Returns the absolute string path or None if not found.
        """
        raise NotImplementedError
