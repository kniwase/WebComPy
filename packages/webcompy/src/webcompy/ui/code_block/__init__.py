from __future__ import annotations

from webcompy.ui.code_block._compatibility import PYGMENTS_SHORT_CLASS
from webcompy.ui.code_block._component import CodeBlock
from webcompy.ui.code_block._highlight import highlight
from webcompy.ui.code_block._tokens import Token, TokenType
from webcompy.ui.code_block.lexers._base import Lexer, LexerInfo
from webcompy.ui.code_block.lexers._registry import (
    LexerNotFoundError,
    get_lexer,
    list_lexers,
    register_builtin_lexers,
    register_lexer,
)

__all__ = [
    "PYGMENTS_SHORT_CLASS",
    "CodeBlock",
    "Lexer",
    "LexerInfo",
    "LexerNotFoundError",
    "Token",
    "TokenType",
    "get_lexer",
    "highlight",
    "list_lexers",
    "register_builtin_lexers",
    "register_lexer",
]


register_builtin_lexers()
