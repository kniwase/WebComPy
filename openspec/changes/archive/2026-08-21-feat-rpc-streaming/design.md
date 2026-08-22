# Design: feat-rpc-streaming

## Context

The RPC layer has three pieces: a `ProcedureRegistry` (`webcompy/rpc/_registry.py`) with `ProcedureInfo`/`SubscriptionInfo`, a transport-neutral dispatch core + bare ASGI dispatcher (`webcompy_server/rpc/_dispatcher.py`), and a WS endpoint with a `SubscriptionHub` (`webcompy_server/rpc/_ws_endpoint.py`, `_subscriptions.py`). Clients are `rpc.call/notify/batch` over `FetchPort` (`webcompy/rpc/_client.py`) and `RpcWsClient` with `call/notify/subscribe` (`webcompy/rpc/_ws_client.py`). Per-item typed encoding already exists (`encode_with_meta` / `from_json` + transfer `meta`, `RpcSubscription._deliver`). `feat-sse-post` provides `FetchPort.stream`/`FetchStream` (upfront `status_code`/`headers`, abort via `close()`) and the `sse-parser` codec. This change adds call-scoped finite streams on top of both transports. See proposal.md for motivation.

## Goals / Non-Goals

**Goals:**

- One registration surface (`@app.rpc.procedure`) and one consumption shape (`RpcStream` async iterator) for streaming procedures on both transports.
- Explicit protocol semantics: symmetric `-32600` mismatches, JSON errors before streams start, mid-stream errors raised client-side.
- Reliable cancellation (client close → server generator stop) on both transports.

**Non-Goals:**

- No touching `SubscriptionInfo` / subscription hub semantics.
- No replay/cursor/rejoin for streams; no SSR baking; no stream delivery via realtime composables.

## Decisions

### 1. Registration: extend `ProcedureInfo`, never `SubscriptionInfo`

`ProcedureInfo` gains `is_streaming: bool` (element type goes into `result_schema`). Detection in `_extract_signature`'s caller: resolve the return annotation via `typing.get_origin`/`get_args` against `collections.abc.AsyncIterator/AsyncIterable/Iterator/Iterable` (covering both `typing.` and `collections.abc.` spellings); validate generator-function kind against the annotation (`inspect.isasyncgenfunction` ↔ async iterables, `inspect.isgeneratorfunction` ↔ sync iterables); reject unsubscripted and non-generator cases with messages naming the offending declaration. Rationale: subscriptions model infinite shared streams — conflating the two kinds in one info type would leak replay semantics into one-shot calls.

### 2. Invocation guard: streaming entries never pass through `_process_entry`'s await path

`dispatch_payload` currently invokes and encodes results inline; awaiting an async generator would raise. A dispatch helper classifies the entry first (streaming + flag checks per the `json-rpc` delta, producing `-32600` bodies or a sentinel for the transport). Each transport then runs its own stream loop: HTTP streams via the ASGI body, WS via `StreamCallHub`. The shared core only contributes classification and error bodies; per-item encoding stays `encode_with_meta`.

### 3. HTTP transport: same endpoint, SSE body, disconnect watcher

The dispatcher stays the bare ASGI app at the same path. On a streaming hit: send `http.response.start` (`text/event-stream`, `Cache-Control: no-store`, no content-length), then a generator task iterates the procedure and sends `item` frames (via the `sse-parser` formatter), `done` on exhaustion, `error` on exception. A sibling task awaits `receive()`; on `http.disconnect` it cancels the generator task and `aclose()`s the generator. Sync generators are wrapped in an async generator (cancellation then lands as `GeneratorExit` at the next yield). Pre-stream failures keep `_json_response_body`.

### 4. WS transport: dedicated lightweight `StreamCallHub`, reusing the connection send queue

`_ws_endpoint.py` gains a `StreamCallHub` mirroring `SubscriptionHub`'s attachment pattern (per-connection `_Connection` send queue reused for response→frame ordering) but with none of the stream-sharing machinery: each flagged call spawns a `_StreamCall` task (generator + per-item `_event_frame`-style emission with `stream_id`, done/error frames). `stream_cancel` and socket close cancel the task. No buffer, no idle grace, no `(method, params)` keying. Rationale: sharing, replay, and grace exist to heal reconnects for long-lived subscriptions — all meaningless for call-scoped streams, and per-call isolation gives exact cancellation semantics.

### 5. Client: one `RpcStream` object, two pumps

A shared `RpcStream` (in `webcompy/rpc/_stream.py`) owns the `_StreamQueue`, `RpcStreamState` signal, close idempotency, `__aenter__/__aexit__`, and the destroy hook. Transport-specific pumps feed it: the HTTP pump consumes `FetchStream` chunks through the `sse-parser`, branches on `Content-Type` before returning (JSON → resolve/raise `RpcError`; SSE → parse), decodes items with `from_json` + meta, and aborts via `FetchStream.close()`; the WS pump receives `stream_id`-routed frames from the existing `_reader` (extended dispatch: `stream_id` map alongside `subscription_id`), converts `stream_done`/`stream_error`/disconnect into finish/RpcError, and sends `stream_cancel` on close. `RpcWsClient.stream()` raises when not usable (mirrors `call()`); `rpc.stream()` outside the browser returns the SSR-degraded closed stream (mirrors subscriptions). Both reject the flag-mismatch cases client-side before returning when the server answers `-32600`.

### 6. Backpressure and failure order

Per-item decode happens on the pump; the queue is the only buffer. HTTP naturally backpressures via the ASGI `send` await; WS reuses the unbounded per-connection send queue (documented caveat carried over from subscriptions). Mid-stream errors are raised at the point of consumption (`__anext__`), so items already queued are yielded before the error surfaces — order preserved.

## Risks / Trade-offs

- **[Risk] The dispatcher's dual-mode response (JSON vs SSE) must branch before any body is read or sent** → Mitigation: classification happens on the parsed envelope before invoking; unit tests cover every pre-stream failure path asserting `application/json`.
- **[Risk] Abandoned clients (no abort sent) leave generators running until disconnect is observed** → Mitigation: ASGI `http.disconnect` and WS close both cancel; acceptable latency, same as today's subscription cleanup on socket close.
- **[Risk] Sync generators that never yield again delay cancellation until the next yield** → Mitigation: documented `GeneratorExit`-at-yield semantics; fast loops are the normal case.
- **[Risk] Flag-mismatch errors require server and client to agree on reserved frame names (`_webcompy.stream_*`)** → Mitigation: names reserved by the existing `_webcompy.*` validation; WS endpoint constants shared with the client module.
- **[Trade-off] No `max_queue` capping for streams (unlike subscriptions)** → deliberate v1 non-goal; the pump drains continuously, and memory is bounded by producer rate, not subscription fan-out.

## Migration Plan

Additive-only: existing procedures, subscriptions, and clients are untouched; new members (`"stream"`) are ignored by non-WebComPy peers per the JSON-RPC extension rule. Rollback is a plain revert. Requires `feat-sse-post` to be present in the base (rebase before implementation).

## Open Questions

(none)
