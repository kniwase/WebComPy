from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TokenType(StrEnum):
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
    type: TokenType
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.type, TokenType):
            raise TypeError(f"Token.type must be TokenType, got {type(self.type).__name__}")
        if not isinstance(self.value, str):
            raise TypeError(f"Token.value must be str, got {type(self.value).__name__}")
