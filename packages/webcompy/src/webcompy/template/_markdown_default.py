from __future__ import annotations

import html
import re
import textwrap

from webcompy.ports._markdown import MarkdownPort

_HEADING_RE = re.compile(r"^ {0,3}(?P<hashes>#{1,6})(?!#)[ \t]*(?P<text>.*?)\s*$")
_LIST_RE = re.compile(r"^(?P<indent> *)(?P<marker>(?:[-*]|\d+[.)]))(?:[ \t]+(?P<text>.*)|$)")
_BLOCKQUOTE_RE = re.compile(r"^ {0,3}>[ \t]?(?P<text>.*)$")
_FENCE_START_RE = re.compile(r"^ {0,3}```(?:.*)$")
_FENCE_END_RE = re.compile(r"^ {0,3}```[ \t]*$")
_HTML_TAG_RE = re.compile(r"^<(?P<tag>[A-Za-z][\w:-]*)\b")
_TEMPLATE_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)
_CODE_RE = re.compile(r"`([^`\n]+)`")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")
_STRIKE_RE = re.compile(r"~~(.+?)~~")


class DefaultMarkdownParser(MarkdownPort):
    def render(self, source: str) -> str:
        normalized = textwrap.dedent(source).replace("\t", "  ")
        lines = normalized.splitlines()
        rendered, _ = self._parse_blocks(lines, 0)
        return "".join(rendered)

    def _parse_blocks(self, lines: list[str], index: int) -> tuple[list[str], int]:
        rendered: list[str] = []
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                index += 1
                continue
            if _FENCE_START_RE.match(line):
                code, index = self._parse_code_block(lines, index)
                rendered.append(code)
                continue
            heading = _HEADING_RE.fullmatch(line)
            if heading is not None:
                level = len(heading.group("hashes"))
                content = heading.group("text").strip()
                rendered.append(f"<h{level}>{self._inline(content)}</h{level}>")
                index += 1
                continue
            if line.strip() in {"---", "***", "___"}:
                rendered.append("<hr>")
                index += 1
                continue
            if _BLOCKQUOTE_RE.match(line):
                blockquote, index = self._parse_blockquote(lines, index)
                rendered.append(blockquote)
                continue
            if _LIST_RE.match(line):
                list_html, index = self._parse_list(lines, index)
                rendered.append(list_html)
                continue
            if line.lstrip().startswith("<"):
                html_block, index = self._parse_html_block(lines, index)
                rendered.append(html_block)
                continue
            paragraph, index = self._parse_paragraph(lines, index)
            rendered.append(paragraph)
        return rendered, index

    def _parse_code_block(self, lines: list[str], index: int) -> tuple[str, int]:
        index += 1
        code_lines: list[str] = []
        while index < len(lines):
            if _FENCE_END_RE.fullmatch(lines[index]):
                index += 1
                break
            code_lines.append(lines[index])
            index += 1
        return f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>", index

    def _parse_blockquote(self, lines: list[str], index: int) -> tuple[str, int]:
        quote_lines: list[str] = []
        while index < len(lines):
            match = _BLOCKQUOTE_RE.fullmatch(lines[index])
            if match is None:
                break
            quote_lines.append(match.group("text").strip())
            index += 1
        content = " ".join(quote_lines)
        return f"<blockquote>{self._inline(content)}</blockquote>", index

    def _parse_html_block(self, lines: list[str], index: int) -> tuple[str, int]:
        first_line = lines[index]
        block_lines = [first_line]
        tag_match = _HTML_TAG_RE.match(first_line.lstrip())
        if tag_match is None:
            return first_line, index + 1
        tag = tag_match.group("tag")
        closing_pattern = re.compile(rf"</{re.escape(tag)}\s*>", re.IGNORECASE)
        first_is_closed = bool(closing_pattern.search(first_line)) or bool(re.search(r"/\s*>\s*$", first_line))
        if not first_is_closed:
            candidate_lines: list[str] = []
            for candidate_index in range(index + 1, len(lines)):
                candidate = lines[candidate_index]
                if not candidate.strip():
                    break
                candidate_lines.append(candidate)
                if closing_pattern.search(candidate):
                    block_lines.extend(candidate_lines)
                    return "\n".join(block_lines), candidate_index + 1
            return first_line, index + 1
        next_index = index + 1
        while next_index < len(lines) and lines[next_index].lstrip().startswith("<"):
            block_lines.append(lines[next_index])
            next_index += 1
        return "\n".join(block_lines), next_index

    def _parse_paragraph(self, lines: list[str], index: int) -> tuple[str, int]:
        paragraph_lines: list[str] = []
        while index < len(lines):
            line = lines[index]
            if not line.strip() or (paragraph_lines and self._is_block_start(line)):
                break
            paragraph_lines.append(line.strip())
            index += 1
        content = " ".join(paragraph_lines)
        return f"<p>{self._inline(content)}</p>", index

    def _is_block_start(self, line: str) -> bool:
        return (
            _FENCE_START_RE.match(line) is not None
            or _HEADING_RE.fullmatch(line) is not None
            or line.strip() in {"---", "***", "___"}
            or _BLOCKQUOTE_RE.match(line) is not None
            or _LIST_RE.match(line) is not None
            or line.lstrip().startswith("<")
        )

    def _parse_list(self, lines: list[str], index: int) -> tuple[str, int]:
        first_match = _LIST_RE.fullmatch(lines[index])
        if first_match is None:
            return "", index
        base_indent = len(first_match.group("indent"))
        list_kind = self._list_kind(first_match.group("marker"))
        items: list[str] = []
        while index < len(lines):
            match = _LIST_RE.fullmatch(lines[index])
            if match is None:
                break
            indent = len(match.group("indent"))
            if indent != base_indent or self._list_kind(match.group("marker")) != list_kind:
                break
            item_text = (match.group("text") or "").strip()
            item_parts: list[str] = []
            if item_text:
                item_parts.append(self._inline(item_text))
            index += 1
            while index < len(lines):
                nested_match = _LIST_RE.fullmatch(lines[index])
                if nested_match is not None:
                    nested_indent = len(nested_match.group("indent"))
                    if nested_indent <= base_indent:
                        break
                    nested_list, index = self._parse_list(lines, index)
                    item_parts.append(nested_list)
                    continue
                if not lines[index].strip():
                    next_nonblank = index
                    while next_nonblank < len(lines) and not lines[next_nonblank].strip():
                        next_nonblank += 1
                    if next_nonblank < len(lines):
                        next_match = _LIST_RE.fullmatch(lines[next_nonblank])
                        if next_match is not None and len(next_match.group("indent")) > base_indent:
                            index = next_nonblank
                            continue
                    index = next_nonblank
                    break
                leading_spaces = len(lines[index]) - len(lines[index].lstrip(" "))
                if leading_spaces > base_indent:
                    item_parts.append(self._inline(lines[index].strip()))
                    index += 1
                    continue
                break
            items.append(f"<li>{''.join(item_parts)}</li>")
        return f"<{list_kind}>{''.join(items)}</{list_kind}>", index

    def _list_kind(self, marker: str) -> str:
        return "ul" if marker in {"-", "*"} else "ol"

    def _inline(self, text: str) -> str:
        tokens: dict[str, str] = {}

        def token(value: str) -> str:
            key = f"__WEBCOMPY_INLINE_{len(tokens)}__"
            tokens[key] = value
            return key

        protected = _TEMPLATE_RE.sub(lambda match: token(match.group(0)), text)
        protected = _CODE_RE.sub(
            lambda match: token(f"<code>{html.escape(match.group(1))}</code>"),
            protected,
        )
        protected = _IMAGE_RE.sub(
            lambda match: token(
                f'<img src="{html.escape(match.group(2), quote=True)}" alt="{html.escape(match.group(1), quote=True)}">'
            ),
            protected,
        )
        protected = _LINK_RE.sub(
            lambda match: token(
                f'<a href="{html.escape(match.group(2), quote=True)}">{self._inline(match.group(1))}</a>'
            ),
            protected,
        )
        protected = _BOLD_RE.sub(
            lambda match: token(f"<strong>{self._inline(match.group(1))}</strong>"),
            protected,
        )
        protected = _ITALIC_RE.sub(
            lambda match: token(f"<em>{self._inline(match.group(1))}</em>"),
            protected,
        )
        protected = _STRIKE_RE.sub(
            lambda match: token(f"<del>{self._inline(match.group(1))}</del>"),
            protected,
        )
        result = html.escape(protected, quote=False)
        for key, value in tokens.items():
            result = result.replace(key, value)
        return result
