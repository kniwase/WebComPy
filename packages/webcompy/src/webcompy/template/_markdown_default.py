from __future__ import annotations

import html
import re
import uuid

from webcompy.ports._markdown import MarkdownPort
from webcompy.template._holes import protect_lbrace
from webcompy.template._markdown_blocks import parse_blocks as _parse_blocks_module

_CODE_RE = re.compile(r"`([^`\n]+)`")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")
_STRIKE_RE = re.compile(r"~~(.+?)~~")
_TEMPLATE_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)
_SCHEME_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")
_ALLOWED_URL_SCHEMES = frozenset({"http", "https", "mailto"})


def _is_safe_url(url: str) -> bool:
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in url):
        return False
    if url.startswith("#"):
        return True
    match = _SCHEME_RE.match(url)
    return match is None or match.group(1).lower() in _ALLOWED_URL_SCHEMES


def _render_inline(text: str) -> str:
    tokens: dict[str, str] = {}
    nonce = uuid.uuid4().hex[:12]

    def token(value: str) -> str:
        key = f"\x00WC{nonce}{len(tokens)}\x00"
        tokens[key] = value
        return key

    protected = _CODE_RE.sub(
        lambda match: token(f"<code>{protect_lbrace(html.escape(match.group(1)))}</code>"),
        text,
    )
    protected = _TEMPLATE_RE.sub(lambda match: token(match.group(0)), protected)
    protected = _IMAGE_RE.sub(
        lambda match: (
            token(
                f'<img src="{html.escape(match.group(2), quote=True)}" alt="{html.escape(match.group(1), quote=True)}">'
            )
            if _is_safe_url(match.group(2))
            else token(_render_inline(match.group(1)))
        ),
        protected,
    )
    protected = _LINK_RE.sub(
        lambda match: (
            token(f'<a href="{html.escape(match.group(2), quote=True)}">{_render_inline(match.group(1))}</a>')
            if _is_safe_url(match.group(2))
            else token(_render_inline(match.group(1)))
        ),
        protected,
    )
    protected = _BOLD_RE.sub(
        lambda match: token(f"<strong>{_render_inline(match.group(1))}</strong>"),
        protected,
    )
    protected = _ITALIC_RE.sub(
        lambda match: token(f"<em>{_render_inline(match.group(1))}</em>"),
        protected,
    )
    protected = _STRIKE_RE.sub(
        lambda match: token(f"<del>{_render_inline(match.group(1))}</del>"),
        protected,
    )
    result = html.escape(protected, quote=False)
    previous: str | None = None
    while previous != result:
        previous = result
        for key, value in tokens.items():
            result = result.replace(key, value)
    return result


def _render_blocks(source: str, inline):
    return _parse_blocks_module(source, inline)


class DefaultMarkdownParser(MarkdownPort):
    def render(self, source: str) -> str:
        return _render_blocks(source, self._inline).html

    def _inline(self, text: str) -> str:
        return _render_inline(text)
