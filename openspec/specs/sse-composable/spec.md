# SSE Composable

## Purpose

Server-Sent Events (SSE) let a server push messages to the browser over a long-lived HTTP connection. WebComPy exposes them through `use_event_source`, the first network-occurrence composable: it returns a connection handle that is itself an `AsyncIterator[SSEvent]`, exposing `.state` (a `Signal[ConnectionState]` cell) and `.close()`. Unlike state signals, SSE messages have occurrence semantics — every arrival matters. This capability defines the composable's contract and the shared, app-DI-scope connection registry (multiplexing per `(transport, url)`, per-subscriber FIFO queues, reference-counted open/close) that additional realtime composables (e.g., WebSocket) will reuse.

## Requirements

### Requirement: use_event_source shall return a connection handle that is an async iterator of SSEvent

The framework SHALL provide `use_event_source(url, *, events=("message",), max_queue=None)` importable from `webcompy` and `webcompy.realtime`, returning a connection-handle object that:

- is itself an `AsyncIterator[SSEvent]`, so `async for ev in handle:` yields every received event in arrival order (occurrence semantics: duplicates are preserved, no equality suppression);
- exposes `.state: Signal[ConnectionState]` where `ConnectionState` is an enum with at least `CONNECTING`, `OPEN`, and `CLOSED` members; the state signal follows normal cell semantics;
- exposes `.close() -> None`.

The iterator surface is the primary API; users who need cell semantics SHALL bridge explicitly via `signal-stream` utilities (`to_signal`, `to_reactive_list`). The handle SHALL NOT register any hydration-transfer entry.

#### Scenario: Iterating received events
- **WHEN** a component calls `es = use_event_source("/events")` and the server sends two identical `message` events with data `"ping"`
- **THEN** `async for ev in es:` SHALL yield both events (no deduplication)
- **AND** each yielded item SHALL be an `SSEvent`

#### Scenario: State is a signal
- **WHEN** the underlying connection opens
- **THEN** `es.state.value` SHALL become `ConnectionState.OPEN`
- **AND** reactive consumers of `es.state` SHALL be notified

#### Scenario: Import paths
- **WHEN** a developer imports `use_event_source`
- **THEN** it SHALL be importable from both `webcompy` and `webcompy.realtime`

### Requirement: SSEvent shall carry event type, data, and last event id

`SSEvent` SHALL be a frozen dataclass with fields `event: str`, `data: str`, and `last_event_id: str`. The `events` parameter of `use_event_source` SHALL select which SSE event types are delivered; `("message",)` SHALL be the default. Events whose type is not in `events` SHALL NOT be delivered to the iterator.

#### Scenario: Default delivers message events
- **WHEN** `use_event_source("/events")` is called without `events`
- **AND** the server sends a `message` event with data `"hello"` and id `"7"`
- **THEN** the iterator SHALL yield `SSEvent(event="message", data="hello", last_event_id="7")`

#### Scenario: Named event types are selectable
- **WHEN** `use_event_source("/events", events=("status",))` is called
- **AND** the server sends a `status` event and a `message` event
- **THEN** only the `status` event SHALL be delivered

### Requirement: A shared connection registry shall multiplex subscribers per app DI scope

The framework SHALL maintain a connection registry scoped to the app DI scope (never module-global), keyed by `(transport, key_component)`, where the SSE transport's key component is the URL for GET connections and `(url, method, body, normalized headers)` for non-GET connections. Header normalization SHALL lower-case header names so equivalent headers spelled differently key identically, and SHALL treat `None` and `{}` as equivalent. For a given key:

- the first subscriber SHALL open one underlying connection through the transport;
- subsequent `use_event_source` calls with the same key SHALL attach to the same underlying connection without opening another. For `EventSource` (GET) connections, provided they request no event types beyond those already registered; fetch-based (non-GET) connections SHALL filter per subscriber and SHALL never reopen for event-type changes;
- when a subsequent GET subscriber requests event types not covered by the existing `EventSource` connection, the registry SHALL close the existing underlying connection and open a new one with the union of all currently requested event types; subscribers of the same URL then share the reopened connection;
- each subscriber SHALL receive its own FIFO queue, and the transport callback SHALL enqueue every event into every live subscriber queue, so a slow consumer SHALL NOT block or starve other subscribers;
- the registry SHALL reference-count subscribers: the underlying connection SHALL be closed when and only when the last subscriber detaches.

The registry and its keying SHALL be transport-agnostic so that additional realtime transports can reuse it without modifying this capability's requirements.

#### Scenario: Two consumers share one connection
- **WHEN** two components call `use_event_source("/events")` within the same app DI scope
- **THEN** exactly one underlying `EventSource` connection SHALL be opened
- **AND** both iterators SHALL receive every event independently

#### Scenario: Last detach closes the connection
- **WHEN** two subscribers share a connection and both call `.close()`
- **THEN** the underlying connection SHALL be closed after the second `.close()`
- **AND** it SHALL remain open after only the first `.close()`

#### Scenario: Different URLs do not share
- **WHEN** `use_event_source("/a")` and `use_event_source("/b")` are called
- **THEN** two separate underlying connections SHALL be opened

#### Scenario: New event types reopen the shared connection with the union
- **WHEN** subscriber A calls `use_event_source("/events", events=("message",))` and subscriber B then calls `use_event_source("/events", events=("status",))` within the same app DI scope
- **THEN** the first call SHALL open one underlying connection
- **AND** the second call SHALL close that connection and open a new one whose listeners cover both `message` and `status`
- **AND** both subscribers SHALL receive only the event types they requested

#### Scenario: Non-GET connections with different bodies do not share
- **WHEN** `use_event_source("/query", method="POST", body="a")` and `use_event_source("/query", method="POST", body="b")` are called within the same app DI scope
- **THEN** two separate underlying fetch connections SHALL be opened

#### Scenario: Identical non-GET requests share
- **WHEN** two components call `use_event_source("/query", method="POST", body="a")` within the same app DI scope
- **THEN** exactly one underlying fetch connection SHALL be opened

#### Scenario: Non-GET connections with different headers do not share
- **WHEN** `use_event_source("/query", method="POST", body="a", headers={"Authorization": "x"})` and `use_event_source("/query", method="POST", body="a", headers={"Authorization": "y"})` are called within the same app DI scope
- **THEN** two separate underlying fetch connections SHALL be opened

#### Scenario: Non-GET connections with equivalent headers share
- **WHEN** `use_event_source("/query", method="POST", body="a", headers={"Content-Type": "application/json"})` and `use_event_source("/query", method="POST", body="a", headers={"content-type": "application/json"})` are called within the same app DI scope
- **THEN** exactly one underlying fetch connection SHALL be opened

### Requirement: Subscriber queues shall be unbounded by default with opt-in drop-oldest capping

Each subscriber queue SHALL be unbounded by default. When `max_queue` is an `int`, the subscriber's queue SHALL keep only the newest `max_queue` events (drop-oldest, `collections.deque(maxlen=N)` semantics). Capping SHALL be per subscriber: one capped subscriber SHALL NOT affect other subscribers of the same connection.

#### Scenario: Unbounded default preserves every event
- **WHEN** a subscriber consumes slowly and 100 events arrive before the first `__anext__`
- **THEN** all 100 events SHALL be delivered in order

#### Scenario: max_queue drops oldest
- **WHEN** `use_event_source("/events", max_queue=2)` is used and three events arrive before consumption
- **THEN** the iterator SHALL yield only the second and third events

### Requirement: close() shall detach only the caller's own subscription

Calling `.close()` on a connection handle SHALL remove the caller's subscriber queue and decrement the registry reference count, and SHALL NOT close the underlying connection while other subscribers remain. After `.close()`, the caller's iterator SHALL finish (raise `StopAsyncIteration` on the next `__anext__`). `.close()` SHALL be idempotent.

#### Scenario: Close detaches self only
- **WHEN** subscribers A and B share a connection and A calls `.close()`
- **THEN** A's iterator SHALL finish
- **AND** B SHALL keep receiving events
- **AND** the underlying connection SHALL remain open

#### Scenario: Close is idempotent
- **WHEN** `.close()` is called twice on the same handle
- **THEN** no exception SHALL be raised

### Requirement: Absence of an app DI scope shall degrade to a private connection with a warning

When `use_event_source` is called and no app DI scope is available, the composable SHALL emit a `UserWarning` and SHALL create a dedicated, non-shared connection for that call instead of using the registry. The returned handle SHALL otherwise behave identically (iterator, `.state`, `.close()`), except that `.close()` closes the private connection directly.

#### Scenario: Standalone usage warns and still works
- **WHEN** `use_event_source("/events")` is called outside any app DI scope
- **THEN** a `UserWarning` SHALL be emitted
- **AND** a working connection handle SHALL be returned
- **AND** a second such call SHALL open a second, independent connection

#### Scenario: No port and no scope returns an empty closed handle
- **WHEN** `use_event_source("/events")` is called in an environment where neither an `EventSourcePort` nor an app DI scope is resolvable
- **THEN** a `UserWarning` SHALL be emitted
- **AND** a handle with an immediately-finished empty iterator and `state == ConnectionState.CLOSED` SHALL be returned
- **AND** no connection SHALL be opened

### Requirement: URLs shall be passed through to the browser-native EventSource without base_url prefixing

On the browser, the given URL (absolute or relative) SHALL be handed to the native `EventSource` constructor unchanged; the browser SHALL resolve relative URLs against the document URL. The composable SHALL NOT prepend `AppConfig.base_url` or otherwise rewrite the URL.

#### Scenario: Relative URL resolves against the document
- **WHEN** `use_event_source("/events")` is called on a page served at `/app/`
- **THEN** the native `EventSource` SHALL be constructed with the string `"/events"` unchanged

### Requirement: SSR shall return an empty finished handle with a warning and no hydration transfer

During SSR/SSG (no browser environment), `use_event_source` SHALL NOT access browser APIs: it SHALL return a handle whose iterator finishes immediately, whose `.state` is `ConnectionState.CLOSED`, and SHALL emit a warning. The handle, its state, and any received events SHALL NOT be collected into the hydration transfer payload. The SSR degradation SHALL apply when no `EventSourcePort` resolves or when the resolved port is the server no-op implementation; a non-noop port resolved outside the browser (e.g., a testing fake) SHALL open a connection through that port instead of degrading.

#### Scenario: SSG produces no connection
- **WHEN** a page using `use_event_source` is statically generated
- **THEN** no `EventSource` SHALL be constructed
- **AND** the handle's iterator SHALL be empty and `.state.value` SHALL be `ConnectionState.CLOSED`
- **AND** the hydration payload SHALL contain no entry for the handle

#### Scenario: Non-noop port outside the browser is not SSR
- **WHEN** `use_event_source` is called in a non-browser environment where a non-noop `EventSourcePort` (e.g., the `webcompy_testing` fake) resolves
- **THEN** the composable SHALL NOT return the SSR empty handle
- **AND** the composable SHALL open a connection through the resolved port

### Requirement: Component-scoped subscriptions shall be detached on component destroy

When `use_event_source` is called inside an active component setup context, the subscription SHALL be detached automatically on component destroy via `on_before_destroy` (chained with any existing hook). Abandoned iterators (e.g., `async for` exited via `break` without `aclose()`) SHALL be protected by `weakref.finalize`-based detachment so the registry reference count cannot leak.

#### Scenario: Component destroy detaches the subscription
- **WHEN** a component using `use_event_source` is destroyed
- **THEN** its subscriber queue SHALL be removed from the registry
- **AND** if it was the last subscriber, the underlying connection SHALL be closed
#### Scenario: Abandoned iterator does not leak the reference count

- **WHEN** a consumer iterates with `async for` and exits via `break` without calling `.close()`, and the handle is garbage-collected
- **THEN** the registry reference count SHALL be decremented as if `.close()` had been called

### Requirement: use_event_source shall reject invalid events and max_queue arguments

`use_event_source` SHALL validate its optional arguments before opening or resolving any connection. Passing `events` as a bare `str` SHALL raise `TypeError`; passing `events=()` SHALL raise `ValueError`; an `events` element that is not a non-empty `str` SHALL raise `TypeError`. `max_queue` SHALL be `None` or an `int` greater than or equal to 1; any other value SHALL raise `TypeError`, and an `int` less than 1 SHALL raise `ValueError`. Validation SHALL happen before any connection is opened: an invalid call SHALL NOT open an underlying connection, SHALL NOT resolve a port, and SHALL NOT emit a warning.

#### Scenario: Bare string events is rejected

- **WHEN** a developer calls `use_event_source("/events", events="message")`
- **THEN** a `TypeError` SHALL be raised
- **AND** no connection SHALL be opened

#### Scenario: Empty events is rejected

- **WHEN** a developer calls `use_event_source("/events", events=())`
- **THEN** a `ValueError` SHALL be raised
- **AND** no connection SHALL be opened

#### Scenario: max_queue below the minimum is rejected

- **WHEN** a developer calls `use_event_source("/events", max_queue=0)` or `max_queue=-1`
- **THEN** a `ValueError` SHALL be raised
- **AND** no connection SHALL be opened

### Requirement: use_event_source shall support non-GET requests through a fetch-based transport

`use_event_source` SHALL additionally accept `method: str = "GET"`, `body: str | None = None`, and `headers: dict[str, str] | None = None` keyword arguments. When `method` is `"GET"`, the composable SHALL behave exactly as before (browser-native `EventSource` transport). When `method` is any other non-empty string, the composable SHALL open a fetch-based SSE connection through the framework's streaming fetch capability, sending `body` as the request body and `headers` as request headers, and SHALL parse the response with the `sse-parser` codec, delivering events to subscribers as `SSEvent` instances with `last_event_id` taken from the parsed `id:` field. Passing `body` or `headers` together with `method="GET"` SHALL raise `ValueError`. Passing a `method` that is not a non-empty string SHALL raise `TypeError`. Validation SHALL happen before any connection is opened, before any port is resolved, and before any warning is emitted.

#### Scenario: POST request with a body is sent via fetch
- **WHEN** `use_event_source("/query", method="POST", body='{"q":"x"}', headers={"Content-Type": "application/json"}, events=("result",))` is called in the browser
- **THEN** a fetch-based connection SHALL be opened with `POST /query`, the given body and headers
- **AND** `result` events from the SSE response SHALL be delivered as `SSEvent` items

#### Scenario: GET with body is rejected
- **WHEN** `use_event_source("/events", body="x")` is called
- **THEN** a `ValueError` SHALL be raised
- **AND** no connection SHALL be opened

#### Scenario: GET path remains native EventSource
- **WHEN** `use_event_source("/events")` is called in the browser
- **THEN** the connection SHALL be opened through the native `EventSource` API exactly as before this change

### Requirement: Fetch-based SSE connections shall reconnect with Last-Event-ID until explicitly closed

A fetch-based connection SHALL expose state transitions `CONNECTING` → `OPEN` → `RECONNECTING` (on connection loss) → `OPEN`, and `CLOSED` only via explicit closure. When the fetch request fails to open, or the response status is not successful, or the response is not a `text/event-stream`-compatible body, or the body stream ends or errors, the connection SHALL enter `RECONNECTING` and SHALL retry after an exponential backoff delay (base 1 second, cap 30 seconds, uniform jitter factor in [0.5, 1.0], unlimited attempts). Reconnect attempts SHALL include a `Last-Event-ID` header carrying the most recent parsed event id once any id has been received. Only `.close()` (or the equivalent detachment/component-destroy paths) SHALL terminate the retry loop and set `CLOSED`.

#### Scenario: Body stream end triggers reconnect, not close
- **WHEN** a fetch-based connection's response body stream ends (server finished the response)
- **THEN** `state` SHALL become `RECONNECTING`
- **AND** a new fetch request SHALL be issued after a backoff delay
- **AND** `state` SHALL return to `OPEN` once that request's response starts streaming

#### Scenario: Reconnect carries the last event id
- **WHEN** a fetch-based connection has received an event with id `"7"` and the stream then ends
- **THEN** the reconnect request SHALL include the header `Last-Event-ID: 7`

#### Scenario: Unsuccessful handshake enters the retry loop
- **WHEN** the initial fetch request of a fetch-based connection receives a `500` status
- **THEN** `state` SHALL become `RECONNECTING` and retries SHALL be scheduled
- **AND** the retry loop SHALL continue until the connection is closed

#### Scenario: Close terminates the retry loop
- **WHEN** `.close()` is called on a fetch-based connection handle while it is `RECONNECTING`
- **THEN** no further fetch requests SHALL be issued
- **AND** `state` SHALL be `CLOSED`

### Requirement: Fetch-based SSE connections shall filter events per subscriber without reopening

Fetch-based connections SHALL read the full event stream once per underlying connection and SHALL deliver each parsed event only to subscribers whose requested `events` set contains the event's type. Because filtering is per-subscriber, a new subscriber requesting additional event types SHALL NOT cause the underlying fetch-based connection to reopen. Per-subscriber queues (`max_queue` semantics), reference counting, `close()` detachment, component-destroy cleanup, abandoned-iterator finalization, SSR/SSG degradation (empty finished handle, `CLOSED`, warning, no hydration transfer), and non-noop-port-outside-browser behavior SHALL apply to fetch-based connections exactly as they apply to `EventSource` connections.

#### Scenario: Event types are filtered per subscriber on a shared fetch connection
- **WHEN** subscriber A uses `events=("a",)` and subscriber B uses `events=("b",)` on the same non-GET request
- **THEN** one underlying fetch connection SHALL be opened
- **AND** an event of type `a` SHALL be delivered only to A
- **AND** an event of type `b` SHALL be delivered only to B
- **AND** the connection SHALL NOT reopen when B attaches

#### Scenario: SSR degradation applies to non-GET requests
- **WHEN** `use_event_source("/query", method="POST", body="{}")` is called during SSR/SSG
- **THEN** a `UserWarning` SHALL be emitted
- **AND** an immediately-finished empty handle with `state == ConnectionState.CLOSED` SHALL be returned
- **AND** no fetch request SHALL be issued

### Requirement: Non-GET URLs shall not be prefixed with base_url

For fetch-based connections, the given URL (absolute or relative) SHALL be passed to the streaming fetch capability unchanged; relative URLs SHALL resolve against the document URL. The composable SHALL NOT prepend `AppConfig.base_url` or otherwise rewrite the URL.

#### Scenario: Relative POST URL resolves against the document
- **WHEN** `use_event_source("/query", method="POST", body="{}")` is called on a page served at `/app/`
- **THEN** the fetch request SHALL be issued for the string `"/query"` unchanged