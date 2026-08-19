# Design: feat-sse-post

## Context

`use_event_source` today is built exclusively on the browser-native `EventSource` API (`webcompy/ports/_event_source.py`, `webcompy/realtime/_sse.py`), which cannot send request bodies. The shared connection registry (`webcompy/realtime/_registry.py`) multiplexes per `(transport, url)` and owns per-subscriber FIFO queues, while reconnection for WebSocket connections (retry tokens, generation guards, `_compute_reconnect_delay`) already exists in the same file. The `FetchPort` abstraction buffers entire response bodies (`fetch()` returns a full `Response`), so there is no streaming primitive at the port layer. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**

- Add a generic streaming-fetch primitive (`FetchPort.stream` / `FetchStream`) that stays backward-compatible via a concrete default implementation on the base class.
- Add a neutral, reusable SSE codec so the parser and the formatter each have exactly one home.
- Give `use_event_source` a POST path that matches GET-path semantics (sharing, queues, close/detach, SSR degradation, component-destroy cleanup) plus EventSource-style auto-reconnect.
- Keep the GET path bit-for-bit unchanged.

**Non-Goals:**

- No changes to `EventSourcePort` or the GET transport.
- No typed-SSE composable (none exists), no user-configurable reconnect parameters, no honoring of the server `retry:` field.
- No server-side SSE endpoint helpers; no changes to `ServerFetchPort`'s fetch behavior — it inherits the default `stream()` fallback and only gains a `noop = True` class attribute used as the realtime SSR/SSG degradation signal.
- No RPC streaming in this change — it consumes `FetchPort.stream` and the parser later.

## Decisions

### 1. `FetchPort.stream()` is a concrete default method, not an abstract one

The base class implements `stream()` as `fetch()` + yield the full text as one chunk. This keeps `ServerFetchPort`, `FakeFetchPort`, and any third-party port working unmodified, and turns streaming into an opt-in capability override.

Alternative considered: an abstract method + new port ABC. Rejected — needlessly breaks every existing implementation for a capability only two of them want.

### 2. `FetchStream` exposes response metadata before the body

`status_code` / `headers` / `ok` are available immediately after the request is opened, without consuming chunks. Rationale: callers must branch on status or `Content-Type` before deciding how to parse the body (the RPC streaming follow-up needs exactly this to distinguish a JSON-RPC error from an SSE stream). `close()` is idempotent, aborts the request, and finishes in-flight iteration.

### 3. The SSE codec lives in `webcompy/ajax/_sse.py`

The parser is pure Python (chunk feed → complete events) and must be importable by `realtime` (this change), `rpc` (the follow-up), and `webcompy_server` (future emitters). Placing it under `ajax/` avoids a realtime→rpc or rpc→realtime dependency direction. The parser defines its own lightweight event record; the realtime layer maps it onto the existing `SSEvent` dataclass. A frame formatter ships alongside so the follow-up RPC server can emit frames without duplicating the wire format.

### 4. POST support is a composable-level transport branch, not a port change

`use_event_source(url, *, method="GET", body=None, headers=None)` keeps using `EventSourcePort` for GET and drives `FetchPort.stream` + the parser for non-GET. `EventSourcePort` stays untouched; ports remain thin callback surfaces. Fetch-based open/error/close callbacks are synthesized inside the realtime layer from the `FetchStream` state, preserving the existing registry callback shape.

### 5. Reconnection is owned by the realtime layer and reuses the WebSocket machinery

Fetch-based connections follow EventSource semantics: EOF, failed opens, non-successful statuses, and wrong content types all enter a retry loop; only explicit close terminates. The loop reuses `ConnectionState.RECONNECTING`, `_compute_reconnect_delay` (base 1s, cap 30s, jitter), and a generation/retry-token guard pattern like `_WSConnection`. Reconnect requests carry `Last-Event-ID` once any `id:` has been parsed. The abort-then-reopen cycle must tolerate the old stream's stale completions (generation guard).

### 6. Registry keying: SSE key component becomes `url` or `(url, method, body)`

GET connections keep the exact `(transport, url)` key. Non-GET connections key by `(transport, (url, method, body))` so identical POSTs share and different bodies never do. Fetch connections skip the event-type-reopen logic entirely: the single underlying stream is parsed once and each subscriber's queue receives only events in its requested set (per-subscriber filtering).

### 7. Backpressure and cleanup reuse existing structures

Per-subscriber `_StreamQueue` (with `max_queue` drop-oldest), `weakref.finalize`-based detachment, and `on_before_destroy` chaining apply unchanged. The fetch reader pump runs as a scheduled async task and is cancelled on close.

## Risks / Trade-offs

- **[Risk] Pyodide FFI surface for `ReadableStream` (`res.body.getReader()`, `reader.read()`, streaming `TextDecoder`, `AbortController`) is the least-proven part of the change** → Mitigation: a dedicated spike task first; the existing `await self._browser.fetch(...)` promise-await in `BrowserFetchPort.fetch` is precedent for the mechanics.
- **[Risk] Infinite reconnect loops on permanently failing endpoints (e.g. expired credentials)** → Mitigation: this is EventSource parity and is spec'd; apps terminate via `.close()`. Custom retry policy is a documented non-goal.
- **[Risk] Parser holds unbounded memory if a single event is huge** → Mitigation: only the current event is buffered; this matches EventSource behavior; `max_queue` bounds the subscriber queue, not the wire event.
- **[Risk] Slow UI consumers vs fast streams** → Mitigation: existing per-subscriber queue with opt-in drop-oldest capping; the pump yields control between chunks.
- **[Trade-off] POST requests are not replayable across reconnects beyond `Last-Event-ID`** → the same trade-off as native SSE; server-side resumability is out of scope.

## Migration Plan

Additive-only change: no data migration, no config migration, no persisted state. GET behavior is unchanged, so existing applications are unaffected. Rollback is a plain revert of the change.

## Open Questions

(none)
