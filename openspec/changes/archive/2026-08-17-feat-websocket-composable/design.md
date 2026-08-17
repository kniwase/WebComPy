# Design: feat-websocket-composable

## Context

`feat-sse-composable` establishes the shared machinery this change builds on: the transport-agnostic connection registry in the app DI scope (keyed by `(transport, key)`, reference-counted, per-subscriber FIFO queues), the connection-handle shape (`AsyncIterator` + `.state` + `.close()`), the SSR fallback, and the port/provisioning/fake-port pattern. This change adds the WebSocket transport.

Grounded facts (verified in codebase and platform docs):

- Native `WebSocket` has no automatic reconnection (unlike `EventSource`), so the framework must own the reconnect loop; reconnecting-websocket is the reference behavior (exponential backoff with jitter, default min ~1s / max ~30s).
- The native `WebSocket(url)` constructor resolves relative URLs against the document base URL and maps `http(s)` → `ws(s)`, so relative-URL passthrough works exactly like `use_event_source` (no `base_url` prefixing).
- Native WebSocket does not expose ping/pong frames to JS — heartbeats must be application-level messages (deferred to `feat-rpc-websocket`).
- `sse-composable`'s `ConnectionState` requirement is phrased "at least `CONNECTING`, `OPEN`, `CLOSED`", so an additive `RECONNECTING` member remains compliant.
- Reconnect-on-shared-connection raises the keying question: two subscribers with the same URL but different `protocols` must not share, so the transport-specific key component for WebSocket includes normalized protocols.

## Goals / Non-Goals

**Goals:**

- `use_websocket(url, *, protocols=None, max_queue=None, reconnect=True, reconnect_base_delay=1.0, reconnect_max_delay=30.0, reconnect_max_attempts=None, buffer_while_disconnected=False)` returning a handle that is an `AsyncIterator[str]` with `.state`, `.last_close`, `.send()`, `.close()`.
- Registry reuse: same `(transport, key)` registry from `sse-composable`; WebSocket key component = `(url, normalized_protocols)`.
- Client-side reconnection: exponential backoff `min(max_delay, base * 2**(n-1))` with random jitter, unlimited attempts by default; no reconnect after user `.close()`, normal closure (1000), or `reconnect=False`.
- `CloseInfo(code, reason, was_clean)` frozen dataclass surfaced via `.last_close: Signal[CloseInfo | None]`, updated on every close (including ones later recovered by reconnection).
- Send policy: connected → send immediately; disconnected → warn + discard by default, or opt-in FIFO buffer flushed on (re)open.
- Text-only; binary frames ignored with a warning. SSR fallback identical to `use_event_source`.

**Non-Goals:**

- Typed messaging, RPC, heartbeats, binary, pluggable reconnect strategies, replay, hydration transfer (see proposal Non-goals).

## Decisions

### D1: Own the reconnect loop in the registry-managed connection, not per subscriber

Reconnection is a property of the shared connection: when the underlying socket drops, the connection object (owned by the registry) schedules and performs reconnect attempts, and all subscribers observe it through their queues and `.state`. Rationale: per-subscriber reconnect would multiply sockets and break the sharing invariant; centralizing matches how react-use-websocket shares one reconnecting socket. Alternative considered (per-subscriber reconnect) rejected: defeats reference-counted sharing.

### D2: Backoff defaults base 1s / cap 30s / unlimited attempts, with jitter

Delay for attempt *n* is `min(reconnect_max_delay, reconnect_base_delay * 2**(n-1))` multiplied by a uniform random jitter factor in `[0.5, 1.0]`; attempts are unlimited unless `reconnect_max_attempts` is set, after which the connection transitions to `CLOSED` and stops. Rationale: matches reconnecting-websocket's well-tested envelope (1s→30s) and avoids thundering-herd via jitter; unlimited-by-default matches native `EventSource` behavior (which retries forever), keeping the two transports philosophically aligned.

### D3: No reconnect on normal closure (1000) or user `.close()`

A clean close is a deliberate end-of-session signal; reconnecting would fight the server. `.close()` (or last-subscriber detach) always stops the loop. Abnormal closures (1006, network drop, timeouts) trigger the loop when `reconnect=True`. Rationale: mirrors graphql-ws-style semantics and prevents surprising "zombie" reconnects; documented so users who want always-reconnect can close-with-abnormal from the server side.

### D4: `.last_close` exposes close code/reason instead of a callback API

`CloseInfo(code, reason, was_clean)` is surfaced as a signal updated on every close and not reset on reopen. Rationale: close codes are state (latest fact), not occurrences, so a Signal is the correct primitive per the cell/occurrence split; a signal also lets UIs react declaratively. Alternative considered (on_close callback) rejected: callbacks bypass reactivity and reintroduce imperative wiring the framework exists to avoid. The two pre-change open points are resolved here: close info IS exposed (`.last_close`), and reconnect defaults are base 1s / cap 30s / unlimited attempts (D2).

### D5: Disconnected sends warn and discard by default; buffer is opt-in

While disconnected, `.send()` warns and drops the data unless `buffer_while_disconnected=True`, in which case sends are buffered FIFO (unbounded, documented memory trade-off) and flushed on (re)open. Rationale: silent buffering by default can queue unbounded data during a long outage and reorder user intent; an explicit opt-in keeps the default honest. Alternative considered (always buffer) rejected: hides outages from the developer.

### D6: `RECONNECTING` state distinguishes first-connect from re-establishment

During a backoff wait or an in-flight reconnect attempt, `.state` is `RECONNECTING` (vs `CONNECTING` for the initial attempt). The enum member is additive to the shared `ConnectionState` (compliant with the "at least" phrasing in `sse-composable`), letting UIs show "reconnecting…" distinctly. Rationale: reconnecting-websocket/vueuse users rely on this distinction; the additive change keeps `sse-composable` untouched.

### D7: Registry key for WebSocket includes normalized protocols

The transport-specific key component is `(url, tuple(sorted(protocols or ())))`, so `use_websocket("/ws")` and `use_websocket("/ws", protocols=["graphql-ws"])` never share a socket. Rationale: subprotocol selects application protocol semantics; sharing across different subprotocols would deliver wrongly-framed messages. `sse-composable`'s `(transport, url)` keying is the SSE instantiation of the same `(transport, key)` scheme, so no change to that capability is required.

### D8: SSR and hydration behavior mirrors `use_event_source`

Server-side: no browser API access, empty finished iterator, `state == CLOSED`, warning, no transfer payload. Rationale: consistency across realtime composables; connections and messages are client-runtime concerns.

## Risks / Trade-offs

- [Unlimited reconnect attempts can spin forever against a dead server] → Matches `EventSource` philosophy; `reconnect_max_attempts` provided; `.state == RECONNECTING` + `.last_close` make the condition observable; docs guidance.
- [Buffered sends flush as a burst on reconnect] → Opt-in only; documented; users needing ordering guarantees should wait for `state == OPEN`.
- [Jitter makes timing tests non-deterministic] → Unit tests assert bounds (`delay ∈ [0.5x, 1.0x]` of the computed backoff) and use the fake port / controllable scheduler, not wall-clock sleeps.
- [Shared reconnect means one key's outage affects all its subscribers equally] → Inherent to sharing; per-subscriber isolation is deliberately not offered (same stance as `sse-composable`).
- [Protocols in the registry key surprise users expecting URL-only sharing] → Documented in docs page; scenario in spec.

## Open Questions

(none — close-info exposure and reconnect defaults are resolved in D4/D2.)
