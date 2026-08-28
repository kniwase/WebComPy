"""Fake port implementations for browserless testing."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, Literal
from unittest.mock import MagicMock

from webcompy.ports._async_scheduler import AsyncSchedulerPort
from webcompy.ports._custom_element import CustomElementBinding, CustomElementPort
from webcompy.ports._dom import DOMNode
from webcompy.ports._event_source import EventSourcePort
from webcompy.ports._fetch import FetchPort, FetchStream, Response
from webcompy.ports._ffi import FFIPort
from webcompy.ports._history import HistoryPort
from webcompy.ports._host import HostPort
from webcompy.ports._media_query import MediaQueryPort
from webcompy.ports._transition import TransitionPort, TransitionStyle
from webcompy.ports._websocket import WebSocketConnection, WebSocketPort
from webcompy_server.ports._dom import ServerDOMPort
from webcompy_testing._dom import FakeDOMNode

_logger = logging.getLogger(__name__)

_MAX_DRAIN_ITERATIONS = 1000


class _FakeCustomElementBinding(CustomElementBinding):
    def __init__(self, port: FakeCustomElementPort) -> None:
        self._port = port

    def dispose(self) -> None:
        self._port.disposed_bindings += 1


class FakeCustomElementPort(CustomElementPort):
    """Record custom-element registrations and bindings for assertions.

    Attributes:
        ensure_defined_calls: Recorded ``(name, observed_attributes,
            definition_key)`` definition requests.
        bind_calls: Recorded ``(node, observed_attributes)`` binding
            requests.
        disposed_bindings: Number of bindings disposed so far.
        connected: Connection state returned by
            ``is_document_connected``.

    """

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
        """Record a custom-element definition request.

        Args:
            name: Custom element tag name.
            observed_attributes: Attributes observed by the element.
            definition_key: Deduplication key for the definition.

        """
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
        """Record a binding and return a disposable handle.

        Args:
            node: DOM node to bind.
            observed_attributes: Attributes observed by the binding.
            on_connected: Callback invoked when connected.
            on_disconnected: Callback invoked when disconnected.
            on_attribute_changed: Callback invoked on attribute changes.

        Returns:
            A binding handle whose ``dispose`` increments the counter.

        """
        self.bind_calls.append((node, observed_attributes))
        return _FakeCustomElementBinding(self)

    def is_document_connected(self, node: Any) -> bool:
        """Report whether a node is considered document-connected.

        Args:
            node: Node to check.

        Returns:
            ``True`` if the fake is configured as connected or the node reports
            ``isConnected``.

        """
        return self.connected or bool(getattr(node, "isConnected", False))


class FakeMediaQueryPort(MediaQueryPort):
    """Provide controllable media-query values for tests.

    Args:
        prefers_dark: Initial value for ``prefers_dark``.
        prefers_reduced_motion: Initial value for ``prefers_reduced_motion``.

    """

    def __init__(
        self,
        *,
        prefers_dark: bool = False,
        prefers_reduced_motion: bool = False,
    ) -> None:
        self._prefers_dark = prefers_dark
        self._prefers_reduced_motion = prefers_reduced_motion

    def prefers_dark(self) -> bool:
        """Return the configured dark-mode preference.

        Returns:
            ``True`` if dark mode is preferred.

        """
        return self._prefers_dark

    def prefers_reduced_motion(self) -> bool:
        """Return the configured reduced-motion preference.

        Returns:
            ``True`` if reduced motion is preferred.

        """
        return self._prefers_reduced_motion

    def set_prefers_reduced_motion(self, value: bool) -> None:
        """Update the reduced-motion preference.

        Args:
            value: New preference value.

        """
        self._prefers_reduced_motion = value


class FakeBrowserDOMPort(ServerDOMPort):
    """Provide an in-memory DOM with synthetic document listeners.

    Attributes:
        body: Document body node.

    """

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
        """Return the document body node."""
        return self._body

    def create_element(self, tag: str) -> FakeDOMNode:
        """Create an element node.

        Args:
            tag: Tag name for the new element.

        Returns:
            A new ``FakeDOMNode`` with the given tag.

        """
        return FakeDOMNode(tag)

    def create_text_node(self, text: str) -> FakeDOMNode:
        """Create a text node.

        Args:
            text: Text content for the node.

        Returns:
            A new text ``FakeDOMNode``.

        """
        return FakeDOMNode("#text", text_content=text)

    def create_comment(self, data: str) -> FakeDOMNode:
        """Create a comment node.

        Args:
            data: Comment text.

        Returns:
            A new comment ``FakeDOMNode``.

        """
        return FakeDOMNode("#comment", text_content=data)

    def query_selector(self, selector: str) -> FakeDOMNode | None:
        """Find the first node matching a simple selector.

        Args:
            selector: CSS selector supporting tag, ``#id``, or
                ``tag[attr="value"]``.

        Returns:
            The first matching node or ``None`` when no match exists.

        """
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

    def query_selector_all(
        self,
        selector: str,
        *,
        root: Any | None = None,
    ) -> list[FakeDOMNode]:
        """Find all nodes matching ``selector`` within ``root`` or document.

        Args:
            selector: CSS selector string. Comma-separated groups and
                ``:not()`` are supported for the overlay use case.
            root: Optional subtree root.

        Returns:
            Matching nodes in document order.

        """
        scope = root if root is not None else self._html
        if not isinstance(scope, FakeDOMNode):
            return []
        collected: list[FakeDOMNode] = []
        stack: list[FakeDOMNode] = [scope]
        while stack:
            node = stack.pop()
            if node.nodeType == 1 and _node_matches_fake_selector(node, selector):
                collected.append(node)
            children = node.childNodes
            for index in range(children.length - 1, -1, -1):
                child = children[index]
                if isinstance(child, FakeDOMNode):
                    stack.append(child)
        order: list[FakeDOMNode] = []
        s: list[FakeDOMNode] = [scope]  # type: ignore[assignment]
        while s:
            cur = s.pop()
            order.append(cur)
            kids = cur.childNodes
            for idx in range(kids.length - 1, -1, -1):
                ch = kids[idx]
                if isinstance(ch, FakeDOMNode):
                    s.append(ch)
        index_map = {id(n): i for i, n in enumerate(order)}
        collected.sort(key=lambda n: index_map.get(id(n), len(order)))
        return collected

    def get_element_by_id(self, element_id: str) -> FakeDOMNode | None:
        """Return the element with the given identifier.

        Args:
            element_id: Value of the ``id`` attribute to search for.

        Returns:
            The matching node or ``None``.

        """
        return _find_by_id(self._html, element_id)

    def add_document_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        """Register a document-level event listener.

        Args:
            event_type: Event type to listen for.
            handler: Callback invoked when the event is dispatched.

        Returns:
            A callable that removes the listener.

        """
        self._document_listeners.setdefault(event_type, []).append(handler)

        def _remove() -> None:
            listeners = self._document_listeners.get(event_type)
            if listeners is None:
                return
            with contextlib.suppress(ValueError):
                listeners.remove(handler)

        return _remove

    def dispatch_document_event(self, event_type: str, event: Any = None) -> None:
        """Dispatch a synthetic document event.

        Args:
            event_type: Event type to dispatch.
            event: Payload forwarded to registered handlers.

        """
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


def _node_matches_fake_selector(node: FakeDOMNode, selector: str) -> bool:
    for group in selector.split(","):
        group = group.strip()
        if group and _fake_group_matches(node, group):
            return True
    return False


def _fake_group_matches(node: FakeDOMNode, group: str) -> bool:
    if ":not(" in group:
        outer, _, inner = group.partition(":not(")
        inner = inner.rstrip(")")
        outer = outer.strip()
        if not _fake_simple_attr_match(node, outer):
            return False
        return not _fake_simple_attr_match(node, inner.strip())
    return _fake_simple_attr_match(node, group)


def _fake_simple_attr_match(node: FakeDOMNode, expr: str) -> bool:
    expr = expr.strip()
    if not expr:
        return False
    tag: str | None = None
    tag_m = re.match(r"^([a-zA-Z][a-zA-Z0-9]*)", expr)
    rest = expr
    if tag_m:
        tag = tag_m.group(1).lower()
        rest = expr[len(tag_m.group(1)) :]
        if not rest.strip():
            return node.nodeName.lower() == tag
    rest = rest.strip()
    if tag is not None and not rest:
        return node.nodeName.lower() == tag
    attr_re = re.compile(r'^\[([a-zA-Z0-9_-]+)(?:="([^"]*)")?\]')
    has_predicate = False
    while rest:
        rest = rest.strip()
        if not rest:
            break
        m = attr_re.match(rest)
        if m is None:
            return False
        has_predicate = True
        attr_name = m.group(1)
        attr_value = m.group(2)
        actual = node.getAttribute(attr_name)
        if attr_value is None:
            if actual is None:
                return False
        else:
            if actual != attr_value:
                return False
        rest = rest[m.end() :]
    if has_predicate:
        return not (tag is not None and node.nodeName.lower() != tag)
    if tag is not None:
        return node.nodeName.lower() == tag
    return False


class FakeBrowserHostPort(HostPort):
    """Provide synthetic window events and macro-task scheduling."""

    def __init__(self, dom_port: FakeBrowserDOMPort | None = None) -> None:
        self._window_listeners: dict[str, list[Any]] = {}
        self._dom_port = dom_port

    def schedule_macro_task(self, callback: Any) -> None:
        """Execute a macro task immediately.

        Args:
            callback: Callable to invoke synchronously.

        """
        callback()

    def add_window_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]:
        """Register a window-level event listener.

        Args:
            event_type: Event type to listen for.
            handler: Callback invoked when the event is dispatched.

        Returns:
            A callable that removes the listener.

        """
        self._window_listeners.setdefault(event_type, []).append(handler)

        def _remove() -> None:
            listeners = self._window_listeners.get(event_type)
            if listeners is None:
                return
            with contextlib.suppress(ValueError):
                listeners.remove(handler)

        return _remove

    def dispatch_window_event(self, event_type: str, event: Any = None) -> None:
        """Dispatch a synthetic window event.

        Args:
            event_type: Event type to dispatch.
            event: Payload forwarded to registered handlers.

        """
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
        """Create a getter for a synthetic JavaScript global.

        Args:
            name: Global name.
            wrapper: Optional wrapper applied to the retrieved value.
            default: Value returned when no wrapper is provided.

        Returns:
            A zero-argument getter returning the wrapped or default value.

        """

        def _getter() -> Any:
            if self._dom_port is not None and name == "document":
                doc = self._dom_port._html  # type: ignore[attr-defined]
                fake_active = getattr(doc, "_fake_active_element", None)
                if wrapper is not None:
                    if fake_active is not None:
                        fake_doc = type("FakeDoc", (), {"activeElement": fake_active})()
                        return wrapper(fake_doc)
                    return wrapper(None)
            if wrapper is not None:
                return wrapper(None)
            return default

        return _getter


class FakeBrowserFFIPort(FFIPort):
    """Provide ``FFIPort`` behavior without a JavaScript bridge."""

    def create_proxy(self, func: Any) -> Any:
        """Create a mock proxy that forwards calls to ``func``.

        Args:
            func: Callable to wrap.

        Returns:
            A ``MagicMock`` proxy with a ``destroy`` method.

        """
        proxy = MagicMock(side_effect=func)
        proxy.destroy = MagicMock()
        return proxy

    def destroy_proxy(self, proxy: Any) -> None:
        """Destroy a proxy created by ``create_proxy``.

        Args:
            proxy: Proxy to destroy.

        """
        if hasattr(proxy, "destroy"):
            proxy.destroy()

    def is_none(self, value: Any) -> bool:
        """Check whether a value is ``None``.

        Args:
            value: Value to test.

        Returns:
            ``True`` when ``value`` is ``None``.

        """
        return value is None

    def to_js(self, value: Any, **kwargs: Any) -> Any:
        """Return the value unchanged as a JS equivalent.

        Args:
            value: Value to convert.
            **kwargs: Additional conversion options.

        Returns:
            ``value`` unchanged.

        """
        return value

    def assign(self, target: Any, source: Any) -> None:
        """Merge ``source`` into ``target``.

        Args:
            target: Mapping to update.
            source: Mapping whose entries are copied into ``target``.

        """
        target.update(source)


class _FakeFetchStream(FetchStream):
    def __init__(
        self,
        chunks: list[str],
        status_code: int,
        headers: dict[str, str],
        ok: bool,
        port: FakeFetchPort,
        key: tuple[str, str],
    ) -> None:
        super().__init__(status_code, headers, ok)
        self._chunks = iter(chunks)
        self._port = port
        self._key = key
        self.aborted = False

    async def __anext__(self) -> str:
        if self._closed:
            raise StopAsyncIteration
        try:
            return next(self._chunks)
        except StopIteration:
            raise StopAsyncIteration from None

    def close(self) -> None:
        if self._closed:
            return
        super().close()
        self.aborted = True
        self._port.aborted_streams.append(self._key)


@dataclass
class RecordedRequest:
    """A fetch request observed by a fake fetch port.

    Attributes:
        method: HTTP method of the observed request.
        url: Target URL of the observed request.
        headers: Request headers mapping.
        body: Request body (text or bytes), or ``None``.

    """

    method: str
    url: str
    headers: dict[str, str]
    body: str | bytes | None


class FakeFetchPort(FetchPort):
    """Serve canned fetch responses and streams for assertions.

    Args:
        responses: Mapping from ``(method, url)`` to canned ``Response``.
        streams: Mapping from ``(method, url)`` to scripted chunk lists.

    Attributes:
        aborted_streams: Recorded ``(method, url)`` pairs of streams
            closed before completion.
        requests: Recorded requests in arrival order.

    """

    def __init__(
        self,
        responses: dict[tuple[str, str], Response] | None = None,
        streams: dict[tuple[str, str], list[str]] | None = None,
    ) -> None:
        self._responses = responses or {}
        self._streams = streams or {}
        self.aborted_streams: list[tuple[str, str]] = []
        self.requests: list[RecordedRequest] = []

    async def fetch(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
    ) -> Response:
        """Return a canned response for the requested URL.

        Args:
            url: Target URL.
            method: HTTP method.
            headers: Optional request headers.
            body: Optional request body as text or bytes.

        Returns:
            The canned ``Response`` for ``(method, url)``.

        Raises:
            KeyError: If no response is registered for the key.

        """
        self.requests.append(
            RecordedRequest(method=method, url=url, headers=dict(headers) if headers else {}, body=body)
        )
        key = (method, url)
        if key in self._responses:
            return self._responses[key]
        raise KeyError(
            f"No canned response registered for {method} {url}. Registered keys: {list(self._responses.keys())}"
        )

    async def stream(
        self,
        url: str,
        *,
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: str | bytes | None = None,
    ) -> FetchStream:
        """Return a scripted stream for the requested URL.

        Args:
            url: Target URL.
            method: HTTP method.
            headers: Optional request headers.
            body: Optional request body as text or bytes.

        Returns:
            A ``FetchStream`` yielding the scripted chunks.

        Raises:
            KeyError: If no stream or response is registered for the key.

        """
        self.requests.append(
            RecordedRequest(method=method, url=url, headers=dict(headers) if headers else {}, body=body)
        )
        key = (method, url)
        response = self._responses.get(key)
        if key in self._streams:
            if response is not None:
                return _FakeFetchStream(
                    list(self._streams[key]), response.status_code, response.headers, response.ok, self, key
                )
            return _FakeFetchStream(
                list(self._streams[key]), 200, {"content-type": "text/event-stream"}, True, self, key
            )
        if response is not None:
            return _FakeFetchStream([response.text], response.status_code, response.headers, response.ok, self, key)
        raise KeyError(
            f"No scripted stream or canned response registered for {method} {url}. "
            f"Registered stream keys: {list(self._streams.keys())}; response keys: {list(self._responses.keys())}"
        )


class FakeHistoryPort(HistoryPort):
    """Record history navigation calls for assertions.

    Args:
        mode: Router mode to simulate.
        initial_path: Initial path for the history.

    Attributes:
        pushed_urls: Recorded ``(path, state)`` pairs passed to
            ``push_url``.
        replaced_urls: Recorded ``(path, state)`` pairs passed to
            ``replace_url``.

    """

    def __init__(self, *, mode: Literal["hash", "history"] = "history", initial_path: str = "/") -> None:
        super().__init__(initial_path, mode=mode)
        self.pushed_urls: list[tuple[str, dict[str, Any] | None]] = []
        self.replaced_urls: list[tuple[str, dict[str, Any] | None]] = []

    def push_url(self, path: str, state: dict[str, Any] | None = None) -> None:
        """Record a push navigation.

        Args:
            path: Path to push.
            state: Optional navigation state.

        """
        self.pushed_urls.append((path, state))

    def replace_url(self, path: str, state: dict[str, Any] | None = None) -> None:
        """Record a replace navigation.

        Args:
            path: Path to replace the current entry with.
            state: Optional navigation state.

        """
        self.replaced_urls.append((path, state))

    def current_search(self) -> str:
        """Return the current search string.

        Returns:
            An empty search string in the fake implementation.

        """
        return ""

    def history_state(self) -> object | None:
        """Return the current history state.

        Returns:
            The stored navigation state.

        """
        return self._state

    def refresh_from_window(self) -> None:
        """Synchronize the fake history with the window location."""
        pass


class _PendingTask:
    """Bookkeeping stand-in for a scheduled coroutine.

    The fake never runs a scheduled coroutine itself; it only records it for a
    later explicit ``drain()``. The returned stand-in satisfies the small
    ``asyncio.Task`` surface that dynamic-element hydration uses (``done``,
    ``cancel``, ``cancelled``, ``exception``, ``add_done_callback``) without
    requiring an event loop at ``schedule()`` time, so sync test contexts do not
    leak un-awaited placeholder coroutines. ``drain()``/``await_pending()``
    settle the stand-ins of the coroutines they execute: the stand-in is marked
    done, the executed coroutine's exception (if any) is recorded, and registered
    done callbacks are invoked. Cancelling an un-executed stand-in drops the
    recorded coroutine so a later ``drain()`` does not run it (mirroring real
    task cancellation in the browser scheduler); cancelling an executed
    stand-in returns ``False`` and is a no-op.
    """

    def __init__(self, scheduler: FakeAsyncSchedulerPort, coro: Coroutine[Any, Any, Any]) -> None:
        self._scheduler = scheduler
        self._coro = coro
        self._done = False
        self._cancelled = False
        self._exception: BaseException | None = None
        self._callbacks: list[Any] = []

    def _settle(self, exception: BaseException | None) -> None:
        if self._done:
            return
        self._done = True
        self._exception = exception
        callbacks = self._callbacks
        self._callbacks = []
        for callback in callbacks:
            callback(self)

    def add_done_callback(self, callback: Any) -> None:
        self._callbacks.append(callback)

    def remove_done_callback(self, callback: Any) -> None:
        with contextlib.suppress(ValueError):
            self._callbacks.remove(callback)

    def cancel(self) -> bool:
        if self._done:
            return False
        self._cancelled = True
        self._done = True
        with contextlib.suppress(ValueError):
            self._scheduler._coroutines.remove(self._coro)
        with contextlib.suppress(ValueError):
            self._scheduler._render_coroutines.remove(self._coro)
        return True

    def cancelled(self) -> bool:
        return self._cancelled

    def done(self) -> bool:
        return self._done

    def exception(self) -> BaseException | None:
        return self._exception


class FakeAsyncSchedulerPort(AsyncSchedulerPort):
    """Queue coroutines and expose a drainable pending-task surface."""

    def __init__(self) -> None:
        self._coroutines: list[Coroutine[Any, Any, Any]] = []
        self._render_coroutines: list[Coroutine[Any, Any, Any]] = []
        self._tasks: list[_PendingTask] = []

    def schedule(
        self,
        coro: Coroutine[Any, Any, Any],
        *,
        render: bool = False,
    ) -> asyncio.Task[Any]:
        """Schedule a coroutine without running it.

        Args:
            coro: Coroutine to queue.
            render: Whether the coroutine is part of the render phase.

        Returns:
            A pending-task stand-in resembling ``asyncio.Task``.

        """
        self._coroutines.append(coro)
        if render:
            self._render_coroutines.append(coro)
        task = _PendingTask(self, coro)
        self._tasks.append(task)
        return task  # type: ignore[return-value]

    async def _execute(self, coros: list[Coroutine[Any, Any, Any]]) -> None:
        results = await asyncio.gather(*coros, return_exceptions=True)
        for coro, result in zip(coros, results, strict=True):
            for task in self._tasks:
                if task._coro is coro:
                    task._settle(result if isinstance(result, BaseException) else None)
                    break

    async def drain(self) -> None:
        """Execute all queued coroutines, including those scheduled recursively."""
        iteration = 0
        while self._coroutines:
            coros = list(self._coroutines)
            self._coroutines = []
            self._render_coroutines = [c for c in self._render_coroutines if c not in coros]
            await self._execute(coros)
            iteration += 1
            if iteration > _MAX_DRAIN_ITERATIONS:
                _logger.warning(
                    "FakeAsyncSchedulerPort.drain exceeded %d drain iterations; "
                    "possible recursive scheduling bug (%d coroutines still collected)",
                    _MAX_DRAIN_ITERATIONS,
                    len(self._coroutines),
                )
                break

    async def await_pending(self, *, only_render: bool = False) -> None:
        """Await pending coroutines.

        Args:
            only_render: When ``True``, await only render-phase coroutines;
                otherwise drain all.

        """
        if not only_render:
            await self.drain()
            return
        iteration = 0
        while self._render_coroutines:
            coros = list(self._render_coroutines)
            self._render_coroutines = []
            self._coroutines = [c for c in self._coroutines if c not in coros]
            await self._execute(coros)
            iteration += 1
            if iteration > _MAX_DRAIN_ITERATIONS:
                _logger.warning(
                    "FakeAsyncSchedulerPort.await_pending exceeded %d drain iterations; "
                    "possible recursive scheduling bug (%d render coroutines still collected)",
                    _MAX_DRAIN_ITERATIONS,
                    len(self._render_coroutines),
                )
                break


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

    Attributes:
        enabled: Whether transition callbacks run; toggled with
            ``set_enabled``.

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
        """Return whether transitions are enabled."""
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        """Enable or disable transition callbacks.

        Args:
            value: ``True`` to enable transitions.

        """
        self._enabled = value

    def schedule_next_frame(self, callback: Callable[[], Any]) -> Callable[[], None]:
        """Schedule a callback for the next frame.

        Args:
            callback: Callable invoked on the next flushed frame.

        Returns:
            A callable that cancels the scheduled frame callback.

        """
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
        """Schedule a callback after a delay on the virtual clock.

        Args:
            callback: Callable to invoke when the timeout fires.
            delay_ms: Delay in milliseconds.

        Returns:
            A callable that cancels the scheduled timeout.

        """
        self._timeout_seq += 1
        seq = self._timeout_seq
        self._timeouts.append((self._now + delay_ms, seq, callback))

        def _cancel() -> None:
            self._timeouts = [entry for entry in self._timeouts if entry[1] != seq]

        return _cancel

    def flush_frame(self) -> None:
        """Execute callbacks scheduled for the next frame."""
        callbacks = list(self._frame_callbacks)
        self._frame_callbacks.clear()
        for callback in callbacks:
            callback()

    def advance_time(self, ms: float) -> None:
        """Advance the virtual clock and fire due timeouts.

        Args:
            ms: Milliseconds to advance.

        """
        self._now += ms
        due = [entry for entry in self._timeouts if entry[0] <= self._now]
        self._timeouts = [entry for entry in self._timeouts if entry[0] > self._now]
        for _, _, callback in due:
            callback()

    def flush_all(self) -> None:
        """Flush one frame and advance the clock to fire all timeouts."""
        self.flush_frame()
        self.advance_time(10**9)

    def get_computed_style(self, node: DOMNode) -> TransitionStyle:
        """Return the fake computed style for a node.

        Args:
            node: Node whose style is requested.

        Returns:
            A ``TransitionStyle`` reflecting values set via ``set_style``.

        """
        return FakeTransitionStyle(self._styles.get(id(node), {}))

    def set_style(self, node: FakeDOMNode, name: str, value: str) -> None:
        """Set a CSS property in the fake computed-style table.

        Args:
            node: Node to associate the style with.
            name: CSS property name.
            value: CSS property value.

        """
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
    """Track server-sent-event subscriptions and allow synthetic events.

    Attributes:
        open_calls: Recorded ``(url, events)`` subscription requests.
        open_connections: Currently active ``(url, events)``
            subscriptions.

    """

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
        """Register a synthetic event-source subscription.

        Args:
            url: Event source URL.
            events: Event types to subscribe to.
            on_open: Callback invoked when the connection opens.
            on_message: Callback invoked for incoming messages.
            on_error: Callback invoked on connection error.
            on_close: Callback invoked when the connection closes.

        Returns:
            A callable that unregisters the subscription.

        """
        reg = _FakeEventSourceRegistration(url, tuple(events), on_open, on_message, on_error, on_close)
        self._registrations.append(reg)
        self.open_calls.append((url, tuple(events)))

        def _cleanup() -> None:
            with contextlib.suppress(ValueError):
                self._registrations.remove(reg)

        return _cleanup

    @property
    def open_connections(self) -> list[tuple[str, tuple[str, ...]]]:
        """Return active event-source subscriptions."""
        return [(reg.url, reg.events) for reg in self._registrations]

    def emit_event(self, url: str, event_type: str, data: str, last_event_id: str = "") -> None:
        """Emit a message event to matching subscriptions.

        Args:
            url: Event source URL.
            event_type: Event type.
            data: Event payload.
            last_event_id: Last event identifier.

        """
        for reg in list(self._registrations):
            if reg.url == url and event_type in reg.events:
                reg.on_message(event_type, data, last_event_id)

    def emit_open(self, url: str) -> None:
        """Trigger ``on_open`` for subscriptions to ``url``.

        Args:
            url: Event source URL.

        """
        for reg in list(self._registrations):
            if reg.url == url:
                reg.on_open()

    def emit_error(self, url: str) -> None:
        """Trigger ``on_error`` for subscriptions to ``url``.

        Args:
            url: Event source URL.

        """
        for reg in list(self._registrations):
            if reg.url == url:
                reg.on_error()

    def emit_close(self, url: str) -> None:
        """Trigger ``on_close`` for subscriptions to ``url``.

        Args:
            url: Event source URL.

        """
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
    """Track WebSocket connections and allow synthetic message injection.

    Attributes:
        open_calls: Recorded ``(url, protocols)`` connection requests.
        open_connections: Currently active ``(url, protocols)``
            registrations.

    """

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
        """Register a synthetic WebSocket connection.

        Args:
            url: WebSocket URL.
            protocols: Subprotocols requested for the connection.
            on_open: Callback invoked when the connection opens.
            on_message: Callback invoked for text messages.
            on_binary: Callback invoked for binary messages.
            on_error: Callback invoked on connection error.
            on_close: Callback invoked when the connection closes.

        Returns:
            A connection handle that records sent frames.

        """
        normalized = tuple(sorted(protocols))
        reg = _FakeWebSocketRegistration(url, normalized, on_open, on_message, on_binary, on_error, on_close)
        self._registrations.append(reg)
        self.open_calls.append((url, normalized))
        return FakeWebSocketConnection(self, reg)

    @property
    def open_connections(self) -> list[tuple[str, tuple[str, ...]]]:
        """Return active WebSocket registrations."""
        return [(reg.url, reg.protocols) for reg in self._registrations]

    def _matching(self, url: str, protocols: tuple[str, ...] | None) -> list[_FakeWebSocketRegistration]:
        if protocols is None:
            return [reg for reg in self._registrations if reg.url == url]
        normalized = tuple(sorted(protocols))
        return [reg for reg in self._registrations if reg.url == url and reg.protocols == normalized]

    def emit_open(self, url: str, protocols: tuple[str, ...] | None = None) -> None:
        """Trigger ``on_open`` for matching WebSocket registrations.

        Args:
            url: WebSocket URL.
            protocols: Protocols to match or ``None`` for any.

        """
        for reg in list(self._matching(url, protocols)):
            reg.on_open()

    def emit_message(self, url: str, text: str, protocols: tuple[str, ...] | None = None) -> None:
        """Deliver a text message to matching registrations.

        Args:
            url: WebSocket URL.
            text: Message payload.
            protocols: Protocols to match or ``None`` for any.

        """
        for reg in list(self._matching(url, protocols)):
            reg.on_message(text)

    def emit_binary(self, url: str, protocols: tuple[str, ...] | None = None) -> None:
        """Trigger ``on_binary`` for matching registrations.

        Args:
            url: WebSocket URL.
            protocols: Protocols to match or ``None`` for any.

        """
        for reg in list(self._matching(url, protocols)):
            reg.on_binary()

    def emit_error(self, url: str, protocols: tuple[str, ...] | None = None) -> None:
        """Trigger ``on_error`` for matching registrations.

        Args:
            url: WebSocket URL.
            protocols: Protocols to match or ``None`` for any.

        """
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
        """Close matching registrations and trigger ``on_close``.

        Args:
            url: WebSocket URL.
            code: Close status code.
            reason: Close reason.
            was_clean: Whether the close was clean.
            protocols: Protocols to match or ``None`` for any.

        """
        for reg in list(self._matching(url, protocols)):
            reg.on_close(code, reason, was_clean)
            with contextlib.suppress(ValueError):
                self._registrations.remove(reg)

    def sent_frames(self, url: str, protocols: tuple[str, ...] | None = None) -> list[str]:
        """Return payloads sent via matching WebSocket registrations.

        Args:
            url: WebSocket URL.
            protocols: Protocols to match or ``None`` for any.

        Returns:
            Concatenated list of sent text frames.

        """
        frames: list[str] = []
        for reg in self._matching(url, protocols):
            frames.extend(reg.sent)
        return frames
