from __future__ import annotations

from typing import Any

import pytest

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
        @define_component()
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

        @define_component()
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
        @define_component()
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

        @define_component()
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

        @define_component()
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

        @define_component()
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

        @define_component()
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

        @define_component()
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

    def test_dict_value_signal_field_dotted_access(self):
        captured: dict[str, Any] = {}

        @define_component()
        def DictValueSignalFieldPage(_: ComponentContext[None]):
            from webcompy.signal import Signal, use_reactive_dict

            d = use_reactive_dict(lambda: {"a": {"name": Signal("Alice")}, "b": {"name": Signal("Bob")}})
            captured["d"] = d
            captured["inner"] = d["a"]["name"]
            return render_template(
                "<ul>{% for v in d %}<li>{{ v.name }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(DictValueSignalFieldPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["Alice", "Bob"]
            captured["inner"].value = "Alicia"
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["Alicia", "Bob"]

    def test_one_var_signal_value_plain_interpolation(self):
        captured: dict[str, Any] = {}

        @define_component()
        def DictValueSignalPage(_: ComponentContext[None]):
            from webcompy.signal import Signal, use_reactive_dict

            d = use_reactive_dict(lambda: {"a": Signal("Alice"), "b": Signal("Bob")})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(DictValueSignalPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["Alice", "Bob"]
            captured["d"]["a"].value = "Alicia"
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["Alicia", "Bob"]

    def test_one_var_none_value_omitted(self):
        captured: dict[str, Any] = {}

        @define_component()
        def DictValueNonePage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": None, "b": "two"})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(DictValueNonePage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["", "two"]

    def test_one_var_none_value_replaced_reactively(self):
        captured: dict[str, Any] = {}

        @define_component()
        def DictValueNoneReplacedPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": None, "b": "two"})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(DictValueNoneReplacedPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["", "two"]
            captured["d"]["a"] = "one"
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["one", "two"]

    def test_one_var_dict_value_dotted_condition(self):
        captured: dict[str, Any] = {}

        @define_component()
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

    def test_one_var_element_value_rendered_as_child(self):
        @define_component()
        def DictValueElementPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(
                lambda: {
                    "a": Element("span", children=[TextElement("Alice")]),
                    "b": Element("span", children=[TextElement("Bob")]),
                }
            )
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(DictValueElementPage) as result:
            spans = result.query_selector_all("span")
            assert [s.textContent for s in spans] == ["Alice", "Bob"]
            lis = result.query_selector_all("li")
            assert [li.textContent for li in lis] == ["Alice", "Bob"]

    def test_two_var_element_value_rendered_as_child(self):
        @define_component()
        def TwoVarDictValueElementPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(
                lambda: {
                    "a": Element("span", children=[TextElement("Alice")]),
                    "b": Element("b", children=[TextElement("Bob")]),
                }
            )
            return render_template(
                "<ul>{% for k, v in d %}<li>{{ k }}:{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(TwoVarDictValueElementPage) as result:
            spans = result.query_selector_all("span")
            bolds = result.query_selector_all("b")
            assert [s.textContent for s in spans] == ["Alice"]
            assert [b.textContent for b in bolds] == ["Bob"]
            lis = result.query_selector_all("li")
            assert [li.textContent for li in lis] == ["a:Alice", "b:Bob"]

    def test_one_var_signal_wrapping_element_value_rendered_as_child(self):
        from webcompy.signal import Signal

        @define_component()
        def DictValueSignalElementPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(
                lambda: {
                    "a": Signal(Element("span", children=[TextElement("Alice")])),
                    "b": Signal(Element("span", children=[TextElement("Bob")])),
                }
            )
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(DictValueSignalElementPage) as result:
            spans = result.query_selector_all("span")
            assert [s.textContent for s in spans] == ["Alice", "Bob"]

    def test_scalar_to_element_replacement_renders_child(self):
        captured: dict[str, Any] = {}

        @define_component()
        def ScalarToElementPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(ScalarToElementPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["1"]
            captured["d"]["a"] = Element("span", children=[TextElement("ELEM")])
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["ELEM"]

    def test_element_to_scalar_replacement_renders_scalar(self):
        captured: dict[str, Any] = {}

        @define_component()
        def ElementToScalarPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": Element("span", children=[TextElement("ELEM")])})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(ElementToScalarPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["ELEM"]
            captured["d"]["a"] = 42
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["42"]

    def test_element_to_element_replacement_renders_new_element(self):
        captured: dict[str, Any] = {}

        @define_component()
        def ElementToElementPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": Element("span", children=[TextElement("A")])})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(ElementToElementPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["A"]
            captured["d"]["a"] = Element("span", children=[TextElement("B")])
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["B"]

    def test_signal_wrapped_element_inner_change_renders_new_element(self):
        captured: dict[str, Any] = {}

        @define_component()
        def SignalElementChangePage(_: ComponentContext[None]):
            from webcompy.signal import Signal, use_reactive_dict

            inner = Signal(Element("span", children=[TextElement("A")]))
            captured["inner"] = inner
            d = use_reactive_dict(lambda: {"a": inner})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with TestRenderer.render(SignalElementChangePage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["A"]
            captured["inner"].value = Element("span", children=[TextElement("B")])
            texts = [li.textContent for li in result.query_selector_all("li")]
        assert texts == ["B"]


class TestReactiveDictComputedLifecycle:
    def _count_consumers(self, signal: Any) -> int:
        count = 0
        edge = signal.consumers
        while edge is not None:
            count += 1
            edge = edge.next_consumer
        return count

    def _page(self, captured: dict[str, Any]):
        @define_component()
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
            assert before - after == 9
            d["c"] = 3
            assert self._count_consumers(d) - after == 9


class TestIntermediateSignalCleanup:
    def _count_consumers(self, signal: Any) -> int:
        count = 0
        edge = signal.consumers
        while edge is not None:
            count += 1
            edge = edge.next_consumer
        return count

    def test_attr_binding_teardown_cleans_intermediate_signal(self):
        from webcompy.signal import Signal

        captured: dict[str, Any] = {}

        @define_component()
        def AttrPage(_: ComponentContext[None]):
            profile = Signal({"name": "Alice"})
            captured["profile"] = profile
            return render_template(
                '<p data-x="{{ user.profile.name }}">x</p>',
                {"user": {"profile": profile}},
            )

        with TestRenderer.render(AttrPage) as result:
            assert self._count_consumers(captured["profile"]) == 1
            result._instance._remove_element()
            assert self._count_consumers(captured["profile"]) == 0

    def test_if_condition_teardown_cleans_intermediate_signal(self):
        from webcompy.signal import Signal

        captured: dict[str, Any] = {}

        @define_component()
        def IfCondPage(_: ComponentContext[None]):
            user = Signal({"visible": True})
            captured["user"] = user
            return render_template(
                "<p>{% if user.visible %}yes{% endif %}</p>",
                {"user": user},
            )

        with TestRenderer.render(IfCondPage) as result:
            assert self._count_consumers(captured["user"]) == 1
            result._instance._remove_element()
            assert self._count_consumers(captured["user"]) == 0

    def test_text_binding_teardown_cleans_intermediate_signal(self):
        from webcompy.signal import Signal

        captured: dict[str, Any] = {}

        @define_component()
        def TextPage(_: ComponentContext[None]):
            profile = Signal({"name": "Alice"})
            captured["profile"] = profile
            return render_template(
                "<p>{{ user.profile.name }}</p>",
                {"user": {"profile": profile}},
            )

        with TestRenderer.render(TextPage) as result:
            assert self._count_consumers(captured["profile"]) == 1
            result._instance._remove_element()
            assert self._count_consumers(captured["profile"]) == 0


class TestReactiveDictEmptyBody:
    def test_empty_body_dict_loop_renders_without_error(self):
        captured: dict[str, Any] = {}

        @define_component()
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

        @define_component()
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

        @define_component()
        def TwoVarEmptyPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1, "b": 2})
            captured["d"] = d
            return render_template("<ul>{% for k, v in d %}{% endfor %}</ul>", {"d": d})

        with TestRenderer.render(TwoVarEmptyPage) as result:
            assert result.query_selector_all("li") == []

    def test_failed_binding_cleans_up_row_computeds(self):
        captured: dict[str, Any] = {}

        @define_component()
        def DictValueFailPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1})
            captured["d"] = d
            return render_template(
                "<ul>{% for v in d %}<li>{{ loop.index + 1 }}{{ missing }}</li>{% endfor %}</ul>",
                {"d": d},
            )

        with pytest.raises(KeyError), TestRenderer.render(DictValueFailPage):
            pass

        d = captured["d"]
        assert d.consumers is None


class TestDictValueRowCallbackRegistration:
    def test_on_set_parent_registers_raw_async_refresh(self):
        captured: dict[str, Any] = {}

        @define_component()
        def DictRowPage(_: ComponentContext[None]):
            from webcompy.signal import use_reactive_dict

            d = use_reactive_dict(lambda: {"a": 1, "b": 2})
            captured["d"] = d
            return render_template("<ul>{% for v in d %}<li>{{ v }}</li>{% endfor %}</ul>", {"d": d})

        with TestRenderer.render(DictRowPage) as result:
            rows = result._instance._children[0]._children[0]._children
            assert all(len(row._callback_nodes) == 1 for row in rows)
            assert all(row._callback_nodes[0]._is_async for row in rows)


class TestIncomingSignalOwnership:
    def _count_consumers(self, signal: Any) -> int:
        count = 0
        edge = signal.consumers
        while edge is not None:
            count += 1
            edge = edge.next_consumer
        return count

    def test_switch_condition_user_computed_not_claimed(self):
        from webcompy.signal import Computed, Signal

        captured: dict[str, Any] = {}

        @define_component()
        def SwitchPage(_: ComponentContext[None]):
            src = Signal(1)
            shared = Computed(lambda: src.value * 2)
            captured["src"] = src
            captured["shared"] = shared
            return render_template(
                "<div>{% if c %}A{% else %}B{% endif %}</div>",
                {"c": shared},
            )

        with TestRenderer.render(SwitchPage) as result:
            assert self._count_consumers(captured["src"]) == 1
            result._instance._remove_element()
            assert self._count_consumers(captured["src"]) == 1
            captured["src"].value = 10
            assert captured["shared"].value == 20

    def test_user_computed_plain_path_condition_not_claimed(self):
        from webcompy.signal import Computed, Signal

        captured: dict[str, Any] = {}

        @define_component()
        def IfPlainPage(_: ComponentContext[None]):
            src = Signal(1)
            is_even = Computed(lambda: src.value % 2 == 0)
            captured["src"] = src
            captured["is_even"] = is_even
            return render_template(
                "<p>{% if is_even %}yes{% endif %}</p>",
                {"src": src, "is_even": is_even},
            )

        with TestRenderer.render(IfPlainPage) as result:
            assert self._count_consumers(captured["src"]) == 1
            result._instance._remove_element()
            assert self._count_consumers(captured["src"]) == 1
            captured["src"].value = 2
            assert captured["is_even"].value is True

    def test_template_expression_condition_computed_still_destroyed(self):
        from webcompy.signal import Signal

        captured: dict[str, Any] = {}

        @define_component()
        def IfExprPage(_: ComponentContext[None]):
            src = Signal(2)
            captured["src"] = src
            return render_template("<p>{% if src % 2 == 0 %}even{% endif %}</p>", {"src": src})

        with TestRenderer.render(IfExprPage) as result:
            assert self._count_consumers(captured["src"]) == 1
            result._instance._remove_element()
            assert self._count_consumers(captured["src"]) == 0

    def test_component_root_attr_user_signal_not_collected_or_destroyed(self):
        from webcompy.hydration._collect import _collect_component_signals
        from webcompy.signal import Signal

        captured: dict[str, Any] = {}

        @define_component()
        def ManualRootPage(_: ComponentContext[None]):
            cls = Signal("user-cls")
            captured["cls"] = cls
            return Element("div", attrs={"class": cls}, children=[TextElement("x")])

        with TestRenderer.render(ManualRootPage) as result:
            inner = result._instance._children[0]
            assert "class" in inner._attrs
            members = _collect_component_signals(result._instance)
            assert not any(key.startswith("__attr_") for key in members)
            result._instance._remove_element()
            captured["cls"].value = "still-alive"
            assert captured["cls"].value == "still-alive"

    def test_template_root_attr_computed_still_destroyed_on_teardown(self):
        from webcompy.signal import Signal

        captured: dict[str, Any] = {}

        @define_component()
        def AttrPage(_: ComponentContext[None]):
            src = Signal("red")
            captured["src"] = src
            return render_template('<p data-x="{{ s }}">x</p>', {"s": src})

        with TestRenderer.render(AttrPage) as result:
            assert self._count_consumers(captured["src"]) == 1
            result._instance._remove_element()
            assert self._count_consumers(captured["src"]) == 0
