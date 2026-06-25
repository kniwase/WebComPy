from __future__ import annotations

from webcompy.ui.code_block._tokens import TokenType

PYGMENTS_SHORT_CLASS: dict[TokenType, str] = {
    TokenType.KEYWORD: "k",
    TokenType.STRING: "s",
    TokenType.NUMBER: "m",
    TokenType.COMMENT: "c",
    TokenType.FUNCTION: "nf",
    TokenType.BUILTIN: "nb",
    TokenType.DECORATOR: "nd",
    TokenType.OPERATOR: "o",
    TokenType.PUNCTUATION: "p",
    TokenType.IDENTIFIER: "",
}
