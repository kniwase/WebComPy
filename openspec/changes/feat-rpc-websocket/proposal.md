# Proposal: feat-rpc-websocket

## Why

`feat-json-rpc` (#244) provides a typed JSON-RPC 2.0 dispatcher and browser client over HTTP POST. Request/response RPC works well over HTTP, but **server→client streaming** (progress events, live updates, pub/sub) cannot ride on one-shot POSTs. With `feat-websocket-composable` and `feat-typed-realtime` in place, the same JSON-RPC machinery can run over a persistent, shared, auto-reconnecting WebSocket — giving WebComPy a full-duplex RPC channel with subscriptions, without users writing JavaScript or hand-rolling frame codecs.

## What Changes

- **Server: WebSocket transport for the JSON-RPC dispatcher.** A Starlette WebSocket endpoint (mounted alongside the HTTP dispatcher, same mount mechanism) that feeds each incoming text frame through the existing dispatch logic and writes responses back as text frames. The dispatcher core becomes transport-neutral; the HTTP POST behavior is unchanged.
- **Client: `RpcWsClient`** built on the typed realtime layer — JSON-RPC envelopes are typed messages over `use_websocket(..., message_type=...)`. Calls correlate responses by `id`; notifications receive no response; errors raise `RpcError` (unchanged semantics).
- **Subscriptions (Phoenix-style).** Server procedures marked subscribable expose an event stream where every event carries a server-assigned monotonic `cursor`. Client-side `rpc_ws.subscribe(method, params)` returns an `AsyncIterator` of events. On reconnect, the client automatically **rejoins with its last received cursor**; the server replays missed events from a bounded replay buffer (catch-up), then continues live. If the cursor is older than the buffer floor, the server answers with a `resync_required` signal so the client refetches authoritative state (documented recipe) instead of silently skipping events.
- **Application-level heartbeat.** Optional periodic `ping` notification with `pong` response; a missed `pong` within the timeout forces an abnormal close so the `use_websocket` reconnect loop engages. (Browser WebSocket exposes no protocol ping frames, so liveness is application-level.)
- SSR: `RpcWsClient` is browser-runtime-only; SSR/SSG emits a warning and performs no socket work. No hydration transfer of subscription state or cursors.

## Capabilities

### New Capabilities

- `rpc-websocket`: JSON-RPC 2.0 over WebSocket — the transport-neutral dispatcher adapter, the `RpcWsClient` (id-correlated calls, notifications, `RpcError`), the subscription protocol (cursor, rejoin, catch-up, `resync_required`), and the application-level heartbeat.

### Modified Capabilities

- `json-rpc`: Add requirements for the WebSocket transport of the dispatcher (transport-neutral dispatch core; WS endpoint mounting; frame-level envelope handling). HTTP POST behavior is unchanged.
- `websocket-composable`: Add an additive `force_close(code, reason)` on the WebSocket handle so the RPC heartbeat can engage the reconnect loop with a non-normal close code.

## Impact

- **Code**: new `packages/webcompy-server/src/webcompy_server/rpc/_ws_endpoint.py`; dispatcher refactor toward transport-neutral core; new `packages/webcompy/src/webcompy/rpc/_ws_client.py`; subscription/cursor types; public re-exports. Builds on `feat-websocket-composable` (transport) and `feat-typed-realtime` (codec).
- **APIs**: additive only (`RpcWsClient`, `subscribe`, subscription event/cursor types, heartbeat parameters). No breaking changes to HTTP JSON-RPC.
- **Dependencies**: `feat-websocket-composable`, `feat-typed-realtime`, existing `json-rpc` dispatcher. No new third-party dependencies.
- **Docs**: new Markdown-driven docs page covering WS RPC calls, subscriptions, reconnect/resync semantics, and heartbeat tuning.

## Known Issues Addressed

(none)

## Non-goals

- Changing the HTTP JSON-RPC transport or its API.
- Server-side event persistence beyond the bounded replay buffer (no durable log; `resync_required` covers overflow).
- Client→server streaming (server-initiated streams only; client streaming is a future change).
- Presence/channels abstraction (Phoenix-style rooms) — plain method-addressed subscriptions only.
- Binary WebSocket frames.
- Hydration transfer of RPC-WS state (calls during SSR use the existing HTTP path + transfer cache).
- Cross-connection subscription migration (subscriptions live and die with their connection; rejoin happens on the new connection).
