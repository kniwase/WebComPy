from __future__ import annotations

import dataclasses
import html
import re
import textwrap
from collections.abc import Callable

CODE_INDENT = 4

reLineEnding = re.compile(r"\r\n|\n|\r")
reMaybeSpecial = re.compile(r"^[#`~*+_=<>0-9-]")
reNonSpace = re.compile(r"[^ \t\f\v\r\n]")
reThematicBreak = re.compile(r"^(?:(?:\*[ \t]*){3,}|(?:_[ \t]*){3,}|(?:-[ \t]*){3,})[ \t]*$")
reATXHeadingMarker = re.compile(r"^#{1,6}(?:[ \t]+|$)")
reCodeFence = re.compile(r"^`{3,}(?!.*`)|^~{3,}")
reClosingCodeFence = re.compile(r"^(?:`{3,}|~{3,})(?= *$)")
reSetextHeadingLine = re.compile(r"^(?:=+|-+)[ \t]*$")
reBulletListMarker = re.compile(r"^[*+-]")
reOrderedListMarker = re.compile(r"^(\d{1,9})([.)])")

reHtmlBlockOpen: list[re.Pattern[str]] = [
    re.compile(r"."),
    re.compile(r"^<(?:script|pre|style|textarea)(?:\s|>|$)", re.IGNORECASE),
    re.compile(r"^<!--"),
    re.compile(r"^<[?]"),
    re.compile(r"^<![A-Z]"),
    re.compile(r"^<!\[CDATA\["),
    re.compile(
        r"^<[/]?(?:address|article|aside|base|basefont|blockquote|body|"
        r"caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|"
        r"fieldset|figcaption|figure|footer|form|frame|frameset|h1|h2|h3|"
        r"h4|h5|h6|head|header|hr|html|iframe|legend|li|link|main|menu|"
        r"menuitem|nav|noframes|ol|optgroup|option|p|param|search|section|"
        r"summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)"
        r"(?:[ \t]|[/]?[>]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"^</?[a-zA-Z][a-zA-Z0-9:-]*(?:[ \t]+[a-zA-Z_:][\w.:-]*"
        r"(?:[ \t]*=[ \t]*[^ \t\"'=<>`]+|=[ \t]*\"[^\"]*\"|"
        r"=[ \t]*'[^']*')?)*[ \t]*/?>\s*$",
        re.IGNORECASE,
    ),
]
reHtmlBlockClose: list[re.Pattern[str]] = [
    re.compile(r"."),
    re.compile(r"</(?:script|pre|style|textarea)>", re.IGNORECASE),
    re.compile(r"-->"),
    re.compile(r"\?>"),
    re.compile(r">"),
    re.compile(r"\]\]>"),
]


def is_blank(s: str) -> bool:
    return re.search(reNonSpace, s) is None


def is_space_or_tab(c: str | None) -> bool:
    return c in (" ", "\t")


def peek(ln: str, pos: int) -> str | None:
    if pos < len(ln):
        return ln[pos]
    return None


@dataclasses.dataclass
class _Block:
    t: str
    parent: _Block | None
    children: list[_Block] = dataclasses.field(default_factory=list)
    is_open: bool = True
    start_line: int = 0
    string_content: str = ""
    literal: str = ""
    level: int = 0
    is_fenced: bool = False
    fence_char: str = ""
    fence_length: int = 0
    fence_offset: int = 0
    info: str = ""
    html_block_type: int = 0
    list_data: dict[str, object] | None = None
    last_line_blank: bool = False
    last_line_checked: bool = False
    task_checked: bool | None = None
    alignments: list[str] = dataclasses.field(default_factory=list)
    header: list[str] = dataclasses.field(default_factory=list)

    @property
    def last_child(self) -> _Block | None:
        return self.children[-1] if self.children else None

    @property
    def first_child(self) -> _Block | None:
        return self.children[0] if self.children else None


@dataclasses.dataclass
class _LinkRef:
    destination: str
    title: str


@dataclasses.dataclass
class _ParseResult:
    html: str
    link_refs: dict[str, _LinkRef] = dataclasses.field(default_factory=dict)


_ContinueFn = Callable[["_Parser", _Block], int]
_FinalizeFn = Callable[["_Parser", _Block], None]
_CanContainFn = Callable[[str], bool]
_StartFn = Callable[["_Parser", _Block], int]

_CONTINUE: dict[str, _ContinueFn] = {}
_FINALIZE: dict[str, _FinalizeFn] = {}
_CAN_CONTAIN: dict[str, _CanContainFn] = {}
_ACCEPTS_LINES: set[str] = set()
BLOCK_STARTS: list[_StartFn] = []


def _register_block(
    t: str,
    *,
    continue_: _ContinueFn,
    finalize: _FinalizeFn,
    can_contain: _CanContainFn,
    accepts_lines: bool,
) -> None:
    _CONTINUE[t] = continue_
    _FINALIZE[t] = finalize
    _CAN_CONTAIN[t] = can_contain
    if accepts_lines:
        _ACCEPTS_LINES.add(t)


def _continue_document(parser: _Parser, container: _Block) -> int:
    return 0


def _finalize_document(parser: _Parser, block: _Block) -> None:
    pass


def _can_contain_document(t: str) -> bool:
    return t != "item"


def _continue_paragraph(parser: _Parser, container: _Block) -> int:
    return 1 if parser.blank else 0


def _finalize_paragraph(parser: _Parser, block: _Block) -> None:
    pass


def _can_contain_paragraph(t: str) -> bool:
    return False


_register_block(
    "document",
    continue_=_continue_document,
    finalize=_finalize_document,
    can_contain=_can_contain_document,
    accepts_lines=False,
)
_register_block(
    "paragraph",
    continue_=_continue_paragraph,
    finalize=_finalize_paragraph,
    can_contain=_can_contain_paragraph,
    accepts_lines=True,
)


def _continue_block_quote(parser: _Parser, container: _Block) -> int:
    ln = parser.current_line
    if not parser.indented and peek(ln, parser.next_nonspace) == ">":
        parser.advance_next_nonspace()
        parser.advance_offset(1, False)
        if is_space_or_tab(peek(ln, parser.offset)):
            parser.advance_offset(1, True)
    else:
        return 1
    return 0


def _finalize_block_quote(parser: _Parser, block: _Block) -> None:
    pass


def _can_contain_block_quote(t: str) -> bool:
    return t != "item"


_register_block(
    "block_quote",
    continue_=_continue_block_quote,
    finalize=_finalize_block_quote,
    can_contain=_can_contain_block_quote,
    accepts_lines=False,
)


def _start_block_quote(parser: _Parser, container: _Block) -> int:
    if not parser.indented and peek(parser.current_line, parser.next_nonspace) == ">":
        parser.advance_next_nonspace()
        parser.advance_offset(1, False)
        if is_space_or_tab(peek(parser.current_line, parser.offset)):
            parser.advance_offset(1, True)
        parser.close_unmatched_blocks()
        parser.add_child("block_quote", parser.next_nonspace)
        return 1
    return 0


BLOCK_STARTS.insert(0, _start_block_quote)


def _continue_heading(parser: _Parser, container: _Block) -> int:
    return 1


def _finalize_heading(parser: _Parser, block: _Block) -> None:
    pass


def _can_contain_heading(t: str) -> bool:
    return False


_register_block(
    "heading",
    continue_=_continue_heading,
    finalize=_finalize_heading,
    can_contain=_can_contain_heading,
    accepts_lines=False,
)


def _continue_thematic_break(parser: _Parser, container: _Block) -> int:
    return 1


def _finalize_thematic_break(parser: _Parser, block: _Block) -> None:
    pass


def _can_contain_thematic_break(t: str) -> bool:
    return False


_register_block(
    "thematic_break",
    continue_=_continue_thematic_break,
    finalize=_finalize_thematic_break,
    can_contain=_can_contain_thematic_break,
    accepts_lines=False,
)


def _start_atx_heading(parser: _Parser, container: _Block) -> int:
    if not parser.indented:
        m = reATXHeadingMarker.search(parser.current_line[parser.next_nonspace :])
        if m:
            parser.advance_next_nonspace()
            parser.advance_offset(len(m.group()), False)
            parser.close_unmatched_blocks()
            heading = parser.add_child("heading", parser.next_nonspace)
            heading.level = len(m.group().strip())
            text = parser.current_line[parser.offset :]
            text = re.sub(r"^[ \t]*#+[ \t]*$", "", text)
            text = re.sub(r"[ \t]+#+[ \t]*$", "", text)
            heading.string_content = text.strip()
            parser.advance_offset(len(parser.current_line) - parser.offset, False)
            return 2
    return 0


def _start_setext_heading(parser: _Parser, container: _Block) -> int:
    if not parser.indented and container.t == "paragraph":
        m = reSetextHeadingLine.search(parser.current_line[parser.next_nonspace :])
        if m:
            parser.close_unmatched_blocks()
            if container.string_content:
                container.t = "heading"
                container.level = 1 if m.group()[0] == "=" else 2
                parser.tip = container
                parser.advance_offset(len(parser.current_line) - parser.offset, False)
                return 2
            return 0
    return 0


def _start_thematic_break(parser: _Parser, container: _Block) -> int:
    if not parser.indented and reThematicBreak.search(parser.current_line[parser.next_nonspace :]):
        parser.close_unmatched_blocks()
        parser.add_child("thematic_break", parser.next_nonspace)
        parser.advance_offset(len(parser.current_line) - parser.offset, False)
        return 2
    return 0


BLOCK_STARTS.append(_start_atx_heading)
BLOCK_STARTS.append(_start_setext_heading)
BLOCK_STARTS.append(_start_thematic_break)


def _parse_reference(content: str, refmap: dict[str, _LinkRef]) -> int:
    return 0


class _Parser:
    def __init__(self) -> None:
        self.doc = _Block(t="document", parent=None, start_line=1)
        self.tip: _Block | None = self.doc
        self.oldtip: _Block | None = self.doc
        self.current_line = ""
        self.line_number = 0
        self.offset = 0
        self.column = 0
        self.next_nonspace = 0
        self.next_nonspace_column = 0
        self.indent = 0
        self.indented = False
        self.blank = False
        self.partially_consumed_tab = False
        self.all_closed = True
        self.last_matched_container = self.doc
        self.refmap: dict[str, _LinkRef] = {}
        self.last_line_length = 0

    def add_line(self) -> None:
        if self.partially_consumed_tab:
            self.offset += 1
            chars_to_tab = 4 - (self.column % 4)
            if self.tip is not None:
                self.tip.string_content += " " * chars_to_tab
        if self.tip is not None:
            self.tip.string_content += self.current_line[self.offset :] + "\n"

    def add_child(self, tag: str, offset: int) -> _Block:
        assert self.tip is not None
        while not _CAN_CONTAIN[self.tip.t](tag):
            self.finalize(self.tip, self.line_number - 1)
            assert self.tip is not None
        new_block = _Block(t=tag, parent=self.tip, start_line=self.line_number)
        self.tip.children.append(new_block)
        self.tip = new_block
        return new_block

    def close_unmatched_blocks(self) -> None:
        if not self.all_closed:
            while self.oldtip is not None and self.oldtip is not self.last_matched_container:
                parent = self.oldtip.parent
                self.finalize(self.oldtip, self.line_number - 1)
                self.oldtip = parent
            self.all_closed = True

    def find_next_nonspace(self) -> None:
        current_line = self.current_line
        i = self.offset
        cols = self.column
        c = current_line[i] if i < len(current_line) else ""
        while c != "":
            if c == " ":
                i += 1
                cols += 1
            elif c == "\t":
                i += 1
                cols += 4 - (cols % 4)
            else:
                break
            c = current_line[i] if i < len(current_line) else ""
        self.blank = c == ""
        self.next_nonspace = i
        self.next_nonspace_column = cols
        self.indent = self.next_nonspace_column - self.column
        self.indented = self.indent >= CODE_INDENT

    def advance_next_nonspace(self) -> None:
        self.offset = self.next_nonspace
        self.column = self.next_nonspace_column
        self.partially_consumed_tab = False

    def advance_offset(self, count: int, columns: bool) -> None:
        current_line = self.current_line
        c = current_line[self.offset] if self.offset < len(current_line) else None
        while count > 0 and c is not None:
            if c == "\t":
                chars_to_tab = 4 - (self.column % 4)
                if columns:
                    self.partially_consumed_tab = chars_to_tab > count
                    chars_to_advance = min(count, chars_to_tab)
                    self.column += chars_to_advance
                    self.offset += 0 if self.partially_consumed_tab else 1
                    count -= chars_to_advance
                else:
                    self.partially_consumed_tab = False
                    self.column += chars_to_tab
                    self.offset += 1
                    count -= 1
            else:
                self.partially_consumed_tab = False
                self.offset += 1
                self.column += 1
                count -= 1
            c = current_line[self.offset] if self.offset < len(current_line) else None

    def incorporate_line(self, ln: str) -> None:
        all_matched = True
        container = self.doc
        self.oldtip = self.tip
        self.offset = 0
        self.column = 0
        self.blank = False
        self.partially_consumed_tab = False
        self.line_number += 1

        if "\u0000" in ln:
            ln = ln.replace("\0", "\ufffd")

        self.current_line = ln

        while True:
            last_child = container.last_child
            if not (last_child is not None and last_child.is_open):
                break
            container = last_child
            self.find_next_nonspace()
            rv = _CONTINUE[container.t](self, container)
            if rv == 0:
                pass
            elif rv == 1:
                all_matched = False
            elif rv == 2:
                self.last_line_length = len(ln)
                return
            else:
                raise ValueError("continue_ returned illegal value")
            if not all_matched:
                container = container.parent  # type: ignore[assignment]
                break

        self.all_closed = container is self.oldtip
        self.last_matched_container = container

        matched_leaf = container.t != "paragraph" and container.t in _ACCEPTS_LINES
        starts = BLOCK_STARTS
        starts_len = len(starts)

        while not matched_leaf:
            self.find_next_nonspace()
            if not self.indented and not re.search(reMaybeSpecial, ln[self.next_nonspace :]):
                self.advance_next_nonspace()
                break
            i = 0
            matched_start = False
            while i < starts_len:
                res = starts[i](self, container)
                if res == 1:
                    container = self.tip  # type: ignore[assignment]
                    matched_start = True
                    break
                elif res == 2:
                    container = self.tip  # type: ignore[assignment]
                    matched_leaf = True
                    matched_start = True
                    break
                else:
                    i += 1
            if not matched_start:
                self.advance_next_nonspace()
                break

        if not self.all_closed and not self.blank and self.tip is not None and self.tip.t == "paragraph":
            self.add_line()
        else:
            self.close_unmatched_blocks()
            if self.blank and container.last_child is not None:
                container.last_child.last_line_blank = True
            t = container.t
            last_line_blank = self.blank and not (
                t == "block_quote"
                or (t == "code_block" and container.is_fenced)
                or (t == "item" and container.first_child is None and container.start_line == self.line_number)
            )
            cont: _Block | None = container
            while cont is not None:
                cont.last_line_blank = last_line_blank
                cont = cont.parent

            if t in _ACCEPTS_LINES:
                self.add_line()
                if (
                    t == "html_block"
                    and 1 <= container.html_block_type <= 5
                    and re.search(
                        reHtmlBlockClose[container.html_block_type],
                        self.current_line[self.offset :],
                    )
                ):
                    self.finalize(container, self.line_number)
            elif self.offset < len(ln) and not self.blank:
                container = self.add_child("paragraph", self.offset)
                self.advance_next_nonspace()
                self.add_line()

        self.last_line_length = len(ln)

    def finalize(self, block: _Block, line_number: int) -> None:
        above = block.parent
        block.is_open = False
        _FINALIZE[block.t](self, block)
        self.tip = above

    def parse(self, source: str) -> _Block:
        self.doc = _Block(t="document", parent=None, start_line=1)
        self.tip = self.doc
        self.oldtip = self.doc
        self.refmap = {}
        self.line_number = 0
        self.last_line_length = 0
        self.offset = 0
        self.column = 0
        self.last_matched_container = self.doc
        self.current_line = ""
        lines = re.split(reLineEnding, source)
        length = len(lines)
        if len(source) > 0 and source[-1] == "\n":
            length -= 1
        for i in range(length):
            self.incorporate_line(lines[i])
        while self.tip is not None:
            self.finalize(self.tip, length)
        return self.doc


def _escape_code_text(text: str) -> str:
    return html.escape(text, quote=False).replace('"', "&quot;")


def _render(block: _Block, inline: Callable[[str], str]) -> str:
    if block.t == "document":
        return "\n".join(_render(c, inline) for c in block.children)
    if block.t == "paragraph":
        content = block.string_content
        if content.endswith("\n"):
            content = content[:-1]
        return "<p>" + inline(content) + "</p>"
    if block.t == "block_quote":
        inner = "\n".join(_render(c, inline) for c in block.children)
        return "<blockquote>\n" + inner + "\n</blockquote>"
    if block.t == "heading":
        content = block.string_content
        if content.endswith("\n"):
            content = content[:-1]
        return f"<h{block.level}>{inline(content)}</h{block.level}>"
    if block.t == "thematic_break":
        return "<hr />"
    raise NotImplementedError(f"unsupported block kind in render: {block.t}")


def parse_blocks(
    source: str,
    inline: Callable[[str], str],
) -> _ParseResult:
    normalized = textwrap.dedent(source) if "\n" in source else source
    parser = _Parser()
    doc = parser.parse(normalized)
    html_out = _render(doc, inline)
    return _ParseResult(html=html_out, link_refs=parser.refmap)
