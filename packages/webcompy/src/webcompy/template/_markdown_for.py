from __future__ import annotations

import re
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
from webcompy.template._holes import resolve_var
from webcompy.template._parser import DIRECTIVE_PATTERN, _parse_for_args

_EXPRESSION_SPAN_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)
_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
_FENCE_LINE_RE = re.compile(r"^ {0,3}```")
_CODE_SPAN_RE = re.compile(r"`[^`\n]+`")


def _rename_in_expressions(text: str, var_name: str, replacement: str) -> str:
    def _replace_in_span(m: re.Match) -> str:
        span = m.group(0)
        return re.sub(rf"\b{re.escape(var_name)}\b", replacement, span)

    return _EXPRESSION_SPAN_RE.sub(_replace_in_span, text)


def _is_list_body(body_text: str) -> bool:
    for line in body_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if DIRECTIVE_PATTERN.fullmatch(stripped):
            continue
        return bool(_LIST_MARKER_RE.match(line))
    return False


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
    in_fence = False
    for line in source.splitlines(keepends=True):
        line_start, line_end = pos, pos + len(line)
        stripped = line.rstrip("\r\n")
        if in_fence or _FENCE_LINE_RE.match(stripped):
            spans.append((line_start, line_end))
            if _FENCE_LINE_RE.match(stripped):
                in_fence = not in_fence
        else:
            for m in _CODE_SPAN_RE.finditer(stripped):
                spans.append((line_start + m.start(), line_start + m.end()))
        pos = line_end
    return spans


def _tokenize_source(source: str) -> list[_Token]:
    protected = _protected_spans(source)
    tokens: list[_Token] = []
    pos = 0
    for m in DIRECTIVE_PATTERN.finditer(source):
        if any(s <= m.start() < e for s, e in protected):
            continue
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
            try:
                resolved = resolve_var(cond, dict(self._ctx))
            except (KeyError, AttributeError):
                continue
            if isinstance(resolved, SignalBase):
                return [_TextSegment(self._source[if_token.start : self._tokens[self._pos - 1].end])]
            if truth(resolved):
                return branch_body

        return []


def _split_markdown_source(source: str, ctx: Mapping[str, Any]) -> list[_TextSegment | _ForBlock]:
    tokens = _tokenize_source(source)
    if not any(t.kind != "text" for t in tokens):
        return [_TextSegment(source)]
    parser = _SourceParser(tokens, source, ctx)
    result = parser.parse()
    if not result:
        result.append(_TextSegment(source))
    return result


def _expand_directives_in_body(body: str, ctx: dict[str, Any], prefix: str) -> str:
    directives = list(DIRECTIVE_PATTERN.finditer(body))
    if not directives:
        return body

    result: list[str] = []
    pos = 0
    i = 0

    while i < len(directives):
        m = directives[i]
        if m.start() > pos:
            result.append(body[pos : m.start()])

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

            iterable = resolve_var(iterable_path, ctx)
            if isinstance(iterable, SignalBase):
                iterable = iterable.value
            is_dict = isinstance(iterable, dict)
            if is_dict:
                items: list[Any] = list(iterable.items())
            else:
                items = list(iterable)

            for n, item in enumerate(items):
                inner_prefix = f"{prefix}{n}_"
                if len(loop_vars) == 1:
                    ctx[f"{inner_prefix}{loop_vars[0]}"] = item
                elif len(loop_vars) == 2 and is_dict:
                    key, value = item
                    ctx[f"{inner_prefix}{loop_vars[0]}"] = key
                    ctx[f"{inner_prefix}{loop_vars[1]}"] = value
                else:
                    raise WebComPyException(
                        f"Two-variable for-loop requires a dict iterable (got {type(iterable).__name__})"
                    )

                expanded = inner_body
                for var in loop_vars:
                    expanded = _rename_in_expressions(expanded, var, f"{inner_prefix}{var}")
                expanded = _expand_directives_in_body(expanded, ctx, inner_prefix)
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
                        expanded = _expand_directives_in_body(branch_body, ctx, prefix)
                        result.append(expanded)
                        emitted = True
                    break
                try:
                    resolved = resolve_var(cond, ctx)
                    if isinstance(resolved, SignalBase):
                        resolved = resolved.value
                    if truth(resolved):
                        expanded = _expand_directives_in_body(branch_body, ctx, prefix)
                        result.append(expanded)
                        emitted = True
                        break
                except (KeyError, AttributeError):
                    continue

            pos = endif_m.end()
            i = j + 1

        else:
            pos = m.end()
            i += 1

    if pos < len(body):
        result.append(body[pos:])

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
        return resolve_var(self._iterable_path, self._context)

    def _on_set_parent(self) -> None:
        self._iterable = self._resolve_iterable()
        self._children = self._generate_children()

    def _generate_children(self) -> list[ElementAbstract]:
        from webcompy.template import _render_nodes, _strip_directive_paragraphs

        iterable_val = self._iterable.value if isinstance(self._iterable, SignalBase) else self._iterable
        is_dict = isinstance(iterable_val, dict)

        if is_dict:
            items: list[Any] = list(iterable_val.items())
        else:
            items = list(iterable_val)

        if not items:
            return []

        augmented_ctx: dict[str, Any] = dict(self._context)
        markdown_parts: list[str] = []

        for n, item in enumerate(items):
            prefix = f"__wmdf_{n}_"

            if len(self._loop_vars) == 1:
                augmented_ctx[f"{prefix}{self._loop_vars[0]}"] = item
            elif len(self._loop_vars) == 2 and is_dict:
                key, value = item
                augmented_ctx[f"{prefix}{self._loop_vars[0]}"] = key
                augmented_ctx[f"{prefix}{self._loop_vars[1]}"] = value
            else:
                raise WebComPyException(
                    f"Two-variable for-loop requires a dict iterable (got {type(iterable_val).__name__})"
                )

            item_body = self._body_markdown
            for var in self._loop_vars:
                item_body = _rename_in_expressions(item_body, var, f"{prefix}{var}")

            item_body = _expand_directives_in_body(item_body, augmented_ctx, prefix)
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
        for c_idx, child in enumerate(self._children):
            child._node_idx = self._node_idx + c_idx
            if child._mounted is None and not self._hydrated:
                await child._render()
        self._hydrated = False
        _position_element_nodes(self, parent_node, self._node_idx)

        if not self._signal_activated:
            self._signal_activated = True
            if isinstance(self._iterable, SignalBase):
                callback = self._refresh if has_async else self._refresh_sync
                self._add_callback_node(self._iterable.on_after_updating(callback))

    def _refresh_sync(self, *args: Any) -> None:
        _run_refresh_sync(self._refresh, *args)

    async def _refresh(self, *args: Any) -> None:
        parent_node = self._parent._get_node()
        if not parent_node:
            raise WebComPyException(f"'{self.__class__.__name__}' does not have its parent.")
        old_children = self._children
        new_children = self._generate_children()
        self._children = _patch_children(old_children, new_children, self._node_idx)

        should_defer = self._signal_activated
        if should_defer:
            start_defer_after_rendering()
        for c_idx, child in enumerate(self._children):
            child._node_idx = self._node_idx + c_idx
            await child._render()
        if should_defer:
            deferred = end_defer_after_rendering()
            for callback in deferred:
                if iscoroutinefunction(callback):
                    callback = lambda cb=callback: aio_run(cb())
                inject(HOST_PORT_KEY).schedule_macro_task(callback)
        _position_element_nodes(self, parent_node, self._node_idx)
        self._parent._re_index_children(False)
