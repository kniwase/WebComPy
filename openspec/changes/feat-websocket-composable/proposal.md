# Proposal: feat-websocket-composable

## Why

`feat-sse-composable` covers server→client push, but SSE is one-directional and text/event-stream only. Bidirectional realtime (chat, collaborative editing, live commands) needs WebSocket. The shared connection registry and connection-handle shape land with `feat-sse-composable`; this change adds the second transport on top of that foundation. Unlike `EventSource`, native WebSocket has **no** automatic reconnection, so the composable must own a reconnect loop.

## What Changes

- New composable `use_websocket(url, *, protocols=None, max_queue=None, reconnect=True, reconnect_base_delay=1.0, reconnect_max_delay=30.0, reconnect_max_attempts=None, buffer_while_disconnected=False)` in `webcompy/realtime/`, returning a connection handle that is an `AsyncIterator[str]` with:
  - `.state: Signal[ConnectionState]` — reuses the shared `ConnectionState` enum from `sse-composable`, extended additively with `RECONNECTING`;
  - `.last_close: Signal[CloseInfo | None]` — exposes the most recent close code / reason / cleanliness;
  - `.send(data: str)` — sends a text frame; while disconnected it warns and discards by default, or buffers (opt-in) and flushes FIFO on (re)open;
  - `.close()` — detaches only the caller's subscription (shared connections are reference-counted, same registry as SSE).
- Client-side reconnection loop with exponential backoff + jitter (base 1s, cap 30s, unlimited attempts by default; all configurable). No reconnect on user-initiated `.close()`, on normal closure (code 1000), or when `reconnect=False`.
- New `WebSocketPort` ABC in `webcompy.ports`, browser implementation over native `WebSocket`, server no-op, `webcompy_testing` fake; `WEBSOCKET_PORT_KEY` and render-context provisioning.
- Registry reuse: WebSocket shares the `sse-composable` connection registry; the transport-specific key component for WebSocket includes the normalized `protocols` so different subprotocols never share a connection.
- Text frames only; binary frames are ignored with a warning.
- SSR behavior and hydration non-transfer identical to `use_event_source` (empty finished iterator, `state == CLOSED`, warning).

## Capabilities

### New Capabilities

- `websocket-composable`: The `use_websocket` composable — bidirectional text messaging over a shared, reference-counted connection; client-side reconnection with backoff; close introspection via `.last_close`; send policy while disconnected; SSR fallback and lifecycle cleanup.

### Modified Capabilities

- `port-abstraction`: Add the `WebSocketPort` ABC requirement (new port for the WebSocket browser API surface).
- `port-provisioning`: Add `WEBSOCKET_PORT_KEY` in core keys and provisioning requirements for browser / server (no-op) / testing (fake) render contexts.
- `testing-module`: Add `FakeWebSocketPort` requirement (scripted message/lifecycle delivery, instance-local registry, idempotent cleanup).

## Impact

- **Code**: new `packages/webcompy/src/webcompy/realtime/_ws.py`; new `packages/webcompy/src/webcompy/ports/_websocket.py` + `ports/_browser/_websocket.py`; `webcompy_server/ports/` no-op; `webcompy_testing` fake port; DI key in `webcompy/ports/_keys.py`; public re-exports. Reuses `webcompy/realtime/_registry.py` and `ConnectionState` from `feat-sse-composable`.
- **APIs**: additive only (`use_websocket`, `CloseInfo`, `WebSocketPort`; additive `RECONNECTING` member on `ConnectionState`). No breaking changes.
- **Dependencies**: `feat-sse-composable` (registry, handle shape, port/provisioning pattern). No new third-party dependencies.
- **Downstream**: foundation for `feat-typed-realtime` (`message_type`) and `feat-rpc-websocket`.
- **Docs**: new Markdown-driven docs page covering `use_websocket`, reconnection behavior, `.last_close`, and send buffering.

## Known Issues Addressed

(none)

## Non-goals

- Typed message send/receive (`message_type`) — `feat-typed-realtime`.
- JSON-RPC over WebSocket and subscription semantics — `feat-rpc-websocket`.
- Binary frames (sent or received).
- Heartbeat / ping-pong keepalive — the browser WebSocket API does not expose ping frames; application-level heartbeats are deferred to `feat-rpc-websocket`.
- Custom reconnection strategies beyond the provided backoff parameters (no pluggable strategy hooks).
- Server-side WebSocket endpoint implementations (E2E tests mount Starlette endpoints via `asgi-mount`).
- Replay / resumability of missed messages during reconnection (documented gap + refetch recipe; server-side replay is opt-in and out of scope).
- Hydration transfer of connection state, close info, or messages.
