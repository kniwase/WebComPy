from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import FakeDOMNode
from webcompy.components._component import _active_app_context
from webcompy.di import inject
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._text import NewLine, RawHTMLElement, TextElement
from webcompy.hydration._report import HydrationReporter
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

    def test_split_text_uses_utf16_offsets(self):
        parent = FakeDOMNode("div")
        node = FakeDOMNode("#text", text_content="😀x")
        parent.appendChild(node)
        new_node = node.splitText(2)
        assert node.textContent == "😀"
        assert new_node.textContent == "x"

    def test_split_text_inside_surrogate_pair_mirrors_browser(self):
        parent = FakeDOMNode("div")
        node = FakeDOMNode("#text", text_content="😀x")
        parent.appendChild(node)
        new_node = node.splitText(1)
        assert node.textContent == "\ud83d"
        assert new_node.textContent == "\ude00x"


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

    def test_content_mismatch_falls_back_without_splitting(self, fake_browser_full):
        _, prerendered = _hydrate_container(
            ["a", "b"],
            [FakeDOMNode("#text", text_content="xy")],
        )
        assert prerendered.childNodes.length == 1
        assert prerendered.childNodes[0].textContent == "a"

    def test_already_split_dom_is_untouched(self, fake_browser_full):
        first = FakeDOMNode("#text", text_content="a")
        second = FakeDOMNode("#text", text_content="b")
        _, prerendered = _hydrate_container(["a", "b"], [first, second])
        assert prerendered.childNodes.length == 2
        assert first.textContent_write_count == 0
        assert second.textContent_write_count == 0

    def test_multiple_merged_runs_are_all_split(self, fake_browser_full):
        el, prerendered = _hydrate_container(
            ["a", "b", Element("span", {}, {}, None, None), "c", "d"],
            [
                FakeDOMNode("#text", text_content="ab"),
                FakeDOMNode("span"),
                FakeDOMNode("#text", text_content="cd"),
            ],
        )
        assert prerendered.childNodes.length == 5
        assert [n.textContent for n in prerendered.childNodes] == ["a", "b", "", "c", "d"]
        assert el._children[3]._node_cache is prerendered.childNodes[3]
        assert el._children[4]._node_cache is prerendered.childNodes[4]

    def test_trailing_empty_text_run_is_split(self, fake_browser_full):
        el, prerendered = _hydrate_container(["a", ""], [FakeDOMNode("#text", text_content="a")])
        assert prerendered.childNodes.length == 2
        assert [n.textContent for n in prerendered.childNodes] == ["a", ""]
        assert el._children[1]._node_cache is prerendered.childNodes[1]

    def test_multiple_trailing_empty_children_are_split(self, fake_browser_full):
        el, prerendered = _hydrate_container(["a", "", ""], [FakeDOMNode("#text", text_content="a")])
        assert prerendered.childNodes.length == 3
        assert [n.textContent for n in prerendered.childNodes] == ["a", "", ""]
        assert el._children[1]._node_cache is prerendered.childNodes[1]
        assert el._children[2]._node_cache is prerendered.childNodes[2]

    def test_all_empty_run_without_dom_node_is_materialized(self, fake_browser_full):
        el, prerendered = _hydrate_container(
            ["", "", Element("span", {}, {}, None, None)],
            [FakeDOMNode("span")],
        )
        assert prerendered.childNodes.length == 3
        assert [n.textContent for n in prerendered.childNodes] == ["", "", ""]
        assert el._children[0]._node_cache is prerendered.childNodes[0]
        assert el._children[1]._node_cache is prerendered.childNodes[1]
        assert el._children[2]._node_cache is prerendered.childNodes[2]

    def test_astral_text_run_is_split_at_utf16_boundaries(self, fake_browser_full):
        first = FakeDOMNode("#text", text_content="😀x")
        el, prerendered = _hydrate_container(["😀", "x"], [first])
        assert prerendered.childNodes.length == 2
        assert [n.textContent for n in prerendered.childNodes] == ["😀", "x"]
        assert el._children[0]._node_cache is prerendered.childNodes[0]
        assert el._children[1]._node_cache is prerendered.childNodes[1]
        assert first.textContent_write_count == 0

    def test_content_mismatch_halts_normalization_for_later_runs(self, fake_browser_full):
        cd_node = FakeDOMNode("#text", text_content="cd")
        _, prerendered = _hydrate_container(
            ["a", "b", Element("span", {}, {}, None, None), "c", "d"],
            [
                FakeDOMNode("#text", text_content="ax"),
                FakeDOMNode("span"),
                cd_node,
            ],
        )
        assert prerendered.childNodes.length == 2
        assert [n.textContent for n in prerendered.childNodes] == ["a", "cd"]
        assert prerendered.childNodes[1] is cd_node
        assert cd_node.textContent == "cd"

    def test_non_text_node_at_run_position_records_tag_mismatch(self, fake_browser_full):
        from webcompy.components._component import _active_app_context
        from webcompy.hydration._report import HydrationReporter

        class _Ctx:
            def __init__(self) -> None:
                self._hydration_in_progress = True
                self._hydration_reporter = HydrationReporter()

        class _CidRootElement(FakeRootElement):
            _get_belonging_component = lambda self: "my-comp"

        ctx = _Ctx()
        token = _active_app_context.set(ctx)
        try:
            parent = _CidRootElement("div", {}, {}, None, None)
            parent._node_cache = FakeDOMNode("div")
            parent._mounted = True
            prerendered = FakeDOMNode("div")
            prerendered.__webcompy_prerendered_node__ = True
            span = FakeDOMNode("span")
            span.__webcompy_prerendered_node__ = True
            prerendered.appendChild(span)
            parent._node_cache.appendChild(prerendered)
            el = Element("div", {}, {}, None, [TextElement("a"), TextElement("b")])
            el._parent = parent
            el._node_idx = 0
            el._hydrate_node()

            tag_records = [r for r in ctx._hydration_reporter.records if r.kind == "tag" and r.expected == "#text"]
            assert len(tag_records) == 1
            assert tag_records[0].actual == "SPAN"
            assert tag_records[0].component_id == "my-comp"
        finally:
            _active_app_context.reset(token)

    def test_text_mismatch_record_carries_owning_component_id(self, fake_browser_full):
        from webcompy.components._component import _active_app_context
        from webcompy.hydration._report import HydrationReporter

        class _Ctx:
            def __init__(self) -> None:
                self._hydration_in_progress = True
                self._hydration_reporter = HydrationReporter()

        class _CidRootElement(FakeRootElement):
            _get_belonging_component = lambda self: "my-comp"

        ctx = _Ctx()
        token = _active_app_context.set(ctx)
        try:
            parent = _CidRootElement("div", {}, {}, None, None)
            parent._node_cache = FakeDOMNode("div")
            parent._mounted = True
            prerendered = FakeDOMNode("div")
            prerendered.__webcompy_prerendered_node__ = True
            text = FakeDOMNode("#text", text_content="old")
            text.__webcompy_prerendered_node__ = True
            prerendered.appendChild(text)
            parent._node_cache.appendChild(prerendered)
            el = Element("div", {}, {}, None, [TextElement("new")])
            el._parent = parent
            el._node_idx = 0
            el._hydrate_node()

            text_records = [r for r in ctx._hydration_reporter.records if r.kind == "text"]
            assert len(text_records) == 1
            assert text_records[0].component_id == "my-comp"
        finally:
            _active_app_context.reset(token)

    def test_newline_tag_mismatch_record_carries_owning_component_id(self, fake_browser_full):
        from webcompy.components._component import _active_app_context
        from webcompy.hydration._report import HydrationReporter

        class _Ctx:
            def __init__(self) -> None:
                self._hydration_in_progress = True
                self._hydration_reporter = HydrationReporter()

        class _CidRootElement(FakeRootElement):
            _get_belonging_component = lambda self: "my-comp"

        ctx = _Ctx()
        token = _active_app_context.set(ctx)
        try:
            parent = _CidRootElement("div", {}, {}, None, None)
            parent._node_cache = FakeDOMNode("div")
            parent._mounted = True
            span = FakeDOMNode("span")
            span.__webcompy_prerendered_node__ = True
            parent._node_cache.appendChild(span)
            newline = NewLine()
            newline._parent = parent
            newline._node_idx = 0

            newline._get_node()

            tag_records = [r for r in ctx._hydration_reporter.records if r.kind == "tag" and r.expected == "br"]
            assert len(tag_records) == 1
            assert tag_records[0].component_id == "my-comp"
        finally:
            _active_app_context.reset(token)


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


class _FakeHydrationCtx:
    def __init__(self) -> None:
        self._hydration_in_progress = True
        self._hydration_reporter = HydrationReporter()


def _hydrate_with_reporter(children: list[Any], dom_children: list[FakeDOMNode]):
    ctx = _FakeHydrationCtx()
    token = _active_app_context.set(ctx)
    try:
        parent = FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        parent_node = parent._get_node()
        prerendered = FakeDOMNode("div")
        prerendered.__webcompy_prerendered_node__ = True
        for node in dom_children:
            prerendered.appendChild(node)
        parent_node.appendChild(prerendered)
        el = Element("div", {}, {}, None, children)
        el._parent = parent
        el._node_idx = 0
        el._hydrate_node()
        return el, prerendered, ctx._hydration_reporter.records
    finally:
        _active_app_context.reset(token)


class TestHydrationSplitTextCoalescing:
    def test_single_text_element_coalesces_split_dom_text_nodes(self):
        quote_open = FakeDOMNode("#text", text_content='"')
        quote_open.__webcompy_prerendered_node__ = True
        decoded = FakeDOMNode("#text", text_content="you@example.com")
        quote_close = FakeDOMNode("#text", text_content='"')
        quote_close.__webcompy_prerendered_node__ = True

        child = TextElement('"you@example.com"')
        _, dom, records = _hydrate_with_reporter([child], [quote_open, decoded, quote_close])

        assert records == []
        assert dom.childNodes.length == 1
        assert dom.childNodes[0] is quote_open
        assert dom.childNodes[0].textContent == '"you@example.com"'
        assert getattr(dom.childNodes[0], "__webcompy_prerendered_node__", False) is True
        assert child._node_cache is quote_open

    def test_single_text_element_preserves_prerendered_flag_from_trailing_text_node(self):
        decoded = FakeDOMNode("#text", text_content="you@example.com")
        trailing = FakeDOMNode("#text", text_content='"')
        trailing.__webcompy_prerendered_node__ = True

        child = TextElement('you@example.com"')
        _, dom, records = _hydrate_with_reporter([child], [decoded, trailing])

        assert records == []
        assert dom.childNodes.length == 1
        assert dom.childNodes[0] is decoded
        assert dom.childNodes[0].textContent == 'you@example.com"'
        assert getattr(decoded, "__webcompy_prerendered_node__", False) is True
        assert child._node_cache is decoded

    def test_single_text_element_mismatched_split_nodes_not_coalesced(self):
        quote_open = FakeDOMNode("#text", text_content='"')
        quote_open.__webcompy_prerendered_node__ = True
        wrong = FakeDOMNode("#text", text_content="other@example.com")
        quote_close = FakeDOMNode("#text", text_content='"')
        quote_close.__webcompy_prerendered_node__ = True

        child = TextElement('"you@example.com"')
        _, _, records = _hydrate_with_reporter([child], [quote_open, wrong, quote_close])

        text_records = [r for r in records if r.kind == "text"]
        count_records = [r for r in records if r.kind == "node-count"]
        assert len(text_records) == 1
        assert text_records[0].expected == '"you@example.com"'
        assert text_records[0].actual == '"'
        assert len(count_records) == 1
        assert count_records[0].expected == 1
        assert count_records[0].actual == 3

    def test_multi_text_run_coalesces_split_nodes_then_resplits(self):
        prefix = FakeDOMNode("#text", text_content="Contact: ")
        prefix.__webcompy_prerendered_node__ = True
        decoded = FakeDOMNode("#text", text_content="you@example.com")

        c1 = TextElement("Contact:")
        c2 = TextElement(" ")
        c3 = TextElement("you@example.com")
        _, dom, records = _hydrate_with_reporter([c1, c2, c3], [prefix, decoded])

        assert records == []
        assert [n.textContent for n in dom.childNodes] == ["Contact:", " ", "you@example.com"]
        assert c1._node_cache is dom.childNodes[0]
        assert c2._node_cache is dom.childNodes[1]
        assert c3._node_cache is dom.childNodes[2]

    def test_multi_text_run_fast_path_leaves_trailing_stray_text_node_untouched(self):
        n1 = FakeDOMNode("#text", text_content="a")
        n1.__webcompy_prerendered_node__ = True
        n2 = FakeDOMNode("#text", text_content="b")
        n2.__webcompy_prerendered_node__ = True
        stray = FakeDOMNode("#text", text_content="extra")
        stray.__webcompy_prerendered_node__ = True

        c1 = TextElement("a")
        c2 = TextElement("b")
        _, dom, records = _hydrate_with_reporter([c1, c2], [n1, n2, stray])

        assert n1.textContent_write_count == 0
        assert n2.textContent_write_count == 0
        assert c1._node_cache is n1
        assert c2._node_cache is n2
        assert [n.textContent for n in dom.childNodes] == ["a", "b"]
        assert [r.kind for r in records] == ["node-count"]

    def test_single_text_coalescing_keeps_following_sibling_element_aligned(self):
        quote_open = FakeDOMNode("#text", text_content='"')
        quote_open.__webcompy_prerendered_node__ = True
        decoded = FakeDOMNode("#text", text_content="you@example.com")
        quote_close = FakeDOMNode("#text", text_content='"')
        quote_close.__webcompy_prerendered_node__ = True
        sibling_span = FakeDOMNode("span")
        sibling_span.__webcompy_prerendered_node__ = True
        sibling_text = FakeDOMNode("#text", text_content="ok")
        sibling_text.__webcompy_prerendered_node__ = True
        sibling_span.appendChild(sibling_text)

        text_child = TextElement('"you@example.com"')
        span_child = Element("span", {}, {}, None, [TextElement("ok")])
        _, dom, records = _hydrate_with_reporter(
            [text_child, span_child],
            [quote_open, decoded, quote_close, sibling_span],
        )

        assert records == []
        assert dom.childNodes.length == 2
        assert text_child._node_cache is quote_open
        assert span_child._node_cache is sibling_span

    def test_multiple_split_runs_in_same_container_are_both_coalesced(self):
        q1_open = FakeDOMNode("#text", text_content='"')
        q1_open.__webcompy_prerendered_node__ = True
        dec_1 = FakeDOMNode("#text", text_content="a@example.com")
        q1_close = FakeDOMNode("#text", text_content='"')
        q1_close.__webcompy_prerendered_node__ = True
        mid_span = FakeDOMNode("span")
        mid_span.__webcompy_prerendered_node__ = True
        mid_text = FakeDOMNode("#text", text_content="mid")
        mid_text.__webcompy_prerendered_node__ = True
        mid_span.appendChild(mid_text)
        q2_open = FakeDOMNode("#text", text_content='"')
        q2_open.__webcompy_prerendered_node__ = True
        dec_2 = FakeDOMNode("#text", text_content="b@example.com")
        q2_close = FakeDOMNode("#text", text_content='"')
        q2_close.__webcompy_prerendered_node__ = True

        t1 = TextElement('"a@example.com"')
        span_child = Element("span", {}, {}, None, [TextElement("mid")])
        t2 = TextElement('"b@example.com"')
        _, dom, records = _hydrate_with_reporter(
            [t1, span_child, t2],
            [q1_open, dec_1, q1_close, mid_span, q2_open, dec_2, q2_close],
        )

        assert records == []
        assert dom.childNodes.length == 3
        assert t1._node_cache is q1_open
        assert span_child._node_cache is mid_span
        assert t2._node_cache is q2_open
        assert [n.textContent for n in dom.childNodes] == ['"a@example.com"', "mid", '"b@example.com"']

    @pytest.mark.asyncio
    async def test_dynamic_fragment_coalesces_split_text_at_nonzero_start_idx(self, fake_browser_full):
        ctx = _FakeHydrationCtx()
        token = _active_app_context.set(ctx)
        try:
            parent = FakeRootElement("div", {}, {}, None, None)
            parent._node_cache = FakeDOMNode("div")
            parent._mounted = True
            parent_node = parent._get_node()

            prefix_span = FakeDOMNode("span")
            prefix_span.__webcompy_prerendered_node__ = True
            quote_open = FakeDOMNode("#text", text_content='"')
            quote_open.__webcompy_prerendered_node__ = True
            decoded = FakeDOMNode("#text", text_content="you@example.com")
            quote_close = FakeDOMNode("#text", text_content='"')
            quote_close.__webcompy_prerendered_node__ = True
            tail_span = FakeDOMNode("span")
            tail_span.__webcompy_prerendered_node__ = True
            tail_text = FakeDOMNode("#text", text_content="ok")
            tail_text.__webcompy_prerendered_node__ = True
            tail_span.appendChild(tail_text)

            for node in (prefix_span, quote_open, decoded, quote_close, tail_span):
                parent_node.appendChild(node)

            text_child = TextElement('"you@example.com"')
            span_child = Element("span", {}, {}, None, [TextElement("ok")])
            frag = FragmentElement([text_child, span_child])
            frag._parent = parent
            frag._node_idx = 1
            frag._hydrate_node()
            await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()

            assert ctx._hydration_reporter.records == []
            assert parent_node.childNodes.length == 3
            assert parent_node.childNodes[0] is prefix_span
            assert text_child._node_cache is quote_open
            assert quote_open.textContent == '"you@example.com"'
            assert getattr(quote_open, "__webcompy_prerendered_node__", False) is True
            assert span_child._node_cache is tail_span
        finally:
            _active_app_context.reset(token)
