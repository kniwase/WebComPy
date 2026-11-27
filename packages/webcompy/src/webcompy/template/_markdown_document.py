"""Loads Markdown files into rendered document objects with TOC support."""

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

    Attributes:
        level: Heading depth (1-6).
        text: Resolved heading text with interpolated values.
        id: Slug id injected into the corresponding heading element.

    """

    level: int
    text: str
    id: str


@dataclass(frozen=True)
class MarkdownDocument:
    """A loaded Markdown document: rendered content, frontmatter, and TOC.

    Attributes:
        content: Rendered element tree of the Markdown body.
        metadata: Frontmatter key-to-value mapping.
        toc: Heading entries extracted from the rendered document.

    """

    content: ElementAbstract
    metadata: Mapping[str, Any]
    toc: tuple[HeadingInfo, ...]


async def load_markdown_document(
    source: str | Path,
    *,
    heading_ids: bool = True,
    heading_anchors: bool = False,
    code_blocks: bool = True,
    copyable_code_blocks: bool = False,
    classes: Mapping[str, str] | None = None,
    wrap_tables: bool = True,
    context: Mapping[str, Any] | None = None,
) -> MarkdownDocument:
    """Load a Markdown file into a rendered document with TOC metadata.

    Reads the source text, splits off frontmatter, renders the body through
    ``render_markdown``, applies document transforms, and collects heading
    information for tables of contents.

    Args:
        source: Resource path or file path of the Markdown source.
        heading_ids: Whether heading elements receive slug ``id``
            attributes.
        heading_anchors: Whether ``<h2>``-``<h6>`` headings with an ``id``
            receive a clickable ``<a class="heading-anchor">`` permalink.
        code_blocks: Whether fenced code blocks are replaced with
            ``CodeBlock`` components.
        copyable_code_blocks: Whether replaced ``CodeBlock`` components
            render a copy-to-clipboard button.
        classes: Optional mapping from tag name to CSS class applied to
            matching elements.
        wrap_tables: Whether ``<table>`` elements are wrapped in
            ``<div class="prose-table-wrapper">`` for horizontal scrolling.
        context: Optional template context for ``{{ }}`` interpolation
            inside the Markdown body.

    Returns:
        The rendered document with frontmatter metadata and heading list.

    """
    from webcompy.template import render_markdown
    from webcompy.template._frontmatter import split_frontmatter
    from webcompy.template._markdown_transforms import apply_heading_anchors, collect_headings
    from webcompy.template._markdown_transforms import wrap_tables as _wrap_tables

    text = await load_text(source)
    metadata, body = split_frontmatter(text)
    content = render_markdown(
        body,
        context,
        heading_ids=heading_ids,
        code_blocks=code_blocks,
        copyable_code_blocks=copyable_code_blocks,
        classes=classes,
    )
    if wrap_tables:
        content = _wrap_tables(content)
    toc = collect_headings(content, heading_ids=heading_ids)
    if heading_anchors:
        apply_heading_anchors(content)
    return MarkdownDocument(content=content, metadata=metadata, toc=toc)
