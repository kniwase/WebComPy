---
title: Testing API
description: API reference for webcompy_testing component rendering, ASGI helpers, fake ports, and browser test runner.
---

# Testing API

<!-- author:start:intro -->
API reference for `webcompy_testing`: synchronous/async component rendering (`TestRenderer`), ASGI test app helpers, fake port implementations, DI scope utilities, and `webcompy_testing.browser_runner` PyScript test orchestration.
<!-- author:end:intro -->

<!-- generated:start -->

## Test Renderer, ASGI Client & Fake Ports

### create_test_app

```python
def create_test_app(
    *,
    root_component: ComponentGenerator,
    **config_overrides: Any,
) -> WebComPyApp
```

Key: `webcompy_testing._scope:create_test_app` · Exports: `from webcompy_testing import create_test_app`

Create a `WebComPyApp` configured for testing.

**Args:**

- `root_component`: Root component for the test app.
- `**config_overrides`: Fields forwarded to `WebComPyAppConfig`.

**Returns:** A configured `WebComPyApp` ready for server-side rendering.

### create_test_asgi_app

```python
def create_test_asgi_app(app: WebComPyApp) -> ASGIApp
```

Key: `webcompy_testing._asgi:create_test_asgi_app` · Exports: `from webcompy_testing import create_test_asgi_app`

Create a Starlette ASGI app that renders the WebComPy app.

**Args:**

- `app`: Application to serve via the test ASGI app.

**Returns:** An `ASGIApp` that renders the WebComPy app for incoming requests.

### FakeAsyncSchedulerPort

```python
class FakeAsyncSchedulerPort(AsyncSchedulerPort):
    def __init__(self) -> None
```

Key: `webcompy_testing._ports:FakeAsyncSchedulerPort` · Exports: `from webcompy_testing import FakeAsyncSchedulerPort`

Queue coroutines and expose a drainable pending-task surface.

#### Members

**`await_pending`** (async_method)

```python
async def await_pending(self, *, only_render: bool = False) -> None
```

Await pending coroutines.

**Args:**

- `only_render`: When `True`, await only render-phase coroutines; otherwise drain all.

**`drain`** (async_method)

```python
async def drain(self) -> None
```

Execute all queued coroutines, including those scheduled recursively.

**`schedule`** (method)

```python
def schedule(
    self,
    coro: Coroutine[Any, Any, Any],
    *,
    render: bool = False,
) -> asyncio.Task[Any]
```

Schedule a coroutine without running it.

**Args:**

- `coro`: Coroutine to queue.
- `render`: Whether the coroutine is part of the render phase.

**Returns:** A pending-task stand-in resembling `asyncio.Task`.

### FakeBrowserDOMPort

```python
class FakeBrowserDOMPort(ServerDOMPort):
    def __init__(self) -> None
```

Key: `webcompy_testing._ports:FakeBrowserDOMPort` · Exports: `from webcompy_testing import FakeBrowserDOMPort`

Provide an in-memory DOM with synthetic document listeners.

**Attributes:**

- `body`: Document body node.

#### Members

**`add_document_event_listener`** (method)

```python
def add_document_event_listener(
    self,
    event_type: str,
    handler: Any,
    *,
    capture: bool = False,
) -> Callable[[], None]
```

Register a document-level event listener.

**Args:**

- `event_type`: Event type to listen for.
- `handler`: Callback invoked when the event is dispatched.
- `capture`: Accepted for interface parity; the fake dispatches to registered handlers regardless of event phase.

**Returns:** A callable that removes the listener.

**`body`** (property)

```python
@property
def body(self) -> FakeDOMNode
```

Return the document body node.

**`create_comment`** (method)

```python
def create_comment(self, data: str) -> FakeDOMNode
```

Create a comment node.

**Args:**

- `data`: Comment text.

**Returns:** A new comment `FakeDOMNode`.

**`create_element`** (method)

```python
def create_element(self, tag: str) -> FakeDOMNode
```

Create an element node.

**Args:**

- `tag`: Tag name for the new element.

**Returns:** A new `FakeDOMNode` with the given tag.

**`create_text_node`** (method)

```python
def create_text_node(self, text: str) -> FakeDOMNode
```

Create a text node.

**Args:**

- `text`: Text content for the node.

**Returns:** A new text `FakeDOMNode`.

**`dispatch_document_event`** (method)

```python
def dispatch_document_event(self, event_type: str, event: Any = None) -> None
```

Dispatch a synthetic document event.

**Args:**

- `event_type`: Event type to dispatch.
- `event`: Payload forwarded to registered handlers.

**`get_element_by_id`** (method)

```python
def get_element_by_id(self, element_id: str) -> FakeDOMNode | None
```

Return the element with the given identifier.

**Args:**

- `element_id`: Value of the `id` attribute to search for.

**Returns:** The matching node or `None`.

**`query_selector`** (method)

```python
def query_selector(self, selector: str) -> FakeDOMNode | None
```

Find the first node matching a simple selector.

**Args:**

- `selector`: CSS selector supporting tag, `#id`, or `tag[attr="value"]`.

**Returns:** The first matching node or `None` when no match exists.

**`query_selector_all`** (method)

```python
def query_selector_all(self, selector: str, *, root: Any | None = None) -> list[FakeDOMNode]
```

Find all nodes matching `selector` within `root` or document.

**Args:**

- `selector`: CSS selector string. Comma-separated groups and `:not()` are supported for the overlay use case.
- `root`: Optional subtree root.

**Returns:** Matching nodes in document order.

### FakeBrowserFFIPort

```python
class FakeBrowserFFIPort(FFIPort)
```

Key: `webcompy_testing._ports:FakeBrowserFFIPort` · Exports: `from webcompy_testing import FakeBrowserFFIPort`

Provide `FFIPort` behavior without a JavaScript bridge.

#### Members

**`assign`** (method)

```python
def assign(self, target: Any, source: Any) -> None
```

Merge `source` into `target`.

**Args:**

- `target`: Mapping to update.
- `source`: Mapping whose entries are copied into `target`.

**`create_proxy`** (method)

```python
def create_proxy(self, func: Any) -> Any
```

Create a mock proxy that forwards calls to `func`.

**Args:**

- `func`: Callable to wrap.

**Returns:** A `MagicMock` proxy with a `destroy` method.

**`destroy_proxy`** (method)

```python
def destroy_proxy(self, proxy: Any) -> None
```

Destroy a proxy created by `create_proxy`.

**Args:**

- `proxy`: Proxy to destroy.

**`is_none`** (method)

```python
def is_none(self, value: Any) -> bool
```

Check whether a value is `None`.

**Args:**

- `value`: Value to test.

**Returns:** `True` when `value` is `None`.

**`to_js`** (method)

```python
def to_js(self, value: Any, **kwargs: Any) -> Any
```

Return the value unchanged as a JS equivalent.

**Args:**

- `value`: Value to convert.
- `**kwargs`: Additional conversion options.

**Returns:** `value` unchanged.

### FakeBrowserHostPort

```python
class FakeBrowserHostPort(HostPort):
    def __init__(self, dom_port: FakeBrowserDOMPort | None = None) -> None
```

Key: `webcompy_testing._ports:FakeBrowserHostPort` · Exports: `from webcompy_testing import FakeBrowserHostPort`

Provide synthetic window events and macro-task scheduling.

#### Members

**`add_window_event_listener`** (method)

```python
def add_window_event_listener(self, event_type: str, handler: Any) -> Callable[[], None]
```

Register a window-level event listener.

**Args:**

- `event_type`: Event type to listen for.
- `handler`: Callback invoked when the event is dispatched.

**Returns:** A callable that removes the listener.

**`create_js_global_getter`** (method)

```python
def create_js_global_getter(
    self,
    name: str,
    *,
    wrapper: Any = None,
    default: Any = None,
) -> Any
```

Create a getter for a synthetic JavaScript global.

**Args:**

- `name`: Global name.
- `wrapper`: Optional wrapper applied to the retrieved value.
- `default`: Value returned when no wrapper is provided.

**Returns:** A zero-argument getter returning the wrapped or default value.

**`dispatch_window_event`** (method)

```python
def dispatch_window_event(self, event_type: str, event: Any = None) -> None
```

Dispatch a synthetic window event.

**Args:**

- `event_type`: Event type to dispatch.
- `event`: Payload forwarded to registered handlers.

**`schedule_macro_task`** (method)

```python
def schedule_macro_task(self, callback: Any) -> None
```

Execute a macro task immediately.

**Args:**

- `callback`: Callable to invoke synchronously.

### FakeCustomElementPort

```python
class FakeCustomElementPort(CustomElementPort):
    def __init__(self) -> None
```

Key: `webcompy_testing._ports:FakeCustomElementPort` · Exports: `from webcompy_testing import FakeCustomElementPort`

Record custom-element registrations and bindings for assertions.

**Attributes:**

- `ensure_defined_calls`: Recorded `(name, observed_attributes, definition_key)` definition requests.
- `bind_calls`: Recorded `(node, observed_attributes)` binding requests.
- `disposed_bindings`: Number of bindings disposed so far.
- `connected`: Connection state returned by `is_document_connected`.

#### Members

**`bind`** (method)

```python
def bind(
    self,
    node: Any,
    *,
    observed_attributes: tuple[str, ...],
    on_connected: Any = None,
    on_disconnected: Any = None,
    on_attribute_changed: Any = None,
) -> CustomElementBinding
```

Record a binding and return a disposable handle.

**Args:**

- `node`: DOM node to bind.
- `observed_attributes`: Attributes observed by the binding.
- `on_connected`: Callback invoked when connected.
- `on_disconnected`: Callback invoked when disconnected.
- `on_attribute_changed`: Callback invoked on attribute changes.

**Returns:** A binding handle whose `dispose` increments the counter.

**`ensure_defined`** (method)

```python
def ensure_defined(
    self,
    name: str,
    observed_attributes: tuple[str, ...],
    definition_key: str,
) -> None
```

Record a custom-element definition request.

**Args:**

- `name`: Custom element tag name.
- `observed_attributes`: Attributes observed by the element.
- `definition_key`: Deduplication key for the definition.

**`is_document_connected`** (method)

```python
def is_document_connected(self, node: Any) -> bool
```

Report whether a node is considered document-connected.

**Args:**

- `node`: Node to check.

**Returns:** `True` if the fake is configured as connected or the node reports `isConnected`.

### FakeDOMNode

```python
class FakeDOMNode(VirtualDOMNode):
    def __init__(
        self,
        tag: str = 'div',
        text_content: str | None = None,
        *,
        node_type: int | None = None,
    ) -> None
```

Key: `webcompy_testing._dom:FakeDOMNode` · Exports: `from webcompy_testing import FakeDOMNode`

Provide a test double for `VirtualDOMNode` with write tracking.

**Args:**

- `tag`: Tag name for the node.
- `text_content`: Initial text content for text/comment nodes.
- `node_type`: Explicit DOM node type override.

**Attributes:**

- `textContent_write_count`: Number of times `textContent` was written on this node.
- `setAttribute_count`: Number of times `setAttribute` was called on this node.

#### Members

**`focus`** (method)

```python
def focus(self) -> None
```

Simulate focusing this node by updating the containing document's active element.

**`setAttribute`** (method)

```python
def setAttribute(self, name: str, value: str | None) -> None
```

Assign an attribute and increment the write counter.

**Args:**

- `name`: Attribute name.
- `value`: Attribute value or `None` to remove the attribute.

**`splitText`** (method)

```python
def splitText(self, offset: int) -> FakeDOMNode
```

Split a text node at a UTF-16 offset and insert the remainder.

**Args:**

- `offset`: UTF-16 code-unit offset at which to split.

**Returns:** The newly created sibling text node containing the tail.

**Raises:**

- `TypeError`: If the node is not a text node.
- `IndexError`: If `offset` is out of range.

### FakeEventSourcePort

```python
class FakeEventSourcePort(EventSourcePort):
    def __init__(self) -> None
```

Key: `webcompy_testing._ports:FakeEventSourcePort` · Exports: `from webcompy_testing import FakeEventSourcePort`

Track server-sent-event subscriptions and allow synthetic events.

**Attributes:**

- `open_calls`: Recorded `(url, events)` subscription requests.
- `open_connections`: Currently active `(url, events)` subscriptions.

#### Members

**`emit_close`** (method)

```python
def emit_close(self, url: str) -> None
```

Trigger `on_close` for subscriptions to `url`.

**Args:**

- `url`: Event source URL.

**`emit_error`** (method)

```python
def emit_error(self, url: str) -> None
```

Trigger `on_error` for subscriptions to `url`.

**Args:**

- `url`: Event source URL.

**`emit_event`** (method)

```python
def emit_event(self, url: str, event_type: str, data: str, last_event_id: str = '') -> None
```

Emit a message event to matching subscriptions.

**Args:**

- `url`: Event source URL.
- `event_type`: Event type.
- `data`: Event payload.
- `last_event_id`: Last event identifier.

**`emit_open`** (method)

```python
def emit_open(self, url: str) -> None
```

Trigger `on_open` for subscriptions to `url`.

**Args:**

- `url`: Event source URL.

**`open`** (method)

```python
def open(
    self,
    url: str,
    *,
    events: tuple[str, ...],
    on_open: Any = None,
    on_message: Any = None,
    on_error: Any = None,
    on_close: Any = None,
) -> Callable[[], None]
```

Register a synthetic event-source subscription.

**Args:**

- `url`: Event source URL.
- `events`: Event types to subscribe to.
- `on_open`: Callback invoked when the connection opens.
- `on_message`: Callback invoked for incoming messages.
- `on_error`: Callback invoked on connection error.
- `on_close`: Callback invoked when the connection closes.

**Returns:** A callable that unregisters the subscription.

**`open_connections`** (property)

```python
@property
def open_connections(self) -> list[tuple[str, tuple[str, ...]]]
```

Return active event-source subscriptions.

### FakeFetchPort

```python
class FakeFetchPort(FetchPort):
    def __init__(
        self,
        responses: dict[tuple[str, str], Response] | None = None,
        streams: dict[tuple[str, str], list[str]] | None = None,
    ) -> None
```

Key: `webcompy_testing._ports:FakeFetchPort` · Exports: `from webcompy_testing import FakeFetchPort`

Serve canned fetch responses and streams for assertions.

**Args:**

- `responses`: Mapping from `(method, url)` to canned `Response`.
- `streams`: Mapping from `(method, url)` to scripted chunk lists.

**Attributes:**

- `aborted_streams`: Recorded `(method, url)` pairs of streams closed before completion.
- `requests`: Recorded requests in arrival order.

#### Members

**`fetch`** (async_method)

```python
async def fetch(
    self,
    url: str,
    *,
    method: str = 'GET',
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
) -> Response
```

Return a canned response for the requested URL.

**Args:**

- `url`: Target URL.
- `method`: HTTP method.
- `headers`: Optional request headers.
- `body`: Optional request body as text or bytes.

**Returns:** The canned `Response` for `(method, url)`.

**Raises:**

- `KeyError`: If no response is registered for the key.

**`stream`** (async_method)

```python
async def stream(
    self,
    url: str,
    *,
    method: str = 'GET',
    headers: dict[str, str] | None = None,
    body: str | bytes | None = None,
) -> FetchStream
```

Return a scripted stream for the requested URL.

**Args:**

- `url`: Target URL.
- `method`: HTTP method.
- `headers`: Optional request headers.
- `body`: Optional request body as text or bytes.

**Returns:** A `FetchStream` yielding the scripted chunks.

**Raises:**

- `KeyError`: If no stream or response is registered for the key.

### FakeHistoryPort

```python
class FakeHistoryPort(HistoryPort):
    def __init__(
        self,
        *,
        mode: Literal['hash', 'history'] = 'history',
        initial_path: str = '/',
    ) -> None
```

Key: `webcompy_testing._ports:FakeHistoryPort` · Exports: `from webcompy_testing import FakeHistoryPort`

Record history navigation calls for assertions.

**Args:**

- `mode`: Router mode to simulate.
- `initial_path`: Initial path for the history.

**Attributes:**

- `pushed_urls`: Recorded `(path, state)` pairs passed to `push_url`.
- `replaced_urls`: Recorded `(path, state)` pairs passed to `replace_url`.

#### Members

**`current_search`** (method)

```python
def current_search(self) -> str
```

Return the current search string.

**Returns:** An empty search string in the fake implementation.

**`history_state`** (method)

```python
def history_state(self) -> object | None
```

Return the current history state.

**Returns:** The stored navigation state.

**`push_url`** (method)

```python
def push_url(self, path: str, state: dict[str, Any] | None = None) -> None
```

Record a push navigation.

**Args:**

- `path`: Path to push.
- `state`: Optional navigation state.

**`refresh_from_window`** (method)

```python
def refresh_from_window(self) -> None
```

Synchronize the fake history with the window location.

**`replace_url`** (method)

```python
def replace_url(self, path: str, state: dict[str, Any] | None = None) -> None
```

Record a replace navigation.

**Args:**

- `path`: Path to replace the current entry with.
- `state`: Optional navigation state.

### FakeMediaQueryPort

```python
class FakeMediaQueryPort(MediaQueryPort):
    def __init__(
        self,
        *,
        prefers_dark: bool = False,
        prefers_reduced_motion: bool = False,
    ) -> None
```

Key: `webcompy_testing._ports:FakeMediaQueryPort` · Exports: `from webcompy_testing import FakeMediaQueryPort`

Provide controllable media-query values for tests.

**Args:**

- `prefers_dark`: Initial value for `prefers_dark`.
- `prefers_reduced_motion`: Initial value for `prefers_reduced_motion`.

#### Members

**`prefers_dark`** (method)

```python
def prefers_dark(self) -> bool
```

Return the configured dark-mode preference.

**Returns:** `True` if dark mode is preferred.

**`prefers_reduced_motion`** (method)

```python
def prefers_reduced_motion(self) -> bool
```

Return the configured reduced-motion preference.

**Returns:** `True` if reduced motion is preferred.

**`set_prefers_reduced_motion`** (method)

```python
def set_prefers_reduced_motion(self, value: bool) -> None
```

Update the reduced-motion preference.

**Args:**

- `value`: New preference value.

### FakeTransitionPort

```python
class FakeTransitionPort(TransitionPort):
    def __init__(self) -> None
```

Key: `webcompy_testing._ports:FakeTransitionPort` · Exports: `from webcompy_testing import FakeTransitionPort`

Transition port driven by a logical frame queue and virtual clock.

`flush_frame()` executes the callbacks scheduled for the next frame and `advance_time(ms)` moves the virtual clock forward, firing due timeouts. Per-node computed styles are registered via `set_style`.

**Attributes:**

- `enabled`: Whether transition callbacks run; toggled with `set_enabled`.

#### Members

**`advance_time`** (method)

```python
def advance_time(self, ms: float) -> None
```

Advance the virtual clock and fire due timeouts.

**Args:**

- `ms`: Milliseconds to advance.

**`enabled`** (property)

```python
@property
def enabled(self) -> bool
```

Return whether transitions are enabled.

**`flush_all`** (method)

```python
def flush_all(self) -> None
```

Flush one frame and advance the clock to fire all timeouts.

**`flush_frame`** (method)

```python
def flush_frame(self) -> None
```

Execute callbacks scheduled for the next frame.

**`get_computed_style`** (method)

```python
def get_computed_style(self, node: DOMNode) -> TransitionStyle
```

Return the fake computed style for a node.

**Args:**

- `node`: Node whose style is requested.

**Returns:** A `TransitionStyle` reflecting values set via `set_style`.

**`schedule_next_frame`** (method)

```python
def schedule_next_frame(self, callback: Callable[[], Any]) -> Callable[[], None]
```

Schedule a callback for the next frame.

**Args:**

- `callback`: Callable invoked on the next flushed frame.

**Returns:** A callable that cancels the scheduled frame callback.

**`schedule_timeout`** (method)

```python
def schedule_timeout(
    self,
    callback: Callable[[], Any],
    delay_ms: float,
) -> Callable[[], None]
```

Schedule a callback after a delay on the virtual clock.

**Args:**

- `callback`: Callable to invoke when the timeout fires.
- `delay_ms`: Delay in milliseconds.

**Returns:** A callable that cancels the scheduled timeout.

**`set_enabled`** (method)

```python
def set_enabled(self, value: bool) -> None
```

Enable or disable transition callbacks.

**Args:**

- `value`: `True` to enable transitions.

**`set_style`** (method)

```python
def set_style(self, node: FakeDOMNode, name: str, value: str) -> None
```

Set a CSS property in the fake computed-style table.

**Args:**

- `node`: Node to associate the style with.
- `name`: CSS property name.
- `value`: CSS property value.

### FakeWebSocketPort

```python
class FakeWebSocketPort(WebSocketPort):
    def __init__(self) -> None
```

Key: `webcompy_testing._ports:FakeWebSocketPort` · Exports: `from webcompy_testing import FakeWebSocketPort`

Track WebSocket connections and allow synthetic message injection.

**Attributes:**

- `open_calls`: Recorded `(url, protocols)` connection requests.
- `open_connections`: Currently active `(url, protocols)` registrations.

#### Members

**`emit_binary`** (method)

```python
def emit_binary(self, url: str, protocols: tuple[str, ...] | None = None) -> None
```

Trigger `on_binary` for matching registrations.

**Args:**

- `url`: WebSocket URL.
- `protocols`: Protocols to match or `None` for any.

**`emit_close`** (method)

```python
def emit_close(
    self,
    url: str,
    code: int = 1000,
    reason: str = '',
    was_clean: bool = True,
    protocols: tuple[str, ...] | None = None,
) -> None
```

Close matching registrations and trigger `on_close`.

**Args:**

- `url`: WebSocket URL.
- `code`: Close status code.
- `reason`: Close reason.
- `was_clean`: Whether the close was clean.
- `protocols`: Protocols to match or `None` for any.

**`emit_error`** (method)

```python
def emit_error(self, url: str, protocols: tuple[str, ...] | None = None) -> None
```

Trigger `on_error` for matching registrations.

**Args:**

- `url`: WebSocket URL.
- `protocols`: Protocols to match or `None` for any.

**`emit_message`** (method)

```python
def emit_message(
    self,
    url: str,
    text: str,
    protocols: tuple[str, ...] | None = None,
) -> None
```

Deliver a text message to matching registrations.

**Args:**

- `url`: WebSocket URL.
- `text`: Message payload.
- `protocols`: Protocols to match or `None` for any.

**`emit_open`** (method)

```python
def emit_open(self, url: str, protocols: tuple[str, ...] | None = None) -> None
```

Trigger `on_open` for matching WebSocket registrations.

**Args:**

- `url`: WebSocket URL.
- `protocols`: Protocols to match or `None` for any.

**`open`** (method)

```python
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
) -> WebSocketConnection
```

Register a synthetic WebSocket connection.

**Args:**

- `url`: WebSocket URL.
- `protocols`: Subprotocols requested for the connection.
- `on_open`: Callback invoked when the connection opens.
- `on_message`: Callback invoked for text messages.
- `on_binary`: Callback invoked for binary messages.
- `on_error`: Callback invoked on connection error.
- `on_close`: Callback invoked when the connection closes.

**Returns:** A connection handle that records sent frames.

**`open_connections`** (property)

```python
@property
def open_connections(self) -> list[tuple[str, tuple[str, ...]]]
```

Return active WebSocket registrations.

**`sent_frames`** (method)

```python
def sent_frames(self, url: str, protocols: tuple[str, ...] | None = None) -> list[str]
```

Return payloads sent via matching WebSocket registrations.

**Args:**

- `url`: WebSocket URL.
- `protocols`: Protocols to match or `None` for any.

**Returns:** Concatenated list of sent text frames.

### format_html

```python
def format_html(html: str) -> str
```

Key: `webcompy_testing._asgi:format_html` · Exports: `from webcompy_testing import format_html`

Format raw HTML for readable output.

**Args:**

- `html`: Raw HTML string to format.

**Returns:** Pretty-printed HTML string produced by BeautifulSoup.

### mock_app_run

```python
def mock_app_run() -> Iterator[None]
```

Key: `webcompy_testing._app:mock_app_run` · Exports: `from webcompy_testing import mock_app_run`

Suppress `WebComPyApp.run` inside the context.

**Yields:** None: Control to the caller while `WebComPyApp.run` is replaced with a no-op; the original method is restored on exit.

### RecordedRequest

```python
class RecordedRequest:
    method: str
    url: str
    headers: dict[str, str]
    body: str | bytes | None
```

Key: `webcompy_testing._ports:RecordedRequest` · Exports: `from webcompy_testing import RecordedRequest`

A fetch request observed by a fake fetch port.

**Attributes:**

- `method`: HTTP method of the observed request.
- `url`: Target URL of the observed request.
- `headers`: Request headers mapping.
- `body`: Request body (text or bytes), or `None`.

### render_app_html_sync

```python
def render_app_html_sync(app: WebComPyApp, path: str = '/', **kwargs: Any) -> str
```

Key: `webcompy_testing._asgi:render_app_html_sync` · Exports: `from webcompy_testing import render_app_html`

Render an app to an HTML string synchronously.

**Args:**

- `app`: Application to render.
- `path`: Route path to render.
- `**kwargs`: Additional options forwarded to `generate_html`.

**Returns:** Rendered HTML string for the requested path.

### restore_signal_values

```python
def restore_signal_values(component: Any, signals_data: dict[str, Any] | None) -> None
```

Key: `webcompy_testing._restore:restore_signal_values` · Exports: `from webcompy_testing import restore_signal_values`

Restore signal values for testing round-trip scenarios.

Directly assigns each value to `signal._value` without re-decoding or triggering reactive notifications. Intended for use in test code that manually constructs signal members and hydration data; not part of the production hydration pipeline (which uses factory-skip via `use_state()` / `use_reactive_list()` / `use_reactive_dict()`).

Callers that construct signals_data by hand should run `decode()` on each value before passing it in.

**Args:**

- `component`: Component instance exposing `__signal_members__`; values are assigned to the signals found there.
- `signals_data`: Mapping of signal attribute names to already-decoded values. `None` or empty skips restoration entirely.

### run_sync

```python
def run_sync(coro: Coroutine[Any, Any, T]) -> T
```

Key: `webcompy_testing._utils:run_sync` · Exports: `from webcompy_testing import run_sync`

Run a coroutine, handling nested event loops from pytest-asyncio.

**Args:**

- `coro`: Coroutine to execute.

**Returns:** The coroutine's result.

### TestRenderer

```python
class TestRenderer
```

Key: `webcompy_testing._renderer:TestRenderer` · Exports: `from webcompy_testing import TestRenderer`

Mount WebComPy components into a fake DOM for assertions.

#### Members

**`render`** (method)

```python
@staticmethod
def render(
    component: ComponentGenerator,
    *,
    parent_scope: DIScope | None = None,
) -> TestRendererResult
```

Render a component into an isolated fake DOM.

**Args:**

- `component`: Component generator to mount.
- `parent_scope`: Optional parent DI scope for the render.

**Returns:** A `TestRendererResult` holding the mounted tree and scopes.

### TestRendererResult

```python
class TestRendererResult:
    def __init__(
        self,
        component: ComponentGenerator,
        instance: object,
        parent_node: VirtualDOMNode,
        scope: DIScope,
        di_token: contextvars.Token | None = None,
    ) -> None
```

Key: `webcompy_testing._renderer:TestRendererResult` · Exports: `from webcompy_testing import TestRendererResult`

Hold the rendered component tree and its DI scope.

Provides query helpers and accessors for fake ports installed during rendering.

**Args:**

- `component`: Component generator that was rendered.
- `instance`: Root component instance.
- `parent_node`: Virtual DOM parent node containing the mounted tree.
- `scope`: DI scope used for the render.
- `di_token`: Token for resetting the active DI scope, or `None`.

**Attributes:**

- `body_node`: Fake document body node, or `None` when no fake DOM port is installed.
- `transition_port`: `FakeTransitionPort` installed for the render, or `None`.
- `media_query_port`: `FakeMediaQueryPort` installed for the render, or `None`.
- `event_source_port`: `FakeEventSourcePort` installed for the render, or `None`.
- `websocket_port`: `FakeWebSocketPort` installed for the render, or `None`.

#### Members

**`assert_element_count`** (method)

```python
def assert_element_count(self, tag: str, count: int) -> None
```

Assert that `count` elements with `tag` exist.

**Args:**

- `tag`: Tag name to count.
- `count`: Expected number of elements.

**`assert_has_class`** (method)

```python
def assert_has_class(self, cls: str) -> None
```

Assert that the root element contains a CSS class.

**Args:**

- `cls`: Class name expected on the root element.

**`body_node`** (property)

```python
@property
def body_node(self) -> VirtualDOMNode | None
```

Return the fake document body node.

**`close`** (method)

```python
def close(self) -> None
```

Dispose the DI scope and reset the active scope token.

**`event_source_port`** (property)

```python
@property
def event_source_port(self) -> FakeEventSourcePort | None
```

Return the `FakeEventSourcePort` installed for the render.

**`find_by_attribute`** (method)

```python
def find_by_attribute(self, name: str, value: str) -> VirtualDOMNode | None
```

Find a node by attribute value.

**Args:**

- `name`: Attribute name.
- `value`: Expected attribute value.

**Returns:** The first matching node or `None`.

**`find_by_text`** (method)

```python
def find_by_text(self, text: str) -> VirtualDOMNode | None
```

Find a node by exact text content.

**Args:**

- `text`: Text to match against `textContent`.

**Returns:** The first matching node or `None`.

**`media_query_port`** (property)

```python
@property
def media_query_port(self) -> FakeMediaQueryPort | None
```

Return the `FakeMediaQueryPort` installed for the render.

**`query_selector`** (method)

```python
def query_selector(self, tag: str) -> VirtualDOMNode | None
```

Return the first node with the given tag.

**Args:**

- `tag`: Tag name to search for.

**Returns:** The first matching node or `None`.

**`query_selector_all`** (method)

```python
def query_selector_all(self, tag: str) -> list[VirtualDOMNode]
```

Return all nodes with the given tag.

**Args:**

- `tag`: Tag name to search for.

**Returns:** List of matching nodes.

**`to_html`** (method)

```python
def to_html(self, *, pretty: bool = False) -> str
```

Render the mounted tree to an HTML string.

**Args:**

- `pretty`: Whether to pretty-print the HTML.

**Returns:** HTML string for the mounted component tree.

**`transition_port`** (property)

```python
@property
def transition_port(self) -> FakeTransitionPort | None
```

Return the `FakeTransitionPort` installed for the render.

**`websocket_port`** (property)

```python
@property
def websocket_port(self) -> FakeWebSocketPort | None
```

Return the `FakeWebSocketPort` installed for the render.

## Browser Test Runner

### bootstrap

```python
def bootstrap() -> None
```

Key: `webcompy_testing.browser_runner._runner:bootstrap` · Exports: `from webcompy_testing.browser_runner import bootstrap`

Expose `run_one` / `evaluate` on `window` and mark the harness page ready.

### evaluate

```python
async def evaluate(code: str) -> str
```

Key: `webcompy_testing.browser_runner._runner:evaluate` · Exports: `from webcompy_testing.browser_runner import evaluate`

Evaluate Python code inside the harness interpreter.

The last expression's value is returned as its `repr` (`None` for statement-only code), mirroring a REPL. State persists across calls via the shared globals dict. Unlike `run_one`, the console error delta is emitted as structured `{"type", "text"}` objects.

**Args:**

- `code`: Python source to evaluate; may span multiple lines and use top-level `await`.

**Returns:** JSON string of shape `{"stdout", "stderr", "result_repr", "console_error_delta", "exc_type", "traceback"}`. Evaluation failures are reported in the payload instead of raising.

### normalize_traceback

```python
def normalize_traceback(text: str) -> str
```

Key: `webcompy_testing.browser_runner._runner:normalize_traceback` · Exports: `from webcompy_testing.browser_runner import normalize_traceback`

Rewrite Emscripten FS source paths back to repo-relative paths.

### parse_test_id

```python
def parse_test_id(test_id: str) -> tuple[str, str, int | None]
```

Key: `webcompy_testing.browser_runner._runner:parse_test_id` · Exports: `from webcompy_testing.browser_runner import parse_test_id`

Split a dispatched test id into module name, qualname, and param index.

### resolve_parametrize_payload

```python
def resolve_parametrize_payload(func: Any, param_index: int | None) -> dict[str, Any]
```

Key: `webcompy_testing.browser_runner._runner:resolve_parametrize_payload` · Exports: `from webcompy_testing.browser_runner import resolve_parametrize_payload`

Resolve `@pytest.mark.parametrize` values for the given index.

### resolve_qualname_target

```python
def resolve_qualname_target(container: Any, qualname: str) -> Any
```

Key: `webcompy_testing.browser_runner._runner:resolve_qualname_target` · Exports: `from webcompy_testing.browser_runner import resolve_qualname_target`

Resolve a `::`-separated qualname to a callable, binding methods.

When the qualname path addresses a method through a class (for example `TestDIScope::test_class_type_key`), the class is instantiated with no arguments and the attribute is fetched from the instance so the returned callable is a bound method. This mirrors pytest's auto-instantiation of test classes and keeps `self` out of the fixture-argument resolution.

**Args:**

- `container`: The module (or any object) in which to resolve.
- `qualname`: The `::`-separated attribute path.

**Returns:** The resolved callable.

**Raises:**

- `TypeError`: If the resolved target is not callable.

### run_one

```python
async def run_one(test_id: str) -> str
```

Key: `webcompy_testing.browser_runner._runner:run_one` · Exports: `from webcompy_testing.browser_runner import run_one`

Execute one browser test function and return its result as a JSON string.

### skip

```python
def skip(reason: str = 'skipped') -> None
```

Key: `webcompy_testing.browser_runner._runner:skip` · Exports: `from webcompy_testing.browser_runner import skip`

Raise a skip signal that maps to a skipped pytest outcome.

### UnknownFixtureError

```python
class UnknownFixtureError(NameError):
    def __init__(self, name: str) -> None
```

Key: `webcompy_testing.browser_runner._runner:UnknownFixtureError` · Exports: `from webcompy_testing.browser_runner import UnknownFixtureError`

Raised when a browser test declares a parameter outside the fixture registry.

<!-- generated:end -->

## Next steps

<!-- author:start:see-also -->
- Testing & serving guides: [Testing](/documents/server/testing), [ASGI Integration](/documents/server/asgi-integration), and [Serving Modes](/documents/server/serving-modes).
<!-- author:end:see-also -->
