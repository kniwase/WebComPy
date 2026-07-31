from __future__ import annotations

import pytest

from tests.conftest import FakeDOMNode
from webcompy.components import define_component
from webcompy.di._scope import _active_di_scope
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.ports._keys import MARKDOWN_PORT_KEY
from webcompy.signal import ReactiveDict, ReactiveList, Signal
from webcompy.template import render_template
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy.template._markdown_for import MarkdownForElement
from webcompy_testing import TestRenderer


class TestMultiLineForLoopInitialRender:
    def test_renders_all_items_on_initial_render(self):
        items = ReactiveList(["a", "b", "c"])

        @define_component
        def LoopPage(context):
            return render_template(
                """
                <ul>
                    {% for item in items %}
                    <li>{{ item }}</li>
                    {% endfor %}
                </ul>
                """,
                {"items": items},
            )

        with TestRenderer.render(LoopPage) as result:
            lis = result.query_selector_all("li")
            assert [li.textContent for li in lis] == ["a", "b", "c"]


class TestMultiLineForLoopRefresh:
    def test_items_kept_in_order_after_pop(self):
        items = ReactiveList(["a", "b", "c"])

        @define_component
        def LoopPage(context):
            return render_template(
                """
                <ul>
                    {% for item in items %}
                    <li>{{ item }}</li>
                    {% endfor %}
                </ul>
                """,
                {"items": items},
            )

        with TestRenderer.render(LoopPage) as result:
            items.pop(0)
            lis = result.query_selector_all("li")
            assert [li.textContent for li in lis] == ["b", "c"]


class TestMultiElementIfBranchToggle:
    def test_branch_toggles_without_losing_nodes(self):
        flag = Signal(True)

        @define_component
        def BranchPage(context):
            return render_template(
                """
                <div>
                    {% if flag %}
                    <p>first</p>
                    <p>second</p>
                    {% else %}
                    <span>other</span>
                    {% endif %}
                </div>
                """,
                {"flag": flag},
            )

        with TestRenderer.render(BranchPage) as result:
            assert [p.textContent for p in result.query_selector_all("p")] == ["first", "second"]
            flag.value = False
            assert [s.textContent for s in result.query_selector_all("span")] == ["other"]
            assert result.query_selector_all("p") == []
            flag.value = True
            assert [p.textContent for p in result.query_selector_all("p")] == ["first", "second"]


class TestKeyedRepeatFragmentChildren:
    def test_dict_repeat_positions_fragments_without_overlap(self):
        d = ReactiveDict({"a": 1, "b": 2, "c": 3})

        @define_component
        def DictPage(context):
            return render_template(
                """
                <ul>
                    {% for k, v in d %}
                    <li>{{ k }}={{ v }}</li>
                    {% endfor %}
                </ul>
                """,
                {"d": d},
            )

        with TestRenderer.render(DictPage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == ["a=1", "b=2", "c=3"]
            del d["a"]
            assert [li.textContent for li in result.query_selector_all("li")] == ["b=2", "c=3"]


class _FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


class TestMarkdownForFragmentChildren:
    @pytest.mark.asyncio
    async def test_render_assigns_cumulative_node_index(self, fake_browser_full):
        _active_di_scope.get().provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": ["a"]})
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        mfe._parent = parent
        mfe._node_idx = 0
        frag = FragmentElement([Element("p"), Element("p")])
        tail = Element("span")
        frag._parent = parent
        tail._parent = parent
        mfe._children = [frag, tail]
        await mfe._render()
        assert frag._node_idx == 0
        assert tail._node_idx == 2
