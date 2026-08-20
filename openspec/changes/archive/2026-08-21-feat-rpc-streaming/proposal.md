# Proposal: feat-rpc-streaming

## Why

RPC procedures today produce a single value per call. Finite streaming responses — one call, one bounded stream of typed results, consumed with `async for` — cannot be expressed: the existing subscription machinery (`register_subscription` + `RpcWsClient.subscribe`) models infinite, shared, fan-out event streams with cursor/replay/rejoin semantics, which are the wrong shape for call-scoped one-shot streams. Streaming must also work in environments where WebSocket is unavailable, so an HTTP transport is required.

## What Changes

- `@app.rpc.procedure` gains streaming support: generator functions whose return annotation is `AsyncIterator[T]` / `AsyncIterable[T]` (async generator functions) or `Iterator[T]` / `Iterable[T]` (sync generator functions) register as streaming procedures, with the element type `T` as the result schema. Unsubscripted return annotations and non-generator functions with iterable annotations are rejected at registration time.
- New JSON-RPC extension member `"stream": true` on single requests. A streaming procedure called without the member, or a non-streaming procedure called with it, SHALL answer `-32600` with a descriptive message. Streaming entries in batch requests SHALL each answer `-32600`; notifications targeting streaming procedures SHALL NOT execute.
- HTTP transport: a flagged single request over the existing `/_webcompy-rpc` endpoint answers with a `text/event-stream` response (`Cache-Control: no-store`) carrying `item` events (`{"data": ..., "meta": ...}`), a `done` event on generator exhaustion, and an `error` event (`{"code", "message", "data"}`) on mid-stream failure. All pre-stream errors (method not found, invalid params, mismatch, batch/notification rejection) keep the standard `application/json` JSON-RPC error responses. Client disconnect SHALL cancel the generator.
- WebSocket transport: a flagged call over `RpcWsClient` answers `{"result": {"stream_id": ...}, "id": ...}`, then delivers items as existing `_webcompy.event` frames carrying `stream_id` (no cursor), `_webcompy.stream_done` on exhaustion, `_webcompy.stream_error` on mid-stream failure, and accepts `_webcompy.stream_cancel` for client-initiated cancellation. Per-call streams are managed by a dedicated lightweight hub (no sharing, replay, or idle grace). Connection loss SHALL fail the stream with `RpcError` (never silently retried, like `call()`).
- Client APIs: `rpc.stream(method, params, *, result_type=None)` over HTTP (reusing `FetchPort.stream` and the `sse-parser` codec from `feat-sse-post`) and `RpcWsClient.stream(method, params, *, result_type=None)` over WebSocket. Both return an `RpcStream[T]`: an `AsyncIterator` with per-item typed decoding (`from_json` + transfer `meta`), `.state: Signal[RpcStreamState]` (`OPEN` / `CLOSED` / `FAILED`), idempotent `.close()`, and `async with` support. Mid-stream errors raise `RpcError` from `__anext__`. Closing (or component destroy) aborts the HTTP fetch / sends the WS cancel notification.
- SSR/SSG: `stream()` returns an immediately-finished empty iterator with a warning; no hydration transfer. Streaming calls bypass the fetch transfer cache.

## Capabilities

### New Capabilities

- `rpc-streaming`: The streaming-procedure contract — registration by generator return annotation, the `"stream"` request member, per-transport stream wire protocols (HTTP SSE and WebSocket frames), typed per-item decoding, `RpcStream` client consumption, cancellation, and SSR degradation.

### Modified Capabilities

- `json-rpc`: the `"stream"` extension member, dispatcher SSE responses, batch/notification restrictions, and symmetric mismatch errors on procedure registration/invocation.
- `rpc-websocket`: stream-call frames over the shared WebSocket (`stream_id` event delivery, `stream_done`/`stream_error`/`stream_cancel`), per-connection stream lifecycle, and fail-fast behavior on disconnect.

## Impact

- **Code**: `packages/webcompy/src/webcompy/rpc/_registry.py` (streaming detection, element-type extraction, validation), `packages/webcompy/src/webcompy/rpc/_client.py` (`stream()`, `RpcStream`), `packages/webcompy/src/webcompy/rpc/_ws_client.py` (`RpcWsClient.stream()`, `stream_id` dispatch, cancel), new `packages/webcompy/src/webcompy/rpc/_stream.py` (client-side stream object/pump), `packages/webcompy-server/src/webcompy_server/rpc/_dispatcher.py` (SSE streaming response, disconnect handling), `packages/webcompy_server/rpc/_ws_endpoint.py` + new `_streams.py` (`StreamCallHub`).
- **APIs**: additive only (`rpc.stream`, `RpcWsClient.stream`, `RpcStream`, `RpcStreamState`, the `"stream"` request member). Existing `call` / `notify` / `batch` / `subscribe` behavior unchanged for existing procedures.
- **Dependencies**: `feat-sse-post` (`FetchPort.stream` / `FetchStream`, the `sse-parser` codec). No new third-party dependencies.
- **Docs**: update the RPC and RPC-over-WebSocket docs pages with streaming sections; add the `rpc-streaming` capability to the review-knowledge tables in `AGENTS.md`.

## Known Issues Addressed

(none)

## Non-goals

- Infinite, shared event subscriptions — that is `register_subscription` / `RpcWsClient.subscribe`, unchanged.
- Cursors, replay buffers, or rejoin for call-scoped streams (WebSocket streams fail on disconnect; HTTP streams have no reconnection).
- SSR/SSG baking of stream results into hydration (SSR returns an empty stream).
- Delivery of RPC streams through `use_event_source` or the realtime composables.
- Streaming in batch requests (rejected per-entry) and notifications (not executed).
- Backpressure beyond the client-side queue (`max_queue`-style capping is not part of this change; the client pump drains the wire as fast as it arrives).
