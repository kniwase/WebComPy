from __future__ import annotations

import asyncio
import gc
import random
from types import SimpleNamespace
from typing import Any

import pytest

import webcompy.realtime._registry as registry_mod
import webcompy.realtime._ws as ws_mod
from webcompy.components._hooks import _active_component_context, on_before_destroy
from webcompy.components._libs import Context
from webcompy.di._scope import DIScope, _active_di_scope
from webcompy.ports._keys import WEBSOCKET_PORT_KEY
from webcompy.realtime import CloseInfo, ConnectionState, WebSocketHandle, use_websocket
from webcompy.realtime._registry import _RealtimeRegistry, _ws_send
from webcompy_testing import FakeWebSocketPort


def _make_context() -> Context:
    return Context(
        props=None,
        slots={},
        component_name="WSComp",
        title_getter=lambda: "",
        meta_getter=lambda: {},
        title_setter=lambda x: None,
        meta_setter=lambda k, v: None,
    )


@pytest.fixture
def rt_env(monkeypatch):
    scope = DIScope()
    port = FakeWebSocketPort()
    scope.provide(WEBSOCKET_PORT_KEY, port)
    monkeypatch.setattr(ws_mod, "_get_app_di_scope", lambda: scope)
    token = _active_di_scope.set(scope)
    yield SimpleNamespace(scope=scope, port=port)
    _active_di_scope.reset(token)


async def _collect(handle: Any, limit: int | None = None) -> list[str]:
    out: list[str] = []
    async for item in handle:
        out.append(item)
        if limit is not None and len(out) >= limit:
            break
    return out


class TestHandleContract:
    @pytest.mark.asyncio
    async def test_iteration_yields_messages_in_order_including_duplicates(self, rt_env) -> None:
        ws = use_websocket("/ws")
        rt_env.port.emit_message("/ws", "pong")
        rt_env.port.emit_message("/ws", "pong")
        got = await _collect(ws, limit=2)
        assert got == ["pong", "pong"]

    @pytest.mark.asyncio
    async def test_send_while_open_sends_exactly_one_frame(self, rt_env) -> None:
        ws = use_websocket("/ws")
        rt_env.port.emit_open("/ws")
        ws.send("hello")
        assert rt_env.port.sent_frames("/ws") == ["hello"]

    @pytest.mark.asyncio
    async def test_binary_frame_ignored_with_warning(self, rt_env) -> None:
        ws = use_websocket("/ws")
        with pytest.warns(UserWarning, match="binary"):
            rt_env.port.emit_binary("/ws")
        rt_env.port.emit_message("/ws", "text")
        got = await _collect(ws, limit=1)
        assert got == ["text"]

    def test_importable_from_webcompy_and_realtime(self) -> None:
        from webcompy import CloseInfo as root_close_info
        from webcompy import use_websocket as root_use_websocket
        from webcompy.realtime import CloseInfo as realtime_close_info
        from webcompy.realtime import use_websocket as realtime_use_websocket

        assert root_use_websocket is realtime_use_websocket
        assert root_close_info is realtime_close_info
        assert WebSocketHandle is not None

    @pytest.mark.asyncio
    async def test_state_transitions_connecting_open_reconnecting_closed(self, rt_env) -> None:
        ws = use_websocket("/ws", reconnect_base_delay=0.05)
        assert ws.state.value == ConnectionState.CONNECTING
        notified: list[ConnectionState] = []
        ws.state.on_after_updating(lambda v: notified.append(v))
        rt_env.port.emit_open("/ws")
        assert ws.state.value == ConnectionState.OPEN
        assert notified == [ConnectionState.OPEN]
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        assert ws.state.value == ConnectionState.RECONNECTING
        ws.close()
        assert ws.state.value == ConnectionState.CLOSED


class TestRegistrySharing:
    @pytest.mark.asyncio
    async def test_same_url_and_protocols_share_one_socket(self, rt_env) -> None:
        a = use_websocket("/ws")
        b = use_websocket("/ws")
        assert len(rt_env.port.open_calls) == 1
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_message("/ws", "m1")
        rt_env.port.emit_message("/ws", "m2")
        got_a = await _collect(a, limit=2)
        got_b = await _collect(b, limit=2)
        assert got_a == got_b == ["m1", "m2"]

    def test_different_protocols_do_not_share(self, rt_env) -> None:
        a = use_websocket("/ws")
        b = use_websocket("/ws", protocols=("graphql-ws",))
        assert len(rt_env.port.open_calls) == 2
        assert rt_env.port.open_connections == [("/ws", ()), ("/ws", ("graphql-ws",))]
        a.close()
        b.close()

    @pytest.mark.asyncio
    async def test_last_detach_closes_the_socket(self, rt_env) -> None:
        a = use_websocket("/ws")
        b = use_websocket("/ws")
        a.close()
        assert len(rt_env.port.open_connections) == 1
        b.close()
        assert rt_env.port.open_connections == []

    @pytest.mark.asyncio
    async def test_standalone_usage_warns_and_uses_private_connections(self, monkeypatch) -> None:
        scope = DIScope()
        port = FakeWebSocketPort()
        scope.provide(WEBSOCKET_PORT_KEY, port)
        monkeypatch.setattr(ws_mod, "_get_app_di_scope", lambda: None)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="no app DI scope"):
                a = use_websocket("/ws")
            with pytest.warns(UserWarning, match="no app DI scope"):
                b = use_websocket("/ws")
            assert len(port.open_calls) == 2
            port.emit_message("/ws", "m1")
            got_a = await _collect(a, limit=1)
            got_b = await _collect(b, limit=1)
            assert got_a == got_b == ["m1"]
            a.close()
            b.close()
        finally:
            _active_di_scope.reset(token)


class TestReconnect:
    @pytest.mark.asyncio
    async def test_abnormal_close_reconnects_within_jitter_bounds(self, rt_env) -> None:
        ws = use_websocket("/ws", reconnect_base_delay=0.05)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        assert ws.state.value == ConnectionState.RECONNECTING
        await asyncio.sleep(0.2)
        assert len(rt_env.port.open_calls) == 2
        rt_env.port.emit_open("/ws")
        assert ws.state.value == ConnectionState.OPEN
        rt_env.port.emit_message("/ws", "m-after")
        got = await _collect(ws, limit=1)
        assert got == ["m-after"]
        ws.close()

    @pytest.mark.asyncio
    async def test_backoff_doubles_up_to_the_cap(self, rt_env, monkeypatch) -> None:
        monkeypatch.setattr(random, "uniform", lambda a, b: 1.0)
        delays = [registry_mod._compute_reconnect_delay(n, 1.0, 30.0) for n in range(1, 8)]
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0]

    def test_jitter_factor_stays_within_bounds(self) -> None:
        for _ in range(100):
            delay = registry_mod._compute_reconnect_delay(1, 1.0, 30.0)
            assert 0.5 <= delay <= 1.0
        for _ in range(100):
            delay = registry_mod._compute_reconnect_delay(6, 1.0, 30.0)
            assert 15.0 <= delay <= 30.0

    @pytest.mark.asyncio
    async def test_state_returns_to_reconnecting_for_each_failed_attempt(self, rt_env) -> None:
        ws = use_websocket("/ws", reconnect_base_delay=0.05)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        await asyncio.sleep(0.2)
        assert ws.state.value == ConnectionState.RECONNECTING
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        assert ws.state.value == ConnectionState.RECONNECTING
        ws.close()


class TestReconnectStopConditions:
    @pytest.mark.asyncio
    async def test_clean_1000_close_is_terminal(self, rt_env) -> None:
        ws = use_websocket("/ws", reconnect_base_delay=0.05)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_close("/ws", code=1000, reason="normal", was_clean=True)
        assert ws.state.value == ConnectionState.CLOSED
        await asyncio.sleep(0.2)
        assert len(rt_env.port.open_calls) == 1
        with pytest.raises(StopAsyncIteration):
            await ws.__anext__()

    @pytest.mark.asyncio
    async def test_user_close_cancels_pending_retry(self, rt_env) -> None:
        ws = use_websocket("/ws", reconnect_base_delay=0.05)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        assert ws.state.value == ConnectionState.RECONNECTING
        ws.close()
        await asyncio.sleep(0.2)
        assert len(rt_env.port.open_calls) == 1

    @pytest.mark.asyncio
    async def test_reconnect_false_goes_terminal_after_single_failure(self, rt_env) -> None:
        ws = use_websocket("/ws", reconnect=False)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        assert ws.state.value == ConnectionState.CLOSED
        await asyncio.sleep(0.2)
        assert len(rt_env.port.open_calls) == 1

    @pytest.mark.asyncio
    async def test_max_attempts_exhausts_to_closed(self, rt_env) -> None:
        ws = use_websocket("/ws", reconnect_base_delay=0.05, reconnect_max_attempts=2)
        rt_env.port.emit_open("/ws")
        for _ in range(3):
            rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
            await asyncio.sleep(0.2)
        assert ws.state.value == ConnectionState.CLOSED
        assert len(rt_env.port.open_calls) == 3
        await asyncio.sleep(0.2)
        assert len(rt_env.port.open_calls) == 3


class TestLastClose:
    def test_last_close_is_none_before_any_close(self, rt_env) -> None:
        ws = use_websocket("/ws")
        assert ws.last_close.value is None
        ws.close()

    @pytest.mark.asyncio
    async def test_close_info_is_recorded(self, rt_env) -> None:
        ws = use_websocket("/ws")
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        assert ws.last_close.value == CloseInfo(code=1006, reason="abnormal", was_clean=False)
        ws.close()

    @pytest.mark.asyncio
    async def test_last_close_persists_across_reconnect(self, rt_env) -> None:
        ws = use_websocket("/ws", reconnect_base_delay=0.05)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        await asyncio.sleep(0.2)
        rt_env.port.emit_open("/ws")
        assert ws.state.value == ConnectionState.OPEN
        assert ws.last_close.value == CloseInfo(code=1006, reason="abnormal", was_clean=False)
        ws.close()


class TestSendPolicy:
    @pytest.mark.asyncio
    async def test_disconnected_send_warns_and_discards_by_default(self, rt_env) -> None:
        ws = use_websocket("/ws")
        with pytest.warns(UserWarning, match="not open"):
            ws.send("x")
        rt_env.port.emit_open("/ws")
        assert rt_env.port.sent_frames("/ws") == []
        ws.close()

    @pytest.mark.asyncio
    async def test_opt_in_buffer_flushes_fifo_on_open(self, rt_env) -> None:
        ws = use_websocket("/ws", buffer_while_disconnected=True)
        ws.send("a")
        ws.send("b")
        rt_env.port.emit_open("/ws")
        assert rt_env.port.sent_frames("/ws") == ["a", "b"]
        ws.close()

    @pytest.mark.asyncio
    async def test_buffer_flushes_after_reconnect(self, rt_env) -> None:
        ws = use_websocket("/ws", reconnect_base_delay=0.05, buffer_while_disconnected=True)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        ws.send("c")
        await asyncio.sleep(0.2)
        rt_env.port.emit_open("/ws")
        assert rt_env.port.sent_frames("/ws") == ["c"]
        ws.close()

    @pytest.mark.asyncio
    async def test_buffer_is_discarded_on_terminal_closed(self, rt_env) -> None:
        ws = use_websocket("/ws", buffer_while_disconnected=True)
        ws.send("a")
        rt_env.port.emit_close("/ws", code=1000, reason="normal", was_clean=True)
        assert ws.state.value == ConnectionState.CLOSED
        with pytest.warns(UserWarning, match="closed"):
            ws.send("b")
        assert rt_env.port.sent_frames("/ws") == []
        ws.close()

    @pytest.mark.asyncio
    async def test_first_subscriber_reconnect_params_win_on_shared_connection(self, rt_env) -> None:
        a = use_websocket("/ws", buffer_while_disconnected=True)
        b = use_websocket("/ws", buffer_while_disconnected=False)
        assert len(rt_env.port.open_calls) == 1
        b.send("y")
        a.send("x")
        rt_env.port.emit_open("/ws")
        assert rt_env.port.sent_frames("/ws") == ["y", "x"]
        a.close()
        b.close()


class TestNoPortFallback:
    @pytest.mark.asyncio
    async def test_scope_without_port_returns_empty_closed_handle(self, monkeypatch) -> None:
        scope = DIScope()
        monkeypatch.setattr(ws_mod, "_get_app_di_scope", lambda: scope)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="no WebSocketPort"):
                ws = use_websocket("/ws")
            assert ws.state.value == ConnectionState.CLOSED
            assert ws.last_close.value is None
            got = await _collect(ws)
            assert got == []
        finally:
            _active_di_scope.reset(token)

    @pytest.mark.asyncio
    async def test_no_scope_and_no_port_returns_empty_closed_handle(self, monkeypatch) -> None:
        monkeypatch.setattr(ws_mod, "_get_app_di_scope", lambda: None)
        with pytest.warns(UserWarning, match="no WebSocketPort"):
            ws = use_websocket("/ws")
        assert ws.state.value == ConnectionState.CLOSED
        got = await _collect(ws)
        assert got == []


class TestSsr:
    def test_ssr_returns_empty_closed_handle_with_warning(self, monkeypatch) -> None:
        from webcompy_server.ports import ServerWebSocketPort

        scope = DIScope()
        opened: list[str] = []

        class _TrackingNoop(ServerWebSocketPort):
            def open(self, url: str, **kwargs: Any) -> Any:
                opened.append(url)
                return super().open(url, **kwargs)

        scope.provide(WEBSOCKET_PORT_KEY, _TrackingNoop())
        monkeypatch.setattr(ws_mod, "_get_app_di_scope", lambda: scope)
        token = _active_di_scope.set(scope)
        try:
            with pytest.warns(UserWarning, match="outside the browser"):
                ws = use_websocket("/ws")
            assert ws.state.value == ConnectionState.CLOSED
            assert ws.last_close.value is None
            got = asyncio.run(_collect(ws))
            assert got == []
            assert opened == []
            with pytest.warns(UserWarning, match="closed"):
                ws.send("x")
        finally:
            _active_di_scope.reset(token)

    def test_ssr_render_payload_contains_no_realtime_transfer_entry(self) -> None:
        from webcompy.components import ComponentContext, define_component
        from webcompy.elements import html
        from webcompy_testing import create_test_app, render_app_html

        @define_component("ws-comp")
        def WsComp(context: ComponentContext[None]):
            ws = use_websocket("/ws")
            return html.SPAN({}, ws.state.value.name)

        app = create_test_app(root_component=WsComp)
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

        @define_component("ws-testing-page")
        def WsTestingPage(context: ComponentContext[None]):
            ws = use_websocket("/ws")
            state = use_computed(lambda: ws.state.value.name)
            return html.DIV({}, html.SPAN({"data-testid": "state"}, state))

        with pytest.warns(UserWarning, match="no app DI scope"), TestRenderer.render(WsTestingPage) as result:
            port = result.websocket_port
            assert port is not None
            assert port.open_connections == [("/ws", ())]
            el = result.find_by_attribute("data-testid", "state")
            assert el is not None and el.textContent == "CONNECTING"
            port.emit_open("/ws")
            assert el.textContent == "OPEN"
            port.emit_message("/ws", "hello")


class TestLifecycle:
    def test_component_destroy_detaches_subscription(self, rt_env) -> None:
        ctx = _make_context()
        token = _active_component_context.set(ctx)
        try:
            ws = use_websocket("/ws")
        finally:
            _active_component_context.reset(token)
        assert len(rt_env.port.open_connections) == 1
        hooks = ctx.__get_lifecyclehooks__()
        assert "on_before_destroy" in hooks
        hooks["on_before_destroy"]()
        assert rt_env.port.open_connections == []
        ws.close()

    def test_destroy_cleanup_chains_with_existing_hook(self, rt_env) -> None:
        ctx = _make_context()
        order: list[str] = []
        token = _active_component_context.set(ctx)
        try:

            @on_before_destroy
            def _user_hook() -> None:
                order.append("user")

            ws = use_websocket("/ws")
        finally:
            _active_component_context.reset(token)
        hooks = ctx.__get_lifecyclehooks__()
        hooks["on_before_destroy"]()
        assert order == ["user"]
        assert rt_env.port.open_connections == []
        ws.close()

    @pytest.mark.asyncio
    async def test_abandoned_iterator_does_not_leak_reference_count(self, rt_env) -> None:
        ws = use_websocket("/ws")
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_message("/ws", "m1")
        iterator = ws.__aiter__()
        assert (await iterator.__anext__()) == "m1"
        del iterator
        del ws
        gc.collect()
        assert rt_env.port.open_connections == []

    @pytest.mark.asyncio
    async def test_last_detach_cancels_pending_reconnect(self, rt_env) -> None:
        a = use_websocket("/ws", reconnect_base_delay=0.05)
        b = use_websocket("/ws", reconnect_base_delay=0.05)
        rt_env.port.emit_open("/ws")
        rt_env.port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False)
        a.close()
        await asyncio.sleep(0.2)
        assert len(rt_env.port.open_calls) == 2
        rt_env.port.emit_open("/ws")
        b.close()
        await asyncio.sleep(0.2)
        assert len(rt_env.port.open_calls) == 2


class TestArgumentValidation:
    def test_protocols_rejects_bare_string(self, rt_env) -> None:
        protocols: Any = "graphql-ws"
        with pytest.raises(TypeError):
            use_websocket("/ws", protocols=protocols)
        assert rt_env.port.open_calls == []

    def test_protocols_rejects_non_string_element(self, rt_env) -> None:
        protocols: Any = ("graphql-ws", 1)
        with pytest.raises(TypeError):
            use_websocket("/ws", protocols=protocols)
        assert rt_env.port.open_calls == []

    def test_protocols_rejects_empty_string_element(self, rt_env) -> None:
        with pytest.raises(TypeError):
            use_websocket("/ws", protocols=("",))
        assert rt_env.port.open_calls == []

    def test_max_queue_rejects_zero_and_negative(self, rt_env) -> None:
        with pytest.raises(ValueError):
            use_websocket("/ws", max_queue=0)
        with pytest.raises(ValueError):
            use_websocket("/ws", max_queue=-1)
        assert rt_env.port.open_calls == []

    def test_max_queue_rejects_non_int(self, rt_env) -> None:
        bad_bool: Any = True
        bad_str: Any = "5"
        with pytest.raises(TypeError):
            use_websocket("/ws", max_queue=bad_bool)
        with pytest.raises(TypeError):
            use_websocket("/ws", max_queue=bad_str)
        assert rt_env.port.open_calls == []

    def test_reconnect_delays_reject_invalid_values(self, rt_env) -> None:
        with pytest.raises(ValueError):
            use_websocket("/ws", reconnect_base_delay=0)
        with pytest.raises(ValueError):
            use_websocket("/ws", reconnect_max_delay=-1.0)
        bad_bool: Any = True
        bad_str: Any = "1"
        with pytest.raises(TypeError):
            use_websocket("/ws", reconnect_base_delay=bad_bool)
        with pytest.raises(TypeError):
            use_websocket("/ws", reconnect_max_delay=bad_str)
        assert rt_env.port.open_calls == []

    def test_reconnect_max_attempts_rejects_invalid_values(self, rt_env) -> None:
        with pytest.raises(ValueError):
            use_websocket("/ws", reconnect_max_attempts=0)
        bad_str: Any = "2"
        with pytest.raises(TypeError):
            use_websocket("/ws", reconnect_max_attempts=bad_str)
        assert rt_env.port.open_calls == []

    @pytest.mark.asyncio
    async def test_max_queue_drops_oldest(self, rt_env) -> None:
        ws = use_websocket("/ws", max_queue=2)
        for i in range(3):
            rt_env.port.emit_message("/ws", f"m{i}")
        got = await _collect(ws, limit=2)
        assert got == ["m1", "m2"]
        ws.close()

    def test_valid_arguments_are_not_rejected(self, rt_env) -> None:
        ws = use_websocket(
            "/ws",
            protocols=("a", "b"),
            max_queue=5,
            reconnect_base_delay=0.5,
            reconnect_max_delay=60.0,
            reconnect_max_attempts=3,
            buffer_while_disconnected=True,
        )
        ws.close()


class TestReviewFixes:
    @pytest.mark.asyncio
    async def test_registry_closes_connection_handle_on_remote_close(self) -> None:
        class _TrackingConnection:
            def __init__(self) -> None:
                self.close_calls = 0

            def send(self, data: str) -> None:
                pass

            def close(self) -> None:
                self.close_calls += 1

        opened: list[_TrackingConnection] = []
        captured: dict[str, Any] = {}

        def _open_fn(**callbacks: Any) -> Any:
            captured.update(callbacks)
            conn = _TrackingConnection()
            opened.append(conn)
            return conn

        registry = _RealtimeRegistry()
        registry.subscribe_ws(
            "ws",
            ("/ws", ()),
            max_queue=None,
            on_state=lambda _v: None,
            on_close_info=lambda _v: None,
            open_fn=_open_fn,
            reconnect=False,
            base_delay=1.0,
            max_delay=1.0,
            max_attempts=None,
            buffer_while_disconnected=False,
        )
        captured["on_close"](1006, "abnormal", False)
        assert opened[0].close_calls == 1
        registry.dispose()

    @pytest.mark.asyncio
    async def test_send_from_close_info_callback_does_not_break_reconnect(self) -> None:
        class _StrictConnection:
            def __init__(self) -> None:
                self.closed = False
                self.sent: list[str] = []

            def send(self, data: str) -> None:
                if self.closed:
                    raise RuntimeError("send on a closed connection")
                self.sent.append(data)

            def close(self) -> None:
                self.closed = True

        opened: list[_StrictConnection] = []
        captured: dict[str, Any] = {}

        def _open_fn(**callbacks: Any) -> Any:
            captured.update(callbacks)
            conn = _StrictConnection()
            opened.append(conn)
            return conn

        registry = _RealtimeRegistry()
        holder: dict[str, Any] = {}

        def _on_close_info(_value: CloseInfo | None) -> None:
            if "conn" in holder:
                _ws_send(holder["conn"], "resync")

        _sub, conn = registry.subscribe_ws(
            "ws",
            ("/ws", ()),
            max_queue=None,
            on_state=lambda _v: None,
            on_close_info=_on_close_info,
            open_fn=_open_fn,
            reconnect=True,
            base_delay=0.05,
            max_delay=1.0,
            max_attempts=None,
            buffer_while_disconnected=False,
        )
        holder["conn"] = conn
        captured["on_open"]()
        opened[0].closed = True
        captured["on_close"](1006, "abnormal", False)
        assert conn.state == ConnectionState.RECONNECTING
        assert opened[0].sent == []
        await asyncio.sleep(0.2)
        assert len(opened) == 2
        registry.dispose()

    @pytest.mark.asyncio
    async def test_open_failure_during_retry_warns_and_terminates_when_exhausted(self) -> None:
        class _NoopConnection:
            def send(self, data: str) -> None:
                pass

            def close(self) -> None:
                pass

        calls = {"open": 0}
        captured: dict[str, Any] = {}

        def _open_fn(**callbacks: Any) -> Any:
            calls["open"] += 1
            captured.update(callbacks)
            if calls["open"] > 1:
                raise RuntimeError("open boom")
            return _NoopConnection()

        registry = _RealtimeRegistry()
        _sub, conn = registry.subscribe_ws(
            "ws",
            ("/ws", ()),
            max_queue=None,
            on_state=lambda _v: None,
            on_close_info=lambda _v: None,
            open_fn=_open_fn,
            reconnect=True,
            base_delay=0.05,
            max_delay=1.0,
            max_attempts=1,
            buffer_while_disconnected=False,
        )
        captured["on_open"]()
        captured["on_close"](1006, "abnormal", False)
        with pytest.warns(UserWarning, match="reconnection attempt failed to open"):
            await asyncio.sleep(0.2)
        assert conn.state == ConnectionState.CLOSED
        assert calls["open"] == 2
        registry.dispose()

    @pytest.mark.asyncio
    async def test_open_failure_during_retry_reschedules_when_unlimited(self) -> None:
        class _NoopConnection:
            def send(self, data: str) -> None:
                pass

            def close(self) -> None:
                pass

        calls = {"open": 0}
        captured: dict[str, Any] = {}

        def _open_fn(**callbacks: Any) -> Any:
            calls["open"] += 1
            captured.update(callbacks)
            if calls["open"] > 1:
                raise RuntimeError("open boom")
            return _NoopConnection()

        registry = _RealtimeRegistry()
        _sub, conn = registry.subscribe_ws(
            "ws",
            ("/ws", ()),
            max_queue=None,
            on_state=lambda _v: None,
            on_close_info=lambda _v: None,
            open_fn=_open_fn,
            reconnect=True,
            base_delay=0.02,
            max_delay=1.0,
            max_attempts=None,
            buffer_while_disconnected=False,
        )
        captured["on_open"]()
        captured["on_close"](1006, "abnormal", False)
        with pytest.warns(UserWarning, match="reconnection attempt failed to open"):
            await asyncio.sleep(0.3)
        assert conn.state == ConnectionState.RECONNECTING
        assert calls["open"] >= 3
        registry.dispose()
        await asyncio.sleep(0.2)
