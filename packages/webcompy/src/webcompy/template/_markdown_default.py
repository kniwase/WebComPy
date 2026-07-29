from __future__ import annotations

from webcompy.ports._markdown import MarkdownPort
from webcompy.template._markdown_blocks import parse_blocks_with_refs
from webcompy.template._markdown_inline import render_inline


class DefaultMarkdownParser(MarkdownPort):
    def render(self, source: str) -> str:
        return parse_blocks_with_refs(source, render_inline).html
