from __future__ import annotations

import html as html_module

from webcompy.ui.code_block._compatibility import PYGMENTS_SHORT_CLASS
from webcompy.ui.code_block._tokens import Token, TokenType
from webcompy.ui.code_block.lexers._registry import LexerNotFoundError, get_lexer


def highlight(code: str, lang: str) -> str:
    return _render_tokens(_tokenize_with_fallback(code, lang))


def _token_span_classes(token_type: TokenType) -> str:
    semantic_class = f"tok-{token_type}"
    pygments_class = PYGMENTS_SHORT_CLASS.get(token_type, "")
    if pygments_class:
        return f"{semantic_class} {pygments_class}"
    return semantic_class


def _tokenize_with_fallback(code: str, lang: str) -> list[Token]:
    if not code:
        return []
    try:
        lexer = get_lexer(lang)
    except LexerNotFoundError:
        return [Token(TokenType.IDENTIFIER, code)]
    tokens: list[Token] = list(lexer.tokenize(code))
    if not tokens:
        return [Token(TokenType.IDENTIFIER, code)]
    return tokens


def _render_tokens(tokens: list[Token]) -> str:
    out: list[str] = []
    for token in tokens:
        out.append(_render_token(token))
    return "".join(out)


def _render_token(token: Token) -> str:
    escaped = html_module.escape(token.value)
    return f'<span class="{_token_span_classes(token.type)}">{escaped}</span>'
