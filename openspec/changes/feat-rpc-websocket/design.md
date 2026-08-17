# Design: feat-rpc-websocket

## Context

The `json-rpc` capability (#244) provides: a JSON-RPC 2.0 dispatcher as an ASGI endpoint (HTTP POST, default `/_webcompy-rpc`), procedure registration by annotated signature, strict allowlist-based decoding, the `meta` extension member, and a typed browser client over `FetchPort` (SSR-baked via the transfer cache). `feat-websocket-composable` provides the shared auto-reconnecting transport; `feat-typed-realtime` provides the typed frame codec and wire envelope. This change composes them into a full-duplex RPC channel.

Grounded facts:

- The dispatcher (`webcompy_server/rpc/_dispatcher.py`) is HTTP-shaped today; its core (envelope validation → procedure invocation → response construction) is transport-neutral in fact and needs a thin extraction.
- Native browser WebSocket exposes no ping/pong frames, so liveness detection must be application-level.
- Reconnection makes naive pub/sub silently lossy: events emitted while the socket was down are missed. Phoenix Channels solve this with rejoin + last-cursor + server catch-up, which is the model adopted here.
- This reconnect-resync path is the one unproven area of the realtime plan, so it carries an explicit spike task.

## Goals / Non-Goals

**Goals:**

- Transport-neutral dispatcher core + Starlette WebSocket endpoint reusing the same mount mechanism and procedure registry.
- `RpcWsClient`: id-correlated calls, notifications, `RpcError` mapping, built on the typed realtime handle.
- Subscription protocol: server-assigned monotonic `cursor` per event; client `subscribe()` iterator; automatic rejoin-with-cursor on reconnect; bounded server replay buffer; `resync_required` honesty signal.
- Application-level heartbeat (configurable interval/timeout; missed pong → abnormal close → reconnect loop).
- SSR no-op + no hydration transfer.

**Non-Goals:**

- HTTP transport changes, durable event logs, client→server streaming, presence/rooms, binary frames, hydration transfer, cross-connection migration (see proposal Non-goals).

## Decisions

### D1: Extract a transport-neutral dispatch core; add a WS endpoint adapter

The existing dispatch logic (envelope validation, batch handling, procedure invocation, error mapping, meta handling) is extracted into a function over plain request/response objects; the HTTP endpoint and the new WebSocket endpoint both call it. Rationale: one canonical implementation of JSON-RPC semantics; the WS adapter only does frame↔object conversion and per-connection lifecycle. Alternative considered (separate WS dispatcher) rejected: duplicated semantics drift.

### D2: Calls over WS use the same envelopes with id correlation

Client calls send standard JSON-RPC request objects as raw text frames (the `use_websocket` handle opened without `message_type`); responses arrive as frames with matching `id`; the client keeps an in-flight map id→pending future. Notifications (no `id`) fire and forget. Errors map to `RpcError` exactly as over HTTP. Typed params/results use the same transfer codec as the HTTP client (`meta` member, `from_json`, `apply_transfer_meta`) — the dispatcher core is fed byte-identical envelope semantics. Rationale: no protocol invention — JSON-RPC 2.0 already defines everything needed; correlation is trivial over an ordered transport. A single-dataclass `message_type` frame was rejected because the typed realtime layer requires a top-level JSON object and cannot carry batch (array) frames, which the shared dispatch core must support.

### D3: Subscriptions are method-addressed streams with server cursors

A procedure marked subscribable returns an async stream; the dispatcher assigns a monotonic `cursor` per event and forwards events as server→client notification frames carrying `subscription_id`, `cursor`, and `data`. The client `subscribe()` call registers a local queue keyed by `subscription_id`. Rationale: method addressing keeps the model flat (no channel/room abstraction) while cursors make loss detectable.

### D4: Reconnect = automatic rejoin with last cursor; overflow = `resync_required`

The client tracks the last received cursor per subscription. After a reconnect, it re-sends the subscribe call including the last cursor; the server replays buffered events with `cursor > last_cursor` then continues the live stream. If the last cursor is older than the bounded replay buffer's floor, the server responds `resync_required` and ends that stream; the client surfaces this on the subscription object (e.g., `.state`/error signal) and the docs recipe refetches authoritative state and resubscribes fresh. Rationale: Phoenix-style honesty — never pretend a gap didn't happen; replay is opportunistic, bounded, and server-side. Alternative considered (silent skip / best-effort) rejected: silent loss violates the framework's "no swallowed occurrences" stance established with `signal-stream`.

### D5: Replay buffer is bounded and per-subscription-stream

The server keeps the newest N events per subscription stream (default e.g. 256, configurable at registration). Rationale: unbounded server memory per client is a DoS surface; the bound is honest because overflow is signalled (D4).

**Stream lifecycle (grace-period model, validated by the spike):** a subscription stream is keyed by `(method, canonical params JSON)` and outlives any single connection. Its source task (the registered async generator) keeps emitting and filling the bounded buffer while any subscriber is attached OR for a grace period after the last subscriber detaches (internal constant `_STREAM_IDLE_TIMEOUT`, default 60s; the spike used 5s). After the grace period the source is cancelled and the buffer released. This is what lets the server "emit cursors 42–44 during the outage": the source does not stop when the socket drops.

**Replay-before-live ordering (validated by the spike):** each connection owns a single FIFO send queue drained by one sender task. On rejoin the endpoint synchronously enqueues the subscribe response followed by the replay frames into that queue, and only then attaches the connection to the stream's live fan-out (same queue). Because there is no `await` between the replay enqueue and the live attach, live events can never interleave with replay frames.

**Buffer boundary rules:** rejoin with `last_cursor`:
- `last_cursor >= stream.cursor` → nothing missed, attach live only;
- buffer floor `<= last_cursor < stream.cursor` → replay `(last_cursor, cursor]`, then live;
- `last_cursor < buffer floor` (or a fresh stream whose buffer cannot cover it) → `resync_required`, no partial replay.

### D6: Heartbeat is optional and uses JSON-RPC notifications

Client sends a `_webcompy.ping` notification every `heartbeat_interval` (default 30s); the server answers with a `_webcompy.pong` notification. If no `pong` (or any frame) arrives within `heartbeat_timeout` (default 10s), the client forces an abnormal close of the underlying socket so the `use_websocket` reconnect loop engages. Rationale: browser WS cannot see protocol pings; TCP-idle connections can look open while dead. Both parameters configurable; heartbeat disabled by passing `heartbeat_interval=None`.

**Forcing the abnormal close:** the realtime layer gains an additive `WebSocketHandle.force_close(code, reason)` (and `TypedWebSocketHandle` forwarding). It is implemented in `_RealtimeRegistry._ws_abort`: it records a synthetic `CloseInfo(code, reason, was_clean=False)`, closes the underlying socket, bumps the connection `generation` so the real browser close event (code 1000) that follows is treated as stale and ignored, then transitions the state to `RECONNECTING` and schedules a retry — so the reconnect loop engages. No port ABC change is required.

### D9: Reserved `_webcompy.*` methods define the WS protocol

The WS endpoint owns a closed set of reserved method names (rejected by `ProcedureRegistry.register` / `register_subscription`, which raise for any name starting with `_webcompy.`):

| Method | Direction | Kind | Payload / Effect |
|---|---|---|---|
| `_webcompy.subscribe` | C→S | call (id) | `{method, params, meta, last_cursor}` → `{subscription_id, resync_required}` |
| `_webcompy.unsubscribe` | C→S | notification | `{subscription_id}` |
| `_webcompy.event` | S→C | notification | `{subscription_id, cursor, data}` (`data` carries `__webcompy_transfer_meta__`, body mode) |
| `_webcompy.ping` / `_webcompy.pong` | C→S / S→C | notification | `{}` |
| `_webcompy.close` | C→S | notification | server closes the socket with code 1011 (abnormal) so the reconnect loop engages |

`_webcompy.close` gives applications a framework way to force server-driven reconnection (e.g., rolling restarts) and is what the E2E catch-up test uses to simulate a server-initiated abnormal close across the process boundary. Inner subscription params are decoded through the same allowlist path as ordinary procedures (`registry.get` + `_decode_params`).

### D7: SSR uses the HTTP path; the WS client is browser-runtime-only

During SSR/SSG, `RpcWsClient` warns and performs no socket work; SSR-time RPC continues to use the existing HTTP client + transfer cache. No subscription state, cursors, or in-flight calls are transferred. Rationale: consistent with the realtime composables' SSR stance; SSR already has a correct RPC story (HTTP bake).

### D8: Reconnect-resync carries a spike task

The rejoin/catch-up/resync path (D4) is the plan's one unproven area (server stream lifetime vs connection lifetime, buffer replay ordering vs live interleave, close-code-driven cancellation). tasks.md includes a time-boxed spike that validates the protocol against a real Starlette WS endpoint before the full implementation lands; findings feed back into the final spec details.

## Spike Findings

The spike (a minimal Starlette WS endpoint + stream registry + TestClient) validated against a real WebSocket transport:

1. **Fresh subscribe** delivers live events with monotonically increasing cursors.
2. **Rejoin with `last_cursor`** replays buffered events (`cursor > last_cursor`) **before** live events resume, with no interleave — achieved by the single-FIFO-send-queue model: the endpoint synchronously enqueues [response, replay...] into the connection's send queue, then attaches the live fan-out to the same queue. There is no `await` between replay enqueue and live attach.
3. **Old cursor** (older than the buffer floor) yields `resync_required` with no partial replay; the boundary is `last_cursor < floor` → resync, `last_cursor == floor` → full replay.
4. **Batch array frames** round-trip as a single frame through the shared dispatch core.
5. **`websocket.close(code=1011)`** is observed by the client as `was_clean=False`, which will drive the reconnect loop (code != 1000).
6. **Grace-period cleanup** reaps the stream (cancels the source, releases the buffer) once no subscribers remain past the idle timeout.

Findings confirm the grace-period stream lifecycle, the replay-before-live ordering model, and the `resync_required` boundary rules described in D4/D5. They also motivate the additive `force_close` (D6) and the reserved `_webcompy.close` notification (D9, used by the E2E catch-up test across the process boundary).

## Risks / Trade-offs

- [Replay-then-live interleave can reorder events around the rejoin boundary] → Server replays the buffer before attaching the live stream; ordering within a stream is cursor-total; documented.
- [Bounded replay buffer forces `resync_required` under long outages] → Honest by design; buffer size configurable; docs recipe for full-state refetch.
- [Heartbeat adds baseline traffic to every connected client] → Optional, conservative defaults (30s/10s); disable-able.
- [In-flight calls during a drop fail] → Documented: callers retry idempotent operations; subscriptions (the streaming case) auto-heal via D4.
- [Server per-connection state grows with subscription count] → Per-connection subscriber entries die with their connection; the shared stream survives only for the grace period (`_STREAM_IDLE_TIMEOUT`), then its source and buffer are released; documented capacity guidance.

## Open Questions

(none — the resubscribe/resync uncertainty is scoped into the D8 spike task rather than left as an open question.)
