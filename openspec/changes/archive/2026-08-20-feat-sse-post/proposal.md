# Proposal: feat-sse-post

## Why

`use_event_source` can only open GET connections, because the browser `EventSource` API does not support request bodies. Servers that expose query-style or one-shot SSE endpoints (POST with a body) are unreachable today, and the framework has no streaming-fetch primitive at the port layer. Building fetch-based POST support also produces two generic building blocks — a streaming `FetchPort` method and a reusable SSE parser — that a later RPC streaming capability will consume directly.

## What Changes

- New `FetchPort.stream(url, *, method="GET", headers=None, body=None) -> FetchStream` capability with a default implementation that performs `fetch()` and yields the full body as one chunk (non-breaking: existing ports keep working). `FetchStream` exposes `status_code` / `headers` / `ok` before body iteration, is an `AsyncIterator[str]` of text chunks, and supports idempotent `close()`/`aclose()` that aborts the underlying request.
- Browser `FetchPort` implementation gains real streaming: `ReadableStream` reader with incremental UTF-8 decoding (streaming `TextDecoder`) and `AbortController`-based cancellation.
- New pure-Python SSE parser in `webcompy/ajax/_sse.py`: incremental chunk feeding, boundary-safe event assembly (`event` / `data` / `id` fields, comment lines, blank-line dispatch), plus a formatting helper that emits valid SSE frames.
- `use_event_source` gains `method`, `body`, and `headers` parameters (default `"GET"`, preserving current behavior). Any non-GET method opens a fetch-based SSE connection through the new streaming fetch path instead of the browser `EventSource` API, with manual reconnection (exponential backoff + jitter, `Last-Event-ID` header on reconnect, EventSource-style terminate-only-on-close semantics) and per-subscriber event-type filtering.
- Shared connection registry keying is extended so POST connections with different `(url, method, body)` never share; fetch-based connections do not reopen when new event types are requested (filtering is per-subscriber).
- `FakeFetchPort` in `webcompy_testing` implements `stream()` with scripted chunk delivery so tests can exercise chunk-boundary parsing and abort behavior.
- GET path, SSR/SSG degradation, hydration non-transfer, component-destroy cleanup, and `max_queue` semantics are unchanged.

## Capabilities

### New Capabilities

- `sse-parser`: The framework-internal SSE framing codec — an incremental, boundary-safe parser for `text/event-stream` payloads and a matching SSE frame formatter, both pure Python and importable from browser and server packages.

### Modified Capabilities

- `sse-composable`: `use_event_source` POST support — non-GET fetch-based connections, reconnection with `Last-Event-ID`, extended registry keying, validation of the new parameters.
- `port-abstraction`: `FetchPort.stream()` and the `FetchStream` contract (upfront response metadata, text-chunk iteration, idempotent abort), including the browser streaming implementation and the default single-chunk fallback.
- `testing-module`: `FakeFetchPort.stream()` with scripted chunks and recorded aborts.

## Impact

- **Code**: `packages/webcompy/src/webcompy/ports/_fetch.py` (FetchStream + default stream), `packages/webcompy/src/webcompy/ports/_browser/_fetch.py` (streaming implementation), new `packages/webcompy/src/webcompy/ajax/_sse.py` (parser/formatter), `packages/webcompy/src/webcompy/realtime/_sse.py` and `_registry.py` (fetch transport, reconnect, keying), `packages/webcompy-testing/src/webcompy_testing/_ports.py` (fake stream). Reuses `ConnectionState.RECONNECTING` and `_compute_reconnect_delay` from the WebSocket composable.
- **APIs**: additive only (`method`/`body`/`headers` params, `FetchPort.stream`, `FetchStream`). No breaking changes; `ServerFetchPort` inherits the default `stream()` fallback and gains a `noop = True` class attribute that marks it for realtime SSR/SSG degradation (its ordinary `fetch()` functionality is unchanged).
- **Dependencies**: none new. Foundation for a future RPC streaming capability (`rpc-streaming`), which will reuse `FetchPort.stream` and the SSE parser.
- **Docs**: update the EventSource docs page with POST usage, reconnection behavior, and `Last-Event-ID` semantics.

## Known Issues Addressed

(none)

## Non-goals

- Typed SSE messages (`use_typed_event_source` does not exist; no typed integration here).
- RPC streaming procedures (`rpc-streaming`) — a follow-up change that consumes the primitives built here.
- User-configurable reconnection parameters or honoring the server `retry:` field for fetch-based connections (fixed default backoff only).
- Server-side SSE endpoint helpers (users mount their own endpoints, e.g. via asgi-mount).
- Replay/resumability of events missed during reconnection beyond what `Last-Event-ID` enables server-side.
- Hydration transfer of connection state or received events.
- Changing the GET/EventSource path behavior in any way.
