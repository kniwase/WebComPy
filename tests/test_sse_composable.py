from __future__ import annotations

import asyncio
import gc
from types import SimpleNamespace
from typing import Any

import pytest

import webcompy.realtime._sse as sse_mod
from webcompy.components._hooks import _active_component_context, on_before_destroy
from webcompy.components._libs import Context
from webcompy.di._keys import _REALTIME_CONNECTION_REGISTRY_KEY
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._keys import EVENT_SOURCE_PORT_KEY
from webcompy.realtime import ConnectionState, EventSourceHandle, SSEvent, use_event_source
from webcompy_testing import FakeEventSourcePort


def _make_context() -> Context:
    return Context(
        props=None,
        slots={},
        component_name="SSEComp",
        title_getter=lambda: "",
        meta_getter=lambda: {},
        title_setter=lambda x: None,
        meta_setter=lambda k, v: None,
    )


@pytest.fixture
def rt_env(monkeypatch):
    scope = DIScope()
    port = FakeEventSourcePort()
    scope.provide(EVENT_SOURCE_PORT_KEY, port)
    monkeypatch.setattr(sse_mod, "_get_app_di_scope", lambda: scope)
    token = _active_di_scope.set(scope)
    yield SimpleNamespace(scope=scope, port=port)
    _active_di_scope.reset(token)


async def _collect(handle: Any, limit: int | None = None) -> list[SSEvent]:
    out: list[SSEvent] = []
    async for ev in handle:
        out.append(ev)
        if limit is not None and len(out) >= limit:
            break
    return out


class TestHandleContract:
    @pytest.mark.asyncio
    async def test_iteration_yields_events_in_order_including_duplicates(self, rt_env) -> None:
        es = use_event_source("/events")
        rt_env.port.emit_event("/events", "message", "ping", "1")
        rt_env.port.emit_event("/events", "message", "ping", "2")
        got = await _collect(es, limit=2)
        assert got == [
            SSEvent(event="message", data="ping", last_event_id="1"),
            SSEvent(event="message", data="ping", last_event_id="2"),
        ]

    @pytest.mark.asyncio
    async def test_state_transitions_connecting_open_closed(self, rt_env) -> None:
        es = use_event_source("/events")
        assert es.state.value == ConnectionState.CONNECTING
        notified: list[ConnectionState] = []
        es.state.on_after_updating(lambda v: notified.append(v))
        rt_env.port.emit_open("/events")
        assert es.state.value == ConnectionState.OPEN
        assert notified == [ConnectionState.OPEN]
        es.close()
        assert es.state.value == ConnectionState.CLOSED

    def test_importable_from_webcompy_and_realtime(self) -> None:
        from webcompy import use_event_source as root_use_event_source
        from webcompy.realtime import use_event_source as realtime_use_event_source

        assert root_use_event_source is realtime_use_event_source
        assert EventSourceHandle is not None


class TestEventFiltering:
    @pytest.mark.asyncio
    async def test_default_delivers_only_message_events(self, rt_env) -> None:
        es = use_event_source("/events")
        rt_env.port.emit_event("/events", "status", "s1", "9")
        rt_env.port.emit_event("/events", "message", "hello", "7")
        got = await _collect(es, limit=1)
        assert got == [SSEvent(event="message", data="hello", last_event_id="7")]

    @pytest.mark.asyncio
    async def test_named_event_types_are_selectable(self, rt_env) -> None:
        es = use_event_source("/events", events=("status",))
        rt_env.port.emit_event("/events", "message", "hello", "7")
        rt_env.port.emit_event("/events", "status", "s1", "9")
        got = await _collect(es, limit=1)
        assert got == [SSEvent(event="status", data="s1", last_event_id="9")]


class TestRegistrySharing:
    @pytest.mark.asyncio
    async def test_same_url_subscribers_share_one_connection(self, rt_env) -> None:
        a = use_event_source("/events")
        b = use_event_source("/events")
        assert len(rt_env.port.open_calls) == 1
        rt_env.port.emit_open("/events")
        rt_env.port.emit_event("/events", "message", "m1", "1")
        rt_env.port.emit_event("/events", "message", "m2", "2")
        got_a = await _collect(a, limit=2)
        got_b = await _collect(b, limit=2)
        assert (
            got_a
            == got_b
            == [
                SSEvent(event="message", data="m1", last_event_id="1"),
                SSEvent(event="message", data="m2", last_event_id="2"),
            ]
        )

    @pytest.mark.asyncio
    async def test_slow_consumer_does_not_block_other(self, rt_env) -> None:
        a = use_event_source("/events")
        b = use_event_source("/events")
        for i in range(100):
            rt_env.port.emit_event("/events", "message", f"m{i}", str(i))
        got_b = await _collect(b, limit=5)
        assert len(got_b) == 5
        got_a = await _collect(a, limit=100)
        assert len(got_a) == 100
        assert got_a[0] == SSEvent(event="message", data="m0", last_event_id="0")

    @pytest.mark.asyncio
    async def test_last_detach_closes_connection(self, rt_env) -> None:
        a = use_event_source("/events")
        b = use_event_source("/events")
        a.close()
        assert len(rt_env.port.open_connections) == 1
        b.close()
        assert rt_env.port.open_connections == []

    def test_different_urls_open_separate_connections(self, rt_env) -> None:
        use_event_source("/a")
        use_event_source("/b")
        assert len(rt_env.port.open_calls) == 2

    def test_registry_dispose_closes_all_open_connections(self, rt_env) -> None:
        a = use_event_source("/events")
        b = use_event_source("/other")
        assert len(rt_env.port.open_connections) == 2
        registry = rt_env.scope.inject(_REALTIME_CONNECTION_REGISTRY_KEY)
        registry.dispose()
        assert rt_env.port.open_connections == []
        assert a.state.value == ConnectionState.CLOSED
        assert b.state.value == ConnectionState.CLOSED

    @pytest.mark.asyncio
    async def test_registry_dispose_ends_iterators(self, rt_env) -> None:
        a = use_event_source("/events")
        registry = rt_env.scope.inject(_REALTIME_CONNECTION_REGISTRY_KEY)
        registry.dispose()
        with pytest.raises(StopAsyncIteration):
            await a.__anext__()


class TestQueuePolicy:
    @pytest.mark.asyncio
    async def test_unbounded_default_preserves_all_events(self, rt_env) -> None:
        es = use_event_source("/events")
        for i in range(100):
            rt_env.port.emit_event("/events", "message", f"m{i}", str(i))
        got = await _collect(es, limit=100)
        assert len(got) == 100
        assert got[0] == SSEvent(event="message", data="m0", last_event_id="0")

    @pytest.mark.asyncio
    async def test_max_queue_drops_oldest(self, rt_env) -> None:
        es = use_event_source("/events", max_queue=2)
        for i in range(3):
            rt_env.port.emit_event("/events", "message", f"m{i}", str(i))
        got = await _collect(es, limit=2)
        assert [ev.data for ev in got] == ["m1", "m2"]

    @pytest.mark.asyncio
    async def test_capped_subscriber_does_not_affect_others(self, rt_env) -> None:
        capped = use_event_source("/events", max_queue=2)
        uncapped = use_event_source("/events")
        for i in range(5):
            rt_env.port.emit_event("/events", "message", f"m{i}", str(i))
        got_capped = await _collect(capped, limit=2)
        got_uncapped = await _collect(uncapped, limit=5)
        assert [ev.data for ev in got_capped] == ["m3", "m4"]
        assert [ev.data for ev in got_uncapped] == ["m0", "m1", "m2", "m3", "m4"]


class TestCloseSemantics:
    @pytest.mark.asyncio
    async def test_close_detaches_only_self(self, rt_env) -> None:
        a = use_event_source("/events")
        b = use_event_source("/events")
        a.close()
        with pytest.raises(StopAsyncIteration):
            await a.__anext__()
        rt_env.port.emit_event("/events", "message", "m1", "1")
        got_b = await _collect(b, limit=1)
        assert got_b == [SSEvent(event="message", data="m1", last_event_id="1")]
        assert len(rt_env.port.open_connections) == 1
        b.close()
        assert rt_env.port.open_connections == []

    def test_close_is_idempotent(self, rt_env) -> None:
        es = use_event_source("/events")
        es.close()
        es.close()


class TestNoScopeFallback:
    @pytest.mark.asyncio
    async def test_standalone_usage_warns_and_uses_private_connections(self, monkeypatch) -> None:
        scope = DIScope()
        port = FakeEventSourcePort()
        scope.provide(EVENT_SOURCE_PORT_KEY, port)
        monkeypatch.setattr(sse_mod, "_get_app_di_scope", lambda: None)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="no app DI scope"):
                a = use_event_source("/events")
            with pytest.warns(UserWarning, match="no app DI scope"):
                b = use_event_source("/events")
            assert len(port.open_calls) == 2
            port.emit_event("/events", "message", "m1", "1")
            got_a = await _collect(a, limit=1)
            got_b = await _collect(b, limit=1)
            assert got_a == got_b == [SSEvent(event="message", data="m1", last_event_id="1")]
            a.close()
            b.close()
        finally:
            _active_di_scope.reset(token)


class TestNoPortFallback:
    @pytest.mark.asyncio
    async def test_scope_without_port_returns_empty_closed_handle(self, monkeypatch) -> None:
        scope = DIScope()
        monkeypatch.setattr(sse_mod, "_get_app_di_scope", lambda: scope)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="no EventSourcePort"):
                es = use_event_source("/events")
            assert es.state.value == ConnectionState.CLOSED
            got = await _collect(es)
            assert got == []
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_no_scope_and_no_port_returns_empty_closed_handle(self, monkeypatch) -> None:
        monkeypatch.setattr(sse_mod, "_get_app_di_scope", lambda: None)
        with pytest.warns(UserWarning, match="no EventSourcePort"):
            es = use_event_source("/events")
        assert es.state.value == ConnectionState.CLOSED
        got = await _collect(es)
        assert got == []


class TestSsr:
    def test_ssr_returns_empty_closed_handle_with_warning(self, monkeypatch) -> None:
        from webcompy_server.ports import ServerEventSourcePort

        scope = DIScope()
        opened: list[str] = []

        class _TrackingNoop(ServerEventSourcePort):
            def open(self, url: str, **kwargs: Any) -> Any:
                opened.append(url)
                return super().open(url, **kwargs)

        scope.provide(EVENT_SOURCE_PORT_KEY, _TrackingNoop())
        monkeypatch.setattr(sse_mod, "_get_app_di_scope", lambda: scope)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="outside the browser"):
                es = use_event_source("/events")
            assert es.state.value == ConnectionState.CLOSED
            got = asyncio.run(_collect(es))
            assert got == []
            assert opened == []
        finally:
            _active_di_scope.reset(token)

    def test_ssr_render_payload_contains_no_realtime_transfer_entry(self) -> None:
        from webcompy.components import ComponentContext, define_component
        from webcompy.elements import html
        from webcompy_testing import create_test_app, render_app_html

        @define_component("sse-comp")
        def SseComp(context: ComponentContext[None]):
            es = use_event_source("/events")
            return html.SPAN({}, es.state.value.name)

        app = create_test_app(root_component=SseComp)
        with pytest.warns(UserWarning, match="outside the browser"):
            html_out = render_app_html(
                app,
                app_package_name="test_pkg",
                dev_mode=False,
                prerender=True,
                wheel_filename="test_pkg-0+sha.abcdef12-py3-none-any.whl",
            )
        assert "ConnectionState" not in html_out
        assert "webcompy-realtime" not in html_out


class TestTestingRenderPath:
    def test_test_renderer_uses_provisioned_fake_port(self) -> None:
        from webcompy.components import ComponentContext, define_component
        from webcompy.elements import html
        from webcompy.signal import use_computed
        from webcompy_testing import TestRenderer

        @define_component("sse-testing-page")
        def SseTestingPage(context: ComponentContext[None]):
            es = use_event_source("/events")
            state = use_computed(lambda: es.state.value.name)
            return html.DIV({}, html.SPAN({"data-testid": "state"}, state))

        with pytest.warns(UserWarning, match="no app DI scope"), TestRenderer.render(SseTestingPage) as result:
            port = result.event_source_port
            assert port is not None
            assert port.open_connections == [("/events", ("message",))]
            el = result.find_by_attribute("data-testid", "state")
            assert el is not None and el.textContent == "CONNECTING"
            port.emit_open("/events")
            assert el.textContent == "OPEN"
            port.emit_event("/events", "message", "hello", "1")


class TestLifecycle:
    def test_component_destroy_detaches_subscription(self, rt_env) -> None:
        ctx = _make_context()
        token = _active_component_context.set(ctx)
        try:
            es = use_event_source("/events")
        finally:
            _active_component_context.reset(token)
        assert len(rt_env.port.open_connections) == 1
        hooks = ctx.__get_lifecyclehooks__()
        assert "on_before_destroy" in hooks
        hooks["on_before_destroy"]()
        assert rt_env.port.open_connections == []
        es.close()

    def test_destroy_cleanup_chains_with_existing_hook(self, rt_env) -> None:
        ctx = _make_context()
        order: list[str] = []
        token = _active_component_context.set(ctx)
        try:

            @on_before_destroy
            def _user_hook() -> None:
                order.append("user")

            es = use_event_source("/events")
        finally:
            _active_component_context.reset(token)
        hooks = ctx.__get_lifecyclehooks__()
        hooks["on_before_destroy"]()
        assert order == ["user"]
        assert rt_env.port.open_connections == []
        es.close()

    @pytest.mark.asyncio
    async def test_abandoned_iterator_does_not_leak_reference_count(self, rt_env) -> None:
        es = use_event_source("/events")
        rt_env.port.emit_open("/events")
        rt_env.port.emit_event("/events", "message", "m1", "1")
        iterator = es.__aiter__()
        assert (await iterator.__anext__()) == SSEvent(event="message", data="m1", last_event_id="1")
        del iterator
        del es
        gc.collect()
        assert rt_env.port.open_connections == []


class TestUnionReopen:
    @pytest.mark.asyncio
    async def test_later_subscriber_with_new_event_type_reopens_with_union(self, rt_env) -> None:
        a = use_event_source("/events", events=("message",))
        assert len(rt_env.port.open_calls) == 1
        rt_env.port.emit_open("/events")
        b = use_event_source("/events", events=("status",))
        assert len(rt_env.port.open_calls) == 2
        assert a.state.value == ConnectionState.CONNECTING
        rt_env.port.emit_open("/events")
        assert a.state.value == ConnectionState.OPEN
        assert b.state.value == ConnectionState.OPEN
        rt_env.port.emit_event("/events", "status", "s1", "10")
        rt_env.port.emit_event("/events", "message", "m1", "11")
        got_a = await _collect(a, limit=1)
        got_b = await _collect(b, limit=1)
        assert got_a == [SSEvent(event="message", data="m1", last_event_id="11")]
        assert got_b == [SSEvent(event="status", data="s1", last_event_id="10")]
        a.close()
        b.close()
        assert rt_env.port.open_connections == []

    @pytest.mark.asyncio
    async def test_late_close_from_superseded_connection_does_not_terminate(self, rt_env) -> None:
        a = use_event_source("/events", events=("message",))
        stale_reg = rt_env.port._registrations[0]
        rt_env.port.emit_open("/events")
        b = use_event_source("/events", events=("status",))
        rt_env.port.emit_open("/events")
        assert a.state.value == ConnectionState.OPEN
        assert b.state.value == ConnectionState.OPEN
        stale_reg.on_close()
        assert a.state.value == ConnectionState.OPEN
        assert b.state.value == ConnectionState.OPEN
        rt_env.port.emit_event("/events", "status", "s1", "2")
        rt_env.port.emit_event("/events", "message", "m1", "1")
        got_a = await _collect(a, limit=1)
        got_b = await _collect(b, limit=1)
        assert got_a == [SSEvent(event="message", data="m1", last_event_id="1")]
        assert got_b == [SSEvent(event="status", data="s1", last_event_id="2")]
        a.close()
        b.close()

    @pytest.mark.asyncio
    async def test_late_error_from_superseded_connection_does_not_flicker_state(self, rt_env) -> None:
        a = use_event_source("/events", events=("message",))
        stale_reg = rt_env.port._registrations[0]
        rt_env.port.emit_open("/events")
        b = use_event_source("/events", events=("status",))
        rt_env.port.emit_open("/events")
        assert a.state.value == ConnectionState.OPEN
        stale_reg.on_error()
        assert a.state.value == ConnectionState.OPEN
        a.close()
        b.close()


class TestPortOpenFailure:
    @pytest.mark.asyncio
    async def test_failed_open_does_not_leave_zombie_connection(self, rt_env) -> None:
        class _FlakyPort(FakeEventSourcePort):
            def __init__(self) -> None:
                super().__init__()
                self.fail_next = True

            def open(self, url: str, **kwargs: Any) -> Any:
                if self.fail_next:
                    self.fail_next = False
                    raise RuntimeError("boom")
                return super().open(url, **kwargs)

        flaky = _FlakyPort()
        rt_env.scope.provide(EVENT_SOURCE_PORT_KEY, flaky)
        with pytest.raises(RuntimeError, match="boom"):
            use_event_source("/events")
        es = use_event_source("/events")
        assert len(flaky.open_calls) == 1
        flaky.emit_event("/events", "message", "m1", "1")
        got = await _collect(es, limit=1)
        assert got == [SSEvent(event="message", data="m1", last_event_id="1")]

    @pytest.mark.asyncio
    async def test_failed_reopen_ends_existing_subscribers(self, rt_env) -> None:
        a = use_event_source("/events", events=("message",))
        rt_env.port.emit_open("/events")
        assert a.state.value == ConnectionState.OPEN

        class _FailingPort(FakeEventSourcePort):
            def open(self, url: str, **kwargs: Any) -> Any:
                raise RuntimeError("boom")

        rt_env.scope.provide(EVENT_SOURCE_PORT_KEY, _FailingPort())
        with pytest.raises(RuntimeError, match="boom"):
            use_event_source("/events", events=("status",))
        assert a.state.value == ConnectionState.CLOSED
        with pytest.raises(StopAsyncIteration):
            await a.__anext__()

        rt_env.scope.provide(EVENT_SOURCE_PORT_KEY, rt_env.port)
        b = use_event_source("/events", events=("message",))
        assert len(rt_env.port.open_calls) == 2
        rt_env.port.emit_event("/events", "message", "m2", "2")
        got_b = await _collect(b, limit=1)
        assert got_b == [SSEvent(event="message", data="m2", last_event_id="2")]


class TestArgumentValidation:
    def test_events_rejects_bare_string(self, rt_env) -> None:
        events: Any = "message"
        with pytest.raises(TypeError):
            use_event_source("/events", events=events)
        assert rt_env.port._registrations == []

    def test_events_rejects_empty(self, rt_env) -> None:
        with pytest.raises(ValueError):
            use_event_source("/events", events=())
        assert rt_env.port._registrations == []

    def test_events_rejects_non_string_element(self, rt_env) -> None:
        events: Any = ("message", 1)
        with pytest.raises(TypeError):
            use_event_source("/events", events=events)
        assert rt_env.port._registrations == []

    def test_events_rejects_empty_string_element(self, rt_env) -> None:
        with pytest.raises(TypeError):
            use_event_source("/events", events=("",))
        assert rt_env.port._registrations == []

    def test_max_queue_rejects_zero(self, rt_env) -> None:
        with pytest.raises(ValueError):
            use_event_source("/events", max_queue=0)
        assert rt_env.port._registrations == []

    def test_max_queue_rejects_negative(self, rt_env) -> None:
        with pytest.raises(ValueError):
            use_event_source("/events", max_queue=-1)
        assert rt_env.port._registrations == []

    def test_max_queue_rejects_non_int(self, rt_env) -> None:
        bad_bool: Any = True
        bad_str: Any = "5"
        with pytest.raises(TypeError):
            use_event_source("/events", max_queue=bad_bool)
        with pytest.raises(TypeError):
            use_event_source("/events", max_queue=bad_str)
        assert rt_env.port._registrations == []

    @pytest.mark.asyncio
    async def test_max_queue_one_keeps_newest_event(self, rt_env) -> None:
        es = use_event_source("/events", max_queue=1)
        for i in range(3):
            rt_env.port.emit_event("/events", "message", f"m{i}", str(i))
        got = await _collect(es, limit=1)
        assert [ev.data for ev in got] == ["m2"]

    def test_valid_arguments_are_not_rejected(self, rt_env) -> None:
        es = use_event_source("/events", events=("message",), max_queue=5)
        es.close()
