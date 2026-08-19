# Tasks: feat-sse-post

## 1. Browser streaming spike

- [x] 1.1 Verify Pyodide/PyScript FFI mechanics for streaming reads: `res.body.getReader()`, awaiting `reader.read()`, `Uint8Array` → `bytes`, streaming `TextDecoder` with `{stream: true}`, and `AbortController`/`signal` on `fetch`, in a throwaway PyScript page; record any differences from the existing `BrowserFetchPort.fetch` pattern

## 2. FetchPort streaming primitive

- [x] 2.1 Add `FetchStream` (upfront `status_code`/`headers`/`ok`, `AsyncIterator[str]`, idempotent `close()`) and the concrete default `FetchPort.stream()` in `webcompy/ports/_fetch.py`; `ruff check` + `pyright` clean
- [x] 2.2 Implement real streaming in `BrowserFetchPort` per design decision 2 and spike 1.1 (reader loop, streaming TextDecoder, AbortController); `ruff check` + `pyright` clean
- [x] 2.3 Unit-test `FetchPort.stream` default fallback (single chunk, metadata, close idempotency) in `tests/`

## 3. SSE codec

- [x] 3.1 Create `webcompy/ajax/_sse.py` with the incremental parser (boundary-safe, comments, multi-`data:` join, `id:` persistence, trailing-partial discard, CRLF) and the frame formatter; `ruff check` + `pyright` clean
- [x] 3.2 Unit-test the parser against every `sse-parser` spec scenario (split chunks, multi-line data, named events, id persistence, comments, EOF discard, CRLF, formatter round-trip) in `tests/`

## 4. use_event_source POST path (basic)

- [x] 4.1 Extend `use_event_source(url, *, method="GET", body=None, headers=None)` with spec'd validation (GET + body/headers → ValueError, method validation) and the GET/non-GET transport branch; `ruff check` + `pyright` clean
- [x] 4.2 Implement the fetch-based open path in `webcompy/realtime/_sse.py` (open via `FetchPort.stream`, parser feed, per-subscriber event-type filtering mapped to `SSEvent`, synthesized open/error/close callbacks) without reconnection yet
- [x] 4.3 Unit-test the POST path with a fake streaming port (event delivery, event filtering, `last_event_id` on `SSEvent`, SSR empty-handle degradation for non-GET) in `tests/`

## 5. Reconnection and registry keying

- [x] 5.1 Extend the registry key component for the SSE transport to `(url, method, body)` for non-GET connections and skip the event-type-reopen logic for fetch-based connections (per-subscriber filtering)
- [x] 5.2 Implement the reconnect loop for fetch-based connections: `RECONNECTING` state, backoff via `_compute_reconnect_delay`, generation/retry-token guards, `Last-Event-ID` header, retry on EOF/error/non-successful status/non-SSE content type, termination only via close/detach
- [x] 5.3 Unit-test reconnection (EOF triggers retry, `Last-Event-ID` header content, close during `RECONNECTING` stops the loop, stale-stream completions ignored) and registry keying (different bodies never share, identical POSTs share, new event types do not reopen fetch connections) in `tests/`

## 6. Testing module

- [x] 6.1 Implement `FakeFetchPort.stream()` with scripted `streams` chunks, canned-response single-chunk fallback, `KeyError` for unregistered keys, and abort recording per the `testing-module` delta
- [x] 6.2 Unit-test `FakeFetchPort.stream` scenarios in `tests/`

## 7. E2E and docs

- [ ] 7.1 Add a browser E2E test in `e2e/` for the POST path: a Starlette SSE endpoint mounted via asgi-mount, POST with body, event delivery, and server-side close triggering client reconnection; run via `scripts/run-e2e-tests.sh`
- [ ] 7.2 Update the EventSource docs page in `docs_app/documents/` (POST usage, reconnection and `Last-Event-ID` semantics, non-goals) and any docs demo if applicable
- [ ] 7.3 Update `AGENTS.md` review-knowledge tables (File → Spec Mapping row for `webcompy/ajax/_sse.py` and `webcompy/ports/_fetch.py`, Current Specs list entry for `sse-parser`) and run `python3 scripts/check-doc-spec-refs.py` until it passes

## 8. Verification

- [ ] 8.1 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, and `uv run python -m pytest tests/ --tb=short`; fix all failures
- [ ] 8.2 Run `openspec validate feat-sse-post --strict` and resolve all findings
