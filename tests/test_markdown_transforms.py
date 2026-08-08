from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest

from webcompy.components._component import Component, HeadPropsStore
from webcompy.components._generator import ComponentStore
from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._text import TextElement
from webcompy.ports._keys import MARKDOWN_PORT_KEY
from webcompy.signal import Signal
from webcompy.template import render_markdown
from webcompy.template._cache import clear_cache
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy.template._markdown_transforms import (
    apply_class_map,
    apply_heading_ids,
    collect_headings,
    replace_code_blocks,
    slugify,
)


@pytest.fixture(autouse=True)
def _reset_template_cache():
    clear_cache()
    yield
    clear_cache()


@contextmanager
def _markdown_di_scope():
    scope = DIScope()
    scope.provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
    token = _active_di_scope.set(scope)
    try:
        yield scope
    finally:
        _active_di_scope.reset(token)
        scope.dispose()


@contextmanager
def _markdown_component_di_scope():
    store = ComponentStore()
    head_props = HeadPropsStore()
    scope = DIScope()
    scope.provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
    scope.provide(_COMPONENT_STORE_KEY, store)
    scope.provide(_HEAD_PROPS_KEY, head_props)
    token = _active_di_scope.set(scope)
    try:
        yield scope
    finally:
        _active_di_scope.reset(token)
        scope.dispose()


def _children_lists(node: Any) -> list[list[Any]]:
    lists: list[list[Any]] = []
    children = getattr(node, "_children", None)
    if isinstance(children, list):
        lists.append(children)
    pending = getattr(node, "_pending_children", None)
    if isinstance(pending, list):
        lists.append(pending)
    return lists


def _find_all(node: Any, predicate) -> list[Any]:
    results: list[Any] = []
    if predicate(node):
        results.append(node)
    for lst in _children_lists(node):
        for child in lst:
            results.extend(_find_all(child, predicate))
    return results


def _heading_elements(node: Any) -> list[Element]:
    return [
        e
        for e in _find_all(
            node, lambda n: isinstance(n, Element) and n._tag_name in {"h1", "h2", "h3", "h4", "h5", "h6"}
        )
    ]


def _extract_text(node: Any) -> str:
    if isinstance(node, TextElement):
        text = node._text
        if isinstance(text, str):
            return text
        return text.value if hasattr(text, "value") else str(text)
    if isinstance(node, str):
        return node
    parts: list[str] = []
    for lst in _children_lists(node):
        for child in lst:
            parts.append(_extract_text(child))
    return "".join(parts)


class TestSlugify:
    def test_ascii_lowercase_and_dashes(self) -> None:
        assert slugify("Getting Started") == "getting-started"

    def test_punctuation_removed(self) -> None:
        assert slugify("Hello, World!") == "hello-world"

    def test_whitespace_runs_single_dash(self) -> None:
        assert slugify("a   b\t c") == "a-b-c"

    def test_cjk_retained(self) -> None:
        assert slugify("日本語 の 見出し") == "日本語-の-見出し"

    def test_underscores_removed(self) -> None:
        assert slugify("a_b") == "ab"


class TestApplyHeadingIds:
    def test_ids_injected(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Getting Started\n\n## Next")
        apply_heading_ids(result)
        headings = _heading_elements(result)
        assert [h._attrs.get("id") for h in headings] == ["getting-started", "next"]

    def test_duplicates_deduplicated(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Same\n\n## Same\n\n### Same")
        apply_heading_ids(result)
        headings = _heading_elements(result)
        assert [h._attrs.get("id") for h in headings] == ["same", "same-2", "same-3"]

    def test_existing_id_reserved(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Dupe\n\n## Dupe")
        headings = _heading_elements(result)
        headings[0]._attrs["id"] = "dupe"
        apply_heading_ids(result)
        assert [h._attrs.get("id") for h in _heading_elements(result)] == ["dupe", "dupe-2"]

    def test_interpolated_heading_slug(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Hello {{ who }}", {"who": "World"})
        apply_heading_ids(result)
        heading = _heading_elements(result)[0]
        assert heading._attrs.get("id") == "hello-world"


class TestCollectHeadings:
    def test_document_order_and_levels(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# H1\n\n## H2a\n\n## H2b\n\n### H3")
        toc = collect_headings(result)
        assert [(h.level, h.text) for h in toc] == [(1, "H1"), (2, "H2a"), (2, "H2b"), (3, "H3")]

    def test_toc_ids_match_content_ids(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Alpha\n\n## Beta\n\n## Beta")
        toc = collect_headings(result)
        content_ids = [h._attrs.get("id") for h in _heading_elements(result)]
        assert [h.id for h in toc] == content_ids

    def test_injects_missing_ids(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# No Id")
        toc = collect_headings(result)
        assert toc[0].id == "no-id"
        assert _heading_elements(result)[0]._attrs.get("id") == "no-id"

    def test_interpolated_text_resolved(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# {{ title }}", {"title": "Intro"})
        toc = collect_headings(result)
        assert toc[0].text == "Intro"
        assert toc[0].id == "intro"

    def test_signal_text_resolved(self) -> None:
        sig = Signal("Dynamic")
        with _markdown_di_scope():
            result = render_markdown("# {{ title }}", {"title": sig})
        toc = collect_headings(result)
        assert toc[0].text == "Dynamic"

    def test_heading_inside_static_if(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Outer\n\n{% if show %}\n## Inner\n{% endif %}", {"show": True})
        toc = collect_headings(result)
        assert [(h.level, h.text) for h in toc] == [(1, "Outer"), (2, "Inner")]

    def test_heading_inside_signal_if_skipped(self) -> None:
        sig = Signal(True)
        with _markdown_di_scope():
            result = render_markdown("# Outer\n\n{% if show %}\n## Inner\n{% endif %}", {"show": sig})
        toc = collect_headings(result)
        assert [(h.level, h.text) for h in toc] == [(1, "Outer")]

    def test_heading_inside_for_resolved(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Outer\n\n{% for x in xs %}\n## {{ x }}\n{% endfor %}", {"xs": ["a", "b"]})
        toc = collect_headings(result)
        assert [(h.level, h.text) for h in toc] == [(1, "Outer"), (2, "a"), (2, "b")]

    def test_heading_inside_list_body_for_skipped(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Outer\n\n{% for x in xs %}\n- {{ x }}\n{% endfor %}", {"xs": ["a", "b"]})
        toc = collect_headings(result)
        assert [(h.level, h.text) for h in toc] == [(1, "Outer")]


class TestReplaceCodeBlocks:
    def test_fenced_code_replaced(self) -> None:
        with _markdown_component_di_scope():
            result = render_markdown("Intro.\n\n```python\nprint('hi')\n```")
            replace_code_blocks(result)
        components = _find_all(
            result, lambda n: isinstance(n, Component) and n._property.get("component_name") == "CodeBlock"
        )
        assert len(components) == 1
        assert components[0]._render_state.context.props["lang"] == "python"

    def test_fenced_code_replaced_with_python(self) -> None:
        with _markdown_component_di_scope():
            result = render_markdown("Intro.\n\n```python\nx = 1\n```")
            replace_code_blocks(result)
        components = _find_all(
            result, lambda n: isinstance(n, Component) and n._property.get("component_name") == "CodeBlock"
        )
        assert len(components) == 1
        assert components[0]._render_state.context.props["code"] == "x = 1\n"

    def test_code_content_stays_literal(self) -> None:
        with _markdown_component_di_scope():
            result = render_markdown(
                "Intro.\n\n```text\n{{ name }} {{ other }}\n```",
                {"name": "X", "other": "Y"},
            )
            replace_code_blocks(result)
        components = _find_all(
            result, lambda n: isinstance(n, Component) and n._property.get("component_name") == "CodeBlock"
        )
        assert len(components) == 1
        assert components[0]._render_state.context.props["code"] == "{{ name }} {{ other }}\n"

    def test_no_language_class_not_replaced(self) -> None:
        with _markdown_component_di_scope():
            result = render_markdown("Intro.\n\n    indented code")
            replace_code_blocks(result)
        pres = _find_all(result, lambda n: isinstance(n, Element) and n._tag_name == "pre")
        assert len(pres) == 1
        assert not _find_all(result, lambda n: isinstance(n, Component))

    def test_standalone_replaces_descendants_not_root(self) -> None:
        with _markdown_component_di_scope():
            result = render_markdown("```text\nx\n```")
            assert isinstance(result, Element) and result._tag_name == "pre"
            replace_code_blocks(result)
            assert isinstance(result, Element) and result._tag_name == "pre"


class TestApplyClassMap:
    def test_classes_injected(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("| a | b |\n|---|---|", {})
        tables = _find_all(result, lambda n: isinstance(n, Element) and n._tag_name == "table")
        assert len(tables) == 1
        apply_class_map(result, {"table": "doc-table"})
        assert tables[0]._attrs["class"] == "doc-table"

    def test_merge_with_existing_classes(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("```python\nx\n```")
        codes = _find_all(result, lambda n: isinstance(n, Element) and n._tag_name == "code")
        assert codes[0]._attrs["class"] == "language-python"
        apply_class_map(result, {"code": "doc-code"})
        assert codes[0]._attrs["class"] == "language-python doc-code"

    def test_unmapped_tags_untouched(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Title\n\nText.")
        apply_class_map(result, {"table": "doc-table"})
        assert all("class" not in h._attrs for h in _heading_elements(result))


class TestRenderMarkdownOptions:
    def test_heading_ids_option(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Getting Started", heading_ids=True)
        assert _heading_elements(result)[0]._attrs.get("id") == "getting-started"

    def test_heading_ids_default_off(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Getting Started")
        assert _heading_elements(result)[0]._attrs.get("id") is None

    def test_code_blocks_option(self) -> None:
        with _markdown_component_di_scope():
            result = render_markdown("Intro.\n\n```python\nx = 1\n```", code_blocks=True)
        components = _find_all(
            result, lambda n: isinstance(n, Component) and n._property.get("component_name") == "CodeBlock"
        )
        assert len(components) == 1

    def test_code_blocks_default_off(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("Intro.\n\n```python\nx = 1\n```")
        pres = _find_all(result, lambda n: isinstance(n, Element) and n._tag_name == "pre")
        assert len(pres) == 1
        assert not _find_all(result, lambda n: isinstance(n, Component))

    def test_classes_option(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("| a | b |\n|---|---|", classes={"table": "doc-table"})
        tables = _find_all(result, lambda n: isinstance(n, Element) and n._tag_name == "table")
        assert tables[0]._attrs["class"] == "doc-table"

    def test_classes_default_off(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("| a | b |\n|---|---|")
        tables = _find_all(result, lambda n: isinstance(n, Element) and n._tag_name == "table")
        assert "class" not in tables[0]._attrs

    def test_all_options_combined(self) -> None:
        with _markdown_component_di_scope():
            result = render_markdown(
                "# Title\n\n```python\nx = 1\n```",
                heading_ids=True,
                code_blocks=True,
                classes={"pre": "doc-pre"},
            )
        assert _heading_elements(result)[0]._attrs.get("id") == "title"
        assert any(
            isinstance(n, Component) and n._property.get("component_name") == "CodeBlock"
            for n in _find_all(result, lambda n: True)
        )


class TestTransformsOnFragment:
    def test_pending_children_walked(self) -> None:
        with _markdown_di_scope():
            result = render_markdown("# Alpha\n\n# Beta")
        assert isinstance(result, FragmentElement)
        apply_heading_ids(result)
        assert [_extract_text(h) for h in _heading_elements(result)] == ["Alpha", "Beta"]
        assert [_h._attrs.get("id") for _h in _heading_elements(result)] == ["alpha", "beta"]
