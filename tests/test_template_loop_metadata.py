from __future__ import annotations

from typing import Any

from webcompy.components import ComponentContext, define_component
from webcompy.elements.types._element import Element
from webcompy.elements.types._text import TextElement
from webcompy.signal import use_reactive_list
from webcompy.template import render_template
from webcompy_testing import TestRenderer


def _text_of(node: Any) -> str:
    if isinstance(node, TextElement):
        return str(node._text)
    if isinstance(node, Element):
        return "".join(_text_of(c) for c in node._children)
    if isinstance(node, str):
        return node
    return str(node)


def _render_text(source: str, ctx: dict[str, Any]) -> list[str]:
    el = render_template(source, ctx)
    assert isinstance(el, Element)
    return [_text_of(c) for c in el._children]


class TestStaticLoopMetadata:
    def test_all_seven_attributes_list(self):
        source = (
            "<li>{{ loop.index }},{{ loop.index0 }},{{ loop.revindex }},"
            "{{ loop.revindex0 }},{{ loop.first }},{{ loop.last }},{{ loop.length }}</li>"
        )
        items = _render_text(
            "<ul>{% for x in items %}" + source + "{% endfor %}</ul>",
            {"items": ["a", "b", "c"]},
        )
        assert items == [
            "1,0,3,2,True,False,3",
            "2,1,2,1,False,False,3",
            "3,2,1,0,False,True,3",
        ]

    def test_first_and_last_flags_only_for_edge_items(self):
        items = _render_text(
            "<ul>{% for x in items %}<li>{{ loop.first }}-{{ loop.last }}</li>{% endfor %}</ul>",
            {"items": ["a", "b", "c"]},
        )
        assert items == ["True-False", "False-False", "False-True"]

    def test_single_item_is_first_and_last(self):
        items = _render_text(
            "<ul>{% for x in items %}<li>{{ loop.first }}-{{ loop.last }}-{{ loop.length }}</li>{% endfor %}</ul>",
            {"items": ["only"]},
        )
        assert items == ["True-True-1"]

    def test_static_dict_one_var_iterates_values(self):
        items = _render_text(
            "<ul>{% for v in d %}<li>{{ loop.index }}:{{ v }}</li>{% endfor %}</ul>",
            {"d": {"x": 1, "y": 2, "z": 3}},
        )
        assert items == ["1:1", "2:2", "3:3"]

    def test_static_dict_two_var(self):
        items = _render_text(
            "<ul>{% for k, v in d %}<li>{{ loop.index }}:{{ k }}={{ v }}</li>{% endfor %}</ul>",
            {"d": {"x": 1, "y": 2}},
        )
        assert items == ["1:x=1", "2:y=2"]

    def test_empty_iterable_produces_no_items(self):
        items = _render_text(
            "<ul>{% for x in items %}<li>{{ loop.index }}</li>{% endfor %}</ul>",
            {"items": []},
        )
        assert items == []

    def test_loop_in_if_condition(self):
        items = _render_text(
            "<ul>{% for x in items %}<li>{% if loop.first %}first{% else %}{{ loop.index }}{% endif %}</li>{% endfor %}</ul>",
            {"items": ["a", "b"]},
        )
        assert items == ["first", "2"]


class TestNestedLoopShadowing:
    def test_inner_loop_shadows_outer(self):
        outer = _render_text(
            "<ul>{% for x in outer %}<li>{% for y in inner %}"
            "<span>{{ loop.index }}/{{ loop.length }}</span>{% endfor %}</li>{% endfor %}</ul>",
            {"outer": [1, 2], "inner": ["a", "b", "c"]},
        )
        assert outer == ["1/32/33/3", "1/32/33/3"]

    def test_user_loop_variable_named_loop_shadows_metadata(self):
        items = _render_text(
            "<ul>{% for loop in items %}<li>{{ loop }}</li>{% endfor %}</ul>",
            {"items": ["a", "b"]},
        )
        assert items == ["a", "b"]

    def test_context_variable_named_loop_unaffected_outside_for(self):
        items = _render_text(
            "<div><span>{{ loop }}</span>{% for x in items %}<p>{{ loop.index }}</p>{% endfor %}</div>",
            {"loop": "ctx-value", "items": ["a"]},
        )
        assert items == ["ctx-value", "1"]


class TestReactiveListLoopMetadata:
    def _page(self, captured: dict[str, Any]):
        @define_component
        def LoopMetadataPage(_: ComponentContext[None]):
            items = use_reactive_list(lambda: ["a", "b"])
            captured["items"] = items
            return render_template(
                "<ul>{% for item in items %}"
                "<li>{{ loop.index }},{{ loop.first }},{{ loop.last }},{{ loop.length }}:{{ item }}</li>"
                "{% endfor %}</ul>",
                {"items": items},
            )

        return LoopMetadataPage

    def test_initial_positions(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,False,2:a", "2,False,True,2:b"]

    def test_metadata_updates_after_append(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            captured["items"].append("c")
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,False,3:a", "2,False,False,3:b", "3,False,True,3:c"]

    def test_metadata_updates_after_remove(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            captured["items"].pop(0)
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,True,1:b"]

    def test_metadata_updates_after_insert(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            captured["items"].insert(0, "z")
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,False,3:z", "2,False,False,3:a", "3,False,True,3:b"]


class TestPlainSignalListLoopMetadata:
    def test_plain_signal_list_replacement(self):
        captured: dict[str, Any] = {}

        @define_component
        def PlainSignalPage(_: ComponentContext[None]):
            from webcompy.signal import use_state

            items = use_state(lambda: ["a"])
            captured["items"] = items
            return render_template(
                "<ul>{% for item in items %}<li>{{ loop.index }}:{{ item }}</li>{% endfor %}</ul>",
                {"items": items},
            )

        with TestRenderer.render(PlainSignalPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["1:a"]
            captured["items"].value = ["a", "b", "c"]
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1:a", "2:b", "3:c"]
