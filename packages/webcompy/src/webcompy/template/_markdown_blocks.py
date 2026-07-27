"""CommonMark two-phase block parser.

The parsing strategy follows the CommonMark specification
(https://commonmark.org/) Appendix: A parsing strategy.
The structural approach is informed by commonmark.py
(BSD-3-Clause, Copyright (c) 2014 Bibek Kafle, Roland Shoemaker;
based on stmd.js by John MacFarlane). This is an independent
implementation adapted to the WebComPy block model.
"""

from __future__ import annotations

import dataclasses
import html
import re
from collections.abc import Callable

from webcompy.template._holes import protect_lbrace

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
        r"^(?:<[a-zA-Z][a-zA-Z0-9-]*(?:[ \t]+[a-zA-Z_:][\w.:-]*"
        r"(?:[ \t]*=[ \t]*[^ \t\"'=<>`]+|=[ \t]*\"[^\"]*\"|"
        r"=[ \t]*'[^']*')?)*[ \t]*/?>"
        r"|</[a-zA-Z][a-zA-Z0-9-]*[ \t]*>)\s*$",
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
    lines: list[str] = dataclasses.field(default_factory=list)

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
    content = block.string_content
    while True:
        consumed = _parse_reference(content, parser.refmap)
        if not consumed:
            break
        content = content[consumed:]
    block.string_content = content
    if not content.strip() and block.parent is not None:
        block.parent.children.remove(block)
        return
    if _try_convert_to_table(block):
        return


_ALIGNMENT_RE = re.compile(r"^\s*:?-+:?\s*$")
_DELIMITER_CELL_RE = re.compile(r"[: ]+")


def _parse_alignments(delimiter_line: str) -> list[str] | None:
    raw = delimiter_line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|") and not raw.endswith(r"\|"):
        raw = raw[:-1]
    cells = [c.strip() for c in re.split(r"(?<!\\)\|", raw)]
    if not cells or any(not _ALIGNMENT_RE.match(c) for c in cells):
        return None
    aligns: list[str] = []
    for cell in cells:
        left = cell.startswith(":")
        right = cell.endswith(":")
        if left and right:
            aligns.append("center")
        elif right:
            aligns.append("right")
        elif left:
            aligns.append("left")
        else:
            aligns.append("")
    return aligns


def _split_row(row: str) -> list[str]:
    text = row.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith(r"\|"):
        text = text[:-1]
    return [c.strip().replace(r"\|", "|") for c in re.split(r"(?<!\\)\|", text)]


def _try_convert_to_table(block: _Block) -> bool:
    lines = block.string_content.split("\n")
    if block.string_content.endswith("\n"):
        lines = lines[:-1]
    if len(lines) < 2:
        return False
    header_line = lines[0]
    delimiter_line = lines[1]
    body_lines = lines[2:]
    if "|" not in header_line:
        return False
    aligns = _parse_alignments(delimiter_line)
    if aligns is None:
        return False
    header = _split_row(header_line)
    ncols = len(header)
    if len(aligns) != ncols:
        return False
    block.t = "table"
    block.string_content = ""
    block.lines = body_lines
    block.header = header
    block.alignments = aligns
    return True


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
            content = container.string_content
            while True:
                consumed = _parse_reference(content, parser.refmap)
                if not consumed:
                    break
                content = content[consumed:]
            container.string_content = content
            if content.strip():
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


def _continue_code_block(parser: _Parser, container: _Block) -> int:
    indent = parser.indent
    if container.is_fenced:
        match = (
            indent <= 3
            and len(parser.current_line) >= parser.next_nonspace + 1
            and parser.current_line[parser.next_nonspace] == container.fence_char
            and reClosingCodeFence.search(parser.current_line[parser.next_nonspace :])
        )
        if match and len(match.group()) >= container.fence_length:
            parser.finalize(container, parser.line_number)
            return 2
        i = container.fence_offset
        while i > 0 and is_space_or_tab(peek(parser.current_line, parser.offset)):
            parser.advance_offset(1, True)
            i -= 1
        return 0
    if indent >= CODE_INDENT:
        parser.advance_offset(CODE_INDENT, True)
    elif parser.blank:
        parser.advance_next_nonspace()
    else:
        return 1
    return 0


def _finalize_code_block(parser: _Parser, block: _Block) -> None:
    if block.is_fenced:
        content = block.string_content
        newline_pos = content.index("\n")
        first_line = content[0:newline_pos]
        rest = content[newline_pos + 1 :]
        block.info = first_line.strip()
        block.literal = rest
    else:
        block.literal = re.sub(r"(\n *)+$", "\n", block.string_content)
    block.string_content = ""


def _can_contain_code_block(t: str) -> bool:
    return False


_register_block(
    "code_block",
    continue_=_continue_code_block,
    finalize=_finalize_code_block,
    can_contain=_can_contain_code_block,
    accepts_lines=True,
)


def _continue_html_block(parser: _Parser, container: _Block) -> int:
    if parser.blank and container.html_block_type in (6, 7):
        return 1
    return 0


def _finalize_html_block(parser: _Parser, block: _Block) -> None:
    block.literal = re.sub(r"(\n *)+$", "", block.string_content)
    block.string_content = ""


def _can_contain_html_block(t: str) -> bool:
    return False


_register_block(
    "html_block",
    continue_=_continue_html_block,
    finalize=_finalize_html_block,
    can_contain=_can_contain_html_block,
    accepts_lines=True,
)


def _start_html_block(parser: _Parser, container: _Block) -> int:
    if parser.indented:
        return 0
    if peek(parser.current_line, parser.next_nonspace) != "<":
        return 0
    s = parser.current_line[parser.next_nonspace :]
    for block_type in range(1, 8):
        if reHtmlBlockOpen[block_type].search(s) and (block_type < 7 or container.t != "paragraph"):
            parser.close_unmatched_blocks()
            hb = parser.add_child("html_block", parser.offset)
            hb.html_block_type = block_type
            return 2
    return 0


def _start_indented_code_block(parser: _Parser, container: _Block) -> int:
    if parser.indented and parser.tip is not None and parser.tip.t != "paragraph" and not parser.blank:
        parser.advance_offset(CODE_INDENT, True)
        parser.close_unmatched_blocks()
        parser.add_child("code_block", parser.offset)
        return 2
    return 0


BLOCK_STARTS.append(_start_indented_code_block)


def _parse_list_marker(parser: _Parser, container: _Block) -> dict[str, object] | None:
    rest = parser.current_line[parser.next_nonspace :]
    data: dict[str, object] = {
        "type": None,
        "tight": True,
        "bullet_char": None,
        "start": None,
        "delimiter": None,
        "padding": None,
        "marker_offset": parser.indent,
    }
    if parser.indent >= CODE_INDENT:
        return None
    m = reBulletListMarker.search(rest)
    m2 = reOrderedListMarker.search(rest)
    if m:
        data["type"] = "bullet"
        data["bullet_char"] = m.group()[0]
    elif m2 and (container.t != "paragraph" or m2.group(1) == "1"):
        m = m2
        data["type"] = "ordered"
        data["start"] = int(m.group(1))
        data["delimiter"] = m.group(2)
    else:
        return None

    nextc = peek(parser.current_line, parser.next_nonspace + len(m.group()))
    if not (nextc is None or nextc == "\t" or nextc == " "):
        return None

    if container.t == "paragraph" and not re.search(
        reNonSpace, parser.current_line[parser.next_nonspace + len(m.group()) :]
    ):
        return None

    parser.advance_next_nonspace()
    parser.advance_offset(len(m.group()), True)
    spaces_start_col = parser.column
    spaces_start_offset = parser.offset
    while True:
        parser.advance_offset(1, True)
        n = peek(parser.current_line, parser.offset)
        if parser.column - spaces_start_col < 5 and is_space_or_tab(n):
            pass
        else:
            break
    blank_item = peek(parser.current_line, parser.offset) is None
    spaces_after_marker = parser.column - spaces_start_col
    if spaces_after_marker >= 5 or spaces_after_marker < 1 or blank_item:
        data["padding"] = len(m.group()) + 1
        parser.column = spaces_start_col
        parser.offset = spaces_start_offset
        if is_space_or_tab(peek(parser.current_line, parser.offset)):
            parser.advance_offset(1, True)
    else:
        data["padding"] = len(m.group()) + spaces_after_marker

    return data


def _lists_match(list_data: dict[str, object], item_data: dict[str, object]) -> bool:
    return (
        list_data.get("type") == item_data.get("type")
        and list_data.get("delimiter") == item_data.get("delimiter")
        and list_data.get("bullet_char") == item_data.get("bullet_char")
    )


def _ends_with_blank_line(block: _Block | None) -> bool:
    while block is not None:
        if block.last_line_blank:
            return True
        if not block.last_line_checked and block.t in ("list", "item"):
            block.last_line_checked = True
            block = block.last_child
        else:
            block.last_line_checked = True
            break
    return False


def _continue_list(parser: _Parser, container: _Block) -> int:
    return 0


def _finalize_list(parser: _Parser, block: _Block) -> None:
    items = block.children
    for i, item in enumerate(items):
        i_has_next = i + 1 < len(items)
        if _ends_with_blank_line(item) and i_has_next:
            assert block.list_data is not None
            block.list_data["tight"] = False
            return
        for j, sub in enumerate(item.children):
            j_has_next = j + 1 < len(item.children)
            if _ends_with_blank_line(sub) and (i_has_next or j_has_next):
                assert block.list_data is not None
                block.list_data["tight"] = False
                return


def _can_contain_list(t: str) -> bool:
    return t == "item"


_register_block(
    "list",
    continue_=_continue_list,
    finalize=_finalize_list,
    can_contain=_can_contain_list,
    accepts_lines=False,
)


def _continue_item(parser: _Parser, container: _Block) -> int:
    if parser.blank:
        if container.first_child is None:
            return 1
        parser.advance_next_nonspace()
        return 0
    ld = container.list_data
    assert ld is not None
    mo = ld["marker_offset"]
    pd = ld["padding"]
    assert isinstance(mo, int)
    assert isinstance(pd, int)
    if parser.indent >= mo + pd:
        parser.advance_offset(mo + pd, True)
    else:
        return 1
    return 0


def _finalize_item(parser: _Parser, block: _Block) -> None:
    first = block.first_child
    if first is not None and first.t == "paragraph" and first.string_content:
        first_line = first.string_content.split("\n", 1)[0]
        if first_line.startswith("["):
            m = _TASK_MARKER_RE.match(first_line)
            if m is not None:
                checked = m.group(1) != " "
                block.task_checked = checked
                rest = first_line[m.end() :]
                if rest:
                    first.string_content = rest + "\n" + first.string_content[len(first_line) + 1 :]
                else:
                    first.string_content = first.string_content[len(first_line) + 1 :] or ""


def _can_contain_item(t: str) -> bool:
    return t != "item"


_register_block(
    "item",
    continue_=_continue_item,
    finalize=_finalize_item,
    can_contain=_can_contain_item,
    accepts_lines=False,
)


def _start_list_item(parser: _Parser, container: _Block) -> int:
    if not (not parser.indented or container.t == "list"):
        return 0
    data = _parse_list_marker(parser, container)
    if data is None:
        return 0
    parser.close_unmatched_blocks()
    assert parser.tip is not None
    reuse = parser.tip.t == "list" and _lists_match(parser.tip.list_data or {}, data)
    if not reuse:
        new_list = parser.add_child("list", parser.next_nonspace)
        new_list.list_data = data
    item = parser.add_child("item", parser.next_nonspace)
    item.list_data = data
    return 1


def match_list_item_start(line: str) -> bool:
    parser = _Parser()
    parser.current_line = line
    parser.find_next_nonspace()
    if parser.blank:
        return False
    return _parse_list_marker(parser, parser.doc) is not None


_TASK_MARKER_RE = re.compile(r"^\[([ xX])\][ \t]")


def _start_fenced_code_block(parser: _Parser, container: _Block) -> int:
    if parser.indented:
        return 0
    m = reCodeFence.search(parser.current_line[parser.next_nonspace :])
    if m:
        fence_length = len(m.group())
        parser.close_unmatched_blocks()
        code = parser.add_child("code_block", parser.next_nonspace)
        code.is_fenced = True
        code.fence_length = fence_length
        code.fence_char = m.group()[0]
        code.fence_offset = parser.indent
        parser.advance_next_nonspace()
        parser.advance_offset(fence_length, False)
        return 2
    return 0


BLOCK_STARTS.insert(BLOCK_STARTS.index(_start_setext_heading), _start_fenced_code_block)
BLOCK_STARTS.insert(BLOCK_STARTS.index(_start_setext_heading) + 1, _start_html_block)
BLOCK_STARTS.insert(BLOCK_STARTS.index(_start_indented_code_block), _start_list_item)


_ESCAPABLE_CHARS = frozenset(r"""!"#$%&'()*+,./:;<=>?@[\]^_`{|}~-""")
_ENTITY_RE_BLOCKS = re.compile(
    r"\\([!\"#$%&'()*+,./:;<=>?@\[\\\]^_`{|}~-])"
    r"|&((?:#[xX][0-9a-fA-F]{1,8}|#[0-9]{1,9}|[A-Za-z][A-Za-z0-9]{1,31}));",
    re.IGNORECASE,
)


def _resolve_entity_body(body: str) -> str:
    if body[0] == "#":
        cp = int(body[2:], 16) if body[1] in "xX" else int(body[1:])
        if cp == 0 or 0xD800 <= cp <= 0xDFFF or cp > 0x10FFFF:
            return "\ufffd"
        return chr(cp)
    resolved = html.entities.html5.get(body + ";")
    if resolved is None:
        resolved = html.entities.html5.get(body)
    return resolved if resolved is not None else "&" + body + ";"


def _unescape_string(text: str) -> str:
    if not _ENTITY_RE_BLOCKS.search(text):
        return text

    def repl(m: re.Match[str]) -> str:
        if m.group(1) is not None:
            return m.group(1)
        return _resolve_entity_body(m.group(2))

    return _ENTITY_RE_BLOCKS.sub(repl, text)


def _unescape_code_info(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\" and i + 1 < n and text[i + 1] in _ESCAPABLE_CHARS:
            out.append(text[i + 1])
            i += 2
            continue
        out.append(c)
        i += 1
    return html.unescape("".join(out))


def _normalize_uri(uri: str) -> str:
    from urllib.parse import quote

    return quote(uri.encode("utf-8"), safe=";/@:+?=&()%#*,")


def _normalize_label(raw: str) -> str:
    text = raw.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def _spnl(content: str, pos: int) -> int:
    n = 0
    length = len(content)
    while pos + n < length and content[pos + n] in (" ", "\t"):
        n += 1
    if pos + n < length and content[pos + n] == "\n":
        n += 1
        while pos + n < length and content[pos + n] in (" ", "\t"):
            n += 1
    return n


def _parse_reference(content: str, refmap: dict[str, _LinkRef]) -> int:
    if not content or content[0] != "[":
        return 0
    m = re.match(r"\[((?:\\.|[^\[\]])*)\]", content, re.DOTALL)
    if m is None:
        return 0
    label_raw = m.group(1)
    label = _normalize_label(label_raw)
    if not label:
        return 0
    pos = m.end()
    if pos >= len(content) or content[pos] != ":":
        return 0
    pos += 1
    pos += _spnl(content, pos)
    destination = ""
    consumed_dest = 0
    if pos < len(content) and content[pos] == "<":
        m2 = re.match(r"<(.*?)>", content[pos:], re.DOTALL)
        if m2 is None:
            return 0
        destination = m2.group(1)
        consumed_dest = m2.end()
    else:
        depth = 0
        end = 0
        i = pos
        while i < len(content):
            c = content[i]
            if c == "\\" and i + 1 < len(content):
                i += 2
                end = i
                continue
            if c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
            elif c in " \t\n":
                break
            i += 1
            end = i
        if depth != 0 or end == pos:
            return 0
        destination = content[pos:end]
        consumed_dest = end - pos
    pos += consumed_dest
    pos += _spnl(content, pos)
    title = ""
    consumed_title = 0
    has_title = False
    if pos < len(content):
        c = content[pos]
        if c == '"':
            m2 = re.match(r'"((?:\\.|[^"\\])*)"', content[pos:], re.DOTALL)
            if m2 is None:
                return 0
            title = m2.group(1)
            consumed_title = m2.end()
            has_title = True
        elif c == "'":
            m2 = re.match(r"'((?:\\.|[^'\\])*)'", content[pos:], re.DOTALL)
            if m2 is None:
                return 0
            title = m2.group(1)
            consumed_title = m2.end()
            has_title = True
        elif c == "(":
            m2 = re.match(r"\(((?:\\.|[^()\\])*)\)", content[pos:], re.DOTALL)
            if m2 is None:
                return 0
            title = m2.group(1)
            consumed_title = m2.end()
            has_title = True
    pos_after_title = pos + consumed_title
    if has_title:
        check = pos_after_title
        while check < len(content) and content[check] in (" ", "\t"):
            check += 1
        if check < len(content) and content[check] != "\n":
            return 0
    while pos_after_title < len(content) and content[pos_after_title] in (" ", "\t"):
        pos_after_title += 1
    if pos_after_title < len(content) and content[pos_after_title] == "\n":
        pos_after_title += 1
    if label and label not in refmap:
        refmap[label] = _LinkRef(
            destination=_normalize_uri(_unescape_string(destination)),
            title=_unescape_string(title),
        )
    return pos_after_title


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


_TAGFILTER_NAMES = frozenset(
    {"title", "textarea", "style", "xmp", "iframe", "noembed", "noframes", "script", "plaintext"}
)
_TAGFILTER_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9-]*)(?=[\s/>])", re.IGNORECASE)


def apply_tagfilter(text: str) -> str:
    def repl(m: re.Match[str]) -> str:
        if m.group(2).lower() in _TAGFILTER_NAMES:
            return "&lt;" + m.group(1) + m.group(2)
        return m.group(0)

    return _TAGFILTER_RE.sub(repl, text)


def _render(block: _Block, inline: Callable[[str], str], *, tight: bool = False) -> str:
    t = block.t
    if t == "document":
        return "\n".join(_render(c, inline) for c in block.children)
    if t == "paragraph":
        content = block.string_content.rstrip()
        result = inline(content)
        return result if tight else f"<p>{result}</p>"
    if t == "block_quote":
        inner = "\n".join(_render(c, inline) for c in block.children)
        return "<blockquote>\n" + inner + "\n</blockquote>"
    if t == "heading":
        content = block.string_content.rstrip()
        return f"<h{block.level}>{inline(content)}</h{block.level}>"
    if t == "thematic_break":
        return "<hr />"
    if t == "code_block":
        cls = ""
        if block.is_fenced and block.info:
            word = block.info.split()[0] if block.info.split() else ""
            if word:
                word = _unescape_code_info(word)
                cls = f' class="language-{_escape_code_text(word)}"'
        content = protect_lbrace(_escape_code_text(block.literal))
        return f"<pre><code{cls}>{content}</code></pre>"
    if t == "html_block":
        return apply_tagfilter(block.literal)
    if t == "table":
        return _render_table(block, inline)
    if t == "list":
        ld = block.list_data or {}
        list_tight = bool(ld.get("tight", True))
        tag = "ol" if ld.get("type") == "ordered" else "ul"
        start_attr = ""
        if tag == "ol":
            start_val = ld.get("start", 1)
            assert isinstance(start_val, int)
            if start_val != 1:
                start_attr = f' start="{start_val}"'
        items_html = "\n".join(_render(c, inline, tight=list_tight) for c in block.children)
        return f"<{tag}{start_attr}>\n{items_html}\n</{tag}>"
    if t == "item":
        children = block.children
        if not children:
            return "<li></li>"
        checkbox = ""
        if block.task_checked is not None:
            checked_attr = 'checked="" ' if block.task_checked else ""
            checkbox = f'<input {checked_attr}disabled="" type="checkbox"> '
        if tight and children[0].t == "paragraph":
            first_inline = inline(children[0].string_content.rstrip())
            rest = [_render(c, inline, tight=True) for c in children[1:]]
            if not rest:
                return f"<li>{checkbox}{first_inline}</li>"
            inner = f"{checkbox}{first_inline}" + "\n" + "\n".join(rest)
            return f"<li>{inner}\n</li>"
        rendered = "\n".join(_render(c, inline, tight=tight) for c in children)
        return f"<li>\n{checkbox}{rendered}\n</li>"
    raise NotImplementedError(f"unsupported block kind in render: {t}")


def _render_table(block: _Block, inline: Callable[[str], str]) -> str:
    header = block.header
    aligns = block.alignments
    body_lines = block.lines
    ncols = len(header)

    def attr_for(i: int) -> str:
        if i < len(aligns) and aligns[i]:
            return f' align="{aligns[i]}"'
        return ""

    head_cells = "\n".join(f"<th{attr_for(i)}>{inline(header[i])}</th>" for i in range(ncols))
    head = f"<tr>\n{head_cells}\n</tr>"

    body_trs: list[str] = []
    for row_line in body_lines:
        row_cells = _split_row(row_line)
        if len(row_cells) < ncols:
            row_cells = row_cells + [""] * (ncols - len(row_cells))
        elif len(row_cells) > ncols:
            row_cells = row_cells[:ncols]
        cell_strs = "\n".join(f"<td{attr_for(i)}>{inline(row_cells[i])}</td>" for i in range(ncols))
        body_trs.append(f"<tr>\n{cell_strs}\n</tr>")

    if body_trs:
        return "<table>\n<thead>\n" + head + "\n</thead>\n<tbody>\n" + "\n".join(body_trs) + "\n</tbody>\n</table>"
    return "<table>\n<thead>\n" + head + "\n</thead>\n</table>"


def parse_blocks_with_refs(
    source: str,
    inline: Callable[[str, dict[str, _LinkRef]], str],
) -> _ParseResult:
    parser = _Parser()
    doc = parser.parse(source)
    html_out = _render(doc, lambda text: inline(text, parser.refmap))
    return _ParseResult(html=html_out, link_refs=parser.refmap)


def parse_blocks(
    source: str,
    inline: Callable[[str], str],
) -> _ParseResult:
    return parse_blocks_with_refs(source, lambda text, _refs: inline(text))
