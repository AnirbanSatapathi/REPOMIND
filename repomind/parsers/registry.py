from __future__ import annotations

from typing import Dict, Iterable

from .base import BaseParser


class ParserRegistry:
    def __init__(self, parsers: Iterable[BaseParser] | None = None):
        self._parsers: Dict[str, BaseParser] = {}
        if parsers:
            for parser in parsers:
                self.register_parser(parser.language, parser)

    def register_parser(self, language: str, parser: BaseParser) -> None:
        self._parsers[language] = parser

    def get_parser(self, language: str) -> BaseParser | None:
        return self._parsers.get(language)

    def supported_languages(self) -> list[str]:
        return sorted(self._parsers.keys())

