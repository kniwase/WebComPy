from __future__ import annotations

from webcompy.ui.code_block.lexers._base import Lexer, LexerInfo
from webcompy.ui.code_block.lexers._bash import BashLexer
from webcompy.ui.code_block.lexers._python import PythonLexer
from webcompy.ui.code_block.lexers._toml import TomlLexer


class LexerNotFoundError(KeyError):
    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.name = name

    def __str__(self) -> str:
        return f"No lexer registered for {self.name!r}"


_REGISTRY: dict[str, Lexer] = {}


def register_lexer(lexer: Lexer) -> None:
    if not isinstance(lexer, Lexer):
        raise TypeError(f"Lexer must implement the Lexer protocol, got {type(lexer).__name__}")
    _REGISTRY[lexer.name] = lexer
    for alias in lexer.aliases:
        _REGISTRY[alias] = lexer
    for ext in lexer.file_extensions:
        _REGISTRY[ext] = lexer


def get_lexer(name: str) -> Lexer:
    if name in _REGISTRY:
        return _REGISTRY[name]
    lowered = name.lower()
    if lowered in _REGISTRY:
        return _REGISTRY[lowered]
    if not name.startswith("."):
        dotted = "." + name
        if dotted in _REGISTRY:
            return _REGISTRY[dotted]
    raise LexerNotFoundError(name)


def list_lexers() -> list[LexerInfo]:
    seen: dict[str, LexerInfo] = {}
    for lexer in _REGISTRY.values():
        if lexer.name not in seen:
            seen[lexer.name] = LexerInfo(
                name=lexer.name,
                aliases=lexer.aliases,
                file_extensions=lexer.file_extensions,
            )
    return sorted(seen.values(), key=lambda info: info.name)


def register_builtin_lexers() -> None:
    if "python" in _REGISTRY:
        return
    register_lexer(PythonLexer())
    register_lexer(BashLexer())
    register_lexer(TomlLexer())
