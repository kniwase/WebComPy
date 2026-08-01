from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest

from tests.conftest import FakeDOMNode, MockHistoryPort
from webcompy.components import define_component
from webcompy.di import DIScope, inject
from webcompy.di._keys import _ROUTER_KEY
from webcompy.di._scope import _active_di_scope
from webcompy.elements import ClientOnly, html
from webcompy.elements.types._element import Element
from webcompy.elements.types._fragment import FragmentElement
from webcompy.elements.types._repeat import RepeatElement
from webcompy.elements.types._suspense import SuspenseElement
from webcompy.elements.types._text import TextElement
from webcompy.ports._async_scheduler import AsyncSchedulerPort
from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, MARKDOWN_PORT_KEY
from webcompy.router._router import Router
from webcompy.router._view import RouterView
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


class TestReactiveIfInsideForToggle:
    def test_double_toggle_preserves_all_items(self):
        items = ReactiveList([1, 2, 3])
        flag = Signal(True)

        @define_component
        def TogglePage(context):
            return render_template(
                """
                <ul>
                    <li>header</li>
                    {% for item in items %}
                    {% if flag %}
                    <li>on-{{ item }}</li>
                    {% else %}
                    <li>off-{{ item }}</li>
                    {% endif %}
                    {% endfor %}
                </ul>
                """,
                {"items": items, "flag": flag},
            )

        with TestRenderer.render(TogglePage) as result:
            assert [li.textContent for li in result.query_selector_all("li")] == [
                "header",
                "on-1",
                "on-2",
                "on-3",
            ]
            flag.value = False
            assert [li.textContent for li in result.query_selector_all("li")] == [
                "header",
                "off-1",
                "off-2",
                "off-3",
            ]
            flag.value = True
            assert [li.textContent for li in result.query_selector_all("li")] == [
                "header",
                "on-1",
                "on-2",
                "on-3",
            ]
            items.pop(0)
            assert [li.textContent for li in result.query_selector_all("li")] == [
                "header",
                "on-2",
                "on-3",
            ]
            items.append(4)
            assert [li.textContent for li in result.query_selector_all("li")] == [
                "header",
                "on-2",
                "on-3",
                "on-4",
            ]


class TestRepeatRefreshWithFollowingSibling:
    def test_following_sibling_preserved_after_pop(self):
        items = ReactiveList(["x", "y"])

        @define_component
        def SiblingPage(context):
            return render_template(
                """
                <div>
                    <p>head</p>
                    {% for item in items %}
                    <b>{{ item }}</b>
                    {% endfor %}
                    <span>tail</span>
                </div>
                """,
                {"items": items},
            )

        with TestRenderer.render(SiblingPage) as result:
            assert result.query_selector("p").textContent == "head"
            assert [b.textContent for b in result.query_selector_all("b")] == ["x", "y"]
            assert result.query_selector("span").textContent == "tail"
            items.pop(0)
            assert result.query_selector("p").textContent == "head"
            assert [b.textContent for b in result.query_selector_all("b")] == ["y"]
            assert result.query_selector("span").textContent == "tail"
            assert len(result.query_selector_all("b")) == 1


class TestNestedForRefresh:
    def test_both_levels_mutate_without_losing_cells(self):
        rows = ReactiveList(["a", "b"])
        cols = ReactiveList([1, 2])

        @define_component
        def NestedPage(context):
            return render_template(
                """
                <table>
                    {% for row in rows %}
                    <tr>
                        {% for col in cols %}
                        <td>{{ row }}{{ col }}</td>
                        {% endfor %}
                    </tr>
                    {% endfor %}
                </table>
                """,
                {"rows": rows, "cols": cols},
            )

        with TestRenderer.render(NestedPage) as result:
            assert [td.textContent for td in result.query_selector_all("td")] == ["a1", "a2", "b1", "b2"]
            cols.pop(0)
            assert [td.textContent for td in result.query_selector_all("td")] == ["a2", "b2"]
            rows.append("c")
            assert [td.textContent for td in result.query_selector_all("td")] == ["a2", "b2", "c2"]
            rows.pop(0)
            assert [td.textContent for td in result.query_selector_all("td")] == ["b2", "c2"]


class TestReindexWithoutNodeIdx:
    def test_fragment_without_node_idx_does_not_raise(self):
        frag = FragmentElement([])
        frag._re_index_children(False)

    def test_fragment_with_children_falls_back_to_zero_base(self):
        parent = _FakeRootElement("div", {}, {}, None, None)
        first = Element("p")
        second = Element("p")
        frag = FragmentElement([first, second])
        frag._parent = parent
        frag._re_index_children(False)
        assert first._node_idx == 0
        assert second._node_idx == 1

    def test_router_view_on_set_parent_without_node_idx(self):
        scope = DIScope()
        router = Router(history=MockHistoryPort(mode="hash"), preload=False)
        scope.provide(_ROUTER_KEY, router)
        scope.__enter__()
        try:
            view = RouterView()
            parent = _FakeRootElement("div", {}, {}, None, None)
            view._parent = parent
            assert view._children[0]._node_idx == 0
        finally:
            scope.__exit__(None, None, None)


class TestMarkdownForRenderReindexesFollowingSibling:
    @pytest.mark.asyncio
    async def test_render_reindexes_following_sibling(self, fake_browser_full):
        _active_di_scope.get().provide(MARKDOWN_PORT_KEY, DefaultMarkdownParser())
        mfe = MarkdownForElement(["item"], "items", "- {{ item }}", {"items": ["a", "b"]})
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        mfe._parent = parent
        mfe._node_idx = 0
        tail = Element("span")
        tail._parent = parent
        tail._node_idx = 5
        parent._children = [mfe, tail]
        await mfe._render()
        assert tail._node_idx == mfe._node_count
        assert mfe._children[0]._node_idx == 0


class _EagerScheduler(AsyncSchedulerPort):
    """Scheduler whose tasks actually run the scheduled coroutine.

    FakeAsyncSchedulerPort returns a bare ``sleep(0)`` task, which cannot
    reproduce ghost renders. This scheduler lets the scheduled render tasks
    execute when the event loop is pumped.
    """

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[Any]] = []

    def schedule(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        task = asyncio.ensure_future(coro)
        self._tasks.append(task)
        return task

    async def await_pending(self) -> None:
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()


class TestStaleHydrationRenderTasks:
    @pytest.mark.asyncio
    async def test_repeat_refresh_cancels_stale_hydration_render_tasks(self, fake_browser_full):
        _active_di_scope.get().provide(ASYNC_SCHEDULER_PORT_KEY, _EagerScheduler())
        rl = ReactiveList(["a", "b"])
        rep = RepeatElement(rl, lambda x: TextElement(x))
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        rep._parent = parent
        rep._node_idx = 0
        rep._hydrate_node()
        assert len(rep._pending_render_tasks) == 2
        await rep._refresh()
        assert rep._pending_render_tasks == []
        await asyncio.sleep(0)
        node = parent._get_node()
        assert node.childNodes.length == 2


class TestKeyedHydrationTaskOwnership:
    def _setup_keyed_fragment_repeat(self):
        rl = ReactiveList(["a", "b"])
        rep = RepeatElement(
            rl,
            lambda item, _key: FragmentElement([TextElement(item), TextElement(item)]),
            key=lambda item: item,
        )
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        rep._parent = parent
        rep._node_idx = 0
        rep._signal_activated = True
        return rl, rep, parent

    @pytest.mark.asyncio
    async def test_reused_fragment_child_render_task_survives_keyed_refresh(self, fake_browser_full):
        _active_di_scope.get().provide(ASYNC_SCHEDULER_PORT_KEY, _EagerScheduler())
        rl, rep, parent = self._setup_keyed_fragment_repeat()
        rep._hydrate_node()
        assert len(rep._pending_render_tasks) == 2
        fragment_b = rep._children[1]

        rl.pop(0)
        await rep._refresh()

        reused_tasks = [task for target, task in rep._pending_render_tasks if target is fragment_b]
        assert reused_tasks, "render task of a reused keyed child must not be cancelled"
        assert fragment_b._hydrated is True

        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()
        node = parent._get_node()
        assert node.childNodes.length == 2
        assert fragment_b._hydrated is False
        assert all(child._mounted for child in fragment_b._children)

    @pytest.mark.asyncio
    async def test_discarded_fragment_child_render_tasks_cancelled(self, fake_browser_full):
        _active_di_scope.get().provide(ASYNC_SCHEDULER_PORT_KEY, _EagerScheduler())
        rl, rep, parent = self._setup_keyed_fragment_repeat()
        rep._hydrate_node()
        assert len(rep._pending_render_tasks) == 2

        rl.clear()
        await rep._refresh()
        assert rep._pending_render_tasks == []

        await inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()
        assert parent._get_node().childNodes.length == 0


class TestRangeScopedOrphanCleanup:
    @pytest.mark.asyncio
    async def test_reconcile_removes_orphan_in_owned_range_preserving_following_sibling(
        self, fake_browser_full, monkeypatch
    ):
        rl = ReactiveList(["a", "b"])
        rep = RepeatElement(rl, lambda item, _key: TextElement(item), key=lambda item: item)
        parent = _FakeRootElement("div", {}, {}, None, None)
        parent._node_cache = FakeDOMNode("div")
        parent._mounted = True
        tail = TextElement("tail")
        tail._parent = parent
        rep._parent = parent
        rep._node_idx = 0
        parent._children = [rep, tail]
        await rep._render()
        await tail._render()
        node = parent._get_node()
        assert [c.textContent for c in node.childNodes] == ["a", "b", "tail"]

        original_remove = TextElement._remove_element

        def _failing_remove(self, recursive=True, remove_node=True):
            original_remove(self, recursive, False)

        monkeypatch.setattr(TextElement, "_remove_element", _failing_remove)
        rl.pop(0)
        await rep._refresh()
        assert [c.textContent for c in node.childNodes] == ["b", "tail"]
