from __future__ import annotations

import pytest

from tests.conftest import FakeDOMNode
from webcompy.components import define_component
from webcompy.di._scope import _active_di_scope
from webcompy.elements.types._element import Element
from webcompy.elements.types._text import RawHTMLElement, TextElement
from webcompy.ports._keys import MARKDOWN_PORT_KEY
from webcompy.signal import ReactiveDict, ReactiveList, Signal
from webcompy.template import render_template
from webcompy.template._markdown_default import DefaultMarkdownParser
from webcompy.template._markdown_for import MarkdownForElement
from webcompy_testing import TestRenderer


class TestUnkeyedForRefreshPreservesFollowingSibling:
    def test_following_sibling_preserved_after_append(self):
        items = ReactiveList(["x", "y"])

        @define_component("sibling-page")
        def SiblingPage(context):
            return render_template(
                "<div>{% for item in items %}<b>{{ item }}</b>{% endfor %}<span>tail</span></div>",
                {"items": items},
            )

        with TestRenderer.render(SiblingPage) as result:
            assert [b.textContent for b in result.query_selector_all("b")] == ["x", "y"]
            items.append("z")
            assert [b.textContent for b in result.query_selector_all("b")] == ["x", "y", "z"]
            assert result.query_selector("span").textContent == "tail"
            div = result.query_selector("div")
            assert [c.nodeName for c in div.childNodes] == ["B", "B", "B", "SPAN"]


class TestKeyedDictRepeatPreservesFollowingSibling:
    def test_following_sibling_preserved_after_dict_insert(self):
        d = ReactiveDict({"a": 1, "b": 2})

        @define_component("dict-page")
        def DictPage(context):
            return render_template(
                "<div>{% for k, v in d %}<b>{{ k }}={{ v }}</b>{% endfor %}<span>tail</span></div>",
                {"d": d},
            )

        with TestRenderer.render(DictPage) as result:
            assert [b.textContent for b in result.query_selector_all("b")] == ["a=1", "b=2"]
            d["c"] = 3
            assert [b.textContent for b in result.query_selector_all("b")] == ["a=1", "b=2", "c=3"]
            assert result.query_selector("span").textContent == "tail"
            div = result.query_selector("div")
            assert [c.nodeName for c in div.childNodes] == ["B", "B", "B", "SPAN"]


class TestIfBranchTogglePreservesFollowingSibling:
    def test_following_sibling_preserved_after_branch_toggle(self):
        flag = Signal(True)

        @define_component("branch-page")
        def BranchPage(context):
            return render_template(
                "<div>{% if flag %}<span>on</span>{% else %}<em>off</em>{% endif %}<p>tail</p></div>",
                {"flag": flag},
            )

        with TestRenderer.render(BranchPage) as result:
            assert result.query_selector("span").textContent == "on"
            assert result.query_selector("p").textContent == "tail"
            flag.value = False
            assert result.query_selector("em").textContent == "off"
            assert result.query_selector("span") is None
            assert result.query_selector("p").textContent == "tail"
            flag.value = True
            assert result.query_selector("span").textContent == "on"
            assert result.query_selector("p").textContent == "tail"


class _FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


class TestMarkdownForRefreshPreservesFollowingSibling:
    @pytest.mark.asyncio
    async def test_following_sibling_preserved_after_append_from_empty(self, fake_browser_full):
        _active_di_scope.get().provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        items = ReactiveList([])
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": items})
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent._append_child(mfe)
        tail = Element("span", {}, {}, None, [TextElement("tail")])
        parent._append_child(tail)
        await mfe._render()
        await tail._render()

        div = parent._node_cache
        assert [c.nodeName for c in div.childNodes] == ["SPAN"]

        items.append("c")

        assert [c.nodeName for c in div.childNodes] == ["UL", "SPAN"]
        ul_node = div.childNodes[0]
        lis = [c for c in ul_node.childNodes if c.nodeName == "LI"]
        assert len(lis) == 1
        assert lis[0].textContent == "c"
        assert div.childNodes[1] is tail._node_cache


class TestPrerenderMismatchStillRecreated:
    def _setup_parent(self):
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        return parent

    def test_element_prerendered_tag_mismatch_removed(self, fake_browser_full):
        parent = self._setup_parent()
        existing = FakeDOMNode("p")
        existing.__webcompy_prerendered_node__ = True
        parent._node_cache.appendChild(existing)
        el = Element("span", {}, {}, None, None)
        el._parent = parent
        el._node_idx = 0
        node = el._init_node()
        assert node is not existing
        assert node.nodeName == "SPAN"
        assert existing.parentNode is None

    def test_text_element_prerendered_type_mismatch_removed(self, fake_browser_full):
        parent = self._setup_parent()
        existing = FakeDOMNode("p")
        existing.__webcompy_prerendered_node__ = True
        parent._node_cache.appendChild(existing)
        el = TextElement("hello")
        el._parent = parent
        el._node_idx = 0
        node = el._init_node()
        assert node is not existing
        assert node.nodeName == "#text"
        assert node.textContent == "hello"
        assert existing.parentNode is None

    def test_raw_html_element_prerendered_tag_mismatch_removed(self, fake_browser_full):
        parent = self._setup_parent()
        existing = FakeDOMNode("div")
        existing.__webcompy_prerendered_node__ = True
        parent._node_cache.appendChild(existing)
        el = RawHTMLElement("<b>hi</b>")
        el._parent = parent
        el._node_idx = 0
        node = el._init_node()
        assert node is not existing
        assert node.nodeName == "SPAN"
        assert existing.parentNode is None
