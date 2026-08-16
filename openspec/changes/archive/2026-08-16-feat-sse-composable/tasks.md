# Tasks: feat-sse-composable

## 1. Port layer

- [x] 1.1 Create `packages/webcompy/src/webcompy/ports/_event_source.py` with the `EventSourcePort` ABC (callback-based open method taking url + event types + callbacks, returning a cleanup callable; no component imports)
- [x] 1.2 Add `EVENT_SOURCE_PORT_KEY = InjectKey[EventSourcePort]("webcompy-port-event-source")` to `webcompy/ports/_keys.py` and export `EventSourcePort` from `webcompy/ports/__init__.py`
- [x] 1.3 Implement `BrowserEventSourcePort` in `webcompy/ports/_browser/_event_source.py` wrapping native `EventSource` (register listeners for requested event types, forward events, cleanup closes the connection)
- [x] 1.4 Implement the server no-op `EventSourcePort` in `webcompy_server/ports/` (no browser API access, returns no-op cleanup)
- [x] 1.5 Wire provisioning: browser context provides the browser port, server context the no-op port, testing path the fake port (mirror `CUSTOM_ELEMENT_PORT_KEY` registration sites)

## 2. Shared connection registry

- [x] 2.1 Create `packages/webcompy/src/webcompy/realtime/_registry.py`: transport-agnostic registry keyed by `(transport, url)`, stored in the app DI scope via the `_get_app_di_scope()` + inject-or-provide pattern (mirror `storage/_composable.py._get_or_create_registry`); reference-counted open/close; per-subscriber FIFO queues (unbounded default, `max_queue` drop-oldest, reuse `aio/_stream.py._StreamQueue` semantics)
- [x] 2.2 Implement subscriber detach (idempotent) and last-detach connection close, including `weakref.finalize` protection for abandoned iterators

## 3. Composable

- [x] 3.1 Create `packages/webcompy/src/webcompy/realtime/_sse.py` with `SSEvent` frozen dataclass, `ConnectionState` enum, and the connection-handle class (AsyncIterator + `.state: Signal[ConnectionState]` + idempotent `.close()` detaching only the caller's subscription)
- [x] 3.2 Implement `use_event_source(url, *, events=("message",), max_queue=None)`: DI-scope registry path, no-scope warning + private-connection fallback, native-URL passthrough, component-destroy detach via `on_before_destroy` chaining (mirror `events/_composable.py._register_destroy_cleanup`)
- [x] 3.3 Implement SSR behavior: empty finished iterator, `state == CLOSED`, warning, no hydration transfer entry
- [x] 3.4 Create `webcompy/realtime/__init__.py` and add public re-exports (`use_event_source`, `SSEvent`, `ConnectionState`) to `webcompy/__init__.py`

## 4. Fake port

- [x] 4.1 Implement `FakeEventSourcePort` in `webcompy_testing` (instance-local registry keyed by `(url, events)`, idempotent cleanup, scripted `emit_*` helpers with callback-list snapshotting) and provision it in the testing render path

## 5. Unit tests (`tests/`, browserless)

- [x] 5.1 Handle contract: async iteration yields `SSEvent`s in order including duplicates; `.state` transitions CONNECTING → OPEN → CLOSED; importable from `webcompy` and `webcompy.realtime`
- [x] 5.2 Event filtering: default delivers only `message`; `events=("status",)` filters named types; `last_event_id` is carried
- [x] 5.3 Registry: same-URL subscribers share one connection (one port open call); each receives events independently; slow consumer does not block others; last detach closes the connection; different URLs open separate connections
- [x] 5.4 Queue policy: unbounded default preserves all events; `max_queue=2` drops oldest per subscriber without affecting others
- [x] 5.5 close semantics: `.close()` detaches only self (shared connection stays open for others), iterator finishes, idempotent
- [x] 5.6 Fallback: no app DI scope emits `UserWarning` and creates independent private connections
- [x] 5.7 SSR: no port access, empty iterator, `state == CLOSED`, warning, no transfer payload entry
- [x] 5.8 Lifecycle: component destroy detaches; `async for` + `break` without close does not leak the reference count (GC-triggered finalize)

## 6. E2E tests (`e2e/core/`)

- [x] 6.1 Add a test SSE endpoint to the E2E app via `WebComPyServerConfig.mounts` (asgi-mount) that streams a fixed event sequence
- [x] 6.2 Add an E2E page + Playwright test asserting received events render (shared connection visible: two consumers, one connection), gated by `WEBCOMPY_RUN_E2E=1` and wired into `scripts/run-e2e-tests.sh`

## 7. Docs (Markdown-driven, per docs-site-documents)

- [x] 7.1 Add `docs_app/documents/event_source.md` (frontmatter + body): `use_event_source` usage, connection sharing, `max_queue`, close semantics, gap/refetch recipe (`state` returns to OPEN → re-pull authoritative state)
- [x] 7.2 Register the page in `docs_app/docs_manifest.py` and add the `docs_app/pages/document/event_source.py` stub

## 8. Review knowledge sync

- [x] 8.1 Update `AGENTS.md`: File → Spec Mapping rows for `webcompy/realtime/`, `ports/_event_source.py`, `ports/_browser/_event_source.py`; Current Specs entries for `sse-composable`
- [x] 8.2 Update `.opencode/skills/webcompy-review/SKILL.md` file→spec mapping and Critical Framework Invariants if a new invariant is introduced
- [x] 8.3 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes

## 9. Validation

- [x] 9.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [x] 9.2 `uv run pyright` passes
- [x] 9.3 `uv run python -m pytest tests/ --tb=short -q` passes (full suite, no regressions)
- [x] 9.4 `openspec validate feat-sse-composable` passes