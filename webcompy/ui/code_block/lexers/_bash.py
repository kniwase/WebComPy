from __future__ import annotations

import re
from collections.abc import Iterable

from webcompy.ui.code_block._tokens import Token, TokenType


class BashLexer:
    name: str = "bash"
    aliases: tuple[str, ...] = ("sh", "shell", "zsh")
    file_extensions: tuple[str, ...] = (".sh", ".bash", ".zsh")

    _BUILTINS: frozenset[str] = frozenset(
        {
            "alias",
            "break",
            "builtin",
            "caller",
            "cd",
            "command",
            "compgen",
            "complete",
            "compopt",
            "continue",
            "declare",
            "dirs",
            "disown",
            "echo",
            "enable",
            "eval",
            "exec",
            "exit",
            "export",
            "false",
            "fc",
            "fg",
            "getopts",
            "hash",
            "help",
            "history",
            "jobs",
            "kill",
            "let",
            "local",
            "logout",
            "mapfile",
            "popd",
            "printf",
            "pushd",
            "pwd",
            "read",
            "readarray",
            "readonly",
            "return",
            "set",
            "shift",
            "shopt",
            "source",
            "suspend",
            "test",
            "times",
            "trap",
            "true",
            "type",
            "typeset",
            "ulimit",
            "umask",
            "unalias",
            "unset",
            "wait",
        }
    )

    _KEYWORDS: frozenset[str] = frozenset(
        {
            "if",
            "then",
            "else",
            "elif",
            "fi",
            "case",
            "esac",
            "for",
            "select",
            "while",
            "until",
            "do",
            "done",
            "in",
            "function",
            "time",
            "[",
            "[[",
            "]",
            "]]",
        }
    )

    _TOKEN_PATTERN: re.Pattern[str] = re.compile(
        r"""
        (?P<comment>\#[^\n]*)
        | (?P<string_dq>"(?:\\.|[^"\\])*")
        | (?P<string_sq>'(?:\\.|[^'\\])*')
        | (?P<variable>\$[A-Za-z_][A-Za-z0-9_]*
              |\$\{[A-Za-z_][A-Za-z0-9_]*\})
        | (?P<number>\b\d+(?:\.\d+)?\b)
        | (?P<word>[A-Za-z_][A-Za-z0-9_]*)
        | (?P<op>[|&;<>=(){}\[\]!`$\\]
          | \*\* | \* | \+ | - | / | % | == | != | <= | >=
          | && | \|\|)
        | (?P<punct>[,.:?~^+])
        | (?P<ws>\s+)
        """,
        re.VERBOSE,
    )

    def tokenize(self, code: str) -> Iterable[Token]:
        if not code:
            return
        pos = 0
        for match in self._TOKEN_PATTERN.finditer(code):
            start, end = match.span()
            if start > pos:
                gap = code[pos:start]
                if gap.strip() or gap:
                    yield Token(TokenType.IDENTIFIER, gap)
            pos = end
            kind = match.lastgroup
            value = match.group()
            if kind == "comment":
                yield Token(TokenType.COMMENT, value)
            elif kind in ("string_dq", "string_sq"):
                yield Token(TokenType.STRING, value)
            elif kind == "variable":
                name = value[2:-1] if value.startswith("${") and value.endswith("}") else value[1:]
                yield Token(TokenType.IDENTIFIER, name)
            elif kind == "number":
                yield Token(TokenType.NUMBER, value)
            elif kind == "word":
                if value in self._KEYWORDS:
                    yield Token(TokenType.KEYWORD, value)
                elif value in self._BUILTINS:
                    yield Token(TokenType.BUILTIN, value)
                else:
                    yield Token(TokenType.IDENTIFIER, value)
            elif kind == "op":
                yield Token(TokenType.OPERATOR, value)
            elif kind == "punct":
                yield Token(TokenType.PUNCTUATION, value)
            elif kind == "ws":
                yield Token(TokenType.IDENTIFIER, value)
        if pos < len(code):
            tail = code[pos:]
            yield Token(TokenType.IDENTIFIER, tail)

    def __call__(self, code: str) -> Iterable[Token]:
        return self.tokenize(code)
