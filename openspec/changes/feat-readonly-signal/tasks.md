# Tasks: feat-readonly-signal

## 1. Core Primitive (`use_readonly_signal`)

- [ ] 1.1 Implement `use_readonly_signal(initial: T) -> (ReadonlySignal[T], Callable[[T], None])` in `packages/webcompy/src/webcompy/signal/_readonly.py` — create a private `Signal(initial)`, return `(readonly(inner), inner.set_value)`. Context-free: no component-context check, no `UserWarning`, no transfer registration, no lifecycle hooks.
- [ ] 1.2 Export `use_readonly_signal` from `webcompy.signal.__init__` and add it to the `webcompy` top-level `__init__.py` import/all list, following the `use_state` precedent.

## 2. Events Package (`webcompy/events`)

- [ ] 2.1 Create the `packages/webcompy/src/webcompy/events/` package (modeled on `webcompy/storage/`), including a local `on_before_destroy` chaining helper (replicating the storage `_register_destroy_unregister` pattern; no cross-package `_`-import).
- [ ] 2.2 Implement `use_window_event(event_type, initial, *, transform=None) -> (ReadonlySignal[T], Callable[[T], None])` — lazy `inject(HOST_PORT_KEY, default=None)`; attach only when an active component context exists and a `HostPort` resolves; wire `transform` (default identity) with `try/except` → `logging.warning` containment; register the port cleanup on `on_before_destroy`; `UserWarning` + no-op when no component context; no-op when the port is missing.
- [ ] 2.3 Implement `use_document_event(event_type, initial, *, transform=None)` with the same semantics using `DOMPort.add_document_event_listener` and `DOM_PORT_KEY`.
- [ ] 2.4 Export `use_window_event` and `use_document_event` from `webcompy.events.__init__` and add them to the `webcompy` top-level `__init__.py` import/all list.

## 3. Test Support (webcompy-testing)

- [ ] 3.1 Extend `FakeBrowserHostPort.add_window_event_listener` (and add equivalent `DOMPort` listener support on the fake DOM port) to record handlers per event type and expose a way to dispatch synthetic events and assert removal, so helper tests can fire `resize`-style events and observe cleanup.

## 4. Unit Tests

- [ ] 4.1 Add `tests/test_readonly_signal.py` covering the primitive scenarios from the spec: initial value, `update` as sole write path, equality no-notify on equal updates, absence of a write accessor on the returned type, and standalone (no component context) usage without warnings.
- [ ] 4.2 Add event-helper tests (e.g. `tests/test_readonly_event_sources.py`) for `use_window_event`/`use_document_event`: transform-driven updates on fired events, equality dedup, effective cleanup (listener removed) on component destroy, `UserWarning` + no attach outside component setup, and transform-exception containment.
- [ ] 4.3 Add an SSR-style test verifying that during server rendering (TestRenderer) the helpers render `initial` without attaching a real listener (i.e. `ServerHostPort`-style no-op path), and that `use_readonly_signal` values never appear in a hydration payload.

## 5. Docs & Governance

- [ ] 5.1 Add a `docs_app` markdown page for `readonly-signal` (alongside the existing signal-stream page), covering the primitive, the window/document helpers, and the why-not-occurrence-events guidance.
- [ ] 5.2 Update `AGENTS.md`: add `readonly-signal` to the "Current Specs" list and add File→Spec Mapping rows for `webcompy/signal/_readonly.py` and `webcompy/events/`.
- [ ] 5.3 Sync `.opencode/skills/webcompy-review/SKILL.md` file→spec mapping / invariant headings to reference the new `readonly-signal` spec where applicable.
- [ ] 5.4 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes.

## 6. Verification

- [ ] 6.1 Run `uv run ruff check .` and `uv run ruff format --check .` on the touched packages and tests; fix any findings.
- [ ] 6.2 Run `uv run pyright` and fix any type errors.
- [ ] 6.3 Run `uv run python -m pytest tests/ --tb=short` and confirm the full unit suite (including the new tests) passes.