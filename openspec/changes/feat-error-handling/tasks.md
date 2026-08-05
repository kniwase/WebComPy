# Tasks

## 1. Core ErrorBoundary Element

- [x] 1.1 Implement `packages/webcompy/src/webcompy/elements/types/_error_boundary.py`: `ErrorBoundaryElement(DynamicElement)` with `children`/`fallback`/`on_error`/`catch_events`; `_render()` wraps children render in try/except; fallback swap reuses the `_patch_children` / `_position_element_nodes` / re-index pattern from `SuspenseElement._handle_error` (`_suspense.py:184-204`)
- [x] 1.2 Implement the D2 propagation walk (parent-chain ascent: component hooks nearest-first with `False` veto → nearest boundary → global handler/log) with lazy `Component` import to avoid cycles; a boundary never catches its own fallback (walk starts above it)
- [x] 1.3 Implement `reset()`: destroy subtree (component destruction + DI-scope disposal), re-run children generator; boundary state is ephemeral (no hydration serialization, no reconciliation keys)
- [x] 1.4 Export `ErrorBoundary` from `webcompy.elements` (mirror the `Suspense = SuspenseElement` pattern)
- [x] 1.5 Unit tests: sync/async setup error → fallback; sibling survival; nested boundaries nearest-first; error-in-fallback escalates; reset success/failure paths

## 2. on_error_captured Hook

- [x] 2.1 Add `context.on_error_captured(fn)` registration following the `_active_component_context` pattern (`components/_hooks.py:40-45`); raise `LookupError` outside setup
- [x] 2.2 Store hooks on the component instance alongside the existing hook machinery (`components/_component.py:225-234`); release on destroy
- [x] 2.3 Unit tests: invocation order (nearest-first), veto semantics, release-on-destroy, LookupError outside setup

## 3. Global Handler and Event-Handler Routing

- [x] 3.1 Add `on_error: Callable[[Exception], Any] | None = None` to `WebComPyAppConfig` (`app/_config.py:18`); swallow+log exceptions raised by the handler itself
- [x] 3.2 Wrap `_generate_event_handler` (`elements/types/_element.py:24-31`) for sync and async (via the `resolve_async` error path) errors, routing into the propagation walk from the attached element; preserve create_proxy/destroy lifecycle
- [x] 3.3 Unit tests: sync/async handler errors reach global handler without DOM change; `catch_events=True` boundary engages; proxy destroy unaffected

## 4. Reactive Re-render and Lifecycle Catch Points

- [x] 4.1 Wrap the internal refresh entry points of dynamic containers (`_dynamic.py`, `_repeat.py`, `_switch.py`) so re-render exceptions route via the propagation walk from the raising element
- [x] 4.2 Catch lifecycle-hook (`on_before_rendering`/`on_after_rendering`/`on_before_destroy`) exceptions at their invocation sites in `Component` and route them
- [x] 4.3 Unit tests: signal-driven re-render failure → boundary fallback, app stays reactive; lifecycle hook error routed

## 5. Signal Notification Isolation (reactive delta)

- [ ] 5.1 Isolate per-consumer notification in `producer_notify_consumers`/`consumer_mark_dirty` (`signal/_graph.py:117,164`) and `SignalCallback._dispatch` (`signal/_base.py:59`); route failures to the pipeline; guarantee `_in_notification_phase` restoration
- [ ] 5.2 Unit tests: failing consumer does not block siblings; producer value consistent; no stuck-dirty Computed; notification phase restored

## 6. Environment Policy (SSR fallback / SSG fail-fast)

- [x] 6.1 Add `ERROR_POLICY_KEY` DI key (values `"ssr" | "ssg"`, default `"ssr"`); `ErrorBoundaryElement` re-raises when `"ssg"`
- [ ] 6.2 Provide `"ssg"` from the SSG entry point (`webcompy_cli/_generate.py`) at render-context creation
- [ ] 6.3 Tests: SSR renders fallback + 200 + rest of page; SSG raises and fails the build

## 7. RouterView Implicit Boundary

- [ ] 7.1 Wrap each chain level in an implicit boundary inside `RouterView._get_or_create_component` (`router/_view.py:91`); fallback renders empty
- [ ] 7.2 Reset the implicit boundary on navigation when in error state (`_on_match_changed`, `_view.py:150`); verify the level-reuse rule is unaffected
- [ ] 7.3 Unit tests (with `webcompy_testing`): page crash preserves layout; re-navigation retries; remount drops error state; app-declared inner boundary engages first

## 8. Hydration Retry (stretch — may be deferred)

- [ ] 8.1 Mark SSR fallback output with `data-webcompy-error-fallback`; on `_hydrate_node`, adopt fallback DOM and schedule one automatic `reset()` via the async scheduler after initial hydration — without touching the `AppDocumentRoot._render()` hydration guard
- [ ] 8.2 Tests: SSR-fallback page hydrates and retries; persistent failure settles into fallback

## 9. E2E and Verification

- [ ] 9.1 Add e2e pages under `e2e/core/my_app/pages/`: crashing component with retry button; crashing page inside a nested layout; Playwright specs under `e2e/core/`
- [ ] 9.2 Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run python -m pytest tests/ --tb=short` (all existing tests MUST pass)
- [ ] 9.3 Run relevant e2e groups via `scripts/run-e2e-tests.sh` and `uv run python -m webcompy generate` on docs_app

## 10. Spec and Housekeeping

- [ ] 10.1 Sync deltas to main specs (`error-handling` new; `components`, `app-config`, `elements`, `router`, `reactive` modified) via the archive flow
- [ ] 10.2 Update `AGENTS.md` File→Spec Mapping (new `_error_boundary.py` → error-handling; `signal/_graph.py`/`_base.py` → reactive + error-handling) and the Current Specs list; check `.opencode/skills/webcompy-review/SKILL.md` invariants for stale assumptions (e.g., notification-chain behavior)
