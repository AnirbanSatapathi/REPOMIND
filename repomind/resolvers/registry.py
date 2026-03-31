from __future__ import annotations

from typing import Any, Dict, List, Optional, Iterable
from pathlib import Path

from .base import BaseResolver


class ResolverRegistry:
    """
    Registry for import resolvers by language.
    """

    def __init__(self, resolvers: Iterable[BaseResolver] | None = None):
        self._resolvers: Dict[str, BaseResolver] = {}
        if resolvers:
            for resolver in resolvers:
                self.register_resolver(resolver.language, resolver)

    def register_resolver(self, language: str, resolver: BaseResolver) -> None:
        """
        Registers a resolver for a specific language string 
        (matching the language returned from the parser).
        """
        self._resolvers[language] = resolver

    def get_resolver(self, language: str) -> Optional[BaseResolver]:
        """
        Retrieves the registered resolver for the given language.
        """
        return self._resolvers.get(language)

    def prepare_all(
        self,
        repo_root: Path,
        file_index: Dict[str, str],
        parsed_files: List[Dict[str, Any]],
    ) -> None:
        """
        Calls prepare() on all registered resolvers.
        """
        for resolver in self._resolvers.values():
            resolver.prepare(repo_root, file_index, parsed_files)

    def supported_languages(self) -> list[str]:
        """Returns the list of languages with registered resolvers."""
        return sorted(self._resolvers.keys())
