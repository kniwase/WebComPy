from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from webcompy.elements.types._abstract import ElementAbstract
from webcompy.resources import load_text


@dataclass(frozen=True)
class HeadingInfo:
    """A heading entry extracted from a rendered Markdown document.

    ``level`` is the heading depth (1-6), ``text`` is the resolved heading
    text with interpolated values, and ``id`` is the slug id injected into
    the corresponding heading element.
    """

    level: int
    text: str
    id: str


@dataclass(frozen=True)
class MarkdownDocument:
    """A loaded Markdown document: rendered content, frontmatter, and TOC."""

    content: ElementAbstract
    metadata: Mapping[str, Any]
    toc: tuple[HeadingInfo, ...]


async def load_markdown_document(
    source: str | Path,
    *,
    heading_ids: bool = True,
    code_blocks: bool = True,
    classes: Mapping[str, str] | None = None,
    context: Mapping[str, Any] | None = None,
) -> MarkdownDocument:
    from webcompy.template import render_markdown
    from webcompy.template._frontmatter import split_frontmatter
    from webcompy.template._markdown_transforms import collect_headings

    text = await load_text(source)
    metadata, body = split_frontmatter(text)
    content = render_markdown(
        body,
        context,
        heading_ids=heading_ids,
        code_blocks=code_blocks,
        classes=classes,
    )
    toc = collect_headings(content, heading_ids=heading_ids)
    return MarkdownDocument(content=content, metadata=metadata, toc=toc)
