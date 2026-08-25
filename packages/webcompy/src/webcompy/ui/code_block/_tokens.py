"""Token and token type primitives for syntax highlighting."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TokenType(StrEnum):
    """Category a highlighted token belongs to.

    Each member's value is the suffix of the emitted ``tok-{value}`` CSS
    class name.
    """

    KEYWORD = "kw"
    STRING = "str"
    NUMBER = "num"
    COMMENT = "comment"
    FUNCTION = "fn"
    BUILTIN = "builtin"
    DECORATOR = "decorator"
    OPERATOR = "op"
    PUNCTUATION = "punct"
    IDENTIFIER = "ident"


@dataclass(frozen=True)
class Token:
    """A single classified span of highlighted source text.

    Immutable and hashable; the fields cannot be reassigned.

    Attributes:
        type: Category of the token.
        value: Raw source text of the span, preserved verbatim.

    Raises:
        TypeError: If ``type`` is not a ``TokenType`` or ``value`` is not
            a ``str``.

    """

    type: TokenType
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.type, TokenType):
            raise TypeError(f"Token.type must be TokenType, got {type(self.type).__name__}")
        if not isinstance(self.value, str):
            raise TypeError(f"Token.value must be str, got {type(self.value).__name__}")
