from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from webcompy.ui.code_block._tokens import Token


@dataclass(frozen=True)
class LexerInfo:
    name: str
    aliases: tuple[str, ...]
    file_extensions: tuple[str, ...]
    source: str


@runtime_checkable
class Lexer(Protocol):
    name: str
    aliases: tuple[str, ...]
    file_extensions: tuple[str, ...]

    def tokenize(self, code: str) -> Iterable[Token]: ...
