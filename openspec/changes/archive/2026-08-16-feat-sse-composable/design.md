# Design: feat-sse-composable

## Context

WebComPy is signal-first: state lives in `Signal`/`ReactiveList` cells and the UI reacts automatically. Realtime data has *occurrence* semantics instead — every arrival matters, duplicates included — and the `signal-stream` capability (#245) already codified the bridge layer (`to_signal` / `to_reactive_list` / `to_async_iter`) with the rule that Signal=cell, Stream=occurrence. The `readonly-signal` capability (#253) separately covers push-based DOM *state* events (`use_window_event` / `use_document_event`) and explicitly notes that occurrence-type events must not use that path. What is missing is the network-occurrence side: Server-Sent Events and WebSocket messages.

This change adds the first network-occurrence composable, `use_event_source`, plus the shared machinery that `feat-websocket-composable` will reuse.

Grounded facts (verified in codebase):

- Component-scoped cleanup uses `_get_active_component_context()` + `on_before_destroy` hook chaining, as in `storage/_composable.py` (`_register_destroy_unregister`) and `events/_composable.py` (`_register_destroy_cleanup`).
- App-scoped registries live in the app DI scope: `storage/_composable.py._get_or_create_registry()` uses `_get_app_di_scope()` + `scope.inject(key, default=None)` + `scope.provide(key, ...)`. The No-New-Globals invariant forbids a module-level registry.
- Drop-oldest queue semantics exist in `aio/_stream.py._StreamQueue` (unbounded `asyncio.Queue` by default; `maxlen` switches to drop-oldest).
- The fake-port pattern for listener-style ports is `FakeBrowserHostPort.add_window_event_listener`: instance-local handler registry, idempotent cleanup, `dispatch_*` helper for tests.
- Port ABC + DI key + provisioning precedent: `CustomElementPort` (#255) added "XPort ABC shall exist" to `port-abstraction`, "X_PORT_KEY shall live in core keys" + "All render contexts shall provision a XPort" (browser / server no-op / testing fake) to `port-provisioning`.
- Browser-side URL handling passes URLs through to the native API (the browser resolves relative URLs against the document URL); see `ajax/_fetch.py`. No `base_url` prefixing is applied on the browser side.
- `app.run()` always runs inside an app DI scope, so the no-scope fallback only triggers in standalone/test usage.

## Goals / Non-Goals

**Goals:**

- `use_event_source(url, *, events=("message",), max_queue=None)` in `webcompy/realtime/`, returning a connection handle that is itself an `AsyncIterator[SSEvent]`.
- A transport-agnostic shared connection registry in the app DI scope: keyed by `(transport, url)`, reference-counted open/close, one FIFO queue per subscriber (unbounded default; `max_queue` = drop-oldest). The registry SHALL be fully specified in this change so that `feat-websocket-composable` can reuse it without modifying this capability.
- Connection handle surface: `.state: Signal[ConnectionState]` (CONNECTING / OPEN / CLOSED) and `.close()` (detaches only the caller's own subscription).
- `SSEvent(event, data, last_event_id)` dataclass; `events` selects the SSE event types to subscribe to.
- `EventSourcePort` ABC (callback surface: on_open / on_message / on_error / on_close semantics), browser implementation over native `EventSource`, server no-op, `webcompy_testing` fake.
- SSR: immediately-finished empty iterator, `state == CLOSED`, warning. No hydration transfer.
- Lifecycle: component-setup subscriptions are detached on component destroy; `weakref.finalize` guards abandoned iterators (the `async for ... break` leak class from `signal-stream`).

**Non-Goals:**

- WebSocket, typed messaging, RPC (later changes); server-side SSE endpoints; binary; custom reconnection control; replay buffers beyond native `Last-Event-ID`; hydration transfer (see proposal Non-goals).

## Decisions

### D1: Iterator-first API; signal-ification is the user's choice via `signal-stream`

The composable returns an async iterator of occurrences, not a Signal. Rationale: the Signal equality contract suppresses equal consecutive writes (verified across Vue/Svelte/Angular and in WebComPy's own `Signal`), which would silently swallow repeated identical messages — exactly the bug class `signal-stream` was created to avoid. Users who want cell semantics call `to_signal(es, initial)` themselves, making the loss explicit and deliberate. Alternative considered (return `Signal[SSEvent | None]`) rejected: it bakes the swallow into the default API.

### D2: Shared connection registry, reference-counted, per app DI scope

One native `EventSource` per `(transport, url)` per app DI scope; the registry opens on first subscriber and closes on last unsubscribe. Rationale: mature libraries converge on shared + ref-counted fan-out (RxJS `webSocket()`, react-use-websocket `share: true`, Svelte stores), and SSE additionally faces the browser's HTTP/1.1 ~6-connections-per-domain ceiling, making sharing close to mandatory. The registry lives in the app DI scope (via the `_get_app_di_scope()` + inject-or-provide pattern from `storage/_composable.py`) because a module-level registry would violate the No-New-Globals invariant. Alternative considered (module-global registry) rejected: breaks app isolation and the invariant.

### D3: Per-subscriber FIFO queues (pull fan-out)

Each subscriber gets its own queue; the port callback enqueues into every live subscriber queue. Slow consumers cannot block others (unlike RxJS-style synchronous fan-out), which is the natural consequence of choosing a pull-based `AsyncIterator` surface. Unbounded by default with `max_queue` opting into drop-oldest, matching `signal-stream`'s queue policy. Rationale: consistency with the existing stream machinery and documented slow-consumer trade-off (memory growth) mitigated by `max_queue`.

### D4: `.close()` detaches the caller's subscription only

`close()` removes the caller's queue and decrements the reference count; it never tears down a connection other subscribers still use. Rationale: mirrors react-use-websocket protecting the shared socket behind a Proxy; a per-subscriber "close" that killed shared state would make sharing hazardous. The registry owns actual connection lifetime.

### D5: No DI scope → warn and fall back to an instance-private connection

When `_get_app_di_scope()` returns `None` (standalone scripts, scope-less tests), the composable emits a `UserWarning` and creates a dedicated, non-shared connection for that call. Rationale: skipping the feature entirely would make standalone usage silently dead; a global fallback registry is forbidden (D2). Under `app.run()` a scope always exists, so the fallback is effectively test/standalone-only. This mirrors the `events/_composable.py` pattern of warning + degraded behavior outside the expected context.

### D6: Relative URLs pass through to native `EventSource` (no `base_url` prefixing)

On the browser the URL is handed to native `EventSource` unchanged; the browser resolves it against the document URL. Rationale: this matches the existing browser-side convention (`ajax/_fetch.py` passes URLs through; only the server-side `FetchPort` does `base_url` resolution), and document-relative resolution is correct under `asgi-embed` prefix deployments. Alternative considered (prefix `AppConfig.base_url`) rejected: diverges from framework convention and breaks embedded deployments.

### D7: SSR returns an empty, finished iterator with a warning

Server-side, the composable never touches browser APIs: it returns a handle whose iterator finishes immediately, whose `.state` is `CLOSED`, and emits a warning. The SSR branch is keyed on the *resolved port* rather than the environment alone: outside the browser, the server no-op port (marked `noop`) — or the absence of any port — triggers degradation, while a non-noop port (e.g., the `webcompy_testing` fake in `TestRenderer` renders) opens a connection through that port. Rationale: consistent with SSR-tolerant composable behavior elsewhere (storage no-op, events standalone fallback) and the SSG-fail-fast policy applies only to rendering errors, not to feature degradation. No hydration transfer — connections and events are client-side runtime concerns (same rule as `Computed`).

### D8: Reconnect gap is handled by transparent continuation + `.state` + docs recipe

Native `EventSource` reconnects automatically and re-sends `Last-Event-ID`; the composable keeps iterating transparently. Missed-during-outage events are not signaled with synthetic sentinel events (no industry precedent; sentinels break data/control separation). Instead, `.state` exposes transitions and the docs provide a refetch recipe (re-pull authoritative state when `state` returns to `OPEN`). Server-side replay via `Last-Event-ID` remains an opt-in server mechanism; `SSEvent.last_event_id` is carried so a future server-side replay feature needs no client change.

### D9: `EventSourcePort` is a callback-surface port, browser impl over native API

The ABC exposes connect/subscribe-style methods returning cleanup functions (like `HostPort.add_window_event_listener`), keeping the port free of component knowledge (per the port-abstraction scoping requirement). The browser implementation wraps native `EventSource`; the server implementation is a no-op; the testing fake records subscriptions and offers scripted `emit_*` delivery, following the `FakeBrowserHostPort` pattern (instance-local registry, idempotent cleanup, no module-level state).

## Risks / Trade-offs

- [Unbounded queues can grow without limit under a stalled consumer] → Documented default; `max_queue` provides drop-oldest capping; same trade-off accepted by `signal-stream`.
- [Shared connection means one subscriber cannot observe "its own" connection lifecycle] → `.state` reflects the shared connection's state; `.close()` semantics documented (D4). Per-subscriber isolation is deliberately not offered.
- [No-DI-scope fallback duplicates connections if abused] → Warning makes the degradation loud; documented as test/standalone-only (D5).
- [Native reconnection is opaque (no backoff control)] → Accepted for SSE; custom reconnection control is an explicit non-goal. `feat-websocket-composable` implements its own reconnect loop because native WebSocket has none.
- [Registry keyed by `(transport, url)` string equality misses equivalent URLs] → Documented: callers should use consistent URL spelling; exact-match keys keep lookup O(1) and predictable.
- [Union reopen drops the connection window] → A later subscriber requesting event types not yet registered closes and reopens the shared native connection with the union of event types. Events arriving in the close→open window are lost, and the new native `EventSource` instance starts fresh, so `Last-Event-ID` resumption state (D8) does not carry across a reopen — only across the browser's automatic reconnection of the same instance. Subscribers using consistent event sets (the common case) never trigger a reopen.
- [No-port degradation returns an empty handle] → When neither a port nor an app DI scope can be resolved (standalone scripts without an injectable port), the composable warns and returns the empty closed handle instead of a private connection; a private connection requires an injectable `EventSourcePort`.
- [Port open failure leaves a registry entry behind] → When the port's open raises (e.g., a malformed URL in the browser), the registry removes the connection entry so later subscribers open fresh; a failed reopen additionally ends the existing subscribers of that connection. The exception propagates to the caller (component setup fails fast).

## Open Questions

(none — the two pre-change open points were resolved: D5 for the no-DI-scope case, D6 for relative-URL handling.)
