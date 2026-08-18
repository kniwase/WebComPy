# Tasks: feat-rpc-websocket

## 1. Spike: reconnect resubscribe and state resync

- [x] 1.1 Time-boxed spike: build a minimal prototype of the rejoin-with-cursor protocol against a real Starlette WebSocket endpoint — validate replay-before-live ordering, buffer overflow → `resync_required`, and cleanup on close; record findings in the design and adjust spec details if needed

## 2. Transport-neutral dispatcher

- [x] 2.1 Extract the dispatch core in `packages/webcompy-server/src/webcompy_server/rpc/_dispatcher.py` into a transport-neutral function over plain request/response objects (HTTP behavior unchanged)
- [x] 2.2 Create `_ws_endpoint.py`: Starlette WebSocket endpoint feeding text frames through the shared core, writing responses back, managing per-connection state, mounted via the same mount mechanism
- [x] 2.3 Implement subscription procedure registration (async stream source, per-stream monotonic cursor, bounded replay buffer with configurable size, rejoin with `last_cursor`, `resync_required` on overflow, cleanup on socket close)
- [x] 2.4 Add `force_close(code, reason)` to the realtime WebSocket handle (`WebSocketHandle`/`TypedWebSocketHandle` + `_RealtimeRegistry._ws_abort`) with a generation guard so stale socket close events are ignored
- [x] 2.5 Handle the reserved `_webcompy.close` notification in the WS endpoint by closing the socket with code `1011`, and reject `_webcompy.*` names in `ProcedureRegistry.register`/`register_subscription`

## 3. Client

- [x] 3.1 Create `packages/webcompy/src/webcompy/rpc/_ws_client.py`: `RpcWsClient` over the typed realtime handle — id-correlated calls (in-flight map), notifications, `RpcError` mapping, in-flight failure on disconnect
- [x] 3.2 Implement `subscribe(method, params, *, event_type=E)`: subscription registry keyed by `subscription_id`, cursor tracking, ordered delivery, unsubscribe notification, component-destroy detach
- [x] 3.3 Implement automatic rejoin-with-cursor on reconnect and `resync_required` surfacing on the subscription state
- [x] 3.4 Implement the heartbeat (reserved notification method names, configurable interval/timeout, timeout → forced abnormal close; `heartbeat_interval=None` disables)
- [x] 3.5 Implement SSR no-op + warning and no hydration transfer; public re-exports from `webcompy/rpc/__init__.py` and `webcompy/__init__.py`

## 4. Unit tests (`tests/`, browserless)

- [x] 4.1 Dispatcher: WS frame round trip matches HTTP semantics (envelope validation, batch, errors); close cleans up subscriptions
- [x] 4.2 Server subscriptions: cursor monotonicity, bounded replay, rejoin replay-before-live, overflow → `resync_required`
- [x] 4.3 Client calls: id correlation, notification fire-and-forget, `RpcError` mapping, in-flight failure on disconnect
- [x] 4.4 Client subscriptions: ordered typed iteration, unsubscribe finishes the iterator, rejoin with last cursor after simulated reconnect, `resync_required` surfaced
- [x] 4.5 Heartbeat: timeout forces abnormal close and reconnect; disabled when `heartbeat_interval=None`
- [x] 4.6 SSR: no socket work, warning, no transfer payload entries
- [x] 4.7 `force_close`: state transitions to `RECONNECTING` then `OPEN`, no-op on closed connections, stale close events ignored, typed handle forwarding

## 5. E2E tests (`e2e/core/`)

- [x] 5.1 Mount the WS RPC endpoint in the E2E app and add a Playwright test: typed call round trip
- [x] 5.2 Add a Playwright test: subscription events render; after a server-initiated abnormal close and emitted events, the client reconnects and catch-up delivers the missed events exactly once; gate with `WEBCOMPY_RUN_E2E=1`

## 6. Docs (Markdown-driven, per docs-site-documents)

- [x] 6.1 Add `docs_app/documents/rpc_websocket.md`: WS RPC calls, subscriptions with cursors, reconnect/catch-up/`resync_required` semantics with the refetch recipe, heartbeat tuning
- [x] 6.2 Register the page in `docs_app/docs_manifest.py` and add the `docs_app/pages/document/rpc_websocket.py` stub

## 7. Review knowledge sync

- [x] 7.1 Update `AGENTS.md`: File → Spec Mapping rows for the new rpc files; Current Specs entry for `rpc-websocket`
- [x] 7.2 Update `.opencode/skills/webcompy-review/SKILL.md` file→spec mapping and Critical Framework Invariants if a new invariant is introduced
- [x] 7.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes

## 8. Validation

- [x] 8.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [x] 8.2 `uv run pyright` passes
- [x] 8.3 `uv run python -m pytest tests/ --tb=short -q` passes (full suite, no regressions)
- [x] 8.4 `openspec validate feat-rpc-websocket` passes

## 9. Review fixes

- [x] 9.1 Client: a subscription answered with `resync_required` (or an error) on rejoin SHALL be removed from the subscription tracking so it is never re-subscribed on later reconnects (`_fail_subscribe` in `_ws_client.py`); stale pending-subscribe id mappings are cleared when in-flight calls fail
- [x] 9.2 Server: a rejoin that answers `resync_required` on a stream with no subscribers SHALL reap the (possibly freshly created) stream instead of leaving its source task running forever
- [x] 9.3 Server: a stream whose source has ended SHALL be reaped after the idle grace period, and a subscribe targeting a finished stream SHALL start a fresh stream instead of attaching to the dead one
- [x] 9.4 Realtime: `force_close` SHALL respect `reconnect=False` and `reconnect_max_attempts` (terminating the connection instead of scheduling a retry)
- [x] 9.5 Docs: fix the `register_subscription` example (async generator function with typed params) and the `resync_required` recovery recipe (state check after the iterator ends); add server capacity guidance
- [x] 9.6 Client: `_handle_subscribe_response` SHALL ignore responses for closed subscriptions (a `sub._done` guard) so a rejoin answered after `sub.close()` cannot re-register or re-activate the subscription
- [x] 9.7 Client: on permanent connection termination (state `CLOSED`), SHALL end every live and pending subscription with state `CLOSED` and finish their iterators
- [x] 9.8 Server: `check_rejoin` SHALL replay the full buffer when `last_cursor == buffer floor - 1` (every missed event is still buffered); `resync_required` only when a missed event was evicted
- [x] 9.9 Align the delta specs with the review fixes: replay-boundary wording, the permanent-termination requirement, and the `force_close` wire wording

## 10. Review fixes (round 2)

- [x] 10.1 Client: `subscribe()` on a permanently terminated connection (state `CLOSED`) SHALL return a `CLOSED` subscription instead of hanging in `PENDING` forever
- [x] 10.2 Client: a rejoin without received events SHALL send `last_cursor: 0` so the server replays the whole buffer (or answers `resync_required` when the buffer no longer covers cursor `0`); a genuinely fresh subscribe SHALL still omit the cursor
- [x] 10.3 Server: `reap` SHALL remove a stream from the hub only when the hub entry still points to that exact stream, so reaping a finished stream can never evict its replacement
- [x] 10.4 Server: an id-less `_webcompy.subscribe` notification SHALL be ignored (no response frame, no orphan subscription stream)
- [x] 10.5 Docs: lifecycle guidance (component-scoped creation or explicit `close()`) in the RPC-WS docs page and `RpcWsClient` docstring; delta spec and design notes for the zero-cursor rejoin
