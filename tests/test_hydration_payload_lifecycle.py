"""Tests for hydration payload lifecycle gating and per-instance transfer ids.

Covers:
- The hydration transfer payload (HYDRATION_SIGNAL_DATA_KEY / HYDRATION_DATA_KEY)
  is only consulted while the initial hydration window is open; component setups
  after the window closes (e.g., client-side navigation) run factories.
- Component instances receive per-instance transfer ids (``<md5(name)>#<ordinal>``)
  so multiple instances of the same component transfer and restore independently,
  while the scoped-CSS ``component_id`` stays definition-stable.
"""

from __future__ import annotations

import pytest

from webcompy.components import ComponentContext, define_component
from webcompy.components._component import (
    _active_app_context,
    _is_hydration_payload_open,
    _set_app_instance,
)
from webcompy.components._context_manager import ComponentRenderState, component_context
from webcompy.components._hooks import use_async_result
from webcompy.components._libs import generate_id
from webcompy.di._keys import HYDRATION_DATA_KEY, HYDRATION_SIGNAL_DATA_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.elements import html
from webcompy.hydration._collect import collect_transfer_data
from webcompy.hydration._payload import TransferAsyncResultEntry
from webcompy.signal import use_state
from webcompy.signal._effect import EffectScope
from webcompy_testing import TestRenderer


class _FakeComponentCtx:
    def __init__(self, name: str = "TestComp", transfer_id: str | None = None) -> None:
        self._component_name = name
        self._transfer_id = transfer_id
        self._transferable_signals: dict = {}
        self._async_results: list = []


def _make_state(name: str = "TestComp", transfer_id: str | None = None) -> ComponentRenderState:
    return ComponentRenderState(
        context=_FakeComponentCtx(name, transfer_id),
        effect_scope=EffectScope(),
        framework_cleanup=lambda: None,
    )


class _FakeAppCtx:
    def __init__(self, closed: bool = False) -> None:
        self._hydration_payload_closed = closed
        self._defer_depth: int = 0
        self._deferred_callbacks: list = []
        self._counters: dict[str, int] = {}

    def _next_transfer_id(self, component_name: str) -> str:
        ordinal = self._counters.get(component_name, 0)
        self._counters[component_name] = ordinal + 1
        return f"{generate_id(component_name)}#{ordinal}"


@pytest.fixture(autouse=True)
def _clean_app_context():
    token = _active_app_context.set(None)
    _set_app_instance(None)
    yield
    _set_app_instance(None)
    _active_app_context.reset(token)


class TestHydrationPayloadOpenCheck:
    def test_open_without_app_context(self):
        assert _is_hydration_payload_open() is True

    def test_open_when_context_exists_but_not_closed(self):
        token = _active_app_context.set(_FakeAppCtx(closed=False))
        try:
            assert _is_hydration_payload_open() is True
        finally:
            _active_app_context.reset(token)

    def test_closed_when_context_marks_payload_closed(self):
        token = _active_app_context.set(_FakeAppCtx(closed=True))
        try:
            assert _is_hydration_payload_open() is False
        finally:
            _active_app_context.reset(token)

    def test_closed_via_app_instance_fallback(self):
        _set_app_instance(_FakeAppCtx(closed=True))
        assert _is_hydration_payload_open() is False

    def test_open_when_context_lacks_the_flag(self):
        token = _active_app_context.set(object())
        try:
            assert _is_hydration_payload_open() is True
        finally:
            _active_app_context.reset(token)


class TestUseStateGating:
    def test_restores_while_window_open(self):
        state = _make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"k": 42}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        app_token = _active_app_context.set(_FakeAppCtx(closed=False))
        try:
            with component_context(state):
                calls: list[str] = []
                s = use_state("k", lambda: calls.append("called") or 0)
            assert s.value == 42
            assert calls == []
        finally:
            _active_app_context.reset(app_token)
            _active_di_scope.reset(token)

    def test_factory_runs_after_window_closed(self):
        state = _make_state()
        cid = generate_id("TestComp")
        payload = {cid: {"k": 42}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        app_token = _active_app_context.set(_FakeAppCtx(closed=True))
        try:
            with component_context(state):
                calls: list[str] = []
                s = use_state("k", lambda: calls.append("called") or 0)
            assert s.value == 0
            assert calls == ["called"]
        finally:
            _active_app_context.reset(app_token)
            _active_di_scope.reset(token)

    def test_stale_entry_for_same_component_name_is_ignored_after_close(self):
        state = _make_state("DemoDisplay")
        cid = generate_id("DemoDisplay")
        payload = {cid: {"k": "stale-from-initial-page"}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        app_token = _active_app_context.set(_FakeAppCtx(closed=True))
        try:
            with component_context(state):
                s = use_state("k", lambda: "fresh")
            assert s.value == "fresh"
        finally:
            _active_app_context.reset(app_token)
            _active_di_scope.reset(token)


class TestUseAsyncResultGating:
    def test_restores_while_window_open(self):
        state = _make_state()
        cid = generate_id("TestComp")
        scope = DIScope()
        scope.provide(HYDRATION_DATA_KEY, {cid: TransferAsyncResultEntry(state="success", data="stale-ok")})
        token = _active_di_scope.set(scope)
        app_token = _active_app_context.set(_FakeAppCtx(closed=False))
        try:
            with component_context(state):

                async def fetch() -> str:
                    raise AssertionError("async function must not run when restored")

                result = use_async_result(fetch, immediate=False)
            from webcompy.aio._async_result import AsyncState

            assert result._state.value == AsyncState.SUCCESS
            assert result._data.value == "stale-ok"
        finally:
            _active_app_context.reset(app_token)
            _active_di_scope.reset(token)

    def test_does_not_restore_after_window_closed(self):
        state = _make_state()
        cid = generate_id("TestComp")
        scope = DIScope()
        scope.provide(HYDRATION_DATA_KEY, {cid: TransferAsyncResultEntry(state="success", data="stale-ok")})
        token = _active_di_scope.set(scope)
        app_token = _active_app_context.set(_FakeAppCtx(closed=True))
        try:
            with component_context(state):

                async def fetch() -> str:
                    return "live"

                result = use_async_result(fetch, immediate=False)
            from webcompy.aio._async_result import AsyncState

            assert result._state.value == AsyncState.PENDING
            assert result._data.value is None
        finally:
            _active_app_context.reset(app_token)
            _active_di_scope.reset(token)


class TestPerInstanceTransferId:
    def test_render_context_assigns_per_name_ordinals(self):
        from webcompy.app._render_context import RenderContext

        class _RenderContextStub(RenderContext):
            def _register_ports(self) -> None:
                pass

        ctx = _RenderContextStub.__new__(_RenderContextStub)
        ctx._transfer_ordinal_counters = {}
        ctx._transfer_probe_depth = 0
        assert ctx._next_transfer_id("Foo") == f"{generate_id('Foo')}#0"
        assert ctx._next_transfer_id("Foo") == f"{generate_id('Foo')}#1"
        assert ctx._next_transfer_id("Bar") == f"{generate_id('Bar')}#0"

    def test_probe_depth_returns_provisional_ids_without_consuming(self):
        from webcompy.app._render_context import RenderContext

        class _RenderContextStub(RenderContext):
            def _register_ports(self) -> None:
                pass

        ctx = _RenderContextStub.__new__(_RenderContextStub)
        ctx._transfer_ordinal_counters = {}
        ctx._transfer_probe_depth = 0
        assert ctx._next_transfer_id("Foo") == f"{generate_id('Foo')}#0"
        counters_before = dict(ctx._transfer_ordinal_counters)
        ctx._transfer_probe_depth += 1
        try:
            assert ctx._next_transfer_id("Foo") == generate_id("Foo")
            assert ctx._transfer_ordinal_counters == counters_before
        finally:
            ctx._transfer_probe_depth -= 1
        assert ctx._next_transfer_id("Foo") == f"{generate_id('Foo')}#1"

    def test_context_falls_back_to_bare_component_id(self):
        from webcompy.components._libs import Context

        ctx: Context[None] = Context(None, {}, "MyComp", lambda: "", lambda: {}, lambda t: None, lambda k, a: None)
        assert ctx._transfer_id == generate_id("MyComp")

    def test_context_uses_explicit_transfer_id(self):
        from webcompy.components._libs import Context

        ctx: Context[None] = Context(
            None, {}, "MyComp", lambda: "", lambda: {}, lambda t: None, lambda k, a: None, transfer_id="tid-1"
        )
        assert ctx._transfer_id == "tid-1"

    def test_component_fallback_to_bare_id_without_app_context(self):
        @define_component()
        def StandaloneComp(context: ComponentContext[None]):
            return html.DIV({}, "x")

        with TestRenderer.render(StandaloneComp) as result:
            instance = result._instance
            assert instance._property["transfer_id"] == generate_id("StandaloneComp")
            assert instance._property["component_id"] == generate_id("StandaloneComp")


class TestMultiInstanceTransfer:
    def test_two_instances_collect_and_restore_independently(self):
        leaf_id = generate_id("MultiLeaf")

        @define_component()
        def MultiLeaf(context: ComponentContext[None]):
            value = use_state("value", lambda: 0)
            return html.DIV({}, f"leaf:{value.value}")

        @define_component()
        def MultiRoot(context: ComponentContext[None]):
            return html.DIV({}, MultiLeaf(None), MultiLeaf(None))

        payload = {
            f"{leaf_id}#0": {"value": 11},
            f"{leaf_id}#1": {"value": 22},
        }
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        fake_app = _FakeAppCtx(closed=False)
        app_token = _active_app_context.set(fake_app)
        try:
            with TestRenderer.render(MultiRoot, parent_scope=scope) as result:
                rendered = result.to_html()
                assert "leaf:11" in rendered
                assert "leaf:22" in rendered

                class _FakeRoot:
                    def __init__(self, children: list) -> None:
                        self._children = children

                collected = collect_transfer_data(_FakeRoot([result._instance]))
                signals = collected.signals
                assert set(signals.keys()) == {f"{leaf_id}#0", f"{leaf_id}#1"}
                assert signals[f"{leaf_id}#0"]["value"] == 11
                assert signals[f"{leaf_id}#1"]["value"] == 22

                leaves = [c for c in result._instance._children[0]._children]
                assert leaves[0]._property["component_id"] == leaf_id
                assert leaves[0]._property["transfer_id"] == f"{leaf_id}#0"
                assert leaves[1]._property["transfer_id"] == f"{leaf_id}#1"
        finally:
            _active_app_context.reset(app_token)

    def test_transfer_id_used_by_use_state_lookup(self):
        state = _make_state(transfer_id="tid-explicit")
        payload = {"tid-explicit": {"k": 7}, generate_id("TestComp"): {"k": 99}}
        scope = DIScope()
        scope.provide(HYDRATION_SIGNAL_DATA_KEY, payload)
        token = _active_di_scope.set(scope)
        try:
            with component_context(state):
                s = use_state("k", lambda: 0)
            assert s.value == 7
        finally:
            _active_di_scope.reset(token)


@pytest.mark.parametrize("closed", [True, False])
def test_payload_close_flag_isolation_between_apps(closed: bool):
    other = _FakeAppCtx(closed=closed)
    token = _active_app_context.set(other)
    try:
        assert _is_hydration_payload_open() is (not closed)
    finally:
        _active_app_context.reset(token)


class TestResolveActiveRenderContext:
    def test_returns_app_context_when_set(self):
        from contextvars import ContextVar

        from webcompy.app._root_component import _resolve_active_render_context

        app_ctx = object()
        app = type("_App", (), {"_render_context_cv": ContextVar("_rt_cv", default=None)})()
        token = _active_app_context.set(app_ctx)
        try:
            assert _resolve_active_render_context(app) is app_ctx
        finally:
            _active_app_context.reset(token)

    def test_falls_back_to_app_context_var(self):
        from contextvars import ContextVar

        from webcompy.app._root_component import _resolve_active_render_context

        cv: ContextVar = ContextVar("_rt_cv", default=None)
        app_ctx = object()
        app = type("_App", (), {"_render_context_cv": cv})()
        cv.set(app_ctx)
        try:
            assert _resolve_active_render_context(app) is app_ctx
        finally:
            cv.set(None)

    def test_falls_back_to_app_instance_global(self):
        from contextvars import ContextVar

        from webcompy.app._root_component import _resolve_active_render_context

        app_ctx = object()
        app = type("_App", (), {"_render_context_cv": ContextVar("_rt_cv", default=None)})()
        _set_app_instance(app_ctx)
        try:
            assert _resolve_active_render_context(app) is app_ctx
        finally:
            _set_app_instance(None)

    def test_returns_none_when_all_channels_unset(self):
        from contextvars import ContextVar

        from webcompy.app._root_component import _resolve_active_render_context

        app = type("_App", (), {"_render_context_cv": ContextVar("_rt_cv", default=None)})()
        assert _resolve_active_render_context(app) is None


class _DummyParent:
    def __init__(self, node) -> None:
        self._node = node

    def _get_node(self):
        return self._node

    def _get_belonging_component(self):
        return ""

    def _get_belonging_components(self):
        return ()

    def _re_index_children(self, recursive):
        pass


class TestRenderClosesPayloadViaFallback:
    @pytest.mark.asyncio
    async def test_finally_closes_payload_when_contextvars_lost(self):
        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing import create_test_app

        @define_component()
        def CloseFallbackRoot(context: ComponentContext[None]):
            return html.DIV({}, "hello")

        app = create_test_app(root_component=CloseFallbackRoot)
        ctx = app.create_render_context()
        assert ctx._hydration_payload_closed is False
        port = ctx.di_scope.inject(DOM_PORT_KEY)
        root_node = port.create_element("div")
        root_node.__webcompy_node__ = False
        root_node.__webcompy_prerendered_node__ = True
        ctx._root._parent = _DummyParent(root_node)  # type: ignore[misc]
        ctx._root._node_idx = 0
        ac_token = _active_app_context.set(None)
        cv_token = app._render_context_cv.set(None)
        _set_app_instance(ctx)
        try:
            await ctx._root.render()
        finally:
            _active_app_context.reset(ac_token)
            app._render_context_cv.reset(cv_token)
            _set_app_instance(None)
            ctx.dispose()
        assert ctx._hydration_payload_closed is True

    @pytest.mark.asyncio
    async def test_non_hydrating_app_closes_payload_before_loading_teardown(self, monkeypatch):
        import asyncio

        from webcompy.ports._keys import DOM_PORT_KEY
        from webcompy_testing import FakeBrowserDOMPort, create_test_app

        @define_component()
        def CloseNonhydrateRoot(context: ComponentContext[None]):
            return html.DIV({}, "hello")

        monkeypatch.setattr("webcompy.app._root_component.ENVIRONMENT", "pyscript")
        app = create_test_app(root_component=CloseNonhydrateRoot, hydrate=False)
        ctx = app.create_render_context()
        assert ctx._hydration_payload_closed is False

        dom_port = FakeBrowserDOMPort()
        mount_node = dom_port.create_element("div")
        mount_node.setAttribute("id", "webcompy-app")
        dom_port.body.appendChild(mount_node)
        loading_el = dom_port.create_element("div")
        loading_el.setAttribute("id", "webcompy-loading")
        dom_port.body.appendChild(loading_el)
        ctx.di_scope.provide(DOM_PORT_KEY, dom_port)

        closed_state_when_fade_starts: list[bool] = []
        real_sleep = asyncio.sleep

        async def _spy_sleep(seconds: float):
            closed_state_when_fade_starts.append(ctx._hydration_payload_closed)
            await real_sleep(0)

        monkeypatch.setattr(asyncio, "sleep", _spy_sleep)
        _set_app_instance(ctx)
        try:
            await ctx._root.render()
        finally:
            _set_app_instance(None)
            ctx.dispose()
        assert ctx._hydration_payload_closed is True
        assert closed_state_when_fade_starts
        assert all(closed_state_when_fade_starts)
