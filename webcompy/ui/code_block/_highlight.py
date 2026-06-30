from __future__ import annotations

import html as html_module

from webcompy.ui.code_block._compatibility import PYGMENTS_SHORT_CLASS
from webcompy.ui.code_block._tokens import Token
from webcompy.ui.code_block.lexers._registry import LexerNotFoundError, get_lexer


def highlight(code: str, lang: str) -> str:
    if not code:
        return ""
    try:
        lexer = get_lexer(lang)
    except LexerNotFoundError:
        return _render_raw(code)
    tokens: list[Token] = list(lexer.tokenize(code))
    if not tokens:
        return _render_raw(code)
    return _render_tokens(tokens)


def _render_raw(code: str) -> str:
    return f'<span class="tok-ident">{html_module.escape(code)}</span>'


def _render_tokens(tokens: list[Token]) -> str:
    out: list[str] = []
    for token in tokens:
        out.append(_render_token(token))
    return "".join(out)


def _render_token(token: Token) -> str:
    semantic_class = f"tok-{token.type}"
    pygments_class = PYGMENTS_SHORT_CLASS.get(token.type, "")
    classes = [semantic_class]
    if pygments_class:
        classes.append(pygments_class)
    class_attr = " ".join(classes)
    escaped = html_module.escape(token.value)
    return f'<span class="{class_attr}">{escaped}</span>'
