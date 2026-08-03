from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import cast

from webcompy.exception import WebComPyException
from webcompy.template._ast import (
    AttrSpec,
    DirectiveToken,
    ElifDirective,
    ElseDirective,
    EndForDirective,
    EndIfDirective,
    ForDirective,
    ForNode,
    IfDirective,
    IfNode,
    TemplateElement,
    TemplateNode,
    TemplateText,
)
from webcompy.template._holes import LiteralText, protect_lbrace, split_text

_RAW_BLOCK_RE = re.compile(r"\{%\s*raw\s*%\}(.*?)\{%\s*endraw\s*%\}", re.DOTALL)
_RAW_OPEN_RE = re.compile(r"\{%\s*raw\s*%\}")
_COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)


def _preprocess(source: str) -> str:
    def protect_raw(m: re.Match[str]) -> str:
        return protect_lbrace(m.group(1))

    out = _RAW_BLOCK_RE.sub(protect_raw, source)
    if _RAW_OPEN_RE.search(out):
        raise WebComPyException("Unclosed {% raw %} block in template")
    return _COMMENT_RE.sub("", out)


VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "keygen",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

REJECTED_TAGS = frozenset(
    {
        "script",
        "style",
        "iframe",
        "noembed",
        "noframes",
        "xmp",
    }
)


_DIRECTIVE_ARGS = r"(?P<args>(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"|%(?!\})|[^%])*)"

DIRECTIVE_PATTERN = re.compile(rf"\{{%\s*(?P<directive>if|elif|else|endif|for|endfor)\b{_DIRECTIVE_ARGS}%\}}")

_SUPPORTED_DIRECTIVES = frozenset({"if", "elif", "else", "endif", "for", "endfor"})

_KNOWN_UNSUPPORTED_DIRECTIVES = frozenset(
    {
        "extends",
        "block",
        "endblock",
        "macro",
        "endmacro",
        "call",
        "endcall",
        "include",
        "import",
        "from",
        "set",
        "with",
        "endwith",
        "filter",
        "endfilter",
        "do",
        "trans",
        "endtrans",
        "pluralize",
        "autoescape",
        "endautoescape",
        "debug",
    }
)

_GENERIC_DIRECTIVE_RE = re.compile(rf"\{{%\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\b{_DIRECTIVE_ARGS}%\}}")


def _reject_tag(tag: str) -> None:
    raise WebComPyException(
        f"<{tag}> is not allowed in templates. Use scoped_style() for CSS or raw_html() for controlled HTML insertion."
    )


def _parse_for_args(args: str) -> tuple[list[str], str]:
    parts = args.split(" in ", 1)
    if len(parts) != 2:
        raise WebComPyException(f"Invalid {{% for %}} directive: missing ' in ' separator (got {args!r})")
    lhs, rhs = parts
    loop_vars = [v.strip() for v in lhs.split(",") if v.strip()]
    if not loop_vars:
        raise WebComPyException(f"Invalid {{% for %}} directive: missing loop variable (got {args!r})")
    iterable_path = rhs.strip()
    if not iterable_path:
        raise WebComPyException(f"Invalid {{% for %}} directive: missing iterable expression (got {args!r})")
    return loop_vars, iterable_path


def _make_directive(match: re.Match) -> DirectiveToken:
    name = match.group("name")
    args = match.group("args").strip()
    if name == "if":
        return IfDirective(condition=args)
    if name == "elif":
        return ElifDirective(condition=args)
    if name == "else":
        return ElseDirective()
    if name == "endif":
        return EndIfDirective()
    if name == "for":
        loop_vars, iterable_path = _parse_for_args(args)
        return ForDirective(loop_vars=loop_vars, iterable_path=iterable_path)
    return EndForDirective()


def _emit_text_segment(text: str) -> list[TemplateText]:
    sub_parts = split_text(text)
    if not sub_parts:
        return []
    return [TemplateText(parts=sub_parts)]


def _scan_text_for_directives(text_node: TemplateText) -> list[TemplateText | DirectiveToken]:
    mask_to_source: dict[str, str] = {}
    buf: list[str] = []
    for idx, part in enumerate(text_node.parts):
        if isinstance(part, LiteralText):
            buf.append(part.text)
        else:
            mask = f"\x00h{idx}\x00"
            mask_to_source[mask] = part.expr_source
            buf.append(mask)
    masked = "".join(buf)
    pieces: list[TemplateText | DirectiveToken] = []
    pos = 0
    for match in _GENERIC_DIRECTIVE_RE.finditer(masked):
        name = match.group("name")
        if match.start() > pos:
            segment = masked[pos : match.start()]
            for mask, source in mask_to_source.items():
                segment = segment.replace(mask, "{{ " + source + " }}")
            pieces.extend(_emit_text_segment(segment))
        if name in _SUPPORTED_DIRECTIVES:
            pieces.append(_make_directive(match))
        elif name in _KNOWN_UNSUPPORTED_DIRECTIVES:
            raise WebComPyException(f"{{% {name} %}} is not supported in WebComPy templates")
        else:
            raise WebComPyException(f"Unknown template directive: {{% {name} %}}")
        pos = match.end()
    if pos < len(masked):
        segment = masked[pos:]
        for mask, source in mask_to_source.items():
            segment = segment.replace(mask, "{{ " + source + " }}")
        pieces.extend(_emit_text_segment(segment))
    return pieces


_IntermediateChild = TemplateText | TemplateElement | DirectiveToken
_IntermediateChildren = list[_IntermediateChild]


def _split_directives_in_children(
    children: list[TemplateNode],
) -> _IntermediateChildren:
    result: _IntermediateChildren = []
    for child in children:
        if isinstance(child, TemplateText):
            result.extend(_scan_text_for_directives(child))
        elif isinstance(child, TemplateElement):
            new_children = _split_directives_in_children(child.children)
            result.append(
                TemplateElement(
                    tag_name=child.tag_name,
                    attrs=child.attrs,
                    children=cast("list[TemplateNode]", new_children),
                )
            )
        else:
            raise WebComPyException(f"Unexpected node in template children (post-restructure): {type(child).__name__}")
    return result


def _restructure_directives(
    children: _IntermediateChildren,
) -> list[TemplateNode]:
    result: list[TemplateNode] = []
    append_stack: list[list[TemplateNode]] = [result]
    context_stack: list[tuple[str, IfNode | ForNode]] = []

    def cur_target() -> list[TemplateNode]:
        return append_stack[-1]

    for child in children:
        if isinstance(child, TemplateText):
            if child.parts:
                cur_target().append(child)
        elif isinstance(child, TemplateElement):
            element_children = cast("_IntermediateChildren", child.children)
            new_children = _restructure_directives(element_children)
            cur_target().append(TemplateElement(tag_name=child.tag_name, attrs=child.attrs, children=new_children))
        elif isinstance(child, IfDirective):
            if_node = IfNode(branches=[(child.condition, [])])
            cur_target().append(if_node)
            context_stack.append(("if", if_node))
            append_stack.append(if_node.branches[0][1])
        elif isinstance(child, ElifDirective):
            if not context_stack or context_stack[-1][0] != "if":
                raise WebComPyException("{% elif %} outside of {% if %} block")
            if_node = context_stack[-1][1]
            assert isinstance(if_node, IfNode)
            new_branch_body: list[TemplateNode] = []
            if_node.branches.append((child.condition, new_branch_body))
            append_stack.pop()
            append_stack.append(new_branch_body)
        elif isinstance(child, ElseDirective):
            if not context_stack or context_stack[-1][0] != "if":
                raise WebComPyException("{% else %} outside of {% if %} block")
            if_node = context_stack[-1][1]
            assert isinstance(if_node, IfNode)
            new_branch_body: list[TemplateNode] = []
            if_node.branches.append((None, new_branch_body))
            append_stack.pop()
            append_stack.append(new_branch_body)
        elif isinstance(child, EndIfDirective):
            if not context_stack or context_stack[-1][0] != "if":
                raise WebComPyException("{% endif %} without matching {% if %}")
            context_stack.pop()
            append_stack.pop()
        elif isinstance(child, ForDirective):
            for_node = ForNode(loop_vars=child.loop_vars, iterable_path=child.iterable_path, body=[])
            cur_target().append(for_node)
            context_stack.append(("for", for_node))
            append_stack.append(for_node.body)
        elif isinstance(child, EndForDirective):
            if not context_stack or context_stack[-1][0] != "for":
                raise WebComPyException("{% endfor %} without matching {% for %}")
            context_stack.pop()
            append_stack.pop()

    if context_stack:
        unclosed = "{% if %}" if context_stack[-1][0] == "if" else "{% for %}"
        raise WebComPyException(f"Unclosed template directive: {unclosed}")

    return result


RCDATA_ELEMENTS = frozenset({"textarea", "title"})


class TemplateTreeBuilder(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self._source = source
        self._stack: list[TemplateElement] = []
        self._roots: list[TemplateNode] = []

    @property
    def roots(self) -> list[TemplateNode]:
        return self._roots

    def error(self, message: str) -> None:
        raise WebComPyException(f"Template parse error: {message} (source: {self._source!r})")

    def _current(self) -> TemplateElement | None:
        return self._stack[-1] if self._stack else None

    def _make_attr_spec(self, name: str, value: str | None) -> AttrSpec:
        if value is None:
            return AttrSpec(name=name, value=[], is_boolean=True)
        return AttrSpec(name=name, value=split_text(value), is_boolean=False)

    def _push_element(self, tag_name: str, attrs: list[AttrSpec]) -> TemplateElement:
        element = TemplateElement(tag_name=tag_name, attrs=attrs, children=[])
        if self._stack:
            self._stack[-1].children.append(element)
        else:
            self._roots.append(element)
        return element

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in REJECTED_TAGS:
            _reject_tag(tag_lower)
        attr_specs = [self._make_attr_spec(n, v) for n, v in attrs]
        if tag_lower in VOID_ELEMENTS:
            self._push_element(tag_lower, attr_specs)
        else:
            element = self._push_element(tag_lower, attr_specs)
            self._stack.append(element)
        if tag_lower in RCDATA_ELEMENTS:
            self.set_cdata_mode(tag_lower)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        if tag_lower in REJECTED_TAGS:
            _reject_tag(tag_lower)
        attr_specs = [self._make_attr_spec(n, v) for n, v in attrs]
        self._push_element(tag_lower, attr_specs)

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if not self._stack:
            raise WebComPyException(f"Stray closing tag </{tag_lower}> with no matching open element")
        if self._stack[-1].tag_name != tag_lower:
            raise WebComPyException(
                f"Mismatched closing tag </{tag_lower}>: expected </{self._stack[-1].tag_name}> (check element nesting)"
            )
        self._stack.pop()

    def handle_data(self, data: str) -> None:
        parts = split_text(data, strict=True)
        if not parts:
            return
        text_node = TemplateText(parts=parts)
        if self._stack:
            self._stack[-1].children.append(text_node)
        else:
            self._roots.append(text_node)

    @property
    def open_tags(self) -> list[str]:
        return [el.tag_name for el in self._stack]

    def handle_comment(self, data: str) -> None:
        return


def parse_template(source: str) -> list[TemplateNode]:
    source = _preprocess(source)
    builder = TemplateTreeBuilder(source)
    builder.feed(source)
    builder.close()
    if builder.open_tags:
        names = ", ".join(f"<{t}>" for t in builder.open_tags)
        raise WebComPyException(f"Unclosed element(s) at end of template: {names}")
    roots = builder.roots
    split_roots = _split_directives_in_children(roots)
    final_roots = _restructure_directives(split_roots)
    return final_roots
