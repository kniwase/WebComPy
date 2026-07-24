from __future__ import annotations

import re

from webcompy.exception import WebComPyException

_KEYFRAMES_RE = re.compile(r"^@(?:-(?:webkit|moz|o)-)?keyframes\b", re.IGNORECASE)
_AT_RULE_NAME_RE = re.compile(r"^@([\w-]+)")
_DECLARATION_BODY_AT_RULES = frozenset({"font-face", "page", "property", "counter-style"})
_COMBINATOR_CHARS = frozenset(",>+~")


def _is_keyframes_rule(selector: str) -> bool:
    return _KEYFRAMES_RE.match(selector.strip()) is not None


def _is_declaration_body_at_rule(selector: str) -> bool:
    match = _AT_RULE_NAME_RE.match(selector.strip())
    return match is not None and match.group(1).lower() in _DECLARATION_BODY_AT_RULES


def _split_selector_parts(selector: str) -> tuple[list[str], list[str]]:
    parts: list[str] = []
    combinators: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(selector)
    paren = 0
    bracket = 0
    quote: str | None = None
    while i < n:
        c = selector[i]
        if quote is not None:
            buf.append(c)
            if c == "\\" and i + 1 < n:
                buf.append(selector[i + 1])
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "\"'":
            quote = c
            buf.append(c)
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            next_char = selector[i + 1]
            buf.append(c)
            buf.append(next_char)
            i += 2
            if next_char in "0123456789abcdefABCDEF":
                for _ in range(5):
                    if i < n and selector[i] in "0123456789abcdefABCDEF":
                        buf.append(selector[i])
                        i += 1
                    else:
                        break
                if i < n and selector[i].isspace():
                    buf.append(selector[i])
                    i += 1
            continue
        if c == "(":
            paren += 1
        elif c == ")":
            paren -= 1
        elif c == "[":
            bracket += 1
        elif c == "]":
            bracket -= 1
        if paren == 0 and bracket == 0:
            if c in _COMBINATOR_CHARS:
                trailing_ws = ""
                while buf and buf[-1].isspace():
                    trailing_ws = buf.pop() + trailing_ws
                j = i + 1
                while j < n and selector[j].isspace():
                    j += 1
                combinators.append(trailing_ws + c + selector[i + 1 : j])
                parts.append("".join(buf))
                buf.clear()
                i = j
                continue
            if c.isspace():
                j = i
                while j < n and selector[j].isspace():
                    j += 1
                if j < n and selector[j] in _COMBINATOR_CHARS:
                    buf.append(c)
                    i += 1
                    continue
                combinators.append(selector[i:j])
                parts.append("".join(buf))
                buf.clear()
                i = j
                continue
        buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts, combinators


def _insert_cid(compound: str, cid: str) -> str:
    i = 0
    n = len(compound)
    paren = 0
    bracket = 0
    quote: str | None = None
    insert_pos = n
    while i < n:
        c = compound[i]
        if quote is not None:
            if c == "\\":
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
        if c == "\\":
            i += 2
            continue
        if c == "(":
            paren += 1
        elif c == ")":
            paren -= 1
        elif c == "[":
            bracket += 1
        elif c == "]":
            bracket -= 1
        elif c == ":" and paren == 0 and bracket == 0 and compound[i : i + 2] == "::":
            insert_pos = i
            break
        i += 1
    return f"{compound[:insert_pos]}[webcompy-cid-{cid}]{compound[insert_pos:]}"


def _contains_top_level_ampersand(selector: str) -> bool:
    i = 0
    n = len(selector)
    paren = 0
    bracket = 0
    quote: str | None = None
    while i < n:
        c = selector[i]
        if quote is not None:
            if c == "\\":
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
        if c == "\\":
            i += 2
            continue
        if c == "(":
            paren += 1
        elif c == ")":
            paren -= 1
        elif c == "[":
            bracket += 1
        elif c == "]":
            bracket -= 1
        elif c == "&" and paren == 0 and bracket == 0:
            return True
        i += 1
    return False


def _raise_nesting_unsupported(selector: str) -> None:
    raise WebComPyException(
        f"CSS nesting with '&' is not supported in scoped styles "
        f"(selector: {selector!r}). Use the nested dict form instead, "
        f"e.g. {{'.btn': {{':hover': {{...}}}}}}."
    )


def _scope_selector(selector: str, cid: str) -> str:
    if _contains_top_level_ampersand(selector):
        _raise_nesting_unsupported(selector)
    parts, combinators = _split_selector_parts(selector)
    out: list[str] = []
    for idx, part in enumerate(parts):
        combinator = combinators[idx] if idx < len(combinators) else ""
        if part:
            out.append(_insert_cid(part, cid) + combinator)
        elif idx == 0:
            out.append(f"*[webcompy-cid-{cid}]{combinator}")
        else:
            out.append(combinator)
    return "".join(out)
