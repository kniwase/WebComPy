"""CommonMark/GFM inline parser.

The parsing strategy follows the CommonMark specification
(https://commonmark.org/) Appendix: "Phase 2: inline structure".
The structural approach is informed by commonmark.py
(BSD-3-Clause, Copyright (c) 2014 Bibek Kafle, Roland Shoemaker;
based on stmd.js by John MacFarlane). This is an independent
implementation adapted to the WebComPy inline model, extended with
the GFM inline extensions (strikethrough, autolinks, disallowed raw
HTML).
"""

from __future__ import annotations

import html
import re
from urllib.parse import quote

from webcompy.template._holes import protect_lbrace
from webcompy.template._markdown_blocks import _LinkRef, _normalize_label, apply_tagfilter

ESCAPABLE = r'[!"#$%&\'()*+,./:;<=>?@[\\\]^_`{|}~-]'
ESCAPED_CHAR = "\\\\" + ESCAPABLE
ENTITY = r"&(?:#[xX][0-9a-fA-F]{1,6}|#[0-9]{1,7}|[A-Za-z][A-Za-z0-9]{1,31});"

reEscapable = re.compile("^" + ESCAPABLE)
reEntityHere = re.compile("^" + ENTITY, re.IGNORECASE)
reTicks = re.compile(r"`+")
reTicksHere = re.compile(r"^`+")
reEmailAutolink = re.compile(
    r"^<([a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
    r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*)>"
)
reAutolink = re.compile(r"^<[A-Za-z][A-Za-z0-9.+-]{1,31}:[^<>\x00-\x20]*>", re.IGNORECASE)
reLinkDestinationBraces = re.compile(r"^(?:<(?:[^<>\n\\\x00]|\\.)*>)")
reLinkTitle = re.compile(
    '^(?:"(' + ESCAPED_CHAR + r'|[^"\x00])*"'
    "|'(" + ESCAPED_CHAR + r"|[^'\x00])*'"
    r"|\((" + ESCAPED_CHAR + r"|[^()\x00])*\))"
)
reLinkLabel = re.compile(r"^\[(?:[^\\\[\]]|\\.){0,1000}\]")
reSpnl = re.compile(r"^ *(?:\n *)?")
reSpaceAtEndOfLine = re.compile(r"^ *(?:\n|$)")
reWhitespaceChar = re.compile(r"^[ \t\n\x0b\x0c\x0d]")
reUnicodeWhitespaceChar = re.compile(r"^\s")
reFinalSpace = re.compile(r" *$")
reInitialSpace = re.compile(r"^ *")
reBackslashOrAmp = re.compile(r"[\\&]")
reEntityOrEscapedChar = re.compile(ESCAPED_CHAR + "|" + ENTITY, re.IGNORECASE)

rePunctuation = re.compile(
    r'[!"#$%&\'()*+,\-./:;<=>?@\[\]\\^_`{|}~\xA1\xA7\xAB\xB6\xB7\xBB'
    r"\xBF\u037E\u0387\u055A-\u055F\u0589\u058A\u05BE\u05C0\u05C3"
    r"\u05C6\u05F3\u05F4\u0609\u060A\u060C\u060D\u061B\u061E\u061F"
    r"\u066A-\u066D\u06D4\u0700-\u070D\u07F7-\u07F9\u0830-\u083E"
    r"\u085E\u0964\u0965\u0970\u0AF0\u0DF4\u0E4F\u0E5A\u0E5B\u0F04-\u0F12"
    r"\u0F14\u0F3A-\u0F3D\u0F85\u0FD0-\u0FD4\u0FD9\u0FDA\u104A-\u104F\u10FB"
    r"\u1360-\u1368\u1400\u166D\u166E\u169B\u169C\u16EB-\u16ED\u1735\u1736"
    r"\u17D4-\u17D6\u17D8-\u17DA\u1800-\u180A\u1944\u1945\u1A1E\u1A1F"
    r"\u2CF9-\u2CFC\u2CFE\u2CFF\u2D70\u2E00-\u2E2E\u2E30-\u2E42"
    r"\u3001-\u3003\u3008-\u3011\u3014-\u301F\u3030\u303D\u30A0\u30FB"
    r"\uFD3E\uFD3F\uFE10-\uFE19\uFE30-\uFE52\uFE54-\uFE61\uFE63"
    r"\uFE68\uFE6A\uFE6B\uFF01-\uFF03\uFF05-\uFF0A\uFF0C-\uFF0F"
    r"\uFF1A\uFF1B\uFF1F\uFF20\uFF3B-\uFF3D\uFF3F\uFF5B\uFF5D\uFF5F-\uFF65]"
)

reMain = re.compile(r"^[^\n`\[\]\\!<&*_~]+", re.MULTILINE)

TAGNAME = "[A-Za-z][A-Za-z0-9-]*"
ATTRIBUTENAME = "[a-zA-Z_:][a-zA-Z0-9:._-]*"
UNQUOTEDVALUE = "[^\"'=<>`\x00-\x20]+"
SINGLEQUOTEDVALUE = "'[^']*'"
DOUBLEQUOTEDVALUE = '"[^"]*"'
ATTRIBUTEVALUE = "(?:" + UNQUOTEDVALUE + "|" + SINGLEQUOTEDVALUE + "|" + DOUBLEQUOTEDVALUE + ")"
ATTRIBUTEVALUESPEC = "(?:" + r"\s*" + "=" + r"\s*" + ATTRIBUTEVALUE + ")"
ATTRIBUTE = "(?:" + r"\s+" + ATTRIBUTENAME + ATTRIBUTEVALUESPEC + "?)"
OPENTAG = "<" + TAGNAME + ATTRIBUTE + "*" + r"\s*/?>"
CLOSETAG = "</" + TAGNAME + r"\s*[>]"
HTMLCOMMENT = "<!---->|<!--(?:-?[^>-])(?:-?[^-])*-->"
PROCESSINGINSTRUCTION = "[<][?].*?[?][>]"
DECLARATION = "<![A-Z]+" + r"\s+[^>]*>"
CDATA = r"<!\[CDATA\[[\s\S]*?\]\]>"
HTMLTAG = (
    "(?:"
    + OPENTAG
    + "|"
    + CLOSETAG
    + "|"
    + HTMLCOMMENT
    + "|"
    + PROCESSINGINSTRUCTION
    + "|"
    + DECLARATION
    + "|"
    + CDATA
    + ")"
)
reHtmlTag = re.compile("^" + HTMLTAG, re.IGNORECASE)


def _resolve_entity_full(text: str) -> str:
    body = text[1:-1]
    if body[0] == "#":
        cp = int(body[2:], 16) if body[1] in "xX" else int(body[1:])
        if cp == 0 or 0xD800 <= cp <= 0xDFFF or cp > 0x10FFFF:
            return "\ufffd"
        return chr(cp)
    resolved = html.entities.html5.get(body + ";")
    if resolved is None:
        resolved = html.entities.html5.get(body)
    return resolved if resolved is not None else text


def unescape_string(s: str) -> str:
    if re.search(reBackslashOrAmp, s):
        return re.sub(
            reEntityOrEscapedChar,
            lambda m: m.group(0)[1:] if m.group(0)[0] == "\\" else _resolve_entity_full(m.group(0)),
            s,
        )
    return s


def normalize_uri(uri: str) -> str:
    try:
        return quote(uri.encode("utf-8"), safe=";/@:+?=&()%#*,")
    except UnicodeDecodeError:
        return quote(uri.encode("utf-8"))


_XMLSPECIAL = re.compile(r'[&<>"]')
_UNSAFE_MAP = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}


def escape_xml(s: str | None) -> str:
    if not s:
        return ""
    if re.search(_XMLSPECIAL, s):
        return re.sub(_XMLSPECIAL, lambda m: _UNSAFE_MAP[m.group(0)], s)
    return s


class _Delim:
    __slots__ = ("can_close", "can_open", "cc", "node", "numdelims", "nxt", "origdelims", "previous")

    def __init__(
        self,
        cc: str,
        numdelims: int,
        node: _Node,
        can_open: bool,
        can_close: bool,
        previous: _Delim | None,
    ) -> None:
        self.cc = cc
        self.numdelims = numdelims
        self.origdelims = numdelims
        self.node = node
        self.previous = previous
        self.nxt: _Delim | None = None
        self.can_open = can_open
        self.can_close = can_close


class _Bracket:
    __slots__ = (
        "active",
        "bracket_after",
        "image",
        "index",
        "node",
        "previous",
        "previous_delimiter",
    )

    def __init__(
        self,
        node: _Node,
        index: int,
        image: bool,
        previous: _Bracket | None,
        previous_delimiter: _Delim | None,
    ) -> None:
        self.node = node
        self.previous = previous
        self.previous_delimiter = previous_delimiter
        self.index = index
        self.image = image
        self.active = True
        self.bracket_after = False


class _Node:
    __slots__ = (
        "destination",
        "first_child",
        "is_autolink",
        "last_child",
        "literal",
        "nxt",
        "parent",
        "prv",
        "t",
        "title",
    )

    def __init__(self, t: str, literal: str = "") -> None:
        self.t = t
        self.literal = literal
        self.parent: _Node | None = None
        self.first_child: _Node | None = None
        self.last_child: _Node | None = None
        self.prv: _Node | None = None
        self.nxt: _Node | None = None
        self.destination: str = ""
        self.title: str = ""
        self.is_autolink: bool = False

    def append_child(self, child: _Node) -> None:
        child.unlink()
        child.parent = self
        if self.last_child is not None:
            self.last_child.nxt = child
            child.prv = self.last_child
            self.last_child = child
        else:
            self.first_child = child
            self.last_child = child

    def insert_after(self, sibling: _Node) -> None:
        sibling.unlink()
        sibling.nxt = self.nxt
        if sibling.nxt is not None:
            sibling.nxt.prv = sibling
        sibling.prv = self
        self.nxt = sibling
        sibling.parent = self.parent
        if sibling.nxt is None and sibling.parent is not None:
            sibling.parent.last_child = sibling

    def unlink(self) -> None:
        if self.prv is not None:
            self.prv.nxt = self.nxt
        elif self.parent is not None:
            self.parent.first_child = self.nxt
        if self.nxt is not None:
            self.nxt.prv = self.prv
        elif self.parent is not None:
            self.parent.last_child = self.prv
        self.parent = None
        self.nxt = None
        self.prv = None


def _text(s: str) -> _Node:
    return _Node("text", s)


class _InlineParser:
    def __init__(self, refmap: dict[str, _LinkRef]) -> None:
        self.subject = ""
        self.pos = 0
        self.refmap = refmap
        self.delimiters: _Delim | None = None
        self.brackets: _Bracket | None = None

    def match(self, regex: re.Pattern[str]) -> str | None:
        m = regex.search(self.subject[self.pos :])
        if m is None:
            return None
        self.pos += m.end()
        return m.group(0)

    def peek(self) -> str | None:
        if self.pos < len(self.subject):
            return self.subject[self.pos]
        return None

    def spnl(self) -> bool:
        self.match(reSpnl)
        return True

    def parse_newline(self, block: _Node) -> bool:
        self.pos += 1
        lastc = block.last_child
        if lastc is not None and lastc.t == "text" and lastc.literal and lastc.literal[-1] == " ":
            linebreak = len(lastc.literal) >= 2 and lastc.literal[-2] == " "
            lastc.literal = re.sub(reFinalSpace, "", lastc.literal)
            if linebreak:
                block.append_child(_Node("linebreak"))
            else:
                block.append_child(_Node("softbreak"))
        else:
            block.append_child(_Node("softbreak"))
        self.match(reInitialSpace)
        return True

    def parse_backslash(self, block: _Node) -> bool:
        subj = self.subject
        self.pos += 1
        if self.peek() == "\n":
            self.pos += 1
            block.append_child(_Node("linebreak"))
        else:
            nxt = subj[self.pos : self.pos + 1]
            if nxt and re.search(reEscapable, nxt):
                block.append_child(_text(nxt))
                self.pos += 1
            else:
                block.append_child(_text("\\"))
        return True

    def parse_entity(self, block: _Node) -> bool:
        m = self.match(reEntityHere)
        if m:
            block.append_child(_text(_resolve_entity_full(m)))
            return True
        return False

    def parse_string(self, block: _Node) -> bool:
        m = self.match(reMain)
        if m:
            match_start = self.pos - len(m)
            prev_char = self.subject[match_start - 1] if match_start > 0 else "\n"
            next_char = self.subject[self.pos] if self.pos < len(self.subject) else "\n"
            self._process_text_autolinks(block, m, prev_char, next_char)
            return True
        return False

    def _process_text_autolinks(self, block: _Node, text: str, orig_prev: str, orig_next: str) -> None:
        pos_before = self.pos
        result: list[_Node] = []
        scan_pos = 0
        current_prev = orig_prev
        while scan_pos < len(text):
            match = self._scan_autolink_in_text(text, scan_pos, current_prev)
            if match is None:
                remaining = text[scan_pos:]
                if remaining:
                    result.append(_text(remaining))
                break
            start, link_end, dest, display = match
            if start > scan_pos:
                result.append(_text(text[scan_pos:start]))
            if dest.startswith("mailto:") and orig_next in "-_" and link_end == len(text):
                result.append(_text(text[scan_pos:link_end]))
                scan_pos = link_end
                current_prev = orig_next
                continue
            link = _Node("link")
            link.is_autolink = True
            link.destination = dest
            link.title = ""
            link.append_child(_text(display))
            result.append(link)
            current_prev = display[-1] if display else " "
            scan_pos = link_end
        self.pos = pos_before
        if len(result) <= 1 and result:
            block.append_child(result[0])
            return
        if not result:
            block.append_child(_text(text))
            return
        for r in result:
            block.append_child(r)

    def parse_backticks(self, block: _Node) -> bool:
        ticks = self.match(reTicksHere)
        if ticks is None:
            return False
        after_open = self.pos
        matched = self.match(reTicks)
        while matched is not None:
            if matched == ticks:
                node = _Node("code")
                contents = self.subject[after_open : self.pos - len(ticks)].replace("\n", " ")
                if contents.lstrip(" ") and contents[0] == contents[-1] == " ":
                    node.literal = contents[1:-1]
                else:
                    node.literal = contents
                block.append_child(node)
                return True
            matched = self.match(reTicks)
        self.pos = after_open
        block.append_child(_text(ticks))
        return True

    def scan_delims(self, c: str) -> tuple[int, bool, bool] | None:
        numdelims = 0
        startpos = self.pos
        while self.peek() == c:
            numdelims += 1
            self.pos += 1
        if numdelims == 0:
            return None
        c_before = "\n" if startpos == 0 else self.subject[startpos - 1]
        c_after = self.peek()
        if c_after is None:
            c_after = "\n"
        after_is_whitespace = bool(re.search(reUnicodeWhitespaceChar, c_after)) or c_after == "\xa0"
        after_is_punctuation = bool(re.search(rePunctuation, c_after))
        before_is_whitespace = bool(re.search(reUnicodeWhitespaceChar, c_before)) or c_before == "\xa0"
        before_is_punctuation = bool(re.search(rePunctuation, c_before))
        left_flanking = not after_is_whitespace and (
            not after_is_punctuation or before_is_whitespace or before_is_punctuation
        )
        right_flanking = not before_is_whitespace and (
            not before_is_punctuation or after_is_whitespace or after_is_punctuation
        )
        if c == "_":
            can_open = left_flanking and (not right_flanking or before_is_punctuation)
            can_close = right_flanking and (not left_flanking or after_is_punctuation)
        else:
            can_open = left_flanking
            can_close = right_flanking
        self.pos = startpos
        return numdelims, can_open, can_close

    def handle_delim(self, cc: str, block: _Node) -> bool:
        res = self.scan_delims(cc)
        if res is None:
            return False
        numdelims, can_open, can_close = res
        startpos = self.pos
        self.pos += numdelims
        contents = self.subject[startpos : self.pos]
        node = _text(contents)
        block.append_child(node)
        d = _Delim(cc, numdelims, node, can_open, can_close, self.delimiters)
        if self.delimiters is not None:
            self.delimiters.nxt = d
        self.delimiters = d
        return True

    def remove_delimiter(self, delim: _Delim) -> None:
        if delim.previous is not None:
            delim.previous.nxt = delim.nxt
        if delim.nxt is None:
            self.delimiters = delim.previous
        else:
            delim.nxt.previous = delim.previous

    def remove_delimiters_between(self, bottom: _Delim, top: _Delim) -> None:
        if bottom.nxt != top:
            bottom.nxt = top
            top.previous = bottom

    def process_emphasis(self, stack_bottom: _Delim | None) -> None:
        openers_bottom: dict[str, _Delim | None] = {
            "_": stack_bottom,
            "*": stack_bottom,
            "~": stack_bottom,
        }
        closer = self.delimiters
        while closer is not None and closer.previous is not stack_bottom:
            closer = closer.previous
        while closer is not None:
            if not closer.can_close:
                closer = closer.nxt
            else:
                opener = closer.previous
                opener_found = False
                closercc = closer.cc
                odd_match = False
                while opener is not None and opener is not stack_bottom and opener is not openers_bottom[closercc]:
                    odd_match = (
                        (closer.can_open or opener.can_close)
                        and closer.origdelims % 3 != 0
                        and (opener.origdelims + closer.origdelims) % 3 == 0
                    )
                    if opener.cc == closercc and opener.can_open and not odd_match:
                        opener_found = True
                        break
                    opener = opener.previous
                old_closer = closer
                if closercc in ("*", "_", "~"):
                    if not opener_found:
                        closer = closer.nxt
                    else:
                        assert opener is not None
                        use_delims = 2 if (closer.numdelims >= 2 and opener.numdelims >= 2) else 1
                        opener_inl = opener.node
                        closer_inl = closer.node
                        opener.numdelims -= use_delims
                        closer.numdelims -= use_delims
                        opener_inl.literal = opener_inl.literal[: len(opener_inl.literal) - use_delims]
                        closer_inl.literal = closer_inl.literal[: len(closer_inl.literal) - use_delims]
                        if closercc == "~":
                            emph = _Node("del")
                        elif use_delims == 1:
                            emph = _Node("emph")
                        else:
                            emph = _Node("strong")
                        tmp = opener_inl.nxt
                        while tmp is not None and tmp is not closer_inl:
                            nxt = tmp.nxt
                            tmp.unlink()
                            emph.append_child(tmp)
                            tmp = nxt
                        opener_inl.insert_after(emph)
                        self.remove_delimiters_between(opener, closer)
                        if opener.numdelims == 0:
                            opener_inl.unlink()
                            self.remove_delimiter(opener)
                        if closer.numdelims == 0:
                            closer_inl.unlink()
                            tempstack = closer.nxt
                            self.remove_delimiter(closer)
                            closer = tempstack
                if not opener_found and not odd_match:
                    openers_bottom[closercc] = old_closer.previous
                    if not old_closer.can_open:
                        self.remove_delimiter(old_closer)
        while self.delimiters is not None and self.delimiters is not stack_bottom:
            self.remove_delimiter(self.delimiters)

    def parse_open_bracket(self, block: _Node) -> bool:
        startpos = self.pos
        self.pos += 1
        node = _text("[")
        block.append_child(node)
        self.add_bracket(node, startpos, False)
        return True

    def parse_bang(self, block: _Node) -> bool:
        startpos = self.pos
        self.pos += 1
        if self.peek() == "[":
            self.pos += 1
            node = _text("![")
            block.append_child(node)
            self.add_bracket(node, startpos + 1, True)
        else:
            block.append_child(_text("!"))
        return True

    def parse_close_bracket(self, block: _Node) -> bool:
        self.pos += 1
        opener = self.brackets
        if opener is None or not opener.active:
            if opener is not None:
                self.remove_bracket()
            block.append_child(_text("]"))
            return True
        is_image = opener.image
        matched = False
        dest = ""
        title = ""
        savepos = self.pos
        if self.peek() == "(":
            self.pos += 1
            self.spnl()
            dest = self.parse_link_destination() or ""
            if self.spnl():
                if re.search(reWhitespaceChar, self.subject[self.pos - 1]):
                    t = self.parse_link_title()
                    if t is not None:
                        title = t
                if self.spnl() and self.peek() == ")":
                    self.pos += 1
                    matched = True
            if not matched:
                self.pos = savepos
        if not matched:
            beforelabel = self.pos
            n = self.parse_link_label()
            if n > 2:
                reflabel = self.subject[beforelabel + 1 : beforelabel + n - 1]
            elif not opener.bracket_after:
                reflabel = self.subject[opener.index + 1 : savepos - 1]
            else:
                reflabel = ""
            if n == 0:
                self.pos = savepos
            if reflabel:
                link = self.refmap.get(_normalize_label(reflabel))
                if link is not None:
                    dest = link.destination
                    title = link.title
                    matched = True
        if matched:
            node = _Node("image" if is_image else "link")
            node.destination = dest
            node.title = title
            tmp = opener.node.nxt
            while tmp is not None:
                nxt = tmp.nxt
                tmp.unlink()
                node.append_child(tmp)
                tmp = nxt
            block.append_child(node)
            self.process_emphasis(opener.previous_delimiter)
            self.remove_bracket()
            opener.node.unlink()
            if not is_image:
                opener = self.brackets
                while opener is not None:
                    if not opener.image:
                        opener.active = False
                    opener = opener.previous
            return True
        else:
            self.remove_bracket()
            self.pos = savepos
            block.append_child(_text("]"))
            return True

    def parse_link_destination(self) -> str | None:
        res = self.match(reLinkDestinationBraces)
        if res is None:
            if self.peek() == "<":
                return None
            savepos = self.pos
            openparens = 0
            while True:
                c = self.peek()
                if c is None:
                    break
                if c == "\\" and re.search(reEscapable, self.subject[self.pos + 1 : self.pos + 2]):
                    self.pos += 1
                    if self.peek() is not None:
                        self.pos += 1
                elif c == "(":
                    self.pos += 1
                    openparens += 1
                elif c == ")":
                    if openparens < 1:
                        break
                    self.pos += 1
                    openparens -= 1
                elif re.search(reWhitespaceChar, c):
                    break
                else:
                    self.pos += 1
            if self.pos == savepos:
                return None
            res = self.subject[savepos : self.pos]
            return normalize_uri(unescape_string(res))
        else:
            return normalize_uri(unescape_string(res[1:-1]))

    def parse_link_title(self) -> str | None:
        title = self.match(reLinkTitle)
        if title is None:
            return None
        return unescape_string(title[1:-1])

    def parse_link_label(self) -> int:
        m = self.match(reLinkLabel)
        if m is None or len(m) > 1001:
            return 0
        return len(m)

    def add_bracket(self, node: _Node, index: int, image: bool) -> None:
        if self.brackets is not None:
            self.brackets.bracket_after = True
        self.brackets = _Bracket(node, index, image, self.brackets, self.delimiters)

    def remove_bracket(self) -> None:
        self.brackets = self.brackets.previous if self.brackets is not None else None

    def parse_autolink(self, block: _Node) -> bool:
        m = self.match(reEmailAutolink)
        if m:
            dest = m[1:-1]
            node = _Node("link")
            node.is_autolink = True
            node.destination = normalize_uri("mailto:" + dest)
            node.title = ""
            node.append_child(_text(dest))
            block.append_child(node)
            return True
        m = self.match(reAutolink)
        if m:
            dest = m[1:-1]
            if _is_dangerous_scheme(dest):
                block.append_child(_text(m))
                return True
            node = _Node("link")
            node.is_autolink = True
            node.destination = normalize_uri(dest)
            node.title = ""
            node.append_child(_text(dest))
            block.append_child(node)
            return True
        return False

    def parse_html_tag(self, block: _Node) -> bool:
        m = self.match(reHtmlTag)
        if m is None:
            return False
        node = _Node("html_inline", m)
        block.append_child(node)
        return True

    def parse_inline(self, block: _Node) -> bool:
        c = self.peek()
        if c is None:
            return False
        res = False
        if c == "\n":
            res = self.parse_newline(block)
        elif c == "\\":
            res = self.parse_backslash(block)
        elif c == "`":
            res = self.parse_backticks(block)
        elif c in ("*", "_", "~"):
            res = self.handle_delim(c, block)
        elif c == "[":
            res = self.parse_open_bracket(block)
        elif c == "!":
            res = self.parse_bang(block)
        elif c == "]":
            res = self.parse_close_bracket(block)
        elif c == "<":
            res = self.parse_autolink(block) or self.parse_html_tag(block)
        elif c == "&":
            res = self.parse_entity(block)
        else:
            res = self.parse_extended_autolink(block) or self.parse_string(block)
        if not res:
            self.pos += 1
            block.append_child(_text(c))
        return True

    _TRAILING_PUNCT = frozenset("?!.,:*_~")

    def _prev_char(self) -> str:
        if self.pos == 0:
            return "\n"
        return self.subject[self.pos - 1]

    def _scan_autolink_in_text(self, text: str, pos: int, prev_char: str) -> tuple[int, int, str, str] | None:
        n = len(text)
        if pos >= n:
            return None
        i = pos
        while i < n:
            c = text[i]
            if c == "\n" or c == " " or c == "\t":
                i += 1
                continue
            pc = prev_char if i == pos or text[i - 1] in " \t\n" else text[i - 1]
            rest = text[i:]
            lower = rest.lower()
            if rest.startswith("www.") and (pc in " \t\n" or pc in "*_~("):
                domain_end = self._scan_domain(text, i + 4)
                if domain_end > i + 4:
                    return self._finalize_autolink_text(text, i, domain_end, "http://", True)
            if pc in " \t\n" or pc in "*_~(":
                for scheme in ("http://", "https://", "ftp://"):
                    if lower.startswith(scheme):
                        domain_end = self._scan_domain(text, i + len(scheme))
                        if domain_end > i + len(scheme):
                            return self._finalize_autolink_text(text, i, domain_end, scheme, False)
            email = self._try_email(text, i)
            if email is not None:
                link_end, dest, display = email
                return i, i + link_end, dest, display
            i += 1
        return None

    def _finalize_autolink_text(
        self, text: str, url_start: int, domain_end: int, scheme: str, is_www: bool
    ) -> tuple[int, int, str, str] | None:
        n = len(text)
        i = domain_end
        while i < n:
            c = text[i]
            if c == " " or c == "\t" or c == "\n" or c == "<":
                break
            i += 1
        link_end = i
        while link_end > domain_end and text[link_end - 1] in self._TRAILING_PUNCT:
            link_end -= 1
        if link_end > domain_end and text[link_end - 1] == ")":
            open_count = 0
            for j in range(url_start, link_end):
                if text[j] == "(":
                    open_count += 1
                elif text[j] == ")":
                    open_count -= 1
            while open_count < 0 and link_end > domain_end and text[link_end - 1] == ")":
                link_end -= 1
                open_count += 1
        if link_end > domain_end and text[link_end - 1] == ";":
            j = link_end - 2
            if j >= url_start and text[j] == "&":
                link_end -= 1
            elif j >= url_start:
                k = j
                while k > url_start and text[k - 1].isalnum():
                    k -= 1
                if k > url_start and text[k - 1] == "&":
                    link_end = k - 1
        raw_url = text[url_start:link_end]
        dest = scheme + raw_url if is_www else raw_url
        return url_start, link_end, dest, raw_url

    def parse_extended_autolink(self, block: _Node) -> bool:
        pc = self._prev_char()
        subj = self.subject
        rest = subj[self.pos :]
        lower = rest.lower()
        if rest.startswith("www.") and (pc in " \t\n" or pc in "*_~("):
            domain_end = self._scan_domain(subj, self.pos + 4)
            if domain_end > self.pos + 4:
                return self._emit_extended(subj, self.pos, domain_end, "http://", block, is_www=True)
        if pc in " \t\n" or pc in "*_~(":
            for scheme in ("http://", "https://", "ftp://"):
                if lower.startswith(scheme):
                    domain_end = self._scan_domain(subj, self.pos + len(scheme))
                    if domain_end > self.pos + len(scheme):
                        return self._emit_extended(subj, self.pos, domain_end, scheme, block, is_www=False)
        email = self._try_email(subj, self.pos)
        if email is not None:
            link_end, dest, display = email
            node = _Node("link")
            node.is_autolink = True
            node.destination = dest
            node.title = ""
            node.append_child(_text(display))
            block.append_child(node)
            self.pos = self.pos + link_end
            return True
        return False

    def _scan_domain(self, text: str, pos: int) -> int:
        n = len(text)
        i = pos
        nparts = 0
        while i < n:
            c = text[i]
            if c.isalnum() or c == "-":
                i += 1
            elif c == "_":
                if nparts < 2:
                    i += 1
                else:
                    break
            elif c == ".":
                if i > pos and text[i - 1] in "_-":
                    break
                nparts += 1
                i += 1
            else:
                break
        if nparts < 1:
            return -1
        while i > pos and text[i - 1] in "_-.":
            i -= 1
        if i <= pos:
            return -1
        return i

    def _emit_extended(
        self, subj: str, url_start: int, domain_end: int, scheme: str, block: _Node, *, is_www: bool
    ) -> bool:
        n = len(subj)
        i = domain_end
        while i < n:
            c = subj[i]
            if c == " " or c == "\t" or c == "\n" or c == "<":
                break
            i += 1
        link_end = i
        while link_end > domain_end and subj[link_end - 1] in self._TRAILING_PUNCT:
            link_end -= 1
        if link_end > domain_end and subj[link_end - 1] == ")":
            open_count = 0
            for j in range(url_start, link_end):
                if subj[j] == "(":
                    open_count += 1
                elif subj[j] == ")":
                    open_count -= 1
            while open_count < 0 and link_end > domain_end and subj[link_end - 1] == ")":
                link_end -= 1
                open_count += 1
        if link_end > domain_end and subj[link_end - 1] == ";":
            j = link_end - 2
            if j >= url_start and subj[j] == "&":
                link_end -= 1
            elif j >= url_start:
                k = j
                while k > url_start and subj[k - 1].isalnum():
                    k -= 1
                if k > url_start and subj[k - 1] == "&":
                    link_end = k - 1
        raw_url = subj[url_start:link_end]
        dest = scheme + raw_url if is_www else raw_url
        node = _Node("link")
        node.is_autolink = True
        node.destination = dest
        node.title = ""
        node.append_child(_text(raw_url))
        block.append_child(node)
        self.pos = link_end
        return True

    def _try_email(self, subj: str, pos: int) -> tuple[int, str, str] | None:
        n = len(subj)
        i = pos
        while i < n:
            c = subj[i]
            if c.isalnum() or c in ".+-_":
                i += 1
            else:
                break
        local_end = i
        if i >= n or subj[i] != "@":
            return None
        domain_start = i + 1
        domain_end = self._scan_domain(subj, domain_start)
        if domain_end <= domain_start:
            return None
        if subj[domain_end - 1] in "-_":
            return None
        if domain_end < n and subj[domain_end] in "-_":
            return None
        while local_end > pos and subj[local_end - 1] in ".+-_":
            local_end -= 1
        if local_end <= pos:
            return None
        email = subj[pos:domain_end]
        if email.endswith("+"):
            return None
        return domain_end - pos, "mailto:" + email, email

    def parse_inlines(self, text: str) -> _Node:
        block = _Node("paragraph")
        self.subject = text
        self.pos = 0
        self.delimiters = None
        self.brackets = None
        while self.parse_inline(block):
            pass
        self.process_emphasis(None)
        return block


_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
_ALLOWED_URL_SCHEMES = frozenset({"http", "https", "mailto"})
_DANGEROUS_SCHEMES = frozenset({"javascript", "data", "vbscript"})


def _is_dangerous_scheme(url: str) -> bool:
    m = _SCHEME_RE.match(url)
    return m is not None and m.group(1).lower() in _DANGEROUS_SCHEMES


def _is_safe_link_url(url: str) -> bool:
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in url):
        return False
    if url.startswith("#"):
        return True
    m = _SCHEME_RE.match(url)
    return m is None or m.group(1).lower() in _ALLOWED_URL_SCHEMES


def _render_plain(node: _Node) -> str:
    out: list[str] = []
    child = node.first_child
    while child is not None:
        if child.t == "text" or child.t == "code":
            out.append(child.literal)
        elif child.t in ("softbreak", "linebreak"):
            out.append("\n")
        else:
            out.append(_render_plain(child))
        child = child.nxt
    return "".join(out)


def _render_children(node: _Node) -> str:
    out: list[str] = []
    child = node.first_child
    while child is not None:
        out.append(_render_node(child))
        child = child.nxt
    return "".join(out)


def _render_node(node: _Node) -> str:
    t = node.t
    if t == "text":
        return escape_xml(node.literal)
    if t == "code":
        return "<code>" + protect_lbrace(escape_xml(node.literal)) + "</code>"
    if t == "html_inline":
        return apply_tagfilter(node.literal)
    if t == "softbreak":
        return "\n"
    if t == "linebreak":
        return "<br />\n"
    inner = _render_children(node)
    if t == "emph":
        return "<em>" + inner + "</em>"
    if t == "strong":
        return "<strong>" + inner + "</strong>"
    if t == "del":
        return "<del>" + inner + "</del>"
    if t == "link":
        if node.is_autolink or _is_safe_link_url(node.destination):
            href = ' href="' + escape_xml(node.destination) + '"'
            title_attr = ""
            if node.title:
                title_attr = ' title="' + escape_xml(node.title) + '"'
            return "<a" + href + title_attr + ">" + inner + "</a>"
        return inner
    if t == "image":
        alt = _render_plain(node)
        if _is_safe_link_url(node.destination):
            src = ' src="' + escape_xml(node.destination) + '"'
            alt_attr = ' alt="' + escape_xml(alt) + '"'
            title_attr = ""
            if node.title:
                title_attr = ' title="' + escape_xml(node.title) + '"'
            return "<img" + src + alt_attr + title_attr + " />"
        return escape_xml(alt)
    if t == "paragraph":
        return _render_children(node)
    return ""


def render_inline(text: str, refmap: dict[str, _LinkRef]) -> str:
    parser = _InlineParser(refmap)
    tree = parser.parse_inlines(text)
    return _render_children(tree)
