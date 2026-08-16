# Proposal: feat-sse-composable

## Why

WebComPy's core promise is "no JavaScript required". Cross-framework analysis identified realtime communication (SSE / WebSocket) as the one gap where that promise currently breaks: there is no way to receive server-pushed events without writing JS, and the target users (who cannot write JS) have no workaround unless the framework itself provides it. The foundations are already in place — `signal-stream` (#245) provides occurrence↔cell bridging utilities and `asgi-mount` (#240) provides an E2E receptacle for test endpoints — so the first realtime composable can land now. SSE is the right first transport: the browser-native `EventSource` gives automatic reconnection and `Last-Event-ID` resumption for free, keeping implementation cost minimal.

## What Changes

- New `webcompy/realtime/` package hosting the realtime composables and their shared machinery.
- New composable `use_event_source(url, *, events=("message",), max_queue=None)` returning a connection-handle object that is itself an `AsyncIterator[SSEvent]` (`async for ev in es:`) with:
  - `.state: Signal[ConnectionState]` (`CONNECTING` / `OPEN` / `CLOSED`) — state is a *cell* (signal), messages are *occurrences* (iterator), preserving the Signal=cell / Stream=occurrence split established by `signal-stream`;
  - `.close()` — detaches only the caller's own subscription; the underlying shared connection is reference-counted and stays open while other subscribers remain.
- New `EventSourcePort` ABC in `webcompy.ports` (callback surface: open/message/error/close), a browser implementation wrapping native `EventSource`, a server no-op implementation, and a fake implementation for `webcompy_testing`.
- A shared connection registry scoped to the app DI scope, keyed by `(transport, url)`: the first subscriber opens the native connection, the last subscriber closes it, and each subscriber receives its own FIFO queue (unbounded by default; `maxlen` switches to drop-oldest), so a slow consumer never blocks others. When no app DI scope exists, the composable warns and falls back to an instance-private connection.
- `SSEvent(event, data, last_event_id)` dataclass as the yielded item type, with an `events` parameter to subscribe to named SSE event types.
- SSR behavior: the composable returns an immediately-finished empty iterator with `state == CLOSED` and emits a warning. No hydration transfer (same rule as `Computed` and the `signal-stream` bridges).

## Capabilities

### New Capabilities

- `sse-composable`: The `use_event_source` composable and its supporting machinery — the transport-agnostic shared connection registry (DI-scope-scoped, reference-counted, per-subscriber queues), the connection-handle return type (async iterator + `.state` signal + `.close()`), `SSEvent`, SSR fallback, and lifecycle cleanup.

### Modified Capabilities

- `port-abstraction`: Add the `EventSourcePort` ABC requirement (new port in the port hierarchy for the SSE browser API surface).
- `port-provisioning`: Add `EVENT_SOURCE_PORT_KEY` in core keys and provisioning requirements for browser / server (no-op) / testing (fake) render contexts.
- `testing-module`: Add `FakeEventSourcePort` requirement (scripted event delivery, cleanup-returning handles, no module-level state), following the existing fake-port pattern.

## Impact

- **Code**: new `packages/webcompy/src/webcompy/realtime/` package; new `packages/webcompy/src/webcompy/ports/_event_source.py` + `ports/_browser/_event_source.py`; `webcompy_server/ports/` no-op implementation; `webcompy_testing` fake port; DI key in `webcompy/ports/_keys.py`; public re-exports in `webcompy/__init__.py`.
- **APIs**: additive only (`use_event_source`, `SSEvent`, `ConnectionState`, `EventSourcePort`). No breaking changes.
- **Dependencies**: none new (stdlib `asyncio`; existing signal, DI, and async-scheduler machinery; `signal-stream` queue semantics).
- **Downstream**: foundation for `feat-websocket-composable` (reuses the shared registry and connection-handle shape), then `feat-typed-realtime` and `feat-rpc-websocket`.
- **Docs**: new Markdown-driven docs page (`docs_app/documents/` + manifest + page stub, per `docs-site-documents`) covering `use_event_source`, connection sharing, and the gap/refetch recipe.

## Known Issues Addressed

(none)

## Non-goals

- WebSocket transport — separate change (`feat-websocket-composable`), reusing this change's registry.
- Typed message send/receive (`message_type`) — `feat-typed-realtime`.
- JSON-RPC over realtime transports — `feat-rpc-websocket`.
- Server-side SSE endpoint implementations (the framework is client-side; E2E tests mount third-party/Starlette endpoints via `asgi-mount`).
- Binary payloads (SSE is text-only by specification).
- Custom reconnection control (the browser's native `EventSource` reconnection is used as-is; no user-configurable backoff in this change).
- Server-initiated replay buffers beyond the browser's native `Last-Event-ID` resumption.
- Hydration transfer of connection state or received events.
