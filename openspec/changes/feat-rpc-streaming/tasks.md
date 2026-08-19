# Tasks: feat-rpc-streaming

## 0. Preconditions

- [x] 0.1 Rebase this branch onto the updated base that includes `feat-sse-post` and verify `FetchPort.stream` / `FetchStream` and the `sse-parser` module are available

## 1. Registry streaming detection

- [x] 1.1 Add `is_streaming` to `ProcedureInfo` and implement generator/iterable return-annotation detection with element-type extraction and the spec'd validation rejections in `webcompy/rpc/_registry.py`; `ruff check` + `pyright` clean
- [x] 1.2 Unit-test registration cases (async gen, sync gen, unsubscripted, non-generator with iterable annotation, name collision) in `tests/`

## 2. HTTP dispatcher SSE streaming

- [x] 2.1 Implement envelope classification in `webcompy_server/rpc/_dispatcher.py` (stream member rules, batch/notification rejection, `-32600` mismatch bodies) shared by both transports
- [x] 2.2 Implement the SSE streaming response in the dispatcher (`text/event-stream` + `Cache-Control: no-store`, `item`/`done`/`error` frames via the `sse-parser` formatter, sync-generator async wrapper) and the disconnect watcher that cancels and closes the generator; `ruff check` + `pyright` clean
- [x] 2.3 Unit-test the HTTP stream path with the ASGI test client (items + done, mid-stream error event, JSON errors for pre-stream failures, batch/notification rules, disconnect stops the generator) in `tests/`

## 3. WebSocket endpoint stream calls

- [x] 3.1 Add `StreamCallHub` (per-connection, per-call generator tasks, `stream_id` emission, done/error frames, cancel on `stream_cancel` and socket close) in a new `webcompy_server/rpc/_streams.py` and wire flagged calls in `_ws_endpoint.py`; `ruff check` + `pyright` clean
- [x] 3.2 Unit-test the WS stream protocol (ack shape, event frames without cursor, done/error ordering, cancel stops the generator, socket close cancels all streams, per-call isolation) in `tests/`

## 4. Client RpcStream object

- [x] 4.1 Implement `RpcStream` in `webcompy/rpc/_stream.py`: `AsyncIterator` with typed per-item decode (`from_json` + transfer `meta`), `RpcStreamState {OPEN, CLOSED, FAILED}` signal, idempotent `.close()`, `async with` support, component-destroy hook, SSR degraded empty stream; `ruff check` + `pyright` clean
- [x] 4.2 Unit-test `RpcStream` semantics (typed items, mid-stream `RpcError`, exhaustion, close idempotency, `async with`, destroy hook, SSR degradation) in `tests/`

## 5. HTTP client stream

- [x] 5.1 Implement `rpc.stream()` in `webcompy/rpc/_client.py`: flagged envelope POST through `FetchPort.stream`, `Content-Type` branching (JSON error → `RpcError` before return, SSE → parse with `sse-parser`), pump task, abort on close; update exports; `ruff check` + `pyright` clean
- [x] 5.2 Unit-test the HTTP client stream (JSON error path, chunk-boundary SSE parsing with `FakeFetchPort.stream`, typed decode, close aborts the fetch, SSR no-op) in `tests/`

## 6. WebSocket client stream

- [ ] 6.1 Implement `RpcWsClient.stream()` in `webcompy/rpc/_ws_client.py`: flagged call, `stream_id` frame dispatch alongside `subscription_id`, `stream_done`/`stream_error` handling, `stream_cancel` on close, fail-fast `RpcError` when unusable, disconnect → `RpcError` (no resubscribe); `ruff check` + `pyright` clean
- [ ] 6.2 Unit-test the WS client stream (ack → active, event routing by `stream_id`, done/error mapping, cancel notification, fail-fast when closed, disconnect failure) in `tests/`

## 7. E2E and docs

- [ ] 7.1 Add browser E2E tests in `e2e/` for HTTP streaming (async-generator procedure over the real dispatcher, typed items, mid-stream error, close/cancel) and WebSocket streaming (stream frames, cancel, disconnect); run via `scripts/run-e2e-tests.sh`
- [ ] 7.2 Update `docs_app/documents/rpc.md` and `rpc_websocket.md` with streaming sections (registration, `rpc.stream` / `RpcWsClient.stream`, wire formats, cancellation, SSR behavior, non-goals)
- [ ] 7.3 Update `AGENTS.md` review-knowledge tables (File → Spec Mapping for the new/changed rpc files and the `rpc-streaming` capability, Current Specs list) and run `python3 scripts/check-doc-spec-refs.py` until it passes

## 8. Verification

- [ ] 8.1 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, and `uv run python -m pytest tests/ --tb=short`; fix all failures
- [ ] 8.2 Run `openspec validate feat-rpc-streaming --strict` and resolve all findings
