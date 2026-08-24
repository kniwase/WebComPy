"""Base lexer protocol and lexer introspection record."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from webcompy.ui.code_block._tokens import Token


@dataclass(frozen=True)
class LexerInfo:
    """Introspection record describing a registered lexer.

    Attributes:
        name: Primary language identifier.
        aliases: Alternative lookup names.
        file_extensions: Registered file extensions (with leading dot).
        source: Origin label: ``"builtin"``, ``"pygments:<lexname>"``, or
            ``"custom"``.

    """

    name: str
    aliases: tuple[str, ...]
    file_extensions: tuple[str, ...]
    source: str


@runtime_checkable
class Lexer(Protocol):
    """Protocol for source code tokenizers.

    Attributes:
        name: Primary language identifier used for registry lookup.
        aliases: Alternative names the lexer is registered under.
        file_extensions: File extensions (with leading dot) the lexer is
            registered under.

    """

    name: str
    aliases: tuple[str, ...]
    file_extensions: tuple[str, ...]

    def tokenize(self, code: str) -> Iterable[Token]:
        """Tokenize source text into classified spans.

        Args:
            code: Source text to tokenize; empty input yields no tokens.

        Returns:
            Tokens in source order whose concatenated values equal ``code``
            exactly.

        """
        ...
