# Tasks: feat-readonly-signal

## 1. Change Artifact Corrections

- [x] 1.1 Correct `proposal.md`: update the `use_readonly_signal` return contract to `(ReadonlySignal[T], Callable[[T], T])`, add `components` and `testing-module` to Modified Capabilities, and update the Impact section (async-setup cleanup in `components/_component.py`, fake-port listener support).
- [x] 1.2 Correct `specs/readonly-signal/spec.md`: `update` typed `Callable[[T], T]` (bound `set_value`, returns current value; add "update returns the current value" scenario), `transform` typed `Callable[[Any], T] | None` with identity semantics, `ReadonlySignal` exported from `webcompy.signal` (not top-level), and the async-setup-failure cleanup scenario.
- [x] 1.3 Add `specs/components/spec.md` delta: async component setup failure SHALL run destroy hooks registered inside the async body (framework cleanup first, no re-run of the failed setup).
- [x] 1.4 Add `specs/testing-module/spec.md` delta: fake Host/DOMPort listener recording, `dispatch_window_event`/`dispatch_document_event`, idempotent per-handler removal; server no-op behavior unchanged.
- [x] 1.5 Correct `design.md`: D1 (return type), D3 (registration-order constraint, context-before-DI), D5 (transform typing), D7 (document-listener fakes + testing-module delta), add D8 (async setup cleanup) and D9 (public `ReadonlySignal` type), resolve Open Questions.
- [x] 1.6 Validate the change: `openspec validate feat-readonly-signal --type change` passes.

## 2. Core Primitive (`use_readonly_signal`)

- [x] 2.1 Implement `use_readonly_signal(initial: T) -> tuple[ReadonlySignal[T], Callable[[T], T]]` in `packages/webcompy/src/webcompy/signal/_readonly.py` — create a private `Signal(initial)` (imported from `webcompy.signal._base`), return `(readonly(inner), inner.set_value)`. Context-free: no component-context check, no `UserWarning`, no transfer registration, no lifecycle hooks; a callable `initial` is treated as a plain value.
- [x] 2.2 Export `use_readonly_signal` and `ReadonlySignal` from `webcompy.signal.__init__`; add `use_readonly_signal` (only) to the `webcompy` top-level `__init__.py` import/all list.
- [x] 2.3 Add `tests/test_readonly_signal.py`: initial value readable immediately, `update` as sole write path, `update` returns the current value (including on equal write), equal consecutive updates do not notify, no value setter / no `set_value` on the returned type, standalone usage emits no `UserWarning`, top-level vs `webcompy.signal` import identity.

## 3. Events Package (`webcompy/events`)

- [x] 3.1 Create `packages/webcompy/src/webcompy/events/` (modeled on `webcompy/storage/`) with a local `on_before_destroy` chaining helper (replicating the storage `_register_destroy_unregister` pattern; no cross-package `_`-import).
- [x] 3.2 Implement `use_window_event(event_type, initial, *, transform=None) -> tuple[ReadonlySignal[T], Callable[[T], T]]` — check `_get_active_component_context()` BEFORE `inject(HOST_PORT_KEY, default=None)`; attach only when a component context exists AND a `HostPort` resolves; `transform: Callable[[Any], T] | None` (identity when `None`) with `try/except` → `webcompy.logging.warning` containment scoped to the transform call; register the port cleanup on `on_before_destroy`; `UserWarning` + no-op when no component context; no-op when the port is missing.
- [x] 3.3 Implement `use_document_event(event_type, initial, *, transform=None)` with the same semantics using `DOMPort.add_document_event_listener` and `DOM_PORT_KEY`.
- [x] 3.4 Export `use_window_event` and `use_document_event` from `webcompy.events.__init__` and add them to the `webcompy` top-level `__init__.py` import/all list (import `events` after `signal`; keep lifecycle/DI imports lazy inside the functions).

## 4. Test Support (webcompy-testing)

- [x] 4.1 Extend `FakeBrowserHostPort.add_window_event_listener` to record handlers per event type in an instance-local registry, return an idempotent cleanup removing exactly that handler, and expose `dispatch_window_event(event_type, event)` (snapshot the handler list; skip handlers removed during dispatch).
- [x] 4.2 Override `FakeBrowserDOMPort.add_document_event_listener` with the same recording semantics and expose `dispatch_document_event(event_type, event)`. `ServerHostPort`/`ServerDOMPort` no-op behavior SHALL remain unchanged.

## 5. Async Setup Failure Cleanup

- [x] 5.1 Fix `Component._cleanup_pending_async()` in `packages/webcompy/src/webcompy/components/_component.py` so the destroy hook is refreshed from the current `Context` (capturing hooks registered inside the failed async body) and invoked with framework cleanup first, without re-running the failed setup and without masking the original error.
- [x] 5.2 Add regression tests in `tests/test_async_component_context.py`: listener cleanup registered in a failed async setup runs exactly once; success-path cleanup ordering (framework before user hook) is unchanged.

## 6. Event Helper & SSR/SSG Unit Tests

- [x] 6.1 Add `tests/test_readonly_event_sources.py` for `use_window_event`/`use_document_event`: transform-driven updates on dispatched events, equality dedup (no notification on equal transformed value), effective removal on destroy (via `result._instance._remove_element()`; `TestRendererResult.close()` does NOT destroy components), no update after destroy, `UserWarning` + no attach outside component setup (even when an app DI scope is active), missing-port no-op without warning, transform-exception containment (logged, signal unchanged), exactly one listener across re-renders, chaining with a pre-existing destroy hook.
- [x] 6.2 Add SSR/SSG tests via `render_app_html` (server context, `ServerHostPort`/`ServerDOMPort`): helpers render `initial` with no `UserWarning`; the `__webcompy_data__` script is parseable and its `signals` section contains no readonly state.

## 7. Docs & Governance

- [x] 7.1 Add `docs_app/documents/readonly_signal.md` (primitive, window/document helpers, why-not-occurrence-events guidance, standalone pattern, SSR/SSG note), `docs_app/pages/document/readonly_signal.py`, and a manifest entry immediately after the signal-stream page.
- [x] 7.2 DEFERRED to the spec-sync step (per user decision) and performed there: `AGENTS.md` updated — "Current Specs" list entry for `readonly-signal` added after `signal-stream`, File→Spec Mapping rows added for `webcompy/signal/_readonly.py` and `webcompy/events/`.
- [x] 7.3 DEFERRED to the spec-sync step (per user decision) and performed there: `.opencode/skills/webcompy-review/SKILL.md` Critical Framework Invariants gained the heading "Readonly Signal & Event Source Lifecycle — `readonly-signal/spec.md`" (after "Event Handler Leaks").
- [x] 7.4 Run `python3 scripts/check-doc-spec-refs.py` and confirm it passes (no new spec references were added in this change).

## 8. Docs E2E

- [x] 8.1 Add `e2e/docs/test_readonly_signal.py`: page title, layout/sidebar, TOC anchors, Prev/Next links (signal-stream → readonly-signal), no console errors.
- [x] 8.2 Update `e2e/docs/test_signal_stream.py` (signal-stream is no longer the last page: its next-link assertion changes to point at readonly-signal).
- [x] 8.3 Register the new file in the `docs-documents` group in `scripts/run-e2e-tests.sh` AND `.github/workflows/ci.yml` (definitions must match).

## 9. Verification

- [x] 9.1 Run `openspec validate feat-readonly-signal --type change`, `openspec validate --specs`, `openspec validate --changes`.
- [x] 9.2 Run `uv run ruff check .` and `uv run ruff format --check .`; fix any findings.
- [x] 9.3 Run `uv run pyright`; fix any type errors.
- [x] 9.4 Run `uv run python -m pytest tests/ --tb=short`; the full unit suite (including new tests) passes.
- [x] 9.5 Run `uv run python -m webcompy generate --config docs_app.webcompy_config` (docs changed).
- [x] 9.6 Run `uv build --package webcompy` and confirm `webcompy/events/` and `webcompy/signal/_readonly.py` are inside the wheel.
- [x] 9.7 Run the full E2E matrix via `scripts/run-e2e-tests.sh` (all core + docs groups, both prod and static modes where applicable; split into per-mode invocations if the runtime requires it, but never skip a group).

## 10. Verification Report

- [x] 10.1 Run the openspec-verify-change flow (completeness/correctness/coherence); produce the report; if any CRITICAL issue remains, STOP and report rather than guessing fixes.
- [x] 10.2 Final commit recording the verification (e.g. `chore: record readonly signal verification`).

## 11. Review Follow-up (PR #253 AI review)

- [x] 11.1 Fix `SuspenseElement` so pending async components run their destroy hooks when resolution fails or is cancelled: add `_cleanup_pending_pairs` and invoke it in `_browser_resolve` (exception and cancellation branches, before `_handle_error`) and in `_server_render` (error-fallback branch before replacing children). No contract change — this makes the existing async-setup-failure cleanup requirement hold on the Suspense path.
- [x] 11.2 Add regression tests `TestSuspenseAsyncSetupFailureCleanup` in `tests/test_async_component_context.py`: browser error-fallback path, browser ErrorBoundary routing path, browser removal-while-resolving (cancellation) path, and server error-fallback path; each asserts the `use_window_event` listener and user destroy hook behave as on the direct path.
- [x] 11.3 Add a docstring to `use_readonly_signal` (public top-level primitive; matches sibling composable convention).
- [x] 11.4 Verify: ruff, pyright, full unit suite, full core E2E matrix, `openspec validate --changes`.
