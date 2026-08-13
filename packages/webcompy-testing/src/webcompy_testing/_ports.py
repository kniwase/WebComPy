from __future__ import annotations

import asyncio
import re
from collections.abc import Callable, Coroutine
from typing import Any, Literal
from unittest.mock import MagicMock

from webcompy.ports._async_scheduler import AsyncSchedulerPort
from webcompy.ports._dom import DOMNode
from webcompy.ports._fetch import FetchPort, Response
from webcompy.ports._ffi import FFIPort
from webcompy.ports._history import HistoryPort
from webcompy.ports._host import HostPort
from webcompy.ports._media_query import MediaQueryPort
from webcompy.ports._transition import TransitionPort, TransitionStyle
from webcompy_server.ports._dom import ServerDOMPort
from webcompy_testing._dom import FakeDOMNode


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
        self._head = FakeDOMNode("head")
        self._body = FakeDOMNode("body")
        self._html.appendChild(self._head)
        self._html.appendChild(self._body)

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
    def schedule_macro_task(self, callback: Any) -> None:
        callback()

    def add_window_event_listener(self, event_type: str, handler: Any) -> Any:
        return lambda: None

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
