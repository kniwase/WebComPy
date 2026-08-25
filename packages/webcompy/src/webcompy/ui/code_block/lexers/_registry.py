"""Lexer registry with name, alias, and file-extension lookup."""

from __future__ import annotations

from webcompy.ui.code_block.lexers._base import Lexer, LexerInfo
from webcompy.ui.code_block.lexers._bash import BashLexer
from webcompy.ui.code_block.lexers._python import PythonLexer
from webcompy.ui.code_block.lexers._toml import TomlLexer


class LexerNotFoundError(KeyError):
    """Raised by ``get_lexer`` when no lexer matches the requested name.

    The error message lists the currently registered lexer names.

    Args:
        name: The lookup name that failed to resolve.

    Attributes:
        name: The lookup name that failed to resolve.

    """

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
    """Register a lexer under its name, aliases, and file extensions.

    Args:
        lexer: Lexer instance implementing the ``Lexer`` protocol.
        override: Replace an existing registration under the same primary
            name.
        source: Origin label recorded for ``list_lexers`` introspection.

    Raises:
        TypeError: If ``lexer`` does not implement the ``Lexer`` protocol.
        ValueError: If the primary name is already registered while
            ``override`` is ``False``.

    """
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
    """Return the lexer registered under ``name``, an alias, or a file extension.

    Lookup is case-insensitive and also accepts file extensions with or
    without a leading dot.

    Args:
        name: Primary name, alias, or file extension to resolve.

    Returns:
        The registered lexer.

    Raises:
        LexerNotFoundError: If no lexer matches ``name``.

    """
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
    """Return introspection records for every registered lexer.

    Returns:
        ``LexerInfo`` records sorted by primary name, one per lexer.

    """
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
    """Register the built-in Python, Bash, and TOML lexers.

    Idempotent: performs no work when a Python lexer is already
    registered. The registrations are labeled ``"builtin"``.
    """
    if "python" in _REGISTRY:
        return
    register_lexer(PythonLexer(), source="builtin")
    register_lexer(BashLexer(), source="builtin")
    register_lexer(TomlLexer(), source="builtin")
