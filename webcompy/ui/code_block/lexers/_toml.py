from __future__ import annotations

import re
from collections.abc import Iterable

from webcompy.ui.code_block._tokens import Token, TokenType


class TomlLexer:
    name: str = "toml"
    aliases: tuple[str, ...] = ()
    file_extensions: tuple[str, ...] = (".toml",)

    _SECTION_RE: re.Pattern[str] = re.compile(
        r"^\s*\[+\s*([A-Za-z0-9_\-\.]+)\s*\]+\s*(?:\#[^\n]*)?$",
        re.MULTILINE,
    )

    _TOKEN_PATTERN: re.Pattern[str] = re.compile(
        r"""
        (?P<comment>\#[^\n]*)
        | (?P<string_multi_basic>\"\"\"(?:\\.|[^"\\])*(?:(?<!")"(?!""))*\"\"\")
        | (?P<string_multi_literal>'''(?:\\.|[^'\\])*(?:(?!')'(?!''))*''')
        | (?P<string_basic>"(?:\\.|[^"\\\n])*")
        | (?P<string_lit>'(?:\\.|[^'\\\n])*')
        | (?P<date>\d{4}-\d{2}-\d{2}(?:[Tt\s][^\n,}\]]*)?)
        | (?P<number>\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)
        | (?P<bool>\b(?:true|false)\b)
        | (?P<op>=)
        | (?P<punct>[\[\]\{\},])
        | (?P<ws>[ \t]+)
        | (?P<newline>\n)
        """,
        re.VERBOSE,
    )

    def tokenize(self, code: str) -> Iterable[Token]:
        if not code:
            return

        section_ranges: list[tuple[int, int, str]] = []
        for match in self._SECTION_RE.finditer(code):
            section_start = match.start()
            section_end = match.end()
            section_name = match.group(1)
            section_ranges.append((section_start, section_end, section_name))

        pos = 0
        for match in self._TOKEN_PATTERN.finditer(code):
            start, end = match.span()
            if start > pos:
                yield from _tokenize_gap(code[pos:start], _is_in_section(start, section_ranges))
            pos = end
            kind = match.lastgroup
            value = match.group()

            if kind == "comment":
                yield Token(TokenType.COMMENT, value)
                continue

            if kind in (
                "string_multi_basic",
                "string_multi_literal",
                "string_basic",
                "string_lit",
                "date",
            ):
                yield Token(TokenType.STRING, value)
                continue

            if kind == "number":
                yield Token(TokenType.NUMBER, value)
                continue

            if kind == "bool":
                yield Token(TokenType.KEYWORD, value)
                continue

            if kind == "op":
                yield Token(TokenType.OPERATOR, value)
                continue

            if kind == "punct":
                yield Token(TokenType.PUNCTUATION, value)
                continue

            if kind in ("ws", "newline"):
                yield Token(TokenType.IDENTIFIER, value)
                continue

        if pos < len(code):
            yield from _tokenize_gap(code[pos:], _is_in_section(pos, section_ranges))

    def __call__(self, code: str) -> Iterable[Token]:
        return self.tokenize(code)


def _is_in_section(pos: int, section_ranges: list[tuple[int, int, str]]) -> bool:
    return any(start <= pos < end for start, end, _name in section_ranges)


def _tokenize_gap(gap: str, in_section: bool) -> Iterable[Token]:
    if not gap:
        return
    if in_section and _SECTION_NAME_RE.fullmatch(gap.strip()):
        yield Token(TokenType.KEYWORD, gap)
    else:
        yield Token(TokenType.IDENTIFIER, gap)


_SECTION_NAME_RE: re.Pattern[str] = re.compile(r"[A-Za-z0-9_\-\.]+")
