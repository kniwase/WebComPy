from __future__ import annotations

import textwrap

from webcompy.components._generator import StyleDeclaration, StyleDict
from webcompy.exception import WebComPyException


def _strip_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    quote: str | None = None
    while i < n:
        c = text[i]
        if quote is not None:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "\"'":
            quote = c
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _skip_ws(text: str, i: int) -> int:
    n = len(text)
    while i < n and text[i].isspace():
        i += 1
    return i


def _read_key(text: str, start: int) -> tuple[str, int]:
    depth = 0
    bracket = 0
    quote: str | None = None
    i = start
    n = len(text)
    while i < n:
        c = text[i]
        if quote is not None:
            if c == "\\" and i + 1 < n:
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "\"'":
            quote = c
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "[":
            bracket += 1
        elif c == "]":
            bracket -= 1
        elif depth == 0 and bracket == 0 and c in "{;":
            return text[start:i].strip(), i
        i += 1
    return text[start:i].strip(), i


def _find_colon(text: str, start: int, end: int) -> int:
    depth = 0
    bracket = 0
    quote: str | None = None
    i = start
    while i < end:
        c = text[i]
        if quote is not None:
            if c == "\\" and i + 1 < end:
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "\"'":
            quote = c
            i += 1
            continue
        if c == "\\" and i + 1 < end:
            i += 2
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "[":
            bracket += 1
        elif c == "]":
            bracket -= 1
        elif depth == 0 and bracket == 0 and c == ":":
            return i
        i += 1
    return -1


def _read_braced(text: str, open_pos: int) -> tuple[str, int]:
    if open_pos >= len(text) or text[open_pos] != "{":
        raise WebComPyException(f"Expected '{{' at position {open_pos}")
    depth = 1
    i = open_pos + 1
    n = len(text)
    start = i
    quote: str | None = None
    while i < n and depth > 0:
        c = text[i]
        if quote is not None:
            if c == "\\" and i + 1 < n:
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "\"'":
            quote = c
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        raise WebComPyException(f"Unbalanced braces: missing closing '}}' for '{{' at position {open_pos}")
    return text[start : i - 1], i


def _parse_stylesheet(text: str) -> dict[str, StyleDict]:
    result: dict[str, StyleDict] = {}
    i = 0
    n = len(text)
    while True:
        i = _skip_ws(text, i)
        if i >= n:
            break
        selector, pos = _read_key(text, i)
        if not selector:
            if pos < n:
                i = pos + 1
                continue
            break
        if pos < n and text[pos] == "{":
            inner, i = _read_braced(text, pos)
            result[selector] = _parse_block_content(inner)
        else:
            if pos < n:
                i = pos + 1
            else:
                break
    return result


def _parse_block_content(body: str) -> StyleDict:
    result: dict[str, StyleDeclaration] = {}
    i = 0
    n = len(body)
    while True:
        i = _skip_ws(body, i)
        if i >= n:
            break
        key, pos = _read_key(body, i)
        if not key:
            if pos < n:
                i = pos + 1
                continue
            break
        if pos < n and body[pos] == "{":
            inner, i = _read_braced(body, pos)
            result[key] = _parse_block_content(inner)
        elif pos < n and body[pos] == ";":
            colon = _find_colon(body, i, pos)
            if colon != -1:
                name = body[i:colon].strip()
                value = body[colon + 1 : pos].strip()
                while value.endswith(";"):
                    value = value[:-1].rstrip()
                if name:
                    result[name] = value
            i = pos + 1
        else:
            colon = _find_colon(body, i, len(body))
            if colon != -1:
                name = body[i:colon].strip()
                value = body[colon + 1 :].strip()
                while value.endswith(";"):
                    value = value[:-1].rstrip()
                if name:
                    result[name] = value
            break
    return result


def parse_css(text: str) -> dict[str, StyleDict]:
    """Parse a CSS text string into a selector-keyed ``dict[str, StyleDict]``.

    The result mirrors the structure consumed by ``ComponentGenerator.scoped_style``
    and ``reactive_scoped_style``, so existing scoping logic is reused unchanged.

    Processing:
      * ``/* ... */`` comments are stripped (string-literal aware: comments inside
        ``"..."``/``'...'`` are preserved).
      * ``textwrap.dedent`` is applied to normalize triple-quoted indentation.
      * Selectors, combinators, pseudo-classes/elements, at-rules
        (``@media``/``@supports``/``@container``/``@keyframes``), and arbitrarily
        nested rules are recognized.

    The parser is intentionally lenient (no validation/linting). Limitations:
      * Statement at-rules without a block (``@import``, ``@charset``,
        ``@namespace``) are not preserved — they don't fit ``StyleDict`` and are
        not meaningful inside a scoped style.
      * Unbalanced braces raise ``WebComPyException``.

    Args:
        text: CSS source string.

    Returns:
        Selector-keyed dict whose values are ``StyleDict`` blocks.

    """
    cleaned = _strip_comments(text)
    cleaned = textwrap.dedent(cleaned)
    return _parse_stylesheet(cleaned)
