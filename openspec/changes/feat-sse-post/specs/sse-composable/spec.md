# SSE Composable (delta)

## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: A shared connection registry shall multiplex subscribers per app DI scope

The framework SHALL maintain a connection registry scoped to the app DI scope (never module-global), keyed by `(transport, key_component)`, where the SSE transport's key component is the URL for GET connections and `(url, method, body)` for non-GET connections. For a given key:

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
