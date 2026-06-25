from __future__ import annotations

import io
import keyword
import token as _py_token
import tokenize as _py_tokenize
from collections.abc import Iterable

from webcompy.ui.code_block._tokens import Token, TokenType


class PythonLexer:
    name: str = "python"
    aliases: tuple[str, ...] = ("py", "python3")
    file_extensions: tuple[str, ...] = (".py", ".pyw")

    _BUILTINS: frozenset[str] = frozenset(
        {
            "abs",
            "all",
            "any",
            "ascii",
            "bin",
            "bool",
            "bytearray",
            "bytes",
            "callable",
            "chr",
            "classmethod",
            "compile",
            "complex",
            "delattr",
            "dict",
            "dir",
            "divmod",
            "enumerate",
            "eval",
            "exec",
            "filter",
            "float",
            "format",
            "frozenset",
            "getattr",
            "globals",
            "hasattr",
            "hash",
            "help",
            "hex",
            "id",
            "input",
            "int",
            "isinstance",
            "issubclass",
            "iter",
            "len",
            "list",
            "locals",
            "map",
            "max",
            "memoryview",
            "min",
            "next",
            "object",
            "oct",
            "open",
            "ord",
            "pow",
            "print",
            "property",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "setattr",
            "slice",
            "sorted",
            "staticmethod",
            "str",
            "sum",
            "super",
            "tuple",
            "type",
            "vars",
            "zip",
            "__import__",
        }
    )

    _DEF_LIKE: frozenset[str] = frozenset({"def", "class", "async"})

    def __init__(self) -> None:
        self._keyword_names: frozenset[str] = frozenset(keyword.kwlist)
        self._soft_kw: frozenset[str] = frozenset(getattr(keyword, "softkwlist", ()))

    def tokenize(self, code: str) -> Iterable[Token]:
        if not code:
            return
        try:
            tokens = list(_py_tokenize.generate_tokens(io.StringIO(code).readline))
        except (_py_tokenize.TokenError, IndentationError, SyntaxError):
            yield Token(TokenType.IDENTIFIER, code)
            return

        pending_def: str | None = None
        pending_decorator: bool = False
        prev_end: tuple[int, int] = (1, 0)
        pending_function_name: str | None = None

        for tok in tokens:
            start_line, start_col = tok.start
            end_line, end_col = tok.end
            if (start_line, start_col) > prev_end:
                gap = _extract_gap(code, prev_end, (start_line, start_col))
                if gap:
                    yield Token(TokenType.IDENTIFIER, gap)
            prev_end = (end_line, end_col)

            tok_type = tok.type
            tok_string = tok.string
            value: str = tok_string

            if tok_type in (_py_tokenize.ENCODING, _py_token.NEWLINE, _py_token.NL, _py_token.INDENT, _py_token.DEDENT):
                pending_decorator = False
                if value and value.strip():
                    yield Token(TokenType.IDENTIFIER, value)
                continue

            if tok_type == _py_token.COMMENT:
                yield Token(TokenType.COMMENT, value)
                continue

            if tok_type == _py_token.STRING:
                yield Token(TokenType.STRING, value)
                continue

            if tok_type == _py_token.NUMBER:
                pending_decorator = False
                yield Token(TokenType.NUMBER, value)
                continue

            if tok_type == _py_token.OP:
                if value == "@":
                    pending_decorator = True
                if pending_function_name is not None and value == "(":
                    yield Token(TokenType.FUNCTION, pending_function_name)
                    pending_function_name = None
                yield Token(TokenType.OPERATOR, value)
                continue

            if tok_type == _py_token.NAME:
                stripped = tok_string.strip()
                if stripped in self._keyword_names or stripped in self._soft_kw:
                    pending_decorator = False
                    pending_def = stripped if stripped in self._DEF_LIKE else None
                    yield Token(TokenType.KEYWORD, value)
                elif pending_decorator:
                    pending_decorator = False
                    pending_def = None
                    yield Token(TokenType.DECORATOR, value)
                elif stripped in self._BUILTINS:
                    pending_def = None
                    yield Token(TokenType.BUILTIN, value)
                elif pending_def is not None and pending_def in self._DEF_LIKE:
                    pending_def = None
                    pending_function_name = value
                else:
                    pending_def = None
                    yield Token(TokenType.IDENTIFIER, value)
                continue

            pending_decorator = False
            pending_def = None
            if value and value.strip():
                yield Token(TokenType.IDENTIFIER, value)

        if pending_function_name is not None:
            yield Token(TokenType.FUNCTION, pending_function_name)

    def __call__(self, code: str) -> Iterable[Token]:
        return self.tokenize(code)


def _extract_gap(code: str, start: tuple[int, int], end: tuple[int, int]) -> str:
    if code is None or not code:
        return ""
    lines = code.splitlines(keepends=True)
    s_line, s_col = start
    e_line, e_col = end
    if s_line == e_line and s_col == e_col:
        return ""
    if s_line == e_line:
        line = lines[s_line - 1] if 0 < s_line <= len(lines) else ""
        return line[s_col:e_col]
    out: list[str] = []
    for ln in range(s_line, e_line + 1):
        if not (0 < ln <= len(lines)):
            continue
        line = lines[ln - 1]
        if ln == s_line and ln == e_line:
            out.append(line[s_col:e_col])
        elif ln == s_line:
            out.append(line[s_col:])
        elif ln == e_line:
            out.append(line[:e_col])
        else:
            out.append(line)
    return "".join(out)
