from __future__ import annotations

import asyncio
import contextlib
import re
from collections.abc import Callable, Coroutine
from typing import Any, Literal
from unittest.mock import MagicMock

from webcompy.ports._async_scheduler import AsyncSchedulerPort
from webcompy.ports._custom_element import CustomElementBinding, CustomElementPort
from webcompy.ports._dom import DOMNode
from webcompy.ports._event_source import EventSourcePort
from webcompy.ports._fetch import FetchPort, Response
from webcompy.ports._ffi import FFIPort
from webcompy.ports._history import HistoryPort
from webcompy.ports._host import HostPort
from webcompy.ports._media_query import MediaQueryPort
from webcompy.ports._transition import TransitionPort, TransitionStyle
from webcompy.ports._websocket import WebSocketConnection, WebSocketPort
from webcompy_server.ports._dom import ServerDOMPort
from webcompy_testing._dom import FakeDOMNode


class _FakeCustomElementBinding(CustomElementBinding):
    def __init__(self, port: FakeCustomElementPort) -> None:
        self._port = port

    def dispose(self) -> None:
        self._port.disposed_bindings += 1


class FakeCustomElementPort(CustomElementPort):
    def __init__(self) -> None:
        self.ensure_defined_calls: list[tuple[str, tuple[str, ...], str]] = []
        self.bind_calls: list[tuple[Any, tuple[str, ...]]] = []
        self.disposed_bindings: int = 0
        self.connected: bool = False

    def ensure_defined(
        self,
        name: str,
        observed_attributes: tuple[str, ...],
        definition_key: str,
    ) -> None:
        self.ensure_defined_calls.append((name, observed_attributes, definition_key))

    def bind(
        self,
        node: Any,
        *,
        observed_attributes: tuple[str, ...],
        on_connected: Any = None,
        on_disconnected: Any = None,
        on_attribute_changed: Any = None,
    ) -> CustomElementBinding:
        self.bind_calls.append((node, observed_attributes))
        return _FakeCustomElementBinding(self)

    def is_document_connected(self, node: Any) -> bool:
        return self.connected or bool(getattr(node, "isConnected", False))


class FakeMediaQueryPort(MediaQueryPort):
    def __init__(
        self,
        *,
        prefers_dark: bool = False,
        prefers_reduced_motion: bool = False,
    ) -> None:
        self._prefers_dark = prefers_dark
        self._prefers_reduced_motion = prefers_reduced_motion

    def prefers_dark(self) -> bool:
        return self._prefers_dark

    def prefers_reduced_motion(self) -> bool:
        return self._prefers_reduced_motion

    def set_prefers_reduced_motion(self, value: bool) -> None:
        self._prefers_reduced_motion = value


class FakeBrowserDOMPort(ServerDOMPort):
    def __init__(self) -> None:
        super().__init__()
        self._html = FakeDOMNode("html")
        self._html.__webcompy_document_root__ = True
        self._head = FakeDOMNode("head")
        self._body = FakeDOMNode("body")
        self._html.appendChild(self._head)
        self._html.appendChild(self._body)
        self._document_listeners: dict[str, list[Any]] = {}

    @property
    def body(self) -> FakeDOMNode:
        return self._body

    def create_element(self, tag: str) -> FakeDOMNode:
        return FakeDOMNode(tag)

    def create_text_node(self, text: str) -> FakeDOMNode:
        return FakeDOMNode("#text", text_content=text)

    def query_selector(self, selector: str) -> FakeDOMNode | None:
        if ">" in selector:
            return None
        tag_match = re.match(r"([a-zA-Z][a-zA-Z0-9]*)", selector)
        id_match = re.match(r"#([a-zA-Z][a-zA-Z0-9_-]*)", selector)
        attr_match = re.match(r'([a-zA-Z][a-zA-Z0-9]*)\[([a-zA-Z_-]+)="([^"]*)"\]', selector)

        if id_match:
            return _find_by_id(self._html, id_match.group(1))
        if attr_match:
            return _find_by_tag_attr(self._html, attr_match.group(1), attr_match.group(2), attr_match.group(3))
        if tag_match:
            return _find_by_tag(self._html, tag_match.group(1))
        return None

    def get_element_by_id(self, element_id: str) -> FakeDOMNode | None:
        return _find_by_id(self._html, element_id)

    def add_document_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        self._document_listeners.setdefault(event_type, []).append(handler)

        def _remove() -> None:
            listeners = self._document_listeners.get(event_type)
            if listeners is None:
                return
            with contextlib.suppress(ValueError):
                listeners.remove(handler)

        return _remove

    def dispatch_document_event(self, event_type: str, event: Any = None) -> None:
        for handler in list(self._document_listeners.get(event_type, ())):
            if handler in self._document_listeners.get(event_type, ()):
                handler(event)


def _find_by_tag(node: FakeDOMNode, tag: str) -> FakeDOMNode | None:
    if node.nodeName == tag.upper():
        return node
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, FakeDOMNode):
            result = _find_by_tag(child, tag)
            if result is not None:
                return result
    return None


def _find_by_id(node: FakeDOMNode, element_id: str) -> FakeDOMNode | None:
    if node.getAttribute("id") == element_id:
        return node
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, FakeDOMNode):
            result = _find_by_id(child, element_id)
            if result is not None:
                return result
    return None


def _find_by_tag_attr(node: FakeDOMNode, tag: str, attr_name: str, attr_value: str) -> FakeDOMNode | None:
    if node.nodeName == tag.upper() and node.getAttribute(attr_name) == attr_value:
        return node
    for i in range(node.childNodes.length):
        child = node.childNodes[i]
        if isinstance(child, FakeDOMNode):
            result = _find_by_tag_attr(child, tag, attr_name, attr_value)
            if result is not None:
                return result
    return None


class FakeBrowserHostPort(HostPort):
    def __init__(self) -> None:
        self._window_listeners: dict[str, list[Any]] = {}

    def schedule_macro_task(self, callback: Any) -> None:
        callback()

    def add_window_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        self._window_listeners.setdefault(event_type, []).append(handler)

        def _remove() -> None:
            listeners = self._window_listeners.get(event_type)
            if listeners is None:
                return
            with contextlib.suppress(ValueError):
                listeners.remove(handler)

        return _remove

    def dispatch_window_event(self, event_type: str, event: Any = None) -> None:
        for handler in list(self._window_listeners.get(event_type, ())):
            if handler in self._window_listeners.get(event_type, ()):
                handler(event)

    def create_js_global_getter(
        self,
        name: str,
        *,
        wrapper: Any = None,
        default: Any = None,
    ) -> Any:
        def _getter() -> Any:
            if wrapper is not None:
                return wrapper(None)
            return default

        return _getter


class FakeBrowserFFIPort(FFIPort):
    def create_proxy(self, func: Any) -> Any:
        proxy = MagicMock(side_effect=func)
        proxy.destroy = MagicMock()
        return proxy

    def destroy_proxy(self, proxy: Any) -> None:
        if hasattr(proxy, "destroy"):
            proxy.destroy()

    def is_none(self, value: Any) -> bool:
        return value is None

    def to_js(self, value: Any, **kwargs: Any) -> Any:
        return value

    def assign(self, target: Any, source: Any) -> None:
        target.update(source)


class FakeFetchPort(FetchPort):
    def __init__(self, responses: dict[tuple[str, str], Response] | None = None) -> None:
        self._responses = responses or {}

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> Response:
        key = (method, url)
        if key in self._responses:
            return self._responses[key]
        raise KeyError(
            f"No canned response registered for {method} {url}. Registered keys: {list(self._responses.keys())}"
        )


class FakeHistoryPort(HistoryPort):
    def __init__(self, *, mode: Literal["hash", "history"] = "history", initial_path: str = "/") -> None:
        super().__init__(initial_path, mode=mode)
        self.pushed_urls: list[tuple[str, dict[str, Any] | None]] = []
        self.replaced_urls: list[tuple[str, dict[str, Any] | None]] = []

    def push_url(self, path: str, state: dict[str, Any] | None = None) -> None:
        self.pushed_urls.append((path, state))

    def replace_url(self, path: str, state: dict[str, Any] | None = None) -> None:
        self.replaced_urls.append((path, state))

    def current_search(self) -> str:
        return ""

    def history_state(self) -> object | None:
        return self._state

    def refresh_from_window(self) -> None:
        pass


class FakeAsyncSchedulerPort(AsyncSchedulerPort):
    def __init__(self) -> None:
        self._coroutines: list[Coroutine[Any, Any, Any]] = []

    def schedule(self, coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
        self._coroutines.append(coro)
        return asyncio.ensure_future(asyncio.sleep(0))

    async def drain(self) -> None:
        coros = self._coroutines
        self._coroutines = []
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

    async def await_pending(self) -> None:
        await self.drain()


class FakeTransitionStyle:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self._values = dict(values or {})

    def get_property_value(self, name: str) -> str:
        return self._values.get(name, "")


class FakeTransitionPort(TransitionPort):
    """Transition port driven by a logical frame queue and virtual clock.

    ``flush_frame()`` executes the callbacks scheduled for the next frame and
    ``advance_time(ms)`` moves the virtual clock forward, firing due
    timeouts. Per-node computed styles are registered via ``set_style``.
    """

    def __init__(self) -> None:
        self._enabled = True
        self._frame_callbacks: list[Callable[[], Any]] = []
        self._timeouts: list[tuple[float, int, Callable[[], Any]]] = []
        self._timeout_seq = 0
        self._now = 0.0
        self._styles: dict[int, dict[str, str]] = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        self._enabled = value

    def schedule_next_frame(self, callback: Callable[[], Any]) -> Callable[[], None]:
        self._frame_callbacks.append(callback)

        def _cancel() -> None:
            if callback in self._frame_callbacks:
                self._frame_callbacks.remove(callback)

        return _cancel

    def schedule_timeout(
        self,
        callback: Callable[[], Any],
        delay_ms: float,
    ) -> Callable[[], None]:
        self._timeout_seq += 1
        seq = self._timeout_seq
        self._timeouts.append((self._now + delay_ms, seq, callback))

        def _cancel() -> None:
            self._timeouts = [entry for entry in self._timeouts if entry[1] != seq]

        return _cancel

    def flush_frame(self) -> None:
        callbacks = list(self._frame_callbacks)
        self._frame_callbacks.clear()
        for callback in callbacks:
            callback()

    def advance_time(self, ms: float) -> None:
        self._now += ms
        due = [entry for entry in self._timeouts if entry[0] <= self._now]
        self._timeouts = [entry for entry in self._timeouts if entry[0] > self._now]
        for _, _, callback in due:
            callback()

    def flush_all(self) -> None:
        self.flush_frame()
        self.advance_time(10**9)

    def get_computed_style(self, node: DOMNode) -> TransitionStyle:
        return FakeTransitionStyle(self._styles.get(id(node), {}))

    def set_style(self, node: FakeDOMNode, name: str, value: str) -> None:
        self._styles.setdefault(id(node), {})[name] = value


class _FakeEventSourceRegistration:
    __slots__ = ("events", "on_close", "on_error", "on_message", "on_open", "url")

    def __init__(
        self,
        url: str,
        events: tuple[str, ...],
        on_open: Any,
        on_message: Any,
        on_error: Any,
        on_close: Any,
    ) -> None:
        self.url = url
        self.events = events
        self.on_open = on_open
        self.on_message = on_message
        self.on_error = on_error
        self.on_close = on_close


class FakeEventSourcePort(EventSourcePort):
    def __init__(self) -> None:
        self._registrations: list[_FakeEventSourceRegistration] = []
        self.open_calls: list[tuple[str, tuple[str, ...]]] = []

    def open(
        self,
        url: str,
        *,
        events: tuple[str, ...],
        on_open: Any = None,
        on_message: Any = None,
        on_error: Any = None,
        on_close: Any = None,
    ) -> Callable[[], None]:
        reg = _FakeEventSourceRegistration(url, tuple(events), on_open, on_message, on_error, on_close)
        self._registrations.append(reg)
        self.open_calls.append((url, tuple(events)))

        def _cleanup() -> None:
            with contextlib.suppress(ValueError):
                self._registrations.remove(reg)

        return _cleanup

    @property
    def open_connections(self) -> list[tuple[str, tuple[str, ...]]]:
        return [(reg.url, reg.events) for reg in self._registrations]

    def emit_event(self, url: str, event_type: str, data: str, last_event_id: str = "") -> None:
        for reg in list(self._registrations):
            if reg.url == url and event_type in reg.events:
                reg.on_message(event_type, data, last_event_id)

    def emit_open(self, url: str) -> None:
        for reg in list(self._registrations):
            if reg.url == url:
                reg.on_open()

    def emit_error(self, url: str) -> None:
        for reg in list(self._registrations):
            if reg.url == url:
                reg.on_error()

    def emit_close(self, url: str) -> None:
        for reg in list(self._registrations):
            if reg.url == url:
                reg.on_close()


class _FakeWebSocketRegistration:
    __slots__ = (
        "on_binary",
        "on_close",
        "on_error",
        "on_message",
        "on_open",
        "protocols",
        "sent",
        "url",
    )

    def __init__(
        self,
        url: str,
        protocols: tuple[str, ...],
        on_open: Any,
        on_message: Any,
        on_binary: Any,
        on_error: Any,
        on_close: Any,
    ) -> None:
        self.url = url
        self.protocols = protocols
        self.on_open = on_open
        self.on_message = on_message
        self.on_binary = on_binary
        self.on_error = on_error
        self.on_close = on_close
        self.sent: list[str] = []


class FakeWebSocketConnection(WebSocketConnection):
    def __init__(self, port: FakeWebSocketPort, reg: _FakeWebSocketRegistration) -> None:
        self._port = port
        self._reg = reg
        self._closed = False

    def send(self, data: str) -> None:
        self._reg.sent.append(data)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        with contextlib.suppress(ValueError):
            self._port._registrations.remove(self._reg)


class FakeWebSocketPort(WebSocketPort):
    def __init__(self) -> None:
        self._registrations: list[_FakeWebSocketRegistration] = []
        self.open_calls: list[tuple[str, tuple[str, ...]]] = []

    def open(
        self,
        url: str,
        *,
        protocols: tuple[str, ...] = (),
        on_open: Any = None,
        on_message: Any = None,
        on_binary: Any = None,
        on_error: Any = None,
        on_close: Any = None,
    ) -> WebSocketConnection:
        normalized = tuple(sorted(protocols))
        reg = _FakeWebSocketRegistration(url, normalized, on_open, on_message, on_binary, on_error, on_close)
        self._registrations.append(reg)
        self.open_calls.append((url, normalized))
        return FakeWebSocketConnection(self, reg)

    @property
    def open_connections(self) -> list[tuple[str, tuple[str, ...]]]:
        return [(reg.url, reg.protocols) for reg in self._registrations]

    def _matching(self, url: str, protocols: tuple[str, ...] | None) -> list[_FakeWebSocketRegistration]:
        if protocols is None:
            return [reg for reg in self._registrations if reg.url == url]
        normalized = tuple(sorted(protocols))
        return [reg for reg in self._registrations if reg.url == url and reg.protocols == normalized]

    def emit_open(self, url: str, protocols: tuple[str, ...] | None = None) -> None:
        for reg in list(self._matching(url, protocols)):
            reg.on_open()

    def emit_message(self, url: str, text: str, protocols: tuple[str, ...] | None = None) -> None:
        for reg in list(self._matching(url, protocols)):
            reg.on_message(text)

    def emit_binary(self, url: str, protocols: tuple[str, ...] | None = None) -> None:
        for reg in list(self._matching(url, protocols)):
            reg.on_binary()

    def emit_error(self, url: str, protocols: tuple[str, ...] | None = None) -> None:
        for reg in list(self._matching(url, protocols)):
            reg.on_error()

    def emit_close(
        self,
        url: str,
        code: int = 1000,
        reason: str = "",
        was_clean: bool = True,
        protocols: tuple[str, ...] | None = None,
    ) -> None:
        for reg in list(self._matching(url, protocols)):
            reg.on_close(code, reason, was_clean)
            with contextlib.suppress(ValueError):
                self._registrations.remove(reg)

    def sent_frames(self, url: str, protocols: tuple[str, ...] | None = None) -> list[str]:
        frames: list[str] = []
        for reg in self._matching(url, protocols):
            frames.extend(reg.sent)
        return frames
