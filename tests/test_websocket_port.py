from __future__ import annotations

from types import SimpleNamespace

import pytest

from webcompy.exception import WebComPyException
from webcompy.ports import WEBSOCKET_PORT_KEY, WebSocketPort
from webcompy_server.ports import ServerWebSocketPort
from webcompy_testing import FakeWebSocketPort


def test_websocket_port_is_importable_from_webcompy_ports() -> None:
    assert WebSocketPort is not None
    assert WEBSOCKET_PORT_KEY is not None


def test_websocket_port_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        WebSocketPort()  # type: ignore[abstract]


def test_websocket_port_module_does_not_import_component_modules() -> None:
    import inspect

    import webcompy.ports._websocket as port_module

    source = inspect.getsource(port_module)
    assert "webcompy.components" not in source


def test_browser_websocket_port_constructor_is_guarded_outside_browser() -> None:
    from webcompy.ports._browser._websocket import BrowserWebSocketPort

    with pytest.raises(WebComPyException):
        BrowserWebSocketPort()


def test_server_websocket_port_invokes_no_callbacks_and_returns_noop_connection() -> None:
    port = ServerWebSocketPort()
    calls: list[str] = []

    def _mark(name: str):
        def _cb(*args: object) -> None:
            calls.append(name)

        return _cb

    conn = port.open(
        "/ws",
        protocols=("graphql-ws",),
        on_open=_mark("open"),
        on_message=_mark("message"),
        on_binary=_mark("binary"),
        on_error=_mark("error"),
        on_close=_mark("close"),
    )
    conn.send("hello")
    conn.close()
    conn.close()
    assert calls == []


def test_fake_websocket_port_scripted_delivery_matches_url_and_protocols() -> None:
    port = FakeWebSocketPort()
    received: list[str] = []
    binary: list[bool] = []
    closed: list[tuple[int, str, bool]] = []
    conn = port.open(
        "/ws",
        protocols=("graphql-ws",),
        on_message=lambda t: received.append(t),
        on_binary=lambda: binary.append(True),
        on_close=lambda c, r, w: closed.append((c, r, w)),
    )
    port.emit_message("/ws", "hello", protocols=("graphql-ws",))
    port.emit_message("/ws/other", "other")
    port.emit_binary("/ws", protocols=("graphql-ws",))
    port.emit_close("/ws", code=1006, reason="abnormal", was_clean=False, protocols=("graphql-ws",))
    conn.close()
    assert received == ["hello"]
    assert binary == [True]
    assert closed == [(1006, "abnormal", False)]


def test_fake_websocket_port_sent_frames_are_recorded_per_connection() -> None:
    port = FakeWebSocketPort()
    conn_a = port.open("/ws", protocols=("graphql-ws",), on_message=lambda t: None)
    port.open("/ws", on_message=lambda t: None)
    conn_a.send("ping")
    assert port.sent_frames("/ws", protocols=("graphql-ws",)) == ["ping"]
    assert port.sent_frames("/ws") == ["ping"]


def test_fake_websocket_port_cleanup_is_idempotent_and_removes_only_its_own_registration() -> None:
    port = FakeWebSocketPort()
    first: list[str] = []
    second: list[str] = []
    conn_a = port.open("/ws", on_message=lambda t: first.append(t))
    port.open("/ws", on_message=lambda t: second.append(t))
    conn_a.close()
    conn_a.close()
    port.emit_message("/ws", "ping")
    assert first == []
    assert second == ["ping"]


def test_fake_websocket_port_registrations_are_instance_local() -> None:
    port_a = FakeWebSocketPort()
    port_b = FakeWebSocketPort()
    received: list[str] = []
    port_a.open("/ws", on_message=lambda t: received.append(t))
    port_b.emit_message("/ws", "ping")
    assert received == []
    assert port_a.open_connections == [("/ws", ())]
    assert port_b.open_connections == []


def test_fake_websocket_port_normalizes_protocols_in_keying() -> None:
    port = FakeWebSocketPort()
    port.open("/ws", protocols=("b", "a"), on_message=lambda t: None)
    port.open("/ws", protocols=("a", "b"), on_message=lambda t: None)
    assert len(port.open_calls) == 2
    assert port.open_connections == [("/ws", ("a", "b")), ("/ws", ("a", "b"))]


def test_browser_websocket_port_closes_native_socket_when_listener_setup_fails(monkeypatch) -> None:
    from webcompy.ports._browser import _websocket as ws_mod
    from webcompy.ports._browser._websocket import BrowserWebSocketPort

    class _FakeProxy:
        def __init__(self) -> None:
            self.destroyed = False

        def destroy(self) -> None:
            self.destroyed = True

    class _FakeFfi:
        def __init__(self) -> None:
            self.calls = 0
            self.proxies: list[_FakeProxy] = []

        def create_proxy(self, func: object) -> object:
            self.calls += 1
            proxy = _FakeProxy()
            self.proxies.append(proxy)
            if self.calls == 2:
                raise RuntimeError("proxy boom")
            return proxy

        def to_js(self, value: object, **kwargs: object) -> object:
            return value

    class _FakeWebSocket:
        def __init__(self) -> None:
            self.closed = False
            self.listeners: list[str] = []

        def addEventListener(self, event: str, handler: object) -> None:
            self.listeners.append(event)

        def close(self) -> None:
            self.closed = True

    ws = _FakeWebSocket()
    ffi = _FakeFfi()
    fake_browser = SimpleNamespace(
        pyscript=SimpleNamespace(ffi=ffi),
        window=SimpleNamespace(WebSocket=type("WS", (), {"new": staticmethod(lambda *args: ws)})),
    )
    monkeypatch.setattr(ws_mod, "ENVIRONMENT", "pyscript")
    monkeypatch.setattr(ws_mod, "_raw_browser", fake_browser)

    port = BrowserWebSocketPort()
    with pytest.raises(RuntimeError, match="proxy boom"):
        port.open(
            "/ws",
            protocols=("graphql-ws",),
            on_open=lambda: None,
            on_message=lambda t: None,
            on_binary=lambda: None,
            on_error=lambda: None,
            on_close=lambda c, r, w: None,
        )
    assert ws.closed is True
    assert ffi.proxies[0].destroyed is True
    assert len(ffi.proxies) == 2
    assert ws.listeners == []


def test_browser_websocket_connection_close_removes_listeners_and_destroys_proxies(monkeypatch) -> None:
    from webcompy.ports._browser import _websocket as ws_mod
    from webcompy.ports._browser._websocket import BrowserWebSocketPort

    class _FakeProxy:
        def __init__(self, name: str) -> None:
            self.name = name
            self.destroyed = False

        def destroy(self) -> None:
            self.destroyed = True

    class _FakeFfi:
        def __init__(self) -> None:
            self.proxies: list[_FakeProxy] = []

        def create_proxy(self, func: object) -> object:
            proxy = _FakeProxy(f"proxy-{len(self.proxies)}")
            self.proxies.append(proxy)
            return proxy

        def to_js(self, value: object, **kwargs: object) -> object:
            return value

    class _FakeWebSocket:
        def __init__(self) -> None:
            self.closed = False
            self.removed: list[tuple[str, object]] = []
            self.sent: list[str] = []

        def addEventListener(self, event: str, handler: object) -> None:
            pass

        def removeEventListener(self, event: str, handler: object) -> None:
            self.removed.append((event, handler))

        def send(self, data: str) -> None:
            self.sent.append(data)

        def close(self) -> None:
            self.closed = True

    ws = _FakeWebSocket()
    ffi = _FakeFfi()
    fake_browser = SimpleNamespace(
        pyscript=SimpleNamespace(ffi=ffi),
        window=SimpleNamespace(WebSocket=type("WS", (), {"new": staticmethod(lambda *args: ws)})),
    )
    monkeypatch.setattr(ws_mod, "ENVIRONMENT", "pyscript")
    monkeypatch.setattr(ws_mod, "_raw_browser", fake_browser)

    port = BrowserWebSocketPort()
    conn = port.open(
        "/ws",
        on_open=lambda: None,
        on_message=lambda t: None,
        on_binary=lambda: None,
        on_error=lambda: None,
        on_close=lambda c, r, w: None,
    )
    conn.send("hello")
    assert ws.sent == ["hello"]
    conn.close()
    conn.close()
    assert ws.closed is True
    assert len(ws.removed) == 4
    assert all(proxy.destroyed for proxy in ffi.proxies)
