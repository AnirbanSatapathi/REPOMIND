from __future__ import annotations

import warnings
from typing import Dict

from tree_sitter import Parser as TSParser
from tree_sitter_languages import get_language


class TreeSitterEngine:
    def __init__(self):
        warnings.filterwarnings(
            "ignore",
            message=r"Language\(path, name\) is deprecated\..*",
            category=FutureWarning,
        )

        self._parsers: Dict[str, TSParser] = {}

    def get_parser(self, language_name: str) -> TSParser:
        parser = self._parsers.get(language_name)
        if parser:
            return parser

        parser = TSParser()
        parser.set_language(get_language(language_name))

        self._parsers[language_name] = parser
        return parser