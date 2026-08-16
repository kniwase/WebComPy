# Tasks: feat-websocket-composable

## 1. Port layer

- [x] 1.1 Create `packages/webcompy/src/webcompy/ports/_websocket.py` with the `WebSocketPort` ABC (callback-based open returning a handle with `send(text)`/`close()`; no component imports)
- [x] 1.2 Add `WEBSOCKET_PORT_KEY = InjectKey[WebSocketPort]("webcompy-port-websocket")` to `webcompy/ports/_keys.py` and export `WebSocketPort` from `webcompy/ports/__init__.py`
- [x] 1.3 Implement `BrowserWebSocketPort` in `webcompy/ports/_browser/_websocket.py` wrapping native `WebSocket` (message/close/error forwarding, send, close)
- [x] 1.4 Implement the server no-op `WebSocketPort` in `webcompy_server/ports/`
- [x] 1.5 Wire provisioning for browser / server (no-op) / testing (fake) render contexts (mirror the `EVENT_SOURCE_PORT_KEY` registration sites)

## 2. Composable

- [x] 2.1 Add the additive `RECONNECTING` member to the shared `ConnectionState` enum and the `CloseInfo` frozen dataclass in `webcompy/realtime/`
- [x] 2.2 Create `packages/webcompy/src/webcompy/realtime/_ws.py` with the WebSocket connection handle (AsyncIterator[str] + `.state` + `.last_close` + `.send()` + idempotent `.close()`), reusing `_registry.py` with the `(url, normalized_protocols)` key component
- [x] 2.3 Implement the reconnection loop on the registry-owned connection: exponential backoff `min(max_delay, base * 2**(n-1))` with jitter `[0.5, 1.0]`, unlimited attempts by default, `RECONNECTING` state during backoff/in-flight attempts, stop conditions (user close, clean 1000, `reconnect=False`, exhausted `reconnect_max_attempts` → `CLOSED`)
- [x] 2.4 Implement `.last_close` updates on every close (no reset on reopen) and the send policy (warn+discard default; opt-in FIFO buffer flushed on OPEN, discarded on terminal CLOSED)
- [x] 2.5 Implement no-DI-scope warning + private-connection fallback, native-URL passthrough, component-destroy detach, `weakref.finalize` protection, binary-frame ignore+warn, and SSR behavior (empty iterator, CLOSED, warning, no transfer)
- [x] 2.6 Export `use_websocket` and `CloseInfo` from `webcompy/realtime/__init__.py` and `webcompy/__init__.py`

## 3. Fake port

- [x] 3.1 Implement `FakeWebSocketPort` in `webcompy_testing` (instance-local registry keyed by `(url, protocols)`, sent-frames log, scripted `emit_message`/`emit_close`/open/error helpers with snapshotting, idempotent close) and provision it in the testing render path

## 4. Unit tests (`tests/`, browserless)

- [ ] 4.1 Handle contract: ordered iteration including duplicates; `.send` while OPEN sends exactly one frame; binary frame ignored with warning; importable from `webcompy` and `webcompy.realtime`
- [ ] 4.2 Sharing: same URL+protocols share one socket; different protocols do not share; last detach closes the socket; no-DI-scope fallback warns and isolates
- [ ] 4.3 Reconnect: abnormal close (1006) schedules a retry with delay within jitter bounds; backoff doubles to the cap; `RECONNECTING` during attempts; success returns to OPEN with transparent continuation
- [ ] 4.4 Reconnect stop conditions: clean 1000 close → CLOSED with no retry; user `.close()` cancels a pending retry; `reconnect=False` → single failure to CLOSED; `reconnect_max_attempts=2` exhausts to CLOSED
- [ ] 4.5 `.last_close`: records code/reason/was_clean; persists across a successful reconnect; `None` before any close
- [ ] 4.6 Send policy: disconnected send warns+discards by default; `buffer_while_disconnected=True` flushes FIFO on open; buffer discarded on terminal CLOSED
- [ ] 4.7 SSR: no port access, empty iterator, CLOSED, `.last_close is None`, send warns, no transfer payload entry
- [ ] 4.8 Lifecycle: component destroy detaches and cancels pending reconnect on last detach; abandoned iterator does not leak the reference count

## 5. E2E tests (`e2e/core/`)

- [ ] 5.1 Add a test WebSocket endpoint (echo + server-initiated close) to the E2E app via `WebComPyServerConfig.mounts` (asgi-mount)
- [ ] 5.2 Add an E2E page + Playwright test: send/receive round trip, two consumers sharing one socket, and reconnect visible via `.state` after a server-initiated abnormal close; gate with `WEBCOMPY_RUN_E2E=1` and wire into `scripts/run-e2e-tests.sh`

## 6. Docs (Markdown-driven, per docs-site-documents)

- [ ] 6.1 Add `docs_app/documents/websocket.md`: `use_websocket` usage, sharing/protocols keying, reconnection defaults and tuning, `.last_close`, disconnected-send policy, gap/refetch recipe
- [ ] 6.2 Register the page in `docs_app/docs_manifest.py` and add the `docs_app/pages/document/websocket.py` stub

## 7. Review knowledge sync

- [ ] 7.1 Update `AGENTS.md`: File → Spec Mapping rows for the new realtime/ports files; Current Specs entry for `websocket-composable`
- [ ] 7.2 Update `.opencode/skills/webcompy-review/SKILL.md` file→spec mapping and Critical Framework Invariants if a new invariant is introduced
- [ ] 7.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes

## 8. Validation

- [ ] 8.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [ ] 8.2 `uv run pyright` passes
- [ ] 8.3 `uv run python -m pytest tests/ --tb=short -q` passes (full suite, no regressions)
- [ ] 8.4 `openspec validate feat-websocket-composable` passes
