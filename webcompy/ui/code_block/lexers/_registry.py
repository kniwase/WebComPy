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
        available = ", ".join(sorted({info.name for info in list_lexers()}) or ["<no lexers registered>"])
        return f"No lexer registered for {self.name!r}. Available: {available}"


_REGISTRY: dict[str, Lexer] = {}
_REGISTRY_SOURCES: dict[str, str] = {}


def register_lexer(
    lexer: Lexer,
    *,
    override: bool = False,
    source: str = "custom",
) -> None:
    if not isinstance(lexer, Lexer):
        raise TypeError(f"Lexer must implement the Lexer protocol, got {type(lexer).__name__}")
    if lexer.name in _REGISTRY and not override:
        raise ValueError(
            f"Lexer {lexer.name!r} is already registered. Pass override=True to replace the existing registration."
        )
    _REGISTRY[lexer.name] = lexer
    _REGISTRY_SOURCES[lexer.name] = source
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
                source=_REGISTRY_SOURCES.get(lexer.name, "custom"),
            )
    return sorted(seen.values(), key=lambda info: info.name)


def reset_lexer_registry() -> None:
    _REGISTRY.clear()
    _REGISTRY_SOURCES.clear()


def register_builtin_lexers() -> None:
    if "python" in _REGISTRY:
        return
    register_lexer(PythonLexer(), source="builtin")
    register_lexer(BashLexer(), source="builtin")
    register_lexer(TomlLexer(), source="builtin")
