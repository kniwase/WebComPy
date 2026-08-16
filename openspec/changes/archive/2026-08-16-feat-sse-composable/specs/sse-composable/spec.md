# SSE Composable Specification (delta)

## ADDED Requirements

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

The framework SHALL maintain a connection registry scoped to the app DI scope (never module-global), keyed by `(transport, url)`. For a given key:

- the first subscriber SHALL open one underlying connection through the transport port;
- subsequent `use_event_source` calls with the same URL SHALL attach to the same underlying connection without opening another, provided they request no event types beyond those already registered;
- when a subsequent subscriber requests event types not covered by the existing connection, the registry SHALL close the existing underlying connection and open a new one with the union of all currently requested event types; subscribers of the same URL then share the reopened connection;
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
