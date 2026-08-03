from __future__ import annotations

from contextlib import contextmanager

import pytest

from tests.conftest import FakeDOMNode
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements.types._element import Element, ElementBase
from webcompy.exception import WebComPyException
from webcompy.ports._keys import MARKDOWN_PORT_KEY
from webcompy.signal import ReactiveDict, ReactiveList, Signal, SignalBase
from webcompy.template import render_markdown
from webcompy.template._cache import clear_cache
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy.template._markdown_for import (
    MarkdownForElement,
    _apply_renames,
    _is_list_body,
    _tokenize_source,
)


class _FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _make_render_parent():
    parent = _FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    return parent


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


def _attach(mfe: MarkdownForElement, parent: ElementBase | None = None) -> ElementBase:
    if parent is None:
        parent = Element("section")
    parent._append_child(mfe)
    return parent


def _find_ul(mfe: MarkdownForElement, tag: str = "ul") -> Element:
    for c in mfe._children:
        if isinstance(c, ElementBase) and c._tag_name == tag:
            return c  # type: ignore[return-value]
    raise StopIteration(f"No <{tag}> found in children")


def _find_lis(ul: Element) -> list[Element]:
    return [c for c in ul._children if isinstance(c, ElementBase) and c._tag_name == "li"]  # type: ignore[misc]


class TestMarkdownForBasic:
    def test_single_list_body_for_produces_one_ul(self):
        with _markdown_di_scope():
            mfe = MarkdownForElement(
                ["item"],
                "items",
                "- {{ item }}",
                {"items": ["a", "b", "c"]},
            )
            _attach(mfe)
        ul = _find_ul(mfe)
        lis = _find_lis(ul)
        assert len(lis) == 3

    def test_ordered_list_body_produces_one_ol(self):
        with _markdown_di_scope():
            mfe = MarkdownForElement(
                ["item"],
                "items",
                "1. {{ item }}",
                {"items": ["a", "b"]},
            )
            _attach(mfe)
        ol = _find_ul(mfe, "ol")
        lis = _find_lis(ol)
        assert len(lis) == 2


class TestMarkdownForFieldReactivity:
    def test_field_level_reactivity_uses_signal_directly(self):
        name_sig = Signal("alice")
        items = [{"name": name_sig}, {"name": Signal("bob")}]
        with _markdown_di_scope():
            mfe = MarkdownForElement(
                ["item"],
                "items",
                "- {{ item.name }}",
                {"items": items},
            )
            _attach(mfe)
        ul = _find_ul(mfe)
        lis = _find_lis(ul)
        text_el = lis[0]._children[0]
        assert isinstance(text_el._text, Signal)
        assert text_el._text is name_sig
        assert text_el._text.value == "alice"


class TestMarkdownForCollectionReactivity:
    def test_reactive_list_iterable_is_signal(self):
        items = ReactiveList(["a", "b"])
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": items})
        with _markdown_di_scope():
            _attach(mfe)
        assert isinstance(mfe._iterable, SignalBase)
        ul = _find_ul(mfe)
        assert len(_find_lis(ul)) == 2

    def test_reactive_list_three_items(self):
        items = ReactiveList(["a", "b", "c"])
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": items})
        with _markdown_di_scope():
            _attach(mfe)
        ul = _find_ul(mfe)
        assert len(_find_lis(ul)) == 3

    def test_reactive_dict_creates_ul(self):
        d = ReactiveDict({"k1": "v1", "k2": "v2"})
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": d})
        with _markdown_di_scope():
            _attach(mfe)
        ul = _find_ul(mfe)
        assert len(_find_lis(ul)) == 2

    @pytest.mark.asyncio
    async def test_reactive_list_pop_decreases_li(self, fake_browser_full):
        _active_di_scope.get().provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        items = ReactiveList(["a", "b", "c"])
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": items})
        parent = _make_render_parent()
        mfe._parent = parent
        mfe._node_idx = 0
        await mfe._render()

        ul = _find_ul(mfe)
        assert len(_find_lis(ul)) == 3

        items.pop(0)

        ul = _find_ul(mfe)
        assert len(_find_lis(ul)) == 2


class TestMarkdownForStaticIterable:
    def test_static_list_iterable_is_not_signal(self):
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": ["a", "b"]})
        with _markdown_di_scope():
            _attach(mfe)
        assert not isinstance(mfe._iterable, SignalBase)
        ul = _find_ul(mfe)
        assert len(_find_lis(ul)) == 2


class TestMarkdownForLoopMetadata:
    def _li_texts(self, mfe: MarkdownForElement) -> list[str]:
        ul = _find_ul(mfe)
        result: list[str] = []
        for li in _find_lis(ul):
            parts: list[str] = []
            for c in li._children:
                if isinstance(c, str):
                    parts.append(c)
                elif hasattr(c, "_text") and isinstance(c._text, str):
                    parts.append(c._text)
            result.append("".join(parts))
        return result

    def test_loop_index_and_edges_rendered(self):
        mfe = MarkdownForElement(
            ["item"],
            "items",
            "- {{ loop.index }}:{{ loop.first }}-{{ loop.last }}/{{ loop.length }} {{ item }}",
            {"items": ["a", "b", "c"]},
        )
        with _markdown_di_scope():
            _attach(mfe)
        assert self._li_texts(mfe) == [
            "1:True-False/3 a",
            "2:False-False/3 b",
            "3:False-True/3 c",
        ]

    def test_loop_revindex_and_index0(self):
        mfe = MarkdownForElement(
            ["item"],
            "items",
            "- {{ loop.index0 }}-{{ loop.revindex }} {{ item }}",
            {"items": ["a", "b"]},
        )
        with _markdown_di_scope():
            _attach(mfe)
        assert self._li_texts(mfe) == ["0-2 a", "1-1 b"]

    def test_literal_text_loop_unaffected(self):
        mfe = MarkdownForElement(
            ["item"],
            "items",
            "- loop: {{ item }}",
            {"items": ["a"]},
        )
        with _markdown_di_scope():
            _attach(mfe)
        assert self._li_texts(mfe) == ["loop: a"]

    def test_loop_in_nested_directive(self):
        mfe = MarkdownForElement(
            ["item"],
            "items",
            "- {% if loop.first %}first{% else %}{{ loop.index }}{% endif %}",
            {"items": ["a", "b"]},
        )
        with _markdown_di_scope():
            _attach(mfe)
        assert self._li_texts(mfe) == ["first", "2"]

    def test_one_var_dict_loop_binds_values_not_tuples(self):
        mfe = MarkdownForElement(
            ["v"],
            "d",
            "- {{ v }}",
            {"d": {"k1": "v1", "k2": "v2"}},
        )
        with _markdown_di_scope():
            _attach(mfe)
        assert self._li_texts(mfe) == ["v1", "v2"]

    def test_one_var_reactive_dict_loop_binds_values(self):
        d = ReactiveDict({"k1": "v1", "k2": "v2"})
        mfe = MarkdownForElement(["v"], "d", "- {{ v }}", {"d": d})
        with _markdown_di_scope():
            _attach(mfe)
        assert self._li_texts(mfe) == ["v1", "v2"]


class TestMarkdownNestedLoopMetadata:
    def _li_texts(self, mfe: MarkdownForElement) -> list[str]:
        ul = _find_ul(mfe)
        result: list[str] = []
        for li in _find_lis(ul):
            parts: list[str] = []
            for c in li._children:
                if isinstance(c, str):
                    parts.append(c)
                elif hasattr(c, "_text") and isinstance(c._text, str):
                    parts.append(c._text)
            result.append("".join(parts))
        return result

    def test_inner_loop_metadata_is_innermost(self):
        items = [{"subs": ["a", "b"]}, {"subs": ["c"]}]
        body = "- {% for sub in item.subs %}{{ loop.index }}:{{ sub }} {% endfor %}outer={{ loop.length }}\n"
        with _markdown_di_scope():
            mfe = MarkdownForElement(["item"], "items", body, {"items": items})
            _attach(mfe)
        assert self._li_texts(mfe) == ["1:a 2:b outer=2", "1:c outer=2"]

    def test_inner_loop_length_differs_from_outer(self):
        items = [{"subs": ["a", "b", "c"]}]
        body = "- {% for sub in item.subs %}{{ loop.length }}:{{ sub }} {% endfor %}outer={{ loop.length }}\n"
        with _markdown_di_scope():
            mfe = MarkdownForElement(["item"], "items", body, {"items": items})
            _attach(mfe)
        assert self._li_texts(mfe) == ["3:a 3:b 3:c outer=1"]

    def test_outer_loop_variable_named_loop_preserves_inner_metadata(self):
        items = [{"label": "L", "subs": ["a", "b"]}]
        body = "- {% for sub in loop.subs %}{{ loop.index }}:{{ sub }} {% endfor %}{{ loop.label }}\n"
        with _markdown_di_scope():
            mfe = MarkdownForElement(["loop"], "items", body, {"items": items})
            _attach(mfe)
        assert self._li_texts(mfe) == ["1:a 2:b L"]

    def test_inner_loop_variable_named_loop_shadows_metadata(self):
        items = [{"subs": ["x", "y"]}, {"subs": ["z"]}]
        body = "- {% for loop in item.subs %}{{ loop }} {% endfor %}\n"
        with _markdown_di_scope():
            mfe = MarkdownForElement(["item"], "items", body, {"items": items})
            _attach(mfe)
        assert self._li_texts(mfe) == ["x y", "z"]

    def test_outer_loop_variable_reference_inside_inner_body(self):
        items = [{"name": "A", "subs": ["x", "y"]}, {"name": "B", "subs": ["z"]}]
        body = "- {% for sub in item.subs %}{{ item.name }}{{ sub }} {% endfor %}\n"
        with _markdown_di_scope():
            mfe = MarkdownForElement(["item"], "items", body, {"items": items})
            _attach(mfe)
        assert self._li_texts(mfe) == ["Ax Ay", "Bz"]


class TestRenaming:
    def test_rename_in_expressions_renames_var_in_hole(self):
        result = _apply_renames("{{ item.name }}", {"item": "__wmdf_0_item"})
        assert result == "{{ __wmdf_0_item.name }}"

    def test_rename_depth_aware_nested_braces_in_hole(self):
        result = _apply_renames("{{ {'a': {'b': 1}} and item }}", {"item": "__wmdf_0_item"})
        assert result == "{{ {'a': {'b': 1}} and __wmdf_0_item }}"

    def test_rename_handles_multibyte_characters(self):
        result = _apply_renames('{{ "é" + item }}', {"item": "__wmdf_0_item"})
        assert result == '{{ "é" + __wmdf_0_item }}'

    def test_rename_in_expressions_preserves_prose(self):
        result = _apply_renames(
            "The item is {{ item.name }} and the items are separate.",
            {"item": "__wmdf_0_item"},
        )
        assert "items are separate" in result
        assert "{{ item.name }}" not in result
        assert "{{ __wmdf_0_item.name }}" in result

    def test_rename_in_expressions_word_boundary_no_partial_match(self):
        result = _apply_renames("{{ items }}", {"item": "__wmdf_0_item"})
        assert result == "{{ items }}"

    def test_rename_preserves_quoted_string_literal(self):
        result = _apply_renames('{{ "loop" }}', {"loop": "__wmdf_0_loop"})
        assert "__wmdf" not in result
        assert "loop" in result

    def test_rename_preserves_multi_backtick_code_span(self):
        text = "- `` `item` {{ item }} ``\n"
        result = _apply_renames(text, {"item": "__wmdf_0_item"})
        assert result == text

    def test_rename_preserves_subscript_string_literal(self):
        result = _apply_renames('{{ x["loop"] }}', {"loop": "__wmdf_0_loop"})
        assert "__wmdf" not in result

    def test_rename_preserves_attribute_access_named_like_loop_var(self):
        result = _apply_renames("{{ obj.loop }}", {"loop": "__wmdf_0_loop"})
        assert "__wmdf" not in result
        assert "obj.loop" in result

    def test_rename_preserves_raw_block_content(self):
        result = _apply_renames("{% raw %}{{ loop }}{% endraw %}", {"loop": "__wmdf_0_loop"})
        assert "__wmdf" not in result
        assert "{{ loop }}" in result

    def test_rename_renames_free_variable_outside_raw_block(self):
        result = _apply_renames("{{ loop.index }}{% raw %}{{ loop }}{% endraw %}", {"loop": "__wmdf_0_loop"})
        assert "{{ __wmdf_0_loop.index }}" in result
        assert "{% raw %}{{ loop }}{% endraw %}" in result

    def test_rename_multiline_expression_renames_names_per_line(self):
        result = _apply_renames("{{ (item.name +\n    item.age) }}", {"item": "__wmdf_0_item"})
        assert result == "{{ (__wmdf_0_item.name +\n    __wmdf_0_item.age) }}"

    def test_rename_multiline_attribute_segment_not_renamed(self):
        result = _apply_renames("{{ (obj.item.name +\n    obj.item.age) }}", {"item": "__wmdf_0_item"})
        assert "__wmdf" not in result
        assert "obj.item" in result

    def test_rename_multiline_string_literal_not_renamed(self):
        result = _apply_renames('{{ (item.name +\n    "item") }}', {"item": "__wmdf_0_item"})
        assert result == '{{ (__wmdf_0_item.name +\n    "item") }}'

    def test_rename_regex_fallback_skips_attribute_segment(self):
        from webcompy.template._markdown_for import _rename_expression

        result = _rename_expression("obj.item + (", {"item": "__wmdf_0_item"})
        assert "__wmdf" not in result

    def test_rename_preserves_inline_code_span(self):
        result = _apply_renames("- `{{ item }}` and {{ item }}", {"item": "__wmdf_0_item"})
        assert "`{{ item }}`" in result
        assert "{{ __wmdf_0_item }}" in result

    def test_rename_preserves_fenced_code_block(self):
        body = "- {{ item }}\n\n```\n{{ item }}\n```"
        result = _apply_renames(body, {"item": "__wmdf_0_item"})
        assert "{{ __wmdf_0_item }}" in result
        assert "```\n{{ item }}\n```" in result

    def test_rename_preserves_code_span_inside_raw_block(self):
        result = _apply_renames("{% raw %}`{{ item }}`{% endraw %}", {"item": "__wmdf_0_item"})
        assert "__wmdf" not in result

    def test_rename_preserves_fenced_code_containing_raw_block(self):
        body = "```\n{% raw %}\n{{ item }}\n{% endraw %}\n```"
        result = _apply_renames(body, {"item": "__wmdf_0_item"})
        assert "__wmdf" not in result
        assert "{{ item }}" in result

    def test_rendered_code_span_keeps_template_text_literal(self):
        def _collect_text(nodes: list[object]) -> str:
            parts: list[str] = []
            for c in nodes:
                if isinstance(c, str):
                    parts.append(c)
                    continue
                text = getattr(c, "_text", None)
                if isinstance(text, str):
                    parts.append(text)
                parts.append(_collect_text(list(getattr(c, "_children", []))))
            return "".join(parts)

        with _markdown_di_scope():
            mfe = MarkdownForElement(["item"], "items", "- `{{ item }}` and {{ item }}", {"items": ["A"]})
            _attach(mfe)
        ul = _find_ul(mfe)
        li = _find_lis(ul)[0]
        assert "{{ item }}" in _collect_text(li._children)
        assert _collect_text(li._children).endswith(" and A")

    def test_loop_variable_renamed_per_iteration(self):
        with _markdown_di_scope():
            mfe = MarkdownForElement(
                ["item"],
                "items",
                "- {{ item.name }}",
                {"items": [{"name": "a"}, {"name": "b"}]},
            )
            _attach(mfe)
        ul = _find_ul(mfe)
        lis = _find_lis(ul)
        texts = [li._children[0]._text for li in lis]
        assert "a" in texts
        assert "b" in texts

    def test_tuple_unpacking_renames_both_vars(self):
        d = {"key1": "val1", "key2": "val2"}
        with _markdown_di_scope():
            mfe = MarkdownForElement(["k", "v"], "d", "- {{ k }}: {{ v }}", {"d": d})
            _attach(mfe)
        ul = _find_ul(mfe)
        lis = _find_lis(ul)
        assert len(lis) == 2


class TestNestedFor:
    def test_nested_list_body_for_merged_recursively(self):
        items = [
            {"name": "A", "subs": ["x", "y"]},
            {"name": "B", "subs": ["z"]},
        ]
        body = "- {{ item.name }}\n{% for sub in item.subs %}\n  - {{ sub }}\n{% endfor %}"
        with _markdown_di_scope():
            mfe = MarkdownForElement(
                ["item"],
                "items",
                body,
                {"items": items},
            )
            _attach(mfe)
        ul = _find_ul(mfe)
        lis = _find_lis(ul)
        assert len(lis) == 2


class TestIfInFor:
    def test_if_truthy_emits_body(self):
        items = [{"name": "a", "active": True}]
        with _markdown_di_scope():
            mfe = MarkdownForElement(
                ["item"],
                "items",
                "- {{ item.name }}",
                {"items": items},
            )
            _attach(mfe)
        ul = _find_ul(mfe)
        assert len(_find_lis(ul)) == 1

    def test_if_falsy_omits_body(self):
        items = [{"name": "a", "active": False}, {"name": "b", "active": False}]
        body = "\n{% if item.active %}\n- {{ item.name }}\n{% endif %}\n"
        with _markdown_di_scope():
            mfe = MarkdownForElement(["item"], "items", body, {"items": items})
            _attach(mfe)
        assert mfe._children == []

    def test_elif_else_within_static_if(self):
        items = [
            {"show_a": True, "show_b": False},
            {"show_a": False, "show_b": True},
            {"show_a": False, "show_b": False},
        ]
        body = (
            "\n{% if item.show_a %}\n- A branch\n"
            "{% elif item.show_b %}\n- B branch\n"
            "{% else %}\n- else branch\n{% endif %}\n"
        )
        with _markdown_di_scope():
            mfe = MarkdownForElement(["item"], "items", body, {"items": items})
            _attach(mfe)
        ul = _find_ul(mfe)
        lis = _find_lis(ul)
        assert len(lis) == 3


class TestBodyDetection:
    def test_list_body_with_dash(self):
        assert _is_list_body("\n- item one\n- item two\n") is True

    def test_list_body_with_asterisk(self):
        assert _is_list_body("\n* item one\n") is True

    def test_list_body_with_plus(self):
        assert _is_list_body("\n+ item one\n") is True

    def test_ordered_list_body(self):
        assert _is_list_body("\n1. item one\n2. item two\n") is True

    def test_non_list_heading_body(self):
        assert _is_list_body("\n# Heading\n") is False

    def test_non_list_paragraph_body(self):
        assert _is_list_body("\nThis is a paragraph.\n") is False

    def test_non_list_html_body(self):
        assert _is_list_body("\n<div>html</div>\n") is False

    def test_list_body_with_if_directive_first(self):
        body = "\n{% if x.visible %}\n- {{ x.name }}\n{% endif %}\n"
        assert _is_list_body(body) is True

    def test_list_body_with_task_marker(self):
        assert _is_list_body("\n- [ ] {{ item }}\n") is True

    def test_list_body_with_checked_task_marker(self):
        assert _is_list_body("\n- [x] {{ item }}\n") is True

    def test_list_body_ordered_marker_any_start_number(self):
        assert _is_list_body("\n3. {{ item }}\n") is True

    def test_indented_code_looking_body_is_not_list(self):
        assert _is_list_body("    - not a list") is False


class TestProtectedSpans:
    def test_tilde_fence_protects_directives(self):
        tokens = _tokenize_source("~~~\n{% for x in xs %}\n~~~")
        assert all(t.kind == "text" for t in tokens)

    def test_backtick_fence_still_protects(self):
        tokens = _tokenize_source("```\n{% for x in xs %}\n```")
        assert all(t.kind == "text" for t in tokens)

    def test_tilde_inside_backtick_fence_does_not_close(self):
        tokens = _tokenize_source("```\n~~~\n{% for x in xs %}\n```")
        assert all(t.kind == "text" for t in tokens)

    def test_backtick_inside_tilde_fence_does_not_close(self):
        tokens = _tokenize_source("~~~\n```\n{% for x in xs %}\n~~~")
        assert all(t.kind == "text" for t in tokens)

    def test_shorter_backtick_fence_does_not_close(self):
        tokens = _tokenize_source("````\n```\n{% endfo %}\n````")
        assert all(t.kind == "text" for t in tokens)

    def test_shorter_tilde_fence_does_not_close(self):
        tokens = _tokenize_source("~~~~\n~~~\n{% endfo %}\n~~~~")
        assert all(t.kind == "text" for t in tokens)

    def test_fence_closing_line_with_trailing_content_does_not_close(self):
        tokens = _tokenize_source("```\n```info\n{% endfo %}\n```")
        assert all(t.kind == "text" for t in tokens)

    def test_directive_inside_comment_not_tokenized(self):
        tokens = _tokenize_source("{# {% for x in xs %} #}")
        assert all(t.kind == "text" for t in tokens)

    def test_directive_inside_html_comment_not_tokenized(self):
        tokens = _tokenize_source("<!-- {% for x in xs %} -->")
        assert all(t.kind == "text" for t in tokens)

    def test_directive_inside_raw_block_not_tokenized(self):
        tokens = _tokenize_source("{% raw %}{% for x in xs %}{% endraw %}")
        assert all(t.kind == "text" for t in tokens)

    def test_directive_inside_hole_not_tokenized(self):
        tokens = _tokenize_source('{{ "{% for x in xs %}" }}')
        assert all(t.kind == "text" for t in tokens)

    def test_directive_inside_unquoted_attr_not_tokenized(self):
        tokens = _tokenize_source("<a href={% endfo %}>link</a>")
        assert all(t.kind == "text" for t in tokens)


class TestExpandDirectivesInBody:
    def test_if_inside_code_span_stays_literal(self):
        from webcompy.template._markdown_for import _expand_directives_in_body

        body = "- `{% if cond %}a{% else %}b{% endif %}`\n"
        result = _expand_directives_in_body(body, {"cond": True}, "", {})
        assert result == body

    def test_if_inside_raw_block_stays_literal(self):
        from webcompy.template._markdown_for import _expand_directives_in_body

        body = "- {% raw %}{% if cond %}a{% endif %}{% endraw %}\n"
        result = _expand_directives_in_body(body, {"cond": True}, "", {})
        assert result == body

    def test_if_inside_comment_stays_literal(self):
        from webcompy.template._markdown_for import _expand_directives_in_body

        body = "- {# {% if cond %}a{% endif %} #}\n"
        result = _expand_directives_in_body(body, {"cond": True}, "", {})
        assert result == body

    def test_unprotected_if_still_expands(self):
        from webcompy.template._markdown_for import _expand_directives_in_body

        body = "- {% if cond %}a{% else %}b{% endif %}\n"
        result = _expand_directives_in_body(body, {"cond": True}, "", {})
        assert result == "- a\n"

    def test_mixed_protected_and_unprotected_directives(self):
        from webcompy.template._markdown_for import _expand_directives_in_body

        body = "- `{% if x %}a{% endif %}` {% if cond %}b{% endif %}"
        result = _expand_directives_in_body(body, {"cond": True}, "", {})
        assert result == "- `{% if x %}a{% endif %}` b"

    def test_modulo_condition_expands(self):
        from webcompy.template._markdown_for import _expand_directives_in_body

        body = "{% if n % 2 == 0 %}\n- even\n{% else %}\n- odd\n{% endif %}"
        assert _expand_directives_in_body(body, {"n": 4}, "", {}) == "\n- even\n"
        assert _expand_directives_in_body(body, {"n": 3}, "", {}) == "\n- odd\n"

    def test_if_elif_else_expression_expands(self):
        from webcompy.template._markdown_for import _expand_directives_in_body

        body = "{% if n % 3 == 0 %}\n- fizz\n{% elif n % 3 == 1 %}\n- one\n{% else %}\n- other\n{% endif %}"
        assert _expand_directives_in_body(body, {"n": 3}, "", {}) == "\n- fizz\n"
        assert _expand_directives_in_body(body, {"n": 4}, "", {}) == "\n- one\n"
        assert _expand_directives_in_body(body, {"n": 5}, "", {}) == "\n- other\n"

    def test_comparison_condition_expands(self):
        from webcompy.template._markdown_for import _expand_directives_in_body

        body = "{% if count > 3 %}\n- big\n{% else %}\n- small\n{% endif %}"
        assert _expand_directives_in_body(body, {"count": 5}, "", {}) == "\n- big\n"
        assert _expand_directives_in_body(body, {"count": 2}, "", {}) == "\n- small\n"

    def test_if_expression_wrapping_list_for_selects_branch(self):
        from webcompy.template._markdown_for import _split_markdown_source

        source = "{% if n % 2 == 0 %}\n{% for item in items %}\n- {{ item }}\n{% endfor %}\n{% endif %}"
        with _markdown_di_scope():
            result = _split_markdown_source(source, {"n": 4, "items": ["a"]})
            assert any(getattr(x, "loop_vars", None) == ["item"] for x in result)
            result_odd = _split_markdown_source(source, {"n": 3, "items": ["a"]})
            assert not any(getattr(x, "loop_vars", None) for x in result_odd)


class TestEscapeHatch:
    def test_html_block_for_uses_repeat_path(self):
        body = "<ul>\n{% for item in items %}<li>{{ item }}</li>{% endfor %}\n</ul>"
        with _markdown_di_scope():
            mfe = MarkdownForElement(["item"], "items", body, {"items": ["a", "b"]})
            _attach(mfe)
        ul = _find_ul(mfe)
        lis = _find_lis(ul)
        assert len(lis) == 2


class TestLifecycle:
    def test_empty_iterable_produces_no_children(self):
        with _markdown_di_scope():
            mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": []})
            _attach(mfe)
        assert mfe._children == []

    @pytest.mark.asyncio
    async def test_callback_registered_after_render(self, fake_browser_full):
        _active_di_scope.get().provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        items = ReactiveList(["a", "b"])
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": items})
        parent = _make_render_parent()
        mfe._parent = parent
        mfe._node_idx = 0

        assert len(mfe._callback_nodes) == 0
        assert mfe._signal_activated is False

        await mfe._render()

        assert mfe._signal_activated is True
        assert len(mfe._callback_nodes) == 1

    @pytest.mark.asyncio
    async def test_static_iterable_no_callback_after_render(self, fake_browser_full):
        _active_di_scope.get().provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": ["a", "b"]})
        parent = _make_render_parent()
        mfe._parent = parent
        mfe._node_idx = 0
        await mfe._render()

        assert mfe._signal_activated is True
        assert len(mfe._callback_nodes) == 0

    @pytest.mark.asyncio
    async def test_callback_destroyed_on_remove_element(self, fake_browser_full):
        _active_di_scope.get().provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        items = ReactiveList(["a", "b"])
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": items})
        parent = _make_render_parent()
        mfe._parent = parent
        mfe._node_idx = 0
        await mfe._render()
        assert len(mfe._callback_nodes) == 1

        nodes_before = list(mfe._callback_nodes)
        for node in nodes_before:
            assert node.producers is not None

        mfe._remove_element()

        for node in nodes_before:
            assert node.producers is None


class TestErrorHandling:
    def test_two_var_for_with_non_dict_raises(self):
        with _markdown_di_scope():
            mfe = MarkdownForElement(
                ["k", "v"],
                "pairs",
                "- {{ k }}: {{ v }}",
                {"pairs": [("a", 1), ("b", 2)]},
            )
            with pytest.raises(WebComPyException, match="Two-variable for-loop requires a dict iterable"):
                _attach(mfe)

    def test_nested_two_var_for_with_non_dict_raises(self):
        items = [{"name": "x", "pairs": [("a", 1)]}]
        body = "- {{ item.name }}\n{% for k, v in item.pairs %}\n  - {{ k }}: {{ v }}\n{% endfor %}"
        with _markdown_di_scope():
            mfe = MarkdownForElement(
                ["item"],
                "items",
                body,
                {"items": items},
            )
            with pytest.raises(WebComPyException, match="Two-variable for-loop requires a dict iterable"):
                _attach(mfe)


class TestMarkdownDirectiveValidation:
    def test_unknown_directive_in_for_body_raises_with_empty_iterable(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="Unknown template directive"):
            render_markdown("{% for item in items %}\n- {% endfo %}\n{% endfor %}", {"items": []})

    def test_unknown_directive_in_for_body_raises_at_render_time(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="Unknown template directive"):
            render_markdown("{% for item in items %}\n- {% endfo %}\n{% endfor %}", {"items": ["a"]})

    def test_unsupported_directive_in_for_body_raises(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="not supported"):
            render_markdown(
                "{% for item in items %}\n- {% extends 'base.html' %}\n{% endfor %}",
                {"items": ["a"]},
            )

    def test_unknown_directive_in_statically_unselected_branch_raises(self):
        body = (
            "{% for item in items %}\n"
            "{% if item.visible %}\n"
            "- {{ item.name }}\n"
            "{% else %}\n"
            "- {% endfo %}\n"
            "{% endif %}\n"
            "{% endfor %}"
        )
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="Unknown template directive"):
            render_markdown(body, {"items": [{"name": "a", "visible": True}]})

    def test_directive_like_text_in_code_span_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("- `{% endfo %}`\n")

    def test_directive_after_four_backtick_fence_with_shorter_line_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("````\n```\n{% endfo %}\n````\n")

    def test_directive_after_fence_closing_line_with_trailing_content_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("```\n```info\n{% endfo %}\n```\n")

    def test_directive_in_multi_backtick_code_span_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("- `` `x` {% endfo %} ``\n")

    def test_directive_after_properly_closed_fence_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        with pytest.raises(WebComPyException, match="Unknown template directive"):
            _validate_directives("```\ncode\n```\n{% endfo %}\n")

    def test_directive_like_text_in_attribute_value_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives('- <a href="{% endfo %}">x</a>\n')

    def test_directive_like_text_in_raw_block_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("- {% raw %}{% endfo %}{% endraw %}\n")

    def test_directive_like_text_in_comment_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("- {# {% endfo %} #}\n")

    def test_directive_like_text_in_html_comment_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("- <!-- {% endfo %} -->\n")

    def test_comment_like_text_inside_raw_block_preserved(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("- {% raw %}{# {% endfo %} #}{% endraw %}\n")

    def test_directive_like_text_in_unquoted_attribute_value_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("- <a href={% endfo %}>x</a>\n")
        _validate_directives("- <a href={%endfo%}>x</a>\n")

    def test_directive_like_text_inside_hole_not_rejected(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives('- {{ "{% endfo %}" }}\n')

    def test_unknown_directive_in_unselected_top_level_branch_raises(self):
        body = "{% if flag %}ok{% else %}{% endfo %}{% endif %}"
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="Unknown template directive"):
            render_markdown(body, {"flag": True})

    def test_unsupported_directive_in_unselected_branch_raises(self):
        body = "{% if flag %}ok{% else %}{% include 'x' %}{% endif %}"
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="not supported"):
            render_markdown(body, {"flag": True})

    def test_for_else_in_list_body_raises(self):
        body = "{% for item in items %}\n- {{ item }}\n{% else %}\n- empty\n{% endfor %}"
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="outside of"):
            render_markdown(body, {"items": ["a", "b"]})

    def test_for_else_in_list_body_raises_with_empty_iterable(self):
        body = "{% for item in items %}\n- {{ item }}\n{% else %}\n- empty\n{% endfor %}"
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="outside of"):
            render_markdown(body, {"items": []})

    def test_for_elif_in_list_body_raises(self):
        body = "{% for item in items %}\n{% elif item %}\n- {{ item }}\n{% endfor %}"
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="outside of"):
            render_markdown(body, {"items": ["a"]})

    def test_stray_endfor_in_markdown_raises(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="without matching"):
            render_markdown("{% endfor %}", {})

    def test_unclosed_for_in_list_body_raises(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="Unclosed"):
            render_markdown("{% for item in items %}\n- {{ item }}", {"items": ["a"]})

    def test_unclosed_raw_in_list_body_raises_with_empty_iterable(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="Unclosed"):
            render_markdown("{% for item in items %}\n- {% raw %}{{ item }}\n{% endfor %}", {"items": []})

    def test_unclosed_raw_in_list_body_raises_with_nonempty_iterable(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="Unclosed"):
            render_markdown("{% for item in items %}\n- {% raw %}{{ item }}\n{% endfor %}", {"items": ["a"]})

    def test_unclosed_raw_at_top_level_raises(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="Unclosed"):
            render_markdown("- {% raw %}{{ x }}\n", {"x": "y"})

    def test_stray_endraw_in_markdown_raises(self):
        with _markdown_di_scope(), pytest.raises(WebComPyException, match="without matching"):
            render_markdown("- {% endraw %}\n", {})

    def test_balanced_raw_block_passes_validation(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("- {% raw %}{{ x }}{% endraw %}\n")

    def test_unclosed_raw_raises_in_validate_directives(self):
        from webcompy.template._markdown_for import _validate_directives

        with pytest.raises(WebComPyException, match="Unclosed"):
            _validate_directives("- {% raw %}{{ x }}\n")

    def test_stray_endraw_raises_in_validate_directives(self):
        from webcompy.template._markdown_for import _validate_directives

        with pytest.raises(WebComPyException, match="without matching"):
            _validate_directives("- {% endraw %}\n")

    def test_sequential_raw_blocks_pass_validation(self):
        from webcompy.template._markdown_for import _validate_directives

        _validate_directives("{% raw %}a{% endraw %}{% raw %}b{% endraw %}")


class TestPreScanNoLeak:
    def test_if_pre_scan_with_signal_intermediate_does_not_leak(self):
        from webcompy.signal import Signal
        from webcompy.template._markdown_for import _split_markdown_source

        user = Signal({"visible": True})
        source = "{% if user.visible %}\n{% for item in items %}\n- {{ item }}\n{% endfor %}\n{% endif %}"
        with _markdown_di_scope():
            for _ in range(3):
                _split_markdown_source(source, {"user": user, "items": ["a", "b"]})
        assert user.consumers is None

    def test_nested_for_iterable_with_signal_intermediate_does_not_leak(self):
        from webcompy.signal import Signal
        from webcompy.template._markdown_for import _expand_directives_in_body

        entry = Signal({"items": ["a"]})
        body = "\n{% for item in entry.items %}\n- {{ item }}\n{% endfor %}\n"
        ctx = {"__wmdf_0_entry": entry, "__wmdf_0_loop": None}
        result = _expand_directives_in_body(body, ctx, "__wmdf_0_", {"entry": "__wmdf_0_entry"})
        assert "- {{ __wmdf_0_0_item }}\n" in result
        assert entry.consumers is None
