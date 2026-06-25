from __future__ import annotations

from collections.abc import Iterable

from webcompy.ui.code_block._tokens import Token, TokenType
from webcompy.ui.code_block.lexers._base import Lexer


class PygmentsLexerWrapper:
    """Adapter for a Pygments lexer.

    This file is intentionally not imported by any other framework module.
    Adopting Pygments in a future change requires only adding `pygments` to
    dependencies and calling `register_pygments_lexer(...)` during application
    startup.
    """

    name: str
    aliases: tuple[str, ...]
    file_extensions: tuple[str, ...]

    def __init__(self, pygments_lexer) -> None:
        self._lexer = pygments_lexer
        self.name = getattr(pygments_lexer, "name", type(pygments_lexer).__name__)
        self.aliases = tuple(getattr(pygments_lexer, "aliases", ()))
        self.file_extensions = tuple(getattr(pygments_lexer, "filenames", ()))

    def tokenize(self, code: str) -> Iterable[Token]:
        from pygments.token import (  # type: ignore[import-untyped]
            Comment,
            Keyword,
            Literal,
            Name,
            Number,
            Operator,
            Punctuation,
            String,
        )
        from pygments.token import (
            Token as PygToken,
        )

        _MAP = (
            (Keyword, TokenType.KEYWORD),
            (Keyword.Constant, TokenType.KEYWORD),
            (Keyword.Declaration, TokenType.KEYWORD),
            (Keyword.Namespace, TokenType.KEYWORD),
            (Keyword.Pseudo, TokenType.KEYWORD),
            (Keyword.Reserved, TokenType.KEYWORD),
            (String, TokenType.STRING),
            (String.Doc, TokenType.STRING),
            (Number, TokenType.NUMBER),
            (Number.Integer, TokenType.NUMBER),
            (Number.Float, TokenType.NUMBER),
            (Comment, TokenType.COMMENT),
            (Comment.Single, TokenType.COMMENT),
            (Comment.Multiline, TokenType.COMMENT),
            (Name.Function, TokenType.FUNCTION),
            (Name.Builtin, TokenType.BUILTIN),
            (Name.Builtin.Pseudo, TokenType.BUILTIN),
            (Name.Decorator, TokenType.DECORATOR),
            (Operator, TokenType.OPERATOR),
            (Punctuation, TokenType.PUNCTUATION),
            (Name, TokenType.IDENTIFIER),
            (Literal, TokenType.IDENTIFIER),
            (PygToken, TokenType.IDENTIFIER),
        )

        for value, pygtok in self._lexer.get_tokens(code):
            for src, target in _MAP:
                if pygtok in src:
                    yield Token(target, value)
                break

    def __call__(self, code: str) -> Iterable[Token]:
        return self.tokenize(code)


def register_pygments_lexer(name_or_class, *, aliases=(), file_extensions=()) -> None:
    """Register a Pygments-backed lexer under one or more lookup names."""
    from webcompy.ui.code_block.lexers._registry import register_lexer

    if isinstance(name_or_class, str):
        from pygments.lexers import get_lexer_by_name  # type: ignore[import-untyped]

        pyg = get_lexer_by_name(name_or_class)
        name = name_or_class
    else:
        pyg = name_or_class()
        name = getattr(pyg, "name", type(pyg).__name__)

    class _Wrapped(PygmentsLexerWrapper, Lexer):
        pass

    wrapped = _Wrapped(pyg)
    wrapped.name = name
    wrapped.aliases = tuple(aliases)
    wrapped.file_extensions = tuple(file_extensions)
    register_lexer(wrapped)
