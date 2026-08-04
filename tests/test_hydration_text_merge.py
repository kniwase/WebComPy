from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import FakeDOMNode
from webcompy.di import inject
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._text import NewLine, RawHTMLElement, TextElement
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
from webcompy.signal import ReactiveDict


class FakeRootElement(Element):
    _get_belonging_component = lambda self: ""
    _get_belonging_components = lambda self: ()


def _hydrate_container(children: list[Any], dom_children: list[FakeDOMNode]):
    parent = FakeRootElement("div", {}, {}, None, None)
    parent._node_cache = FakeDOMNode("div")
    parent._mounted = True
    parent_node = parent._get_node()
    prerendered = FakeDOMNode("div")
    prerendered.__webcompy_prerendered_node__ = True
    for node in dom_children:
        node.__webcompy_prerendered_node__ = True
        prerendered.appendChild(node)
    parent_node.appendChild(prerendered)
    el = Element("div", {}, {}, None, children)
    el._parent = parent
    el._node_idx = 0
    el._hydrate_node()
    return el, prerendered


class TestFakeDOMNodeSplitText:
    def test_split_text_splits_content(self):
        parent = FakeDOMNode("div")
        node = FakeDOMNode("#text", text_content="ab")
        parent.appendChild(node)
        new_node = node.splitText(1)
        assert node.textContent == "a"
        assert new_node.textContent == "b"
        assert new_node is not node

    def test_split_text_inserts_new_node_after_receiver(self):
        parent = FakeDOMNode("div")
        first = FakeDOMNode("#text", text_content="aa")
        middle = FakeDOMNode("#text", text_content="bb")
        last = FakeDOMNode("#text", text_content="cc")
        parent.appendChild(first)
        parent.appendChild(middle)
        parent.appendChild(last)
        new_middle = middle.splitText(1)
        assert [n.textContent for n in parent.childNodes] == ["aa", "b", "b", "cc"]
        assert new_middle.parentNode is parent
        assert new_middle is parent.childNodes[2]

    def test_split_text_at_end_appends(self):
        parent = FakeDOMNode("div")
        node = FakeDOMNode("#text", text_content="ab")
        parent.appendChild(node)
        new_node = node.splitText(2)
        assert node.textContent == "ab"
        assert new_node.textContent == ""
        assert parent.childNodes.length == 2

    def test_split_text_zero_offset_keeps_all_in_new_node(self):
        parent = FakeDOMNode("div")
        node = FakeDOMNode("#text", text_content="ab")
        parent.appendChild(node)
        new_node = node.splitText(0)
        assert node.textContent == ""
        assert new_node.textContent == "ab"

    def test_split_text_out_of_range_raises(self):
        node = FakeDOMNode("#text", text_content="ab")
        with pytest.raises(IndexError):
            node.splitText(-1)
        with pytest.raises(IndexError):
            node.splitText(3)

    def test_split_text_on_element_node_raises(self):
        node = FakeDOMNode("div")
        with pytest.raises(TypeError):
            node.splitText(0)


class TestHydrationTextMergeSpike:
    def test_merged_text_nodes_are_split_for_1to1_adoption(self, fake_browser_full):
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent_node = parent._get_node()

        prerendered = FakeDOMNode("div")
        prerendered.__webcompy_prerendered_node__ = True
        merged = FakeDOMNode("#text", text_content="ab")
        merged.__webcompy_prerendered_node__ = True
        prerendered.appendChild(merged)
        parent_node.appendChild(prerendered)

        el = Element("div", {}, {}, None, ["a", "b"])
        el._parent = parent
        el._node_idx = 0
        el._hydrate_node()

        assert el._node_cache is prerendered
        assert prerendered.childNodes.length == 2
        assert prerendered.childNodes[0].textContent == "a"
        assert prerendered.childNodes[1].textContent == "b"


class TestHydrationTextRunNormalization:
    def test_fragment_body_with_merged_adjacent_text(self, fake_browser_full):
        el, prerendered = _hydrate_container(
            [Element("span", {}, {}, None, None), "a", "b", Element("span", {}, {}, None, None)],
            [
                FakeDOMNode("span"),
                FakeDOMNode("#text", text_content="ab"),
                FakeDOMNode("span"),
            ],
        )
        assert el._node_cache is prerendered
        assert prerendered.childNodes.length == 4
        assert [n.textContent for n in prerendered.childNodes] == ["", "a", "b", ""]
        assert el._children[1]._node_cache is prerendered.childNodes[1]
        assert el._children[2]._node_cache is prerendered.childNodes[2]
        assert el._children[3]._node_cache is prerendered.childNodes[3]

    def test_newline_terminates_text_run(self, fake_browser_full):
        _, prerendered = _hydrate_container(
            ["a", NewLine(), "b", "c"],
            [
                FakeDOMNode("#text", text_content="a"),
                FakeDOMNode("br"),
                FakeDOMNode("#text", text_content="bc"),
            ],
        )
        assert prerendered.childNodes.length == 4
        assert [n.textContent for n in prerendered.childNodes] == ["a", "", "b", "c"]

    def test_rawhtml_terminates_text_run(self, fake_browser_full):
        _, prerendered = _hydrate_container(
            ["a", RawHTMLElement("<b>x</b>"), "b", "c"],
            [
                FakeDOMNode("#text", text_content="a"),
                FakeDOMNode("span"),
                FakeDOMNode("#text", text_content="bc"),
            ],
        )
        assert prerendered.childNodes.length == 4
        assert [n.textContent for n in prerendered.childNodes] == ["a", "", "b", "c"]

    def test_empty_text_element_in_run(self, fake_browser_full):
        _, prerendered = _hydrate_container(
            ["a", "", "b"],
            [FakeDOMNode("#text", text_content="ab")],
        )
        assert prerendered.childNodes.length == 3
        assert [n.textContent for n in prerendered.childNodes] == ["a", "", "b"]

    def test_content_mismatch_falls_back_without_splitting(self, fake_browser_full, caplog):
        _, prerendered = _hydrate_container(
            ["a", "b"],
            [FakeDOMNode("#text", text_content="xy")],
        )
        assert prerendered.childNodes.length == 1
        assert prerendered.childNodes[0].textContent == "a"
        assert "Hydration text-run mismatch" in caplog.text

    def test_already_split_dom_is_untouched(self, fake_browser_full):
        first = FakeDOMNode("#text", text_content="a")
        second = FakeDOMNode("#text", text_content="b")
        _, prerendered = _hydrate_container(["a", "b"], [first, second])
        assert prerendered.childNodes.length == 2
        assert first.textContent_write_count == 0
        assert second.textContent_write_count == 0


class TestKeyedReactiveDictHydrationReconcile:
    @pytest.mark.asyncio
    async def test_composite_body_hydrates_then_reorders(self, fake_browser_full):
        d = ReactiveDict({"a": 1, "b": 2})

        def item_body(v: int, k: str | int):
            return FragmentElement(
                [
                    TextElement("["),
                    TextElement(f"{k}="),
                    Element("span", {}, {}, None, [str(v)]),
                ]
            )

        rep = RepeatElement(d, item_body)
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent_node = parent._get_node()
        for k, v in (("a", 1), ("b", 2)):
            merged = FakeDOMNode("#text", text_content=f"[{k}=")
            merged.__webcompy_prerendered_node__ = True
            parent_node.appendChild(merged)
            span = FakeDOMNode("span")
            span.__webcompy_prerendered_node__ = True
            text = FakeDOMNode("#text", text_content=str(v))
            text.__webcompy_prerendered_node__ = True
            span.appendChild(text)
            parent_node.appendChild(span)
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        rep._hydrate_node()
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

        assert [n.textContent for n in parent_node.childNodes] == ["[", "a=", "1", "[", "b=", "2"]
        assert all(getattr(n, "__webcompy_prerendered_node__", False) for n in parent_node.childNodes), (
            "hydration must adopt every prerendered node (no index drift)"
        )
        frag_a, frag_b = rep._children
        assert [c._node_cache for c in frag_a._children] == [parent_node.childNodes[i] for i in range(3)]
        assert [c._node_cache for c in frag_b._children] == [parent_node.childNodes[i] for i in range(3, 6)]

        d.pop("a")
        d["a"] = 1
        await rep._refresh()
        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

        assert [n.textContent for n in parent_node.childNodes] == ["[", "b=", "2", "[", "a=", "1"]
        assert all(getattr(n, "__webcompy_prerendered_node__", False) for n in parent_node.childNodes), (
            "reconcile must not leave newly created or stray nodes"
        )
