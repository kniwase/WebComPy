from __future__ import annotations

import pytest

from tests.conftest import FakeDOMNode
from webcompy.components import define_component
from webcompy.di._scope import _active_di_scope
from webcompy.elements import ClientOnly, html
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._suspense import SuspenseElement
from webcompy.elements.types._text import TextElement
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


class TestDynamicChildMaterialization:
    def test_client_only_preserves_following_sibling(self):
        @define_component
        def ClientOnlyPage(context):
            return html.DIV(
                {},
                ClientOnly(
                    children=lambda: TextElement("client"),
                    fallback=lambda: TextElement("fallback"),
                ),
                html.P({}, "tail"),
            )

        with TestRenderer.render(ClientOnlyPage) as result:
            children = result._root_node.childNodes
            assert [child.nodeName for child in children] == ["#text", "P"]
            assert children[0].textContent == "fallback"
            assert children[1].textContent == "tail"

    def test_suspense_preserves_following_sibling(self):
        @define_component
        def SuspensePage(context):
            return html.DIV(
                {},
                SuspenseElement(
                    fallback=lambda: html.I({}, "fallback"),
                    children=lambda: html.SPAN({}, "suspense"),
                ),
                html.P({}, "tail"),
            )

        with TestRenderer.render(SuspensePage) as result:
            children = result._root_node.childNodes
            assert [child.nodeName for child in children] == ["SPAN", "P"]
            assert children[0].textContent == "suspense"
            assert children[1].textContent == "tail"

    def test_fragment_materialization_preserves_following_siblings(self):
        @define_component
        def FragmentPage(context):
            return html.DIV(
                {},
                FragmentElement(
                    [
                        ClientOnly(
                            children=lambda: TextElement("client"),
                            fallback=lambda: TextElement("fallback"),
                        ),
                        html.SPAN({}, "inside"),
                    ]
                ),
                html.P({}, "tail"),
            )

        with TestRenderer.render(FragmentPage) as result:
            children = result._root_node.childNodes
            assert [child.nodeName for child in children] == ["#text", "SPAN", "P"]
            assert [child.textContent for child in children] == ["fallback", "inside", "tail"]


class TestDynamicChildHydration:
    def test_client_only_hydration_reindexes_following_sibling(self, fake_browser_full, monkeypatch):
        monkeypatch.setattr("webcompy.elements.types._client_only.ENVIRONMENT", "pyscript")

        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        prerendered_fallback = FakeDOMNode("#text", text_content="loading")
        prerendered_fallback.__webcompy_prerendered_node__ = True
        prerendered_tail = FakeDOMNode("p", text_content="tail")
        prerendered_tail.__webcompy_prerendered_node__ = True
        parent._node_cache.appendChild(prerendered_fallback)
        parent._node_cache.appendChild(prerendered_tail)

        client_only = ClientOnly(
            children=lambda: TextElement("client"),
            fallback=lambda: TextElement("loading"),
        )
        tail = Element("p", {}, {}, None, [TextElement("tail")])
        parent._append_child(client_only)
        parent._append_child(tail)

        client_only._hydrate_node()
        tail._hydrate_node()

        assert tail._node_idx == 1
        assert tail._node_cache is prerendered_tail
