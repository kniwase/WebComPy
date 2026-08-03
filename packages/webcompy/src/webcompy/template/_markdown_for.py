from __future__ import annotations

import ast
import re
import textwrap
from collections.abc import Mapping
from dataclasses import dataclass
from inspect import iscoroutinefunction
from operator import truth
from typing import Any

from webcompy.aio._aio import aio_run
from webcompy.components._component import (
    end_defer_after_rendering,
    start_defer_after_rendering,
)
from webcompy.di import inject
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._dynamic import (
    DynamicElement,
    _patch_children,
    _position_element_nodes,
    _run_refresh_sync,
    _subtree_has_async_setup,
)
from webcompy.exception import WebComPyException
from webcompy.ports._keys import HOST_PORT_KEY, MARKDOWN_PORT_KEY
from webcompy.signal import SignalBase
from webcompy.signal._computed import _OwnedComputed
from webcompy.template._binder import _make_loop_meta
from webcompy.template._expression import (
    _EvalState,
    compile_expression,
    evaluate,
    resolve_scope,
)
from webcompy.template._holes import (
    LiteralText,
    _path_is_reactive,
    _resolve_segments,
    _scan_hole_end,
    resolve_var,
    split_text,
)
from webcompy.template._markdown_blocks import match_list_item_start
from webcompy.template._parser import (
    _GENERIC_DIRECTIVE_RE,
    _KNOWN_UNSUPPORTED_DIRECTIVES,
    _SUPPORTED_DIRECTIVES,
    DIRECTIVE_PATTERN,
    _parse_for_args,
)

_FENCE_LINE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_CLOSING_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})\s*$")
_CODE_SPAN_RE = re.compile(r"(`+)([^`\n]|`(?!\1))*?\1")
_STRING_LITERAL_RE = re.compile(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"")
_RAW_BLOCK_RE = re.compile(r"\{%\s*raw\s*%\}(.*?)\{%\s*endraw\s*%\}", re.DOTALL)
_ATTR_VALUE_RE = re.compile(
    r"""[a-zA-Z_:][-a-zA-Z0-9_:.]*\s*=\s*"[^"]*"|"""
    r"""[a-zA-Z_:][-a-zA-Z0-9_:.]*\s*=\s*'[^']*'|"""
    r"""[a-zA-Z_:][-a-zA-Z0-9_:.]*\s*=\s*[^\s"'=<>`]+"""
)
_COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--(?!>|->)[\s\S]*?(?<!-)-->")


def _hole_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    i = 0
    n = len(text)
    while i < n - 1:
        if text[i] == "{" and text[i + 1] == "{":
            try:
                end = _scan_hole_end(text, i + 2)
            except WebComPyException:
                end = None
            if end is not None:
                spans.append((i, end + 2))
                i = end + 2
                continue
        i += 1
    return spans


def _rename_expression_regex(expr: str, renames: dict[str, str]) -> str:
    protected: dict[str, str] = {}

    def _stash(m: re.Match[str]) -> str:
        key = f"\x00wc-lit-{len(protected)}\x00"
        protected[key] = m.group(0)
        return key

    text = _STRING_LITERAL_RE.sub(_stash, expr)
    for name, replacement in renames.items():
        text = re.sub(rf"(?<!\.)\b{re.escape(name)}\b", replacement, text)
    for key, original in protected.items():
        text = text.replace(key, original)
    return text


def _rename_expression(expr: str, renames: dict[str, str]) -> str:
    if not renames:
        return expr
    stripped = expr.strip()
    lead_ws = expr[: len(expr) - len(expr.lstrip())]
    trail_ws = expr[len(expr.rstrip()) :]
    try:
        tree = ast.parse(stripped, mode="eval")
    except SyntaxError:
        return _rename_expression_regex(expr, renames)
    byte_lines = stripped.encode("utf-8").split(b"\n")
    line_offsets: list[int] = []
    running = 0
    for line in byte_lines:
        line_offsets.append(running)
        running += len(line) + 1
    targets: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id in renames
            and node.lineno is not None
            and node.col_offset is not None
            and node.end_lineno is not None
            and node.end_col_offset is not None
        ):
            start = line_offsets[node.lineno - 1] + node.col_offset
            end = line_offsets[node.end_lineno - 1] + node.end_col_offset
            targets.append((start, end, renames[node.id]))
    if not targets:
        return expr
    encoded = bytearray(stripped.encode("utf-8"))
    for start, end, repl in sorted(targets, key=lambda t: t[0], reverse=True):
        encoded[start:end] = repl.encode("utf-8")
    return f"{lead_ws}{encoded.decode('utf-8')}{trail_ws}"


def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _apply_renames(text: str, renames: dict[str, str]) -> str:
    if not renames:
        return text
    spans = [(m.start(), m.end()) for m in _RAW_BLOCK_RE.finditer(text)]
    spans.extend(_protected_spans(text))
    stashed: list[str] = []
    chunks: list[str] = []
    pos = 0
    for start, end in _merge_spans(spans):
        chunks.append(text[pos:start])
        chunks.append(f"\x00wc-prot-{len(stashed)}\x00")
        stashed.append(text[start:end])
        pos = end
    chunks.append(text[pos:])
    protected_text = "".join(chunks)
    out: list[str] = []
    for part in split_text(protected_text):
        if isinstance(part, LiteralText):
            out.append(part.text)
        else:
            out.append("{{ " + _rename_expression(part.expr_source, renames) + " }}")
    result = "".join(out)
    for i, original in enumerate(stashed):
        result = result.replace(f"\x00wc-prot-{i}\x00", original)
    return result


def _validate_directives(text: str) -> None:
    """Reject unsupported/unknown directives in Markdown source.

    Code spans, fenced code, ``{% raw %}`` blocks, quoted and unquoted
    attribute values, ``{# #}``/HTML comments, and ``{{ }}`` interpolation
    holes are protected: directive-like spans inside them stay literal,
    mirroring the HTML template path.

    Supported directives are also checked structurally: ``elif``/``else``
    outside an ``if`` (including a for-level ``else``), mismatched or
    unclosed ``if``/``for`` blocks raise ``WebComPyException`` with the same
    messages as the HTML template path. ``{% raw %}``/``{% endraw %}`` pairs
    are tracked for balance: an unclosed ``{% raw %}`` or a stray
    ``{% endraw %}`` raises ``WebComPyException`` so that empty-iterable
    list-body for-loops (which bypass the parser's ``_preprocess`` raw
    validation) still surface the error at compile time.
    """
    stack: list[str] = []
    raw_depth = 0
    for m in _masked_directive_matches(text, _GENERIC_DIRECTIVE_RE):
        name = m.group("name")
        if name == "raw":
            if m.group("args").strip():
                raise WebComPyException("Unknown template directive: {% raw %}")
            raw_depth += 1
            continue
        if name == "endraw":
            if m.group("args").strip():
                raise WebComPyException("Unknown template directive: {% endraw %}")
            if raw_depth == 0:
                raise WebComPyException("{% endraw %} without matching {% raw %}")
            raw_depth -= 1
            continue
        if name in _KNOWN_UNSUPPORTED_DIRECTIVES:
            raise WebComPyException(f"{{% {name} %}} is not supported in WebComPy templates")
        if name not in _SUPPORTED_DIRECTIVES:
            raise WebComPyException(f"Unknown template directive: {{% {name} %}}")
        if name in ("if", "for"):
            stack.append(name)
        elif name in ("elif", "else"):
            if not stack or stack[-1] != "if":
                raise WebComPyException(f"{{% {name} %}} outside of {{% if %}} block")
        elif name == "endif":
            if not stack or stack[-1] != "if":
                raise WebComPyException("{% endif %} without matching {% if %}")
            stack.pop()
        elif name == "endfor":
            if not stack or stack[-1] != "for":
                raise WebComPyException("{% endfor %} without matching {% for %}")
            stack.pop()
    if stack:
        raise WebComPyException(f"Unclosed template directive: {{% {stack[-1]} %}}")
    if raw_depth > 0:
        raise WebComPyException("Unclosed {% raw %} block in Markdown source")


def _is_list_body(body_text: str) -> bool:
    if "\n" in body_text:
        body_text = textwrap.dedent(body_text)
    for line in body_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if DIRECTIVE_PATTERN.fullmatch(stripped):
            continue
        return match_list_item_start(line)
    return False


def _strip_blank_edge_lines(text: str) -> str:
    lines = text.split("\n")
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return "\n".join(lines[start:end])


@dataclass
class _TextSegment:
    text: str


@dataclass
class _ForBlock:
    loop_vars: list[str]
    iterable_path: str
    body_markdown: str


@dataclass
class _Token:
    kind: str
    start: int
    end: int
    args: str


def _protected_spans(source: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    pos = 0
    fence_char: str | None = None
    fence_length = 0
    for line in source.splitlines(keepends=True):
        line_start, line_end = pos, pos + len(line)
        stripped = line.rstrip("\r\n")
        if fence_char is not None:
            spans.append((line_start, line_end))
            m = _CLOSING_FENCE_RE.match(stripped)
            if m is not None and m.group(1)[0] == fence_char and len(m.group(1)) >= fence_length:
                fence_char = None
                fence_length = 0
        else:
            m = _FENCE_LINE_RE.match(stripped)
            if m is not None:
                spans.append((line_start, line_end))
                fence_char = m.group(1)[0]
                fence_length = len(m.group(1))
            else:
                for cm in _CODE_SPAN_RE.finditer(stripped):
                    spans.append((line_start + cm.start(), line_start + cm.end()))
        pos = line_end
    return spans


def _masked_directive_matches(text: str, pattern: re.Pattern[str]) -> list[re.Match[str]]:
    """Directive matches outside protected Markdown/template syntax spans.

    Protected: fenced code blocks, code spans, ``{% raw %}`` blocks, quoted and
    unquoted attribute values, ``{# #}``/HTML comments, and ``{{ }}`` holes.
    """
    protected = _protected_spans(text)
    protected.extend(_hole_spans(text))
    protected.extend((m.start(), m.end()) for m in _RAW_BLOCK_RE.finditer(text))
    protected.extend((m.start(), m.end()) for m in _ATTR_VALUE_RE.finditer(text))
    protected.extend((m.start(), m.end()) for m in _COMMENT_RE.finditer(text))
    protected.extend((m.start(), m.end()) for m in _HTML_COMMENT_RE.finditer(text))
    merged = _merge_spans(protected)
    return [m for m in pattern.finditer(text) if not any(s <= m.start() < e for s, e in merged)]


def _tokenize_source(source: str) -> list[_Token]:
    tokens: list[_Token] = []
    pos = 0
    for m in _masked_directive_matches(source, DIRECTIVE_PATTERN):
        if m.start() > pos:
            tokens.append(_Token("text", pos, m.start(), ""))
        name = m.group("directive")
        args = m.group("args").strip()
        tokens.append(_Token(name, m.start(), m.end(), args))
        pos = m.end()
    if pos < len(source):
        tokens.append(_Token("text", pos, len(source), ""))
    return tokens


class _SourceParser:
    def __init__(self, tokens: list[_Token], source: str, ctx: Mapping[str, Any]) -> None:
        self._tokens = tokens
        self._source = source
        self._ctx = ctx
        self._pos = 0

    def parse(self) -> list[_TextSegment | _ForBlock]:
        return self._parse_block()

    def _parse_block(self) -> list[_TextSegment | _ForBlock]:
        result: list[_TextSegment | _ForBlock] = []
        while self._pos < len(self._tokens):
            token = self._tokens[self._pos]
            if token.kind == "text":
                if token.end > token.start:
                    result.append(_TextSegment(self._source[token.start : token.end]))
                self._pos += 1
            elif token.kind == "for":
                block = self._parse_for()
                if block is not None:
                    result.append(block)
            elif token.kind == "if":
                result.extend(self._parse_if())
            elif token.kind in ("endfor", "endif", "elif", "else"):
                break
            else:
                self._pos += 1
        return result

    def _parse_for(self) -> _TextSegment | _ForBlock | None:
        for_token = self._tokens[self._pos]
        try:
            loop_vars, iterable_path = _parse_for_args(for_token.args)
        except WebComPyException:
            self._pos += 1
            return _TextSegment(self._source[for_token.start : for_token.end])

        depth = 1
        j = self._pos + 1
        while j < len(self._tokens):
            kind = self._tokens[j].kind
            if kind == "for":
                depth += 1
            elif kind == "endfor":
                depth -= 1
                if depth == 0:
                    break
            j += 1

        if j >= len(self._tokens):
            self._pos += 1
            return _TextSegment(self._source[for_token.start : for_token.end])

        endfor_token = self._tokens[j]
        body_text = self._source[for_token.end : endfor_token.start]
        self._pos = j + 1

        if _is_list_body(body_text):
            return _ForBlock(loop_vars, iterable_path, body_text)
        return _TextSegment(self._source[for_token.start : endfor_token.end])

    def _parse_if(self) -> list[_TextSegment | _ForBlock]:
        if_token = self._tokens[self._pos]
        self._pos += 1

        branches: list[tuple[str | None, list[_TextSegment | _ForBlock]]] = []
        current_cond: str | None = if_token.args

        body = self._parse_block()
        branches.append((current_cond, body))

        while self._pos < len(self._tokens):
            token = self._tokens[self._pos]
            if token.kind == "elif":
                current_cond = token.args
                self._pos += 1
                body = self._parse_block()
                branches.append((current_cond, body))
            elif token.kind == "else":
                current_cond = None
                self._pos += 1
                body = self._parse_block()
                branches.append((None, body))
            elif token.kind == "endif":
                self._pos += 1
                break
            else:
                break

        for cond, branch_body in branches:
            if cond is None:
                return branch_body
            is_reactive, evaluated, resolved = _eval_condition(cond, self._ctx)
            if is_reactive:
                return [_TextSegment(self._source[if_token.start : self._tokens[self._pos - 1].end])]
            if not evaluated:
                continue
            if truth(resolved):
                return branch_body

        return []


def _eval_condition(cond: str, ctx: Mapping[str, Any]) -> tuple[bool, bool, Any]:
    """Evaluate a Markdown pre-scan directive condition.

    Returns ``(is_reactive, evaluated, value)`` where ``evaluated`` is False
    when the condition cannot be resolved (missing variable etc.). Supports
    the full safe expression subset (modulo, comparisons, filters), not just
    dotted paths. Never allocates a ``Computed``: plain paths use the
    non-allocating ``_path_is_reactive`` probe plus ``_resolve_segments``,
    and expressions are evaluated once via ``evaluate`` (Signal reads carry
    no active consumer, so no graph edges are created). Expression
    compilation errors propagate as ``WebComPyException`` per the template
    contract (malformed directive expressions are reported at bind time).
    """
    plan = compile_expression(cond)
    if plan.is_plain_path:
        segments = cond.split(".")
        is_reactive = _path_is_reactive(cond, ctx)
        try:
            value = _resolve_segments(segments, ctx)
        except (KeyError, AttributeError):
            return is_reactive, False, None
        return is_reactive, True, value
    scope = resolve_scope(plan, dict(ctx))
    state = _EvalState()
    try:
        value = evaluate(plan, scope, state)
    except (KeyError, AttributeError):
        return False, False, None
    return state.saw_signal, True, value


def _split_markdown_source(source: str, ctx: Mapping[str, Any]) -> list[_TextSegment | _ForBlock]:
    _validate_directives(source)
    tokens = _tokenize_source(source)
    if not any(t.kind != "text" for t in tokens):
        return [_TextSegment(source)]
    parser = _SourceParser(tokens, source, ctx)
    result = parser.parse()
    if not result:
        result.append(_TextSegment(source))
    return result


def _expand_directives_in_body(
    body: str,
    ctx: dict[str, Any],
    prefix: str,
    renames: dict[str, str],
) -> str:
    """Expand nested directives in ``body``, renaming loop-scoped names.

    ``renames`` maps bare names to prefixed names for all enclosing loop scopes.
    Text at the current scope is renamed with ``renames``; each nested for-loop
    body is expanded recursively with an extended mapping where the nested
    loop's variables and ``loop`` metadata shadow outer entries (innermost-wins
    shadowing).
    """
    directives = _masked_directive_matches(body, DIRECTIVE_PATTERN)
    if not directives:
        return _apply_renames(body, renames)

    result: list[str] = []
    pos = 0
    i = 0

    while i < len(directives):
        m = directives[i]
        if m.start() > pos:
            result.append(_apply_renames(body[pos : m.start()], renames))

        name = m.group("directive")

        if name == "for":
            depth = 1
            j = i + 1
            while j < len(directives):
                dj_name = directives[j].group("directive")
                if dj_name == "for":
                    depth += 1
                elif dj_name == "endfor":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1

            if j >= len(directives):
                result.append(body[pos : m.end()])
                pos = m.end()
                i += 1
                continue

            endfor_m = directives[j]
            inner_body = body[m.end() : endfor_m.start()]
            args = m.group("args").strip()
            try:
                loop_vars, iterable_path = _parse_for_args(args)
            except WebComPyException:
                result.append(body[pos : endfor_m.end()])
                pos = endfor_m.end()
                i = j + 1
                continue

            iterable_path = _rename_expression(iterable_path, renames)
            plan = compile_expression(iterable_path)
            if plan.is_plain_path:
                iterable = _resolve_segments(iterable_path.split("."), ctx)
            else:
                scope = resolve_scope(plan, ctx)
                state = _EvalState()
                iterable = evaluate(plan, scope, state)
            is_dict = isinstance(iterable, dict)
            n_vars = len(loop_vars)
            if n_vars == 2:
                if not is_dict:
                    raise WebComPyException(
                        f"Two-variable for-loop requires a dict iterable (got {type(iterable).__name__})"
                    )
                items: list[Any] = list(iterable.items())
            elif n_vars == 1:
                items = list(iterable.values()) if is_dict else list(iterable)
            else:
                raise WebComPyException(f"Invalid for-loop variable count: expected 1 or 2, got {n_vars}")

            total = len(items)
            for n, item in enumerate(items):
                inner_prefix = f"{prefix}{n}_"
                ctx[f"{inner_prefix}loop"] = _make_loop_meta(n, total)
                if n_vars == 1:
                    ctx[f"{inner_prefix}{loop_vars[0]}"] = item
                else:
                    key, value = item
                    ctx[f"{inner_prefix}{loop_vars[0]}"] = key
                    ctx[f"{inner_prefix}{loop_vars[1]}"] = value

                inner_renames = dict(renames)
                inner_renames["loop"] = f"{inner_prefix}loop"
                for var in loop_vars:
                    inner_renames[var] = f"{inner_prefix}{var}"
                expanded = _expand_directives_in_body(inner_body, ctx, inner_prefix, inner_renames)
                result.append(expanded)

            pos = endfor_m.end()
            i = j + 1

        elif name == "if":
            depth = 1
            j = i + 1
            while j < len(directives):
                dj_name = directives[j].group("directive")
                if dj_name == "if":
                    depth += 1
                elif dj_name == "endif":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1

            if j >= len(directives):
                result.append(body[pos : m.end()])
                pos = m.end()
                i += 1
                continue

            endif_m = directives[j]

            branches: list[tuple[str | None, str]] = []
            branch_start = m.end()
            current_cond = m.group("args").strip()
            if_depth = 1

            for k in range(i + 1, j + 1):
                dk = directives[k]
                dk_name = dk.group("directive")
                if dk_name == "if":
                    if_depth += 1
                elif dk_name == "endif":
                    if_depth -= 1

                if if_depth == 1 and dk_name in ("elif", "else"):
                    branch_body = body[branch_start : dk.start()]
                    branches.append((current_cond, branch_body))
                    if dk_name == "elif":
                        current_cond = dk.group("args").strip()
                    elif dk_name == "else":
                        current_cond = None
                    branch_start = dk.end()
                elif if_depth == 0 and dk_name == "endif":
                    branch_body = body[branch_start : dk.start()]
                    branches.append((current_cond, branch_body))
                    break

            emitted = False
            for cond, branch_body in branches:
                if cond is None:
                    if not emitted:
                        expanded = _expand_directives_in_body(branch_body, ctx, prefix, renames)
                        result.append(expanded)
                        emitted = True
                    break
                _, evaluated, resolved = _eval_condition(_rename_expression(cond, renames), ctx)
                if not evaluated:
                    continue
                if truth(resolved):
                    expanded = _expand_directives_in_body(branch_body, ctx, prefix, renames)
                    result.append(expanded)
                    emitted = True
                    break

            pos = endif_m.end()
            i = j + 1

        elif name in ("elif", "else"):
            raise WebComPyException(f"{{% {name} %}} outside of {{% if %}} block")
        else:
            raise WebComPyException(f"{{% {name} %}} without matching {{% if %}} or {{% for %}}")

    if pos < len(body):
        result.append(_apply_renames(body[pos:], renames))

    return "".join(result)


class MarkdownForElement(DynamicElement):
    def __init__(
        self,
        loop_vars: list[str],
        iterable_path: str,
        body_markdown: str,
        context: Mapping[str, Any],
    ) -> None:
        self._loop_vars = loop_vars
        self._iterable_path = iterable_path
        self._body_markdown = body_markdown
        self._context: dict[str, Any] = dict(context)
        self._iterable: Any = None
        self._signal_activated = False
        super().__init__()

    def _resolve_iterable(self) -> Any:
        plan = compile_expression(self._iterable_path)
        if plan.is_plain_path:
            return resolve_var(self._iterable_path, self._context)
        scope = resolve_scope(plan, self._context)
        state = _EvalState()
        value = evaluate(plan, scope, state)
        if state.saw_signal:
            return _OwnedComputed(lambda plan=plan, scope=scope: evaluate(plan, scope))
        return value

    def _on_set_parent(self) -> None:
        self._iterable = self._resolve_iterable()
        if self._children:
            for child in self._children:
                child._parent = self._parent
            return
        self._children = self._generate_children()

    def _generate_children(self) -> list[ElementAbstract]:
        from webcompy.template import _render_nodes, _strip_directive_paragraphs

        iterable_val = self._iterable.value if isinstance(self._iterable, SignalBase) else self._iterable
        is_dict = isinstance(iterable_val, dict)
        n_vars = len(self._loop_vars)

        if n_vars == 2:
            if not is_dict:
                raise WebComPyException(
                    f"Two-variable for-loop requires a dict iterable (got {type(iterable_val).__name__})"
                )
            items: list[Any] = list(iterable_val.items())
        elif n_vars == 1:
            items = list(iterable_val.values()) if is_dict else list(iterable_val)
        else:
            raise WebComPyException(f"Invalid for-loop variable count: expected 1 or 2, got {n_vars}")

        if not items:
            return []

        augmented_ctx: dict[str, Any] = dict(self._context)
        markdown_parts: list[str] = []
        total = len(items)

        for n, item in enumerate(items):
            prefix = f"__wmdf_{n}_"
            augmented_ctx[f"{prefix}loop"] = _make_loop_meta(n, total)

            if n_vars == 1:
                augmented_ctx[f"{prefix}{self._loop_vars[0]}"] = item
            else:
                key, value = item
                augmented_ctx[f"{prefix}{self._loop_vars[0]}"] = key
                augmented_ctx[f"{prefix}{self._loop_vars[1]}"] = value

            renames: dict[str, str] = {"loop": f"{prefix}loop"}
            for var in self._loop_vars:
                renames[var] = f"{prefix}{var}"

            item_body = _expand_directives_in_body(self._body_markdown, augmented_ctx, prefix, renames)
            item_body = _strip_blank_edge_lines(item_body)
            if not item_body.strip():
                continue
            markdown_parts.append(item_body)

        concatenated = "\n".join(markdown_parts)

        parser = inject(MARKDOWN_PORT_KEY)
        html = parser.render(concatenated)
        html = _strip_directive_paragraphs(html)
        nodes = _render_nodes(html, augmented_ctx)

        children: list[ElementAbstract] = []
        for node in nodes:
            if node is None:
                continue
            if isinstance(node, str) and not node.strip():
                continue
            child = self._create_child_element(self._parent, None, node)
            if child is not None:
                children.append(child)
        return children

    async def _render(self) -> None:
        has_async = bool(self._children) and _subtree_has_async_setup(self)
        parent_node = self._parent._get_node()
        idx = self._node_idx
        for child in self._children:
            child._node_idx = idx
            if child._mounted is None and not self._hydrated:
                await child._render()
            idx += child._node_count
        self._hydrated = False
        _position_element_nodes(self, parent_node, self._node_idx)
        self._parent._re_index_children(False)

        if not self._signal_activated:
            self._signal_activated = True
            if isinstance(self._iterable, SignalBase):
                callback = self._refresh if has_async else self._refresh_sync
                self._add_callback_node(self._iterable.on_after_updating(callback))

    def _refresh_sync(self, *args: Any) -> None:
        _run_refresh_sync(self._refresh, *args)

    async def _refresh(self, *args: Any) -> None:
        self._cancel_pending_render_tasks()
        parent_node = self._parent._get_node()
        if not parent_node:
            raise WebComPyException(f"'{self.__class__.__name__}' does not have its parent.")
        old_children = self._children
        new_children = self._generate_children()
        self._children = _patch_children(old_children, new_children, self._node_idx)

        should_defer = self._signal_activated
        if should_defer:
            start_defer_after_rendering()
        idx = self._node_idx
        for child in self._children:
            child._node_idx = idx
            await child._render()
            idx += child._node_count
        if should_defer:
            deferred = end_defer_after_rendering()
            for callback in deferred:
                if iscoroutinefunction(callback):
                    callback = lambda cb=callback: aio_run(cb())
                inject(HOST_PORT_KEY).schedule_macro_task(callback)
        _position_element_nodes(self, parent_node, self._node_idx)
        self._parent._re_index_children(False)
