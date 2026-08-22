from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from webcompy.components._generator import define_component
from webcompy.components._libs import generate_id
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.elements.generators import suspense
from webcompy.elements.types._suspense import SuspenseElement
from webcompy.ports._keys import DOM_PORT_KEY, FFI_PORT_KEY, HOST_PORT_KEY
from webcompy_server.ports import VirtualDOMNode
from webcompy_testing import FakeBrowserDOMPort, FakeBrowserFFIPort, FakeBrowserHostPort


class _DummyParent:
    def __init__(self, node=None):
        self._node = node or VirtualDOMNode("div")
        self._node.__webcompy_node__ = False
        self._node.__webcompy_prerendered_node__ = True

    def _get_node(self):
        return self._node

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self):
        return ()

    def _re_index_children(self, recursive):
        pass


@pytest.fixture
def suspense_scope():
    from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
    from webcompy_testing import FakeAsyncSchedulerPort

    scope = DIScope()
    scope.provide(ASYNC_SCHEDULER_PORT_KEY, FakeAsyncSchedulerPort())
    scope.provide(DOM_PORT_KEY, FakeBrowserDOMPort())
    scope.provide(HOST_PORT_KEY, FakeBrowserHostPort())
    scope.provide(FFI_PORT_KEY, FakeBrowserFFIPort())
    token = _active_di_scope.set(scope)
    yield scope
    _active_di_scope.reset(token)
    scope.dispose()


@define_component("suspense-provide-child")
def SuspenseProvideChild(context):
    from webcompy.di import provide

    provide("leak-key", "leaked")
    return html.DIV({}, "child")


@define_component("suspense-ordinal-child")
def SuspenseOrdinalChild(context):
    return html.DIV({}, "x")


class TestSuspenseScopeRestoration:
    def _suspense_with_provider(self):
        return SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: SuspenseProvideChild(None),
        )

    def _scope_with_head_props(self, suspense_scope):
        from webcompy.components._component import HeadPropsStore
        from webcompy.di._keys import _HEAD_PROPS_KEY
        from webcompy.ports._keys import CUSTOM_ELEMENT_PORT_KEY
        from webcompy_testing import FakeCustomElementPort

        suspense_scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
        suspense_scope.provide(CUSTOM_ELEMENT_PORT_KEY, FakeCustomElementPort())

    @pytest.mark.asyncio
    async def test_server_resolution_restores_parent_scope_after_provide(self, suspense_scope):
        from webcompy.di import inject

        self._scope_with_head_props(suspense_scope)
        el = self._suspense_with_provider()
        el._parent = _DummyParent()
        el._node_idx = 0

        original = _active_di_scope.get(None)
        await el._server_render()

        assert _active_di_scope.get(None) is original
        assert inject("leak-key", default=None) is None

    @pytest.mark.asyncio
    async def test_browser_resolution_restores_parent_scope_after_provide(self, monkeypatch, suspense_scope):
        from webcompy.di import inject

        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")
        self._scope_with_head_props(suspense_scope)
        el = self._suspense_with_provider()
        el._parent = _DummyParent()
        el._node_idx = 0

        original = _active_di_scope.get(None)
        await el._browser_resolve()

        assert _active_di_scope.get(None) is original
        assert inject("leak-key", default=None) is None

    def test_hydration_fast_path_restores_scope_after_provide(self, monkeypatch, suspense_scope):
        from webcompy.di import inject
        from webcompy.di._keys import HYDRATION_DATA_KEY

        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")
        self._scope_with_head_props(suspense_scope)
        suspense_scope.provide(HYDRATION_DATA_KEY, {generate_id("SuspenseProvideChild"): {"state": "success"}})
        el = self._suspense_with_provider()
        el._parent = _DummyParent()
        el._node_idx = 0

        original = _active_di_scope.get(None)
        el._hydrate_node()

        assert el._resolved is True
        assert _active_di_scope.get(None) is original
        assert inject("leak-key", default=None) is None

    @pytest.mark.asyncio
    async def test_deferred_hydration_passes_pre_probe_scope(self, monkeypatch, suspense_scope):
        from webcompy.di import inject
        from webcompy.di._keys import HYDRATION_DATA_KEY
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")
        self._scope_with_head_props(suspense_scope)
        suspense_scope.provide(HYDRATION_DATA_KEY, {})

        captured: dict[str, Any] = {}

        async def _noop():
            return None

        def _spy(inner_self, children=None, pairs=None, *, original_scope=None):
            captured["original_scope"] = original_scope
            return _noop()

        monkeypatch.setattr(SuspenseElement, "_browser_resolve", _spy)

        unresolved_cid = generate_id("UnresolvedProvideComp")

        def children_generator():
            return html.DIV(
                {},
                SuspenseProvideChild(None),
                TestSuspenseHydrationFastPath._make_component(unresolved_cid, f"{unresolved_cid}#0"),
            )

        el = SuspenseElement(fallback=lambda: html.P({}, "loading"), children=children_generator)
        el._parent = _DummyParent()
        el._node_idx = 0

        original = _active_di_scope.get(None)
        el._hydrate_node()

        assert captured["original_scope"] is original
        await inject(ASYNC_SCHEDULER_PORT_KEY).drain()


class TestSuspenseElement:
    def test_suspense_is_dynamic_element_subclass(self):
        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, "content"),
        )
        from webcompy.elements.types._dynamic import DynamicElement

        assert isinstance(el, DynamicElement)

    def test_init_stores_parameters(self):
        def fallback():
            return html.P({}, "loading")

        def children():
            return html.DIV({}, "content")

        def error_fb():
            return html.P({}, "error")

        el = SuspenseElement(
            fallback=fallback,
            children=children,
            error_fallback=error_fb,
            timeout=30.0,
        )
        assert el._fallback_generator is fallback
        assert el._children_generator is children
        assert el._error_fallback_generator is error_fb
        assert el._timeout == 30.0

    def test_children_generator_not_called_during_init(self):
        call_count = 0

        def children():
            nonlocal call_count
            call_count += 1
            return html.DIV({}, "content")

        SuspenseElement(fallback=lambda: html.P({}, "loading"), children=children)
        assert call_count == 0

    @pytest.mark.asyncio
    async def test_sync_children_render_immediately_without_fallback(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        parent = _DummyParent()

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({"id": "content"}, "hello"),
        )
        el._parent = parent
        el._node_idx = 0
        await el._render()

        assert len(el._children) > 0
        assert parent._node.childNodes.length > 0

    @pytest.mark.asyncio
    async def test_fallback_shown_when_async_children_pending(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        parent = _DummyParent()

        async def _dummy_coro():
            await asyncio.sleep(0)
            return html.DIV({}, "resolved")

        def children_generator():
            from webcompy.components._component import Component

            mock_component = MagicMock(spec=Component)
            mock_component._pending_async_template = _dummy_coro()
            mock_component._property = {"component_id": "test-cmp"}
            mock_component._children = []
            mock_component._node_idx = 0
            mock_component._mounted = None
            mock_component._parent = parent
            return html.DIV({}, mock_component)

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading..."),
            children=children_generator,
        )
        el._parent = parent
        el._node_idx = 0
        await el._render()

        assert len(el._children) > 0
        html_out = _render_to_html(parent._node)
        assert "loading" in html_out

    @pytest.mark.asyncio
    async def test_suspense_generator_creates_suspense_element(self):
        el = suspense(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, "content"),
        )
        assert isinstance(el, SuspenseElement)

    @pytest.mark.asyncio
    async def test_suspense_on_set_parent_noops(self):
        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, "content"),
        )
        parent = _DummyParent()
        el._parent = parent
        assert el._children == []

    @pytest.mark.asyncio
    async def test_remove_element_cancels_pending_tasks(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, "content"),
        )
        parent = _DummyParent()
        el._parent = parent
        el._node_idx = 0
        await el._render()

        task = asyncio.ensure_future(asyncio.sleep(10))
        el._pending_tasks.append(task)
        assert not task.done()

        el._remove_element(recursive=False, remove_node=False)
        await asyncio.sleep(0)
        assert task.cancelled()
        assert task not in el._pending_tasks

    def test_generate_fallback_returns_fallback_element(self):
        el = SuspenseElement(
            fallback=lambda: html.SPAN({}, "fallback text"),
            children=lambda: html.DIV({}, "content"),
        )
        parent = _DummyParent()
        el._parent = parent

        fallback = el._generate_fallback()
        assert len(fallback) == 1
        html_out = _render_to_html(parent._node)
        _ = html_out


def _render_to_html(node: VirtualDOMNode) -> str:
    from webcompy_server.ports._dom import ServerDOMPort

    port = ServerDOMPort()
    return port.render_html(node)


class TestSuspenseHydrationOrdinals:
    @pytest.mark.asyncio
    async def test_hydration_fallback_uses_provisional_transfer_ids(self, monkeypatch, suspense_scope):
        from webcompy.app._render_context import RenderContext
        from webcompy.components._component import HeadPropsStore, _active_app_context
        from webcompy.di import inject
        from webcompy.di._keys import _HEAD_PROPS_KEY, HYDRATION_DATA_KEY
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, CUSTOM_ELEMENT_PORT_KEY
        from webcompy_testing import FakeCustomElementPort

        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        class _ProbeAppCtx(RenderContext):
            def _register_ports(self) -> None:
                pass

        app_ctx = _ProbeAppCtx.__new__(_ProbeAppCtx)
        app_ctx._transfer_ordinal_counters = {}
        app_ctx._transfer_probe_depth = 0
        app_ctx._hydration_payload_closed = False
        app_token = _active_app_context.set(app_ctx)

        async def _noop():
            return None

        def _spy(inner_self, children=None, pairs=None, **kwargs):
            return _noop()

        monkeypatch.setattr(SuspenseElement, "_browser_resolve", _spy)

        try:
            suspense_scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
            suspense_scope.provide(CUSTOM_ELEMENT_PORT_KEY, FakeCustomElementPort())
            name_id = generate_id("SuspenseOrdinalChild")
            suspense_scope.provide(HYDRATION_DATA_KEY, {f"{name_id}#0": {"state": "success"}})

            unresolved_cid = generate_id("UnresolvedOrdinalComp")
            probe: dict[str, Any] = {}

            def children_generator():
                wrapper = html.DIV(
                    {},
                    SuspenseOrdinalChild(None),
                    TestSuspenseHydrationFastPath._make_component(unresolved_cid, f"{unresolved_cid}#0"),
                )
                probe["wrapper"] = wrapper
                return wrapper

            el = SuspenseElement(
                fallback=lambda: html.P({}, SuspenseOrdinalChild(None)),
                children=children_generator,
            )
            el._parent = _DummyParent()
            el._node_idx = 0

            el._hydrate_node()

            probe_child = probe["wrapper"]._children[0]
            fallback_child = el._children[0]._children[0]
            assert probe_child._property["transfer_id"] == f"{name_id}#0"
            assert fallback_child._property["transfer_id"] == name_id
            assert app_ctx._transfer_ordinal_counters["SuspenseOrdinalChild"] == 1

            later = SuspenseOrdinalChild(None)
            assert later._property["transfer_id"] == f"{name_id}#1"

            await inject(ASYNC_SCHEDULER_PORT_KEY).drain()
        finally:
            _active_app_context.reset(app_token)


class TestSuspenseTimeoutProbeDestroy:
    @pytest.mark.asyncio
    async def test_timeout_destroys_probe_subtree_and_keeps_fallback(self, monkeypatch, suspense_scope, caplog):
        import logging

        from webcompy.components._component import HeadPropsStore
        from webcompy.components._context_manager import ComponentRenderState
        from webcompy.di import inject
        from webcompy.di._keys import _HEAD_PROPS_KEY
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY, CUSTOM_ELEMENT_PORT_KEY
        from webcompy.signal._effect import EffectScope
        from webcompy_testing import FakeCustomElementPort

        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")
        suspense_scope.provide(_HEAD_PROPS_KEY, HeadPropsStore())
        suspense_scope.provide(CUSTOM_ELEMENT_PORT_KEY, FakeCustomElementPort())

        destroyed: list[str] = []

        @define_component("timeout-destroy-child")
        def TimeoutDestroyChild(context):
            from webcompy.components import on_before_destroy

            on_before_destroy(lambda: destroyed.append("child-destroyed"))
            return html.DIV({}, "probe")

        slow_cid = generate_id("SlowTimeoutComp")

        class _Ctx:
            _component_name = "SlowTimeoutComp"
            _transfer_id = f"{slow_cid}#0"

            def __init__(self) -> None:
                self._transferable_signals = {}
                self._async_results = []

        state = ComponentRenderState(
            context=_Ctx(),
            effect_scope=EffectScope(),
            framework_cleanup=lambda: None,
        )

        async def template():
            await asyncio.sleep(0.5)
            return html.DIV({}, "late")

        comp = TestSuspenseHydrationFastPath._make_component(slow_cid, f"{slow_cid}#0")
        comp._pending_async_template = template()
        comp._render_state = state

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, TimeoutDestroyChild(None), comp),
            timeout=0.05,
        )
        el._parent = _DummyParent()
        el._node_idx = 0

        el._hydrate_node()
        children_before = list(el._children)

        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        with caplog.at_level(logging.WARNING, logger="webcompy.elements.types._suspense"):
            await scheduler.await_pending(only_render=True)

        assert any("timed out" in record.message for record in caplog.records)
        assert list(el._children) == children_before
        assert destroyed == ["child-destroyed"]


class TestSuspenseHydrationFastPath:
    CID = "fast-child"

    @staticmethod
    def _make_component(cid: str, transfer_id: str | None = None):
        from webcompy.components._component import Component

        mock_component = MagicMock(spec=Component)
        mock_component._pending_async_template = None
        mock_component._property = {"component_id": cid}
        if transfer_id is not None:
            mock_component._property["transfer_id"] = transfer_id
        mock_component._children = []
        mock_component._node_idx = 0
        mock_component._node_count = 1
        mock_component._mounted = False
        mock_component._render = AsyncMock()
        return mock_component

    def test_adopt_fast_path_with_per_instance_transfer_id(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")
        from webcompy.di._keys import HYDRATION_DATA_KEY

        cid = generate_id(self.CID)
        suspense_scope.provide(HYDRATION_DATA_KEY, {f"{cid}#0": {"state": "success"}})

        probe: dict[str, Any] = {}

        def children_generator():
            wrapper = html.DIV({"id": "resolved"}, self._make_component(cid, f"{cid}#0"))
            probe["wrapper"] = wrapper
            return wrapper

        el = SuspenseElement(fallback=lambda: html.P({}, "loading"), children=children_generator)
        el._parent = _DummyParent()
        el._node_idx = 0

        el._hydrate_node()

        assert el._resolved is True
        assert el._pending_tasks == []
        assert probe["wrapper"] in el._children

    def test_bare_component_id_does_not_trigger_fast_path(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")
        from webcompy.di._keys import HYDRATION_DATA_KEY

        cid = generate_id(self.CID)
        suspense_scope.provide(HYDRATION_DATA_KEY, {cid: {"state": "success"}})

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, self._make_component(cid, f"{cid}#0")),
        )
        el._parent = _DummyParent()
        el._node_idx = 0

        el._hydrate_node()

        assert el._resolved is False
        assert len(el._pending_tasks) == 1

    @pytest.mark.asyncio
    async def test_fallback_resolution_reuses_probe_children(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        captured: dict[str, Any] = {}

        async def _noop():
            return None

        def _spy(inner_self, children=None, pairs=None, **kwargs):
            captured["children"] = children
            return _noop()

        monkeypatch.setattr(SuspenseElement, "_browser_resolve", _spy)

        probe: dict[str, Any] = {}
        unresolved_cid = generate_id("UnresolvedComp")

        def children_generator():
            wrapper = html.DIV({"id": "unresolved"}, self._make_component(unresolved_cid, f"{unresolved_cid}#0"))
            probe["wrapper"] = wrapper
            return wrapper

        el = SuspenseElement(fallback=lambda: html.P({}, "loading"), children=children_generator)
        el._parent = _DummyParent()
        el._node_idx = 0

        el._hydrate_node()

        assert len(el._pending_tasks) == 1
        assert captured["children"] is not None
        assert probe["wrapper"] in captured["children"]
        await inject(ASYNC_SCHEDULER_PORT_KEY).drain()

    @pytest.mark.asyncio
    async def test_fallback_resolution_is_render_scoped(self, monkeypatch, suspense_scope):
        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")
        from webcompy.di import inject
        from webcompy.di._keys import HYDRATION_DATA_KEY
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY

        cid = generate_id("DeferredComp")
        suspense_scope.provide(HYDRATION_DATA_KEY, {})

        scheduled: list[tuple[object, bool]] = []

        async def _noop():
            return None

        sentinels: list[object] = []

        def _spy_browser_resolve(inner_self, children=None, pairs=None, **kwargs):
            coro = _noop()
            sentinels.append(coro)
            return coro

        monkeypatch.setattr(SuspenseElement, "_browser_resolve", _spy_browser_resolve)

        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        original_schedule = scheduler.schedule

        def _spy_schedule(coro, *, render=False):
            scheduled.append((coro, render))
            return original_schedule(coro, render=render)

        monkeypatch.setattr(scheduler, "schedule", _spy_schedule)

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, self._make_component(cid, f"{cid}#0")),
        )
        el._parent = _DummyParent()
        el._node_idx = 0

        el._hydrate_node()

        resolve_flags = [render for coro, render in scheduled if coro in sentinels]
        assert resolve_flags == [True]
        await scheduler.drain()

    @pytest.mark.asyncio
    async def test_deferred_resolution_restores_within_window(self, monkeypatch, suspense_scope):
        from webcompy.components._component import (
            _active_app_context,
            _is_hydration_payload_open,
        )
        from webcompy.components._context_manager import ComponentRenderState
        from webcompy.di import inject
        from webcompy.di._keys import HYDRATION_SIGNAL_DATA_KEY
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
        from webcompy.signal import use_state
        from webcompy.signal._effect import EffectScope

        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        cid = generate_id("DeferredAsync")
        other_cid = generate_id("OtherChild")

        class _AppCtx:
            def __init__(self) -> None:
                self._hydration_payload_closed = False
                self._counters: dict[str, int] = {}

            def _next_transfer_id(self, name: str) -> str:
                ordinal = self._counters.get(name, 0)
                self._counters[name] = ordinal + 1
                return f"{generate_id(name)}#{ordinal}"

        app_ctx = _AppCtx()
        token = _active_app_context.set(app_ctx)
        try:
            suspense_scope.provide(HYDRATION_SIGNAL_DATA_KEY, {f"{cid}#0": {"k": 42}})

            observed: dict[str, Any] = {}

            class _Ctx:
                _component_name = "DeferredAsync"
                _transfer_id = f"{cid}#0"

                def __init__(self) -> None:
                    self._transferable_signals = {}
                    self._async_results = []

            state = ComponentRenderState(
                context=_Ctx(),
                effect_scope=EffectScope(),
                framework_cleanup=lambda: None,
            )

            async def template():
                s = use_state("k", lambda: "factory-ran")
                observed["value"] = s.value
                observed["window_open"] = _is_hydration_payload_open()
                return html.DIV({}, str(s.value))

            comp = self._make_component(cid, f"{cid}#0")
            comp._pending_async_template = template()
            comp._render_state = state

            unresolved = self._make_component(other_cid, f"{other_cid}#0")

            el = SuspenseElement(
                fallback=lambda: html.P({}, "loading"),
                children=lambda: html.DIV({}, comp, unresolved),
            )
            el._parent = _DummyParent()
            el._node_idx = 0

            el._hydrate_node()

            scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
            await scheduler.await_pending(only_render=True)
            app_ctx._hydration_payload_closed = True
            await scheduler.drain()

            assert observed["window_open"] is True
            assert observed["value"] == 42
        finally:
            _active_app_context.reset(token)

    @pytest.mark.asyncio
    async def test_deferred_resolution_timeout_keeps_fallback(self, monkeypatch, suspense_scope, caplog):
        import logging

        from webcompy.components._context_manager import ComponentRenderState
        from webcompy.di import inject
        from webcompy.ports._keys import ASYNC_SCHEDULER_PORT_KEY
        from webcompy.signal._effect import EffectScope

        monkeypatch.setattr("webcompy.elements.types._suspense.ENVIRONMENT", "pyscript")

        cid = generate_id("SlowComp")
        other_cid = generate_id("TimeoutOther")

        class _Ctx:
            _component_name = "SlowComp"
            _transfer_id = f"{cid}#0"

            def __init__(self) -> None:
                self._transferable_signals = {}
                self._async_results = []

        state = ComponentRenderState(
            context=_Ctx(),
            effect_scope=EffectScope(),
            framework_cleanup=lambda: None,
        )

        async def template():
            await asyncio.sleep(0.5)
            return html.DIV({}, "late")

        comp = self._make_component(cid, f"{cid}#0")
        comp._pending_async_template = template()
        comp._render_state = state
        unresolved = self._make_component(other_cid, f"{other_cid}#0")

        el = SuspenseElement(
            fallback=lambda: html.P({}, "loading"),
            children=lambda: html.DIV({}, comp, unresolved),
            timeout=0.05,
        )
        el._parent = _DummyParent()
        el._node_idx = 0

        el._hydrate_node()
        children_before = list(el._children)

        scheduler = inject(ASYNC_SCHEDULER_PORT_KEY)
        with caplog.at_level(logging.WARNING, logger="webcompy.elements.types._suspense"):
            await scheduler.await_pending(only_render=True)

        assert any("timed out" in record.message for record in caplog.records)
        assert list(el._children) == children_before
