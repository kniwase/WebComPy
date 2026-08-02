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


class TestReactiveDictLoopMetadata:
    def _page(self, captured: dict[str, Any]):
        @define_component
        def ReactiveDictPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"x": 1, "y": 2, "z": 9})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}"
                "<li>{{ loop.index }},{{ loop.first }},{{ loop.last }},{{ loop.length }}:{{ v }}</li>"
                "{% endfor %}</ul>",
                {"d": d},
            )

        return ReactiveDictPage

    def test_initial_positions(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,False,3:1", "2,False,False,3:2", "3,False,True,3:9"]

    def test_metadata_updates_after_remove(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            captured["d"].pop("x")
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,False,2:2", "2,False,True,2:9"]

    def test_metadata_updates_after_add(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            captured["d"].pop("x")
            captured["d"]["w"] = 0
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,False,3:2", "2,False,False,3:9", "3,False,True,3:0"]

    def test_metadata_updates_after_reorder(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            d = captured["d"]
            d.pop("z")
            d["z"] = 9
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,False,3:1", "2,False,False,3:2", "3,False,True,3:9"]

    def test_metadata_updates_after_repeated_mutations(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            d = captured["d"]
            d.pop("z")
            d["z"] = 9
            d.pop("y")
            d["y"] = 2
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,False,3:1", "2,False,False,3:9", "3,False,True,3:2"]

    def test_metadata_after_clear_and_refill(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            d = captured["d"]
            d.clear()
            assert [li.textContent for li in result.query_selector_all("li")] == []
            d["a"] = 5
            d["b"] = 6
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1,True,False,2:5", "2,False,True,2:6"]

    def test_two_var_dict_loop_with_metadata(self):
        captured: dict[str, Any] = {}

        @define_component
        def TwoVarPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1, "b": 2})
            captured["d"] = d
            return render_template(
                "<ul>{% for k, v in d %}<li>{{ loop.index }}:{{ k }}={{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(TwoVarPage) as result:
            texts = [li.textContent for li in result.query_selector_all("li")]
            assert texts == ["1:a=1", "2:b=2"]
            captured["d"]["c"] = 3
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["1:a=1", "2:b=2", "3:c=3"]


class TestReactiveDictValueReactivity:
    def test_one_var_value_replacement_updates_existing_key(self):
        captured: dict[str, Any] = {}

        @define_component
        def DictValuePage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"x": 1, "y": 2})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(DictValuePage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["1", "2"]
            captured["d"]["x"] = 99
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["99", "2"]

    def test_two_var_value_replacement_updates_existing_key(self):
        captured: dict[str, Any] = {}

        @define_component
        def TwoVarValuePage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1, "b": 2})
            captured["d"] = d
            return render_template(
                "<ul>{% for k, v in d %}<li>{{ k }}={{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(TwoVarValuePage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["a=1", "b=2"]
            captured["d"]["b"] = 7
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["a=1", "b=7"]

    def test_one_var_dict_value_dotted_access(self):
        captured: dict[str, Any] = {}

        @define_component
        def DictValueDottedPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(
                lambda: {"a": {"name": "Alice", "visible": True}, "b": {"name": "Bob", "visible": False}}
            )
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ v.name }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(DictValueDottedPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["Alice", "Bob"]
            captured["d"]["b"] = {"name": "Bobby", "visible": False}
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["Alice", "Bobby"]

    def test_two_var_dict_value_dotted_access(self):
        captured: dict[str, Any] = {}

        @define_component
        def TwoVarDictValueDottedPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": {"name": "Alice"}, "b": {"name": "Bob"}})
            captured["d"] = d
            return render_template(
                "<ul>{% for k, v in d %}<li>{{ k }}={{ v.name }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(TwoVarDictValueDottedPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["a=Alice", "b=Bob"]
            captured["d"]["c"] = {"name": "Carol"}
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["a=Alice", "b=Bob", "c=Carol"]

    def test_one_var_dict_value_dotted_condition(self):
        captured: dict[str, Any] = {}

        @define_component
        def DictValueConditionPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(
                lambda: {"a": {"name": "Alice", "visible": True}, "b": {"name": "Bob", "visible": False}}
            )
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}{% if v.visible %}<li>{{ v.name }}</li>{% endif %}{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(DictValueConditionPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["Alice"]
            captured["d"]["b"] = {"name": "Bob", "visible": True}
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["Alice", "Bob"]


class TestReactiveDictComputedLifecycle:
    def _count_consumers(self, signal: Any) -> int:
        count = 0
        edge = signal.consumers
        while edge is not None:
            count += 1
            edge = edge.next_consumer
        return count

    def _page(self, captured: dict[str, Any]):
        @define_component
        def DictLifecyclePage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1, "b": 2})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>item</li>{% endfor %}</ul>",
                {"d": d},
            )

        return DictLifecyclePage

    def test_key_removal_destroys_item_computeds(self):
        captured: dict[str, Any] = {}
        with TestRenderer.render(self._page(captured)) as result:
            assert len(result.query_selector_all("li")) == 2
            d = captured["d"]
            before = self._count_consumers(d)
            d.pop("a")
            after = self._count_consumers(d)
            assert before - after == 8
            d["c"] = 3
            assert self._count_consumers(d) - after == 8


class TestReactiveDictEmptyBody:
    def test_empty_body_dict_loop_renders_without_error(self):
        captured: dict[str, Any] = {}

        @define_component
        def EmptyBodyPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1, "b": 2})
            captured["d"] = d
            return render_template("<ul>{% for v in d %}{% endfor %}</ul>", {"d": d})

        with TestRenderer.render(EmptyBodyPage) as result:
            assert result.query_selector_all("li") == []
            captured["d"]["c"] = 3
            assert result.query_selector_all("li") == []

    def test_conditionally_empty_body_dict_loop_renders(self):
        captured: dict[str, Any] = {}

        @define_component
        def CondEmptyPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1, "b": 2})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}{% if show %}<li>{{ v }}</li>{% endif %}{% endfor %}</ul>",
                {"d": d, "show": False},
            )

        with TestRenderer.render(CondEmptyPage) as result:
            assert result.query_selector_all("li") == []

    def test_empty_body_two_var_dict_loop_renders(self):
        captured: dict[str, Any] = {}

        @define_component
        def TwoVarEmptyPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1, "b": 2})
            captured["d"] = d
            return render_template("<ul>{% for k, v in d %}{% endfor %}</ul>", {"d": d})

        with TestRenderer.render(TwoVarEmptyPage) as result:
            assert result.query_selector_all("li") == []
