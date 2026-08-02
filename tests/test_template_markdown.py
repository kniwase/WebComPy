from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from webcompy.components._component import Component, HeadPropsStore
from webcompy.components._generator import ComponentGenerator, ComponentStore, define_component
from webcompy.di._keys import _COMPONENT_STORE_KEY, _HEAD_PROPS_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements.types._abstract import ElementAbstract
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._text import TextElement
from webcompy.exception import WebComPyException
from webcompy.ports._keys import MARKDOWN_PORT_KEY, RESOURCE_PORT_KEY
from webcompy.resources import load_text
from webcompy.signal import Signal
from webcompy.template import render_markdown
from webcompy.template._cache import clear_cache
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy.template._markdown_for import MarkdownForElement


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


def _extract_text(node: ElementAbstract | str | None) -> str:
    if node is None:
        return ""
    if isinstance(node, TextElement):
        text = node._text
        if isinstance(text, str):
            return text
        return text.value if hasattr(text, "value") else str(text)
    if isinstance(node, str):
        return node
    if isinstance(node, Element):
        return "".join(_extract_text(c) for c in node._children)
    if isinstance(node, Component):
        return "".join(_extract_text(c) for c in node._children)
    return ""


class TestRenderMarkdownSingleRoot:
    def test_single_root_returns_element_directly(self):
        with _markdown_di_scope():
            result = render_markdown("# Hello {{ name }}", {"name": "World"})
        assert isinstance(result, Element)
        assert not isinstance(result, FragmentElement)
        assert result._tag_name == "h1"
        assert _extract_text(result) == "Hello World"


class TestRenderMarkdownMultiRoot:
    def test_multi_root_returns_fragment_with_no_whitespace_children(self):
        with _markdown_di_scope():
            result = render_markdown("# Title\n\nText.", {})
        assert isinstance(result, FragmentElement)
        assert len(result._pending_children) == 2
        h1, p = result._pending_children
        assert isinstance(h1, Element) and h1._tag_name == "h1"
        assert isinstance(p, Element) and p._tag_name == "p"
        assert p._children[0]._text == "Text."

    def test_empty_markdown_returns_empty_fragment(self):
        with _markdown_di_scope():
            result = render_markdown("", {})
        assert isinstance(result, FragmentElement)
        assert result._pending_children == []


class TestRenderMarkdownInterpolation:
    def test_str_interpolation_in_heading(self):
        with _markdown_di_scope():
            result = render_markdown("## {{ title }}", {"title": "Home"})
        assert isinstance(result, Element)
        assert result._tag_name == "h2"
        assert _extract_text(result) == "Home"

    def test_signal_interpolation_in_paragraph(self):
        sig = Signal("initial")
        with _markdown_di_scope():
            result = render_markdown("Hello, {{ name }}!", {"name": sig})
        assert isinstance(result, Element)
        assert result._tag_name == "p"
        sig_child = result._children[1]
        assert isinstance(sig_child, TextElement)
        assert sig_child._text is sig
        assert result._children[0]._text == "Hello, "
        assert result._children[2]._text == "!"

    def test_signal_value_reflects_current_state(self):
        sig = Signal("a")
        with _markdown_di_scope():
            result = render_markdown("Hi {{ name }}", {"name": sig})
        sig_child = next(c for c in result._children if isinstance(c, TextElement) and c._text is sig)
        assert sig_child._text is sig
        assert sig_child._text.value == "a"


class TestRenderMarkdownIfElifElse:
    def test_if_branch_selected(self):
        with _markdown_di_scope():
            result = render_markdown("{% if a %}A{% endif %}", {"a": True})
        assert _extract_text(result) == "A"

    def test_else_branch_selected_when_condition_false(self):
        with _markdown_di_scope():
            result = render_markdown(
                "{% if a %}A{% else %}B{% endif %}",
                {"a": False},
            )
        assert _extract_text(result) == "B"
        assert "A" not in _extract_text(result)

    def test_elif_branch_selected(self):
        with _markdown_di_scope():
            result = render_markdown(
                "{% if a %}A{% elif b %}B{% else %}C{% endif %}",
                {"a": False, "b": True},
            )
        assert _extract_text(result) == "B"
        assert "A" not in _extract_text(result)
        assert "C" not in _extract_text(result)

    def test_else_branch_falls_through(self):
        with _markdown_di_scope():
            result = render_markdown(
                "{% if a %}A{% elif b %}B{% else %}C{% endif %}",
                {"a": False, "b": False},
            )
        assert _extract_text(result) == "C"


class TestRenderMarkdownDirectiveRejection:
    def test_unsupported_directive_rejected(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="not supported"):
            render_markdown("{% block content %}block{% endblock %}", {})

    def test_unknown_directive_rejected(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="Unknown template directive"):
            render_markdown("{% endfo %}", {})

    def test_unsupported_directive_rejected_inside_list_body_for(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="not supported"):
            render_markdown(
                "{% for item in items %}\n- {{ item }}{% extends 'x.html' %}\n{% endfor %}",
                {"items": ["a"]},
            )


class TestRenderMarkdownForBlock:
    def test_for_over_list_body_produces_single_ul(self):
        with _markdown_di_scope():
            result = render_markdown(
                "{% for item in items %}\n- {{ item }}\n{% endfor %}",
                {"items": ["a", "b", "c"]},
            )
            assert isinstance(result, MarkdownForElement)
            parent = Element("section")
            parent._append_child(result)
            ul = next(c for c in result._children if isinstance(c, Element) and c._tag_name == "ul")
            lis = [c for c in ul._children if isinstance(c, Element) and c._tag_name == "li"]
            assert len(lis) == 3
            for li in lis:
                text = li._children[0]._text
                assert text in ("a", "b", "c")

    def test_for_and_endfor_directives_p_stripped(self):
        with _markdown_di_scope():
            result = render_markdown(
                "{% for x in xs %}\n- {{ x }}\n{% endfor %}",
                {"xs": ["a", "b"]},
            )
            assert isinstance(result, MarkdownForElement)
            parent = Element("section")
            parent._append_child(result)
            ul = next(c for c in result._children if isinstance(c, Element) and c._tag_name == "ul")
            assert ul._tag_name == "ul"
            lis = [c for c in ul._children if isinstance(c, Element) and c._tag_name == "li"]
            assert len(lis) == 2

    def test_for_with_nested_if_in_body(self):
        with _markdown_di_scope():
            result = render_markdown(
                ("{% for x in xs %}\n{% if x.visible %}\n- {{ x.name }}\n{% endif %}\n{% endfor %}\n"),
                {
                    "xs": [
                        {"name": "a", "visible": True},
                        {"name": "b", "visible": False},
                        {"name": "c", "visible": True},
                    ]
                },
            )
            assert isinstance(result, MarkdownForElement)
            parent = Element("section")
            parent._append_child(result)
            ul = next(c for c in result._children if isinstance(c, Element) and c._tag_name == "ul")
            lis = [c for c in ul._children if isinstance(c, Element) and c._tag_name == "li"]
            names = [_extract_text(li) for li in lis]
            assert "a" in names
            assert "c" in names
            assert "b" not in names


class TestRenderMarkdownComponentTags:
    def test_component_tag_in_html_block_is_resolved(self):
        captured: dict[str, Any] = {}

        def setup(ctx):
            captured["title"] = ctx.props.get("title")
            return Element("span", children=[TextElement(ctx.props.get("title", ""))])

        with _markdown_component_di_scope():
            ComponentGenerator("UserCard", setup)
            result = render_markdown('<user-card title="Hello" />', {})
        assert captured["title"] == "Hello"
        assert isinstance(result, ElementAbstract)
        assert result._tag_name == "span"
        assert _extract_text(result) == "Hello"

    def test_component_tag_in_html_block_alongside_paragraph(self):
        captured: dict[str, Any] = {}

        def setup(ctx):
            captured["label"] = ctx.props.get("label")
            return Element("strong", children=[TextElement(ctx.props.get("label", ""))])

        with _markdown_component_di_scope():
            ComponentGenerator("MyBadge", setup)
            result = render_markdown(
                "Hello\n\n<my-badge label='World' />\n",
                {},
            )
        assert captured["label"] == "World"
        assert isinstance(result, FragmentElement)
        assert len(result._pending_children) == 2
        p, badge = result._pending_children
        assert isinstance(p, Element) and p._tag_name == "p"
        assert p._children[0]._text == "Hello"
        assert isinstance(badge, ElementAbstract)
        assert badge._tag_name == "strong"
        assert badge._children[0]._text == "World"


class TestRenderMarkdownFileLoading:
    @pytest.mark.asyncio
    async def test_load_text_then_render_markdown(self, tmp_path: Path):
        pkg = tmp_path / "app"
        pkg.mkdir()
        (pkg / "page.md").write_text("# {{ title }}\n\nHello", encoding="utf-8")

        from webcompy_server.ports._resource import ServerResourcePort

        port = ServerResourcePort(pkg, frozenset({"page.md"}))

        with _markdown_di_scope() as scope:
            scope.provide(RESOURCE_PORT_KEY, port)
            text = await load_text("page.md")
            result = render_markdown(text, {"title": "Title"})

        assert isinstance(result, FragmentElement)
        h1, p = result._pending_children
        assert isinstance(h1, Element) and h1._tag_name == "h1"
        assert h1._children[0]._text == "Title"
        assert isinstance(p, Element) and p._tag_name == "p"
        assert p._children[0]._text == "Hello"

        recorded = port.get_recorded_resources()
        assert "page.md" in recorded
        assert recorded["page.md"] == b"# {{ title }}\n\nHello"


class TestRenderMarkdownDedent:
    def test_dedent_applied_to_indented_source(self):
        with _markdown_di_scope():
            result = render_markdown(
                """
                    # Title

                    paragraph
                """,
                {},
            )
        assert isinstance(result, FragmentElement)
        h1, p = result._pending_children
        assert isinstance(h1, Element) and h1._tag_name == "h1"
        assert isinstance(p, Element) and p._tag_name == "p"


class TestFragmentTransparency:
    def test_fragment_element_renders_transparently_in_parent(self):
        with _markdown_di_scope():
            md = render_markdown("# Title\n\nText.", {})
        assert isinstance(md, FragmentElement)
        assert len(md._pending_children) == 2

        parent = Element("article", children=[md])
        assert md._parent is parent
        assert md._pending_children == []
        assert len(md._children) == 2
        for child in md._children:
            assert child._parent is parent
        assert md._node_count == 2


class TestComponentRootIntegration:
    def test_multi_root_raises_when_returned_directly_from_component(self):
        @define_component
        def FragmentRoot(context):
            return render_markdown("# Title\n\nText.", {})

        with _markdown_component_di_scope():
            FragmentRoot._try_register()
            with pytest.raises(
                WebComPyException,
                match="Root Node of Component must be instance of 'Element'",
            ):
                FragmentRoot({})

    def test_explicit_element_wrapper_makes_markdown_valid_component_root(self):
        @define_component
        def ArticlePage(context):
            return Element(
                "article",
                children=[render_markdown("# Title\n\nText.", {})],
            )

        with _markdown_component_di_scope():
            ArticlePage._try_register()
            comp = ArticlePage({})
        assert isinstance(comp, Component)
        assert comp._tag_name == "article"
        assert len(comp._children) == 1
        assert isinstance(comp._children[0], FragmentElement)


class TestRenderMarkdownCodeBlockTemplateProtection:
    def test_hole_in_fenced_code_block_rendered_literally(self):
        with _markdown_di_scope():
            result = render_markdown("```\n{{ x }}\n```", {"x": "secret"})
        text = _extract_text(result)
        assert "{{ x }}" in text
        assert "secret" not in text

    def test_directive_in_fenced_code_block_not_executed(self):
        with _markdown_di_scope():
            result = render_markdown("```\n{% if y %}boom{% endif %}\n```", {"y": True})
        text = _extract_text(result)
        assert "{% if y %}" in text
        assert "{% endif %}" in text
        assert "boom" in text

    def test_hole_in_inline_code_span_rendered_literally(self):
        with _markdown_di_scope():
            result = render_markdown("Hello `{{ x }}` world", {"x": "secret"})
        text = _extract_text(result)
        assert "{{ x }}" in text
        assert "secret" not in text


class TestRenderMarkdownUrlSanitization:
    def test_javascript_url_in_link(self):
        with _markdown_di_scope():
            result = render_markdown("[click](javascript:alert(1))", {})
        text = _extract_text(result)
        assert "javascript:" not in text
        assert "click" in text

    def test_javascript_url_in_image(self):
        with _markdown_di_scope():
            result = render_markdown("![alt](javascript:alert(1))", {})
        text = _extract_text(result)
        assert "javascript:" not in text
        assert "<img" not in text


class TestRenderMarkdownDirectivesInCodeNotExecuted:
    def test_if_directive_in_fenced_code_block_not_executed(self):
        with _markdown_di_scope():
            result = render_markdown("```\n{% if y %}x{% endif %}\n```", {"y": False})
        text = _extract_text(result)
        assert "{% if y %}" in text
        assert text.count("{% if y %}") == 1

    def test_if_directive_in_fenced_code_block_keeps_intact(self):
        with _markdown_di_scope():
            result = render_markdown("```\n{% if y %}x{% endif %}\n```", {"y": True})
        assert isinstance(result, Element)
        assert result._tag_name == "pre"
        inner_text = _extract_text(result)
        assert "{% if y %}" in inner_text
        assert "{% endif %}" in inner_text

    def test_hole_in_fenced_code_block_keeps_intact(self):
        with _markdown_di_scope():
            result = render_markdown("```\n{{ x }}\n```", {"x": "SECRET"})
        assert isinstance(result, Element)
        assert result._tag_name == "pre"
        inner_text = _extract_text(result)
        assert "{{ x }}" in inner_text
        assert "SECRET" not in inner_text
