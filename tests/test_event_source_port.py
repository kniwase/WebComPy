from __future__ import annotations

import pytest

from webcompy.exception import WebComPyException
from webcompy.ports import EVENT_SOURCE_PORT_KEY, EventSourcePort
from webcompy_server.ports import ServerEventSourcePort
from webcompy_testing import FakeEventSourcePort


def test_event_source_port_is_importable_from_webcompy_ports() -> None:
    assert EventSourcePort is not None
    assert EVENT_SOURCE_PORT_KEY is not None


def test_event_source_port_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        EventSourcePort()  # type: ignore[abstract]


def test_event_source_port_module_does_not_import_component_modules() -> None:
    import inspect

    import webcompy.ports._event_source as port_module

    source = inspect.getsource(port_module)
    assert "webcompy.components" not in source


def test_browser_event_source_port_constructor_is_guarded_outside_browser() -> None:
    from webcompy.ports._browser._event_source import BrowserEventSourcePort

    with pytest.raises(WebComPyException):
        BrowserEventSourcePort()


def test_server_event_source_port_invokes_no_callbacks_and_returns_noop_cleanup() -> None:
    port = ServerEventSourcePort()
    calls: list[str] = []

    def _mark(name: str):
        def _cb(*args: object) -> None:
            calls.append(name)

        return _cb

    cleanup = port.open(
        "/events",
        events=("message", "status"),
        on_open=_mark("open"),
        on_message=_mark("message"),
        on_error=_mark("error"),
        on_close=_mark("close"),
    )
    cleanup()
    cleanup()
    assert calls == []


def test_fake_event_source_port_scripted_delivery_matches_url_and_event_type() -> None:
    port = FakeEventSourcePort()
    received: list[tuple[str, str, str]] = []
    cleanup = port.open(
        "/events",
        events=("message", "status"),
        on_message=lambda t, d, i: received.append((t, d, i)),
    )
    port.emit_event("/events", "status", "s1", "8")
    port.emit_event("/events", "message", "hello", "7")
    port.emit_event("/other", "message", "other", "9")
    cleanup()
    assert received == [("status", "s1", "8"), ("message", "hello", "7")]


def test_fake_event_source_port_cleanup_is_idempotent_and_removes_only_its_own_registration() -> None:
    port = FakeEventSourcePort()
    first: list[str] = []
    second: list[str] = []
    cleanup_a = port.open("/events", events=("message",), on_message=lambda t, d, i: first.append(d))
    port.open("/events", events=("message",), on_message=lambda t, d, i: second.append(d))
    cleanup_a()
    cleanup_a()
    port.emit_event("/events", "message", "ping", "1")
    assert first == []
    assert second == ["ping"]


def test_fake_event_source_port_registrations_are_instance_local() -> None:
    port_a = FakeEventSourcePort()
    port_b = FakeEventSourcePort()
    received: list[str] = []
    port_a.open("/events", events=("message",), on_message=lambda t, d, i: received.append(d))
    port_b.emit_event("/events", "message", "ping", "1")
    assert received == []
    assert port_a.open_connections == [("/events", ("message",))]
    assert port_b.open_connections == []


def test_browser_event_source_port_closes_native_connection_when_listener_setup_fails(monkeypatch) -> None:
    from types import SimpleNamespace

    from webcompy.ports._browser import _event_source as es_mod
    from webcompy.ports._browser._event_source import BrowserEventSourcePort

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

        def is_none(self, value: object) -> bool:
            return value is None

    class _FakeEventSource:
        def __init__(self) -> None:
            self.closed = False

        def addEventListener(self, event: str, handler: object) -> None:
            pass

        def close(self) -> None:
            self.closed = True

    es = _FakeEventSource()
    ffi = _FakeFfi()
    fake_browser = SimpleNamespace(
        pyscript=SimpleNamespace(ffi=ffi),
        window=SimpleNamespace(EventSource=type("ES", (), {"new": staticmethod(lambda url: es)})),
    )
    monkeypatch.setattr(es_mod, "ENVIRONMENT", "pyscript")
    monkeypatch.setattr(es_mod, "_raw_browser", fake_browser)

    port = BrowserEventSourcePort()
    with pytest.raises(RuntimeError, match="proxy boom"):
        port.open(
            "/events",
            events=("message",),
            on_open=lambda: None,
            on_message=lambda *a: None,
            on_error=lambda: None,
            on_close=lambda: None,
        )
    assert es.closed is True
    assert ffi.proxies[0].destroyed is True
    assert len(ffi.proxies) == 2
