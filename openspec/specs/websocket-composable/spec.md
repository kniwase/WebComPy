# WebSocket Composable

## Purpose

WebSockets provide a bidirectional, full-duplex text channel between the browser and a server. WebComPy exposes them through `use_websocket`, the second network-occurrence composable: it returns a connection handle that is itself an `AsyncIterator[str]`, exposing `.state` (a `Signal[ConnectionState]` cell, extended additively with `RECONNECTING`), `.last_close` (a `Signal[CloseInfo | None]` cell), `.send()`, and `.close()`. The composable reuses the shared, app-DI-scope connection registry from `sse-composable` (multiplexing per `(transport, key)`, per-subscriber FIFO queues, reference-counted open/close) with a protocols-aware key component. Unlike native `EventSource`, native `WebSocket` has no automatic reconnection, so the framework owns a reconnect loop with exponential backoff and jitter.

## Requirements

### Requirement: use_websocket shall return a bidirectional connection handle that is an async iterator of text messages

The framework SHALL provide `use_websocket(url, *, protocols=None, max_queue=None, reconnect=True, reconnect_base_delay=1.0, reconnect_max_delay=30.0, reconnect_max_attempts=None, buffer_while_disconnected=False)` importable from `webcompy` and `webcompy.realtime`, returning a connection-handle object that:

- is itself an `AsyncIterator[str]` yielding every received text message in arrival order (occurrence semantics: duplicates preserved);
- exposes `.state: Signal[ConnectionState]` (the shared enum from `sse-composable`, extended additively with `RECONNECTING`);
- exposes `.last_close: Signal[CloseInfo | None]` where `CloseInfo` is a frozen dataclass with `code: int`, `reason: str`, `was_clean: bool`;
- exposes `.send(data: str) -> None` for text frames;
- exposes `.close() -> None` detaching only the caller's own subscription.

The handle SHALL NOT register any hydration-transfer entry. Binary frames received from the server SHALL be ignored with a warning.

#### Scenario: Iterating received text messages

- **WHEN** a component calls `ws = use_websocket("/ws")` and the server sends two identical text frames `"pong"`
- **THEN** `async for msg in ws:` SHALL yield both messages (no deduplication)

#### Scenario: Sending a text message while connected

- **WHEN** the connection state is `OPEN` and `ws.send("hello")` is called
- **THEN** exactly one text frame `"hello"` SHALL be sent on the underlying socket

#### Scenario: Binary frames are ignored with a warning

- **WHEN** the server sends a binary frame
- **THEN** a warning SHALL be emitted and no item SHALL be delivered to any subscriber iterator

### Requirement: use_websocket shall share connections through the realtime registry with protocols-aware keying

`use_websocket` SHALL use the shared connection registry from `sse-composable`. The registry key SHALL be `(transport, key)` where the WebSocket key component SHALL include the URL and the normalized `protocols` (sorted tuple, empty when `None`). Subscribers with identical URL and protocols SHALL share one underlying socket; differing URLs or differing protocols SHALL NOT share. Reference-counted open/close and per-subscriber FIFO queues (unbounded default; `max_queue` drop-oldest) SHALL behave as specified for the registry in `sse-composable`.

#### Scenario: Same URL and protocols share one socket

- **WHEN** two components call `use_websocket("/ws")` in the same app DI scope
- **THEN** exactly one underlying `WebSocket` SHALL be opened and both iterators SHALL receive every message independently

#### Scenario: Different protocols do not share

- **WHEN** `use_websocket("/ws")` and `use_websocket("/ws", protocols=["graphql-ws"])` are both used
- **THEN** two separate underlying sockets SHALL be opened

#### Scenario: No DI scope falls back with a warning

- **WHEN** `use_websocket("/ws")` is called with no app DI scope available
- **THEN** a `UserWarning` SHALL be emitted and a dedicated non-shared connection SHALL be created for that call

#### Scenario: Differing reconnection parameters warn on a shared connection

- **WHEN** a subsequent subscriber requests the same URL and protocols with reconnection parameters that differ from the existing shared connection
- **THEN** a `UserWarning` SHALL be emitted
- **AND** the existing connection's parameters SHALL remain in effect for the shared connection

### Requirement: use_websocket shall reconnect with exponential backoff and jitter after abnormal closure

When the underlying socket closes abnormally (any close other than user-initiated `.close()` or a clean server close with code `1000`) and `reconnect=True`, the shared connection SHALL attempt reconnection: the delay before attempt *n* SHALL be `min(reconnect_max_delay, reconnect_base_delay * 2**(n-1))` multiplied by a uniform random jitter factor in `[0.5, 1.0]`. Attempts SHALL be unlimited unless `reconnect_max_attempts` is an `int`, after which the connection SHALL transition to `CLOSED` and stop. During a backoff wait or in-flight reconnect attempt, `.state` SHALL be `RECONNECTING`; on success it SHALL become `OPEN` and iteration SHALL continue transparently. No reconnect SHALL occur after user-initiated `.close()`, after a clean `1000` close, or when `reconnect=False` (single failure transitions to `CLOSED`).

#### Scenario: Reconnect after abnormal closure

- **WHEN** an open connection drops with close code `1006` and `reconnect=True`
- **THEN** `.state` SHALL become `RECONNECTING`
- **AND** a reconnection attempt SHALL be scheduled with delay in `[0.5 * reconnect_base_delay, reconnect_base_delay]`
- **AND** on success `.state` SHALL become `OPEN` and subscribers SHALL keep receiving messages

#### Scenario: Backoff doubles up to the cap

- **WHEN** reconnection attempts fail repeatedly with `reconnect_base_delay=1.0` and `reconnect_max_delay=30.0`
- **THEN** successive attempt delays SHALL follow `1, 2, 4, 8, …` seconds (times jitter in `[0.5, 1.0]`) and SHALL never exceed `30.0` seconds before jitter

#### Scenario: No reconnect on clean close

- **WHEN** the server closes with code `1000`
- **THEN** `.state` SHALL become `CLOSED` and no reconnection SHALL be attempted

#### Scenario: Max attempts exhausts to CLOSED

- **WHEN** `reconnect_max_attempts=2` and both attempts fail
- **THEN** `.state` SHALL become `CLOSED` and no further attempts SHALL be scheduled

#### Scenario: A retry open failure does not silently stop the loop

- **WHEN** a reconnection attempt fails to open because the underlying connection cannot be constructed (the port raises)
- **THEN** a warning SHALL be emitted
- **AND** when `reconnect_max_attempts` is not exhausted another attempt SHALL be scheduled
- **AND** when `reconnect_max_attempts` is exhausted the connection SHALL transition to `CLOSED` and stop

### Requirement: use_websocket shall expose the most recent close information

`.last_close` SHALL be a signal holding a `CloseInfo` for the most recent close event of the underlying connection, or `None` if it has never closed. It SHALL be updated on every close, including closures that are later recovered by reconnection (it SHALL NOT be reset on reopen).

#### Scenario: Close info is recorded

- **WHEN** the connection closes with code `1006`, reason `"abnormal"`, unclean
- **THEN** `.last_close.value` SHALL be `CloseInfo(code=1006, reason="abnormal", was_clean=False)`

#### Scenario: Last close persists across reconnection

- **WHEN** the connection drops (code `1006`) and then reconnects successfully
- **THEN** `.last_close.value` SHALL still hold the `1006` `CloseInfo` while `.state.value` is `OPEN`

### Requirement: Disconnected sends shall warn and discard by default, with opt-in buffering

When `.send(data)` is called while the connection is not `OPEN`, the default behavior SHALL be to emit a warning and discard the data. When `buffer_while_disconnected=True`, disconnected sends SHALL be appended to a FIFO buffer (unbounded) and flushed in order on the next transition to `OPEN`. The buffer SHALL be discarded when the connection reaches a terminal `CLOSED` state.

#### Scenario: Default discards with a warning

- **WHEN** `ws.send("x")` is called while `.state` is `RECONNECTING` and buffering is not enabled
- **THEN** a warning SHALL be emitted and no frame SHALL be sent later for that call

#### Scenario: Opt-in buffer flushes on open

- **WHEN** `buffer_while_disconnected=True`, `ws.send("a")` and `ws.send("b")` are called during `RECONNECTING`, and the connection later opens
- **THEN** frames `"a"` then `"b"` SHALL be sent in that order upon opening

### Requirement: URLs shall be passed through to the native WebSocket constructor

On the browser, the given URL (absolute or relative) SHALL be handed to the native `WebSocket` constructor unchanged; the browser SHALL resolve relative URLs against the document base URL and map `http(s)` to `ws(s)`. The composable SHALL NOT prepend `AppConfig.base_url` or otherwise rewrite the URL.

#### Scenario: Relative URL passes through unchanged

- **WHEN** `use_websocket("/ws")` is called on a page served at `/app/`
- **THEN** the native `WebSocket` SHALL be constructed with the string `"/ws"` unchanged

### Requirement: SSR shall return an empty finished handle with a warning and no hydration transfer

During SSR/SSG, `use_websocket` SHALL NOT access browser APIs: it SHALL return a handle whose iterator finishes immediately, whose `.state` is `ConnectionState.CLOSED`, whose `.last_close` is `None`, whose `.send()` warns and discards, and SHALL emit a warning. Nothing about the handle SHALL be collected into the hydration transfer payload.

#### Scenario: SSG produces no socket

- **WHEN** a page using `use_websocket` is statically generated
- **THEN** no `WebSocket` SHALL be constructed, the iterator SHALL be empty, `.state.value` SHALL be `ConnectionState.CLOSED`, and the hydration payload SHALL contain no entry for the handle

### Requirement: Component-scoped subscriptions shall be detached on component destroy

When `use_websocket` is called inside an active component setup context, the subscription SHALL be detached automatically on component destroy via `on_before_destroy` (chained with any existing hook). Abandoned iterators SHALL be protected by `weakref.finalize`-based detachment so the registry reference count cannot leak.

#### Scenario: Component destroy detaches

- **WHEN** a component using `use_websocket` is destroyed
- **THEN** its subscriber queue SHALL be removed and, if it was the last subscriber, the underlying socket SHALL be closed and any pending reconnect SHALL be cancelled
