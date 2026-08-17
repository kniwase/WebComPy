# Tasks: Fix Hydration "Adopt & Render"

## 1. Pre-verification

- [x] 1.1 Confirm the "adopted children never render" risk for Suspense (resolved path) and Transition with failing unit tests (fake browser: prerendered content, `_hydrate_node`, then assert children never completed a render; fail first, pass after Phase 2)
- [x] 1.2 Investigate the double route-content render observed in browser instrumentation (REM/ADD × 2 on the page root) and record the cause in the design doc's decisions (D1/D7) before implementing the wrapper
- [x] 1.3 Add a unit-test helper that measures hydration: count DOM node removals/additions and per-element `_render` invocations during a fake-browser hydration of a prerendered tree (used by all subsequent tasks)

## 2. Hydration contract foundation

- [x] 2.1 `BrowserAsyncSchedulerPort`: add a task registry; `schedule()` records tasks, `await_pending()` awaits all unfinished recorded tasks (idempotent, no exception propagation)
- [x] 2.2 `webcompy_testing` `FakeAsyncSchedulerPort`: replicate the registry/drain semantics so existing tests stay green and new drain tests are possible
- [x] 2.3 `DynamicElement._hydrate_node`: for each child, `child._hydrate_node()` then schedule a hydration render wrapper (`_schedule_hydration_render`) instead of only scheduling unmounted children
- [x] 2.4 `DynamicElement._render`: render children during a hydration render wrapper even when mounted (transient per-element flag set by the wrapper, cleared on completion); keep the non-hydration skip semantics unchanged
- [x] 2.5 Mismatch collector: per-`RenderContext` record sink with `report_mismatch(kind, expected, actual, component_id)`; render-context integration and DI-free access for element code (context-var based, no new module-level globals)

## 3. Element-type convergence

- [x] 3.1 `RouterView._hydrate_node`: keep match-time child creation; call `child._hydrate_node()` on the boundary and schedule the boundary's hydration render wrapper; verify `_node_count` accounting lets the parent cleanup preserve SSR route content
- [x] 3.2 `ErrorBoundaryElement`: eager child generation during `_hydrate_node` covers RouterView-boundary adoption (existing eager path) and the wrapper render reaches mounted children; fallback-path behavior unchanged
- [x] 3.3 `RepeatElement`: pre-populate key map in `_hydrate_node`; first refresh with adopted/mounted children becomes reposition + key-map-rebuild without destroying SSR nodes; keep the full-rebuild path for non-hydrated mounts
- [x] 3.4 `SwitchElement`: preset the rendered branch at hydration (same selection logic as `_select_generator`); verify first refresh with unchanged condition performs no branch replacement
- [x] 3.5 `SuspenseElement` resolved path: schedule hydration render wrappers for resolved children (adopt + render); fallback path unchanged
- [x] 3.6 `TransitionElement`: schedule hydration render wrapper for hydrated children; `_initial_rendered`/enter-suppression behavior preserved (regression: hydrated content does not enter)
- [x] 3.7 Wire mismatch reporting into repair points: tag-mismatch removal, excess-node cleanup, text-run skip warning, differing attribute write (recoverable) — without changing repair behavior

## 4. Completion synchronization and diagnostics

- [x] 4.1 `AppDocumentRoot._render`: await `inject(ASYNC_SCHEDULER_PORT_KEY).await_pending()` immediately before the loading-removal block
- [x] 4.2 Aggregated hydration warning: emit exactly one `logging.warning` after the drain when records exist (counts by kind and by component ID); silence when empty
- [x] 4.3 `RenderContext.hydration_report`: expose the record list (empty before hydration / on server); add public API smoke test

## 5. Unit tests (fake browser)

- [x] 5.1 RouterView hydration: sync and async route pages preserve all prerendered nodes (survival assertion) and complete exactly one hydration render each
- [x] 5.2 Repeat: SSR children survive the first hydration refresh; keyed mutation after hydration reconciles correctly
- [x] 5.3 Switch: SSR branch survives first refresh; condition flip after hydration patches correctly
- [x] 5.4 Suspense: resolved children survive and react (signal-driven child updates after hydration); fallback path regression
- [x] 5.5 Transition: adopted content does not enter; children wiring regression after hydration
- [x] 5.6 Mismatch diagnostics: recoverable text/attr patch records; structural tag/node-count repair records; matching content → no records; `hydration_report` contents verified
- [x] 5.7 Scheduler drain: `await_pending` completes scheduled renders; overlay-removal ordering covered at `AppDocumentRoot` level
- [x] 5.8 Update existing expectations: `test_full_hydration.py`, `test_dynamic_child_node_index.py`, `test_hydration_text_merge.py`, `test_error_boundary_hydration_retry.py`, `test_custom_element_components.py`, `test_suspense.py`, `test_transition.py`, `test_repeat.py`, `test_switch.py`, `test_client_only.py`

## 6. E2E regression

- [x] 6.1 Docs pages: MutationObserver-based test asserting zero removals of prerendered `#webcompy-app` content between DOMContentLoaded and loading-indicator removal, and zero hydration-mismatch warnings on the quickstart/installation pages
- [x] 6.2 Nested-routes app: existing navigation suite passes (sibling/param/query remount semantics) with the new hydration path
- [x] 6.3 Run `scripts/run-e2e-tests.sh` (core + docs groups, prod and static modes)

## 7. Verification and measurement

- [x] 7.1 `ruff check .` + `ruff format --check .` + `pyright`
- [x] 7.2 `uv run python -m pytest tests/ --tb=short`
- [x] 7.3 SSG smoke: `uv run python -m webcompy generate` produces pages whose prerendered content matches (existing generate check)
- [x] 7.4 Re-run the browser instrumentation script: route roots identity-preserved, overlay removed, zero mismatch warnings; residual inner-content rebuild measured (quickstart alive 104/218, home 137/366 — dead-node counts exactly equal the `tok-*` highlight spans in the SSG HTML, see D9). The full `alive ≈ 218/218` acceptance moves to task 8.5
- [x] 7.5 Update `.opencode/skills/webcompy-review/SKILL.md` (file→spec mapping and Critical Framework Invariants) and `AGENTS.md` hydration invariant references; run `python3 scripts/check-doc-spec-refs.py` (deferred: main specs unchanged until archive)

## 8. RawHTMLElement adoption preservation (D9)

- [x] 8.1 `RawHTMLElement._adopt_node()`: adopt the compare-then-apply pattern of `TextElement._adopt_node()` — when the adopted wrapper's existing content (`innerHTML`, or `textContent` when `innerHTML` is unavailable) equals the rendered value, skip `_apply_html` so prerendered child nodes survive; when it differs, re-apply and record a `raw_html` mismatch
- [x] 8.2 Add `"raw_html"` to `MismatchKind` in `webcompy/hydration/_report.py`; confirm the aggregated warning summary covers the new kind
- [x] 8.3 Unit tests: matching raw-HTML content is adopted without innerHTML writes and with no records; differing content is patched and records a `raw_html` mismatch with expected/actual values; empty wrapper content re-applies
- [x] 8.4 E2E: extend the docs preservation regression to assert `tok-*` highlight span identity on the quickstart page (references captured before hydration remain connected after loading-indicator removal)
- [x] 8.5 Verification: `ruff` + `pyright` + full `pytest tests/`; E2E groups `template`, `components`, `docs-documents`, `docs-home` (prod + static); browser measurement alive ≈ 218/218 (quickstart) and 366/366 (home) with zero mismatch warnings; `openspec validate`

## 9. Environment-stable auto transfer keys (signal-value-transfer)

- [x] 9.1 Diagnose the helloworld demo `raw_html` mismatch: `use_state()` auto keys embed the absolute filesystem path, which differs between SSR (checkout path) and browser (wheel `site-packages` path), so restoration misses and the prerendered highlighted content is wiped. All `use_state`/`use_reactive_list`/`use_reactive_dict` call sites are affected in real deployments (unit tests never caught it because both sides run in the same environment)
- [x] 9.2 `_auto_key()` derives keys from the call-site module identity (`__name__`, with basename fallback) plus line/column instead of `co_filename`; keys are environment-independent while remaining distinct per call site
- [x] 9.3 Regression test: auto key is module-based and contains no filesystem path (`tests/test_use_state.py::TestAutoKey::test_auto_key_is_module_based_not_filesystem_path`)
- [x] 9.4 Verify restoration in the browser: helloworld / todo / fetch / fizzbuzz demo pages all reach 100% SSR node survival (alive = total, tok = total) with zero hydration-mismatch warnings
- [x] 9.5 Adjust the lifecycle E2E fixture: `render_count` becomes a plain `Signal` (client-local) instead of `use_state`, because with restoration working the SSR-side hook increments would transfer and make the cross-environment counter display 3 instead of the intended client-side count of 1; `count` remains a transferable `use_state` signal. Components E2E group passes (2/2)

## 10. Review fixes (code review of this change)

- [x] 10.1 `SwitchElement._refresh`/`_render`: scope `_cancel_pending_render_tasks()` to the inline-render and branch-changed paths so the unchanged-branch adopted children keep their scheduled hydration-render wrappers (adopted branch children now complete exactly one hydration render; nested dynamic elements stay wired; no `RuntimeWarning: coroutine … was never awaited`). Regression: `test_switch_adopted_branch_nested_repeat_stays_wired`
- [x] 10.2 `RepeatElement`: partial adoption — `_adoption_preserved` uses `any(child._mounted …)`; the first refresh preserves matched adopted nodes and lets the missing positions render via their scheduled tasks. Tests: `test_repeat_len_mismatch_preserves_adopted_nodes`, `test_repeat_partial_adoption_preserves_matched_nodes`
- [x] 10.3 Scoped drain: `AsyncSchedulerPort.schedule(coro, *, render=False)` and `await_pending(*, only_render=False)`; browser/fake ports track the flag; server accepts and ignores it; render call sites (`_dynamic`, `_teleport`, `_error_boundary`) mark `render=True`; `AppDocumentRoot._render` calls `await_pending(only_render=True)`. Tests: `test_await_pending_render_only_*` (fake + browser ports). Delta specs: async-rendering (drain wording + non-render scenario), async-scheduler (new), elements (partial-adoption + switch-wiring scenarios)
- [x] 10.4 `AppDocumentRoot._render`: reset `_hydration_in_progress` in the `finally` block so a failed render closes the mismatch window. Tests: `TestHydrationWindowClose`
- [x] 10.5 Fix invalid `MismatchKind` string in `tests/test_hydration_report.py` (`"attributes"` → `"attribute"`)
- [x] 10.6 Update design decisions (D2/D3/D6 refinements, Risks) and proposal Impact (async-scheduler capability, port API change, `record_mismatch`/`HydrationMismatchRecord` public exports)
- [x] 10.7 Verification: `ruff check` + `ruff format --check` + `pyright` pass; full `pytest tests/` (4485 passed); E2E `docs-documents` (prod + static), `docs-demos` (prod + static), `components` (prod + static) all pass
- [x] 10.8 Strengthen the E2E mismatch-warning assertion: the aggregated warning surfaces as Playwright console type `error` in the browser (Pyodide stderr mapping), so `test_hydration_preservation.py` now matches `m.type in ("warning", "error")` (the previous `"warning"`-only check could not catch regressions)

## 11. Review fixes (second code review of this change)

- [x] 11.1 `BrowserAsyncSchedulerPort.await_pending`: remove the registry-rebuild line (`self._registry = [entry for entry in self._registry if entry[0] is current]`) — it dropped non-render tasks from the registry during a render-only drain, so a later unqualified `await_pending()` could not await them (contradicting the "await all registered tasks" contract). The loop termination already relies on the `not task.done()` filter. Regression: `test_await_pending_render_only_keeps_plain_tasks_registered`; async-scheduler delta spec gains a "Render-only drain keeps non-render tasks registered" scenario
- [x] 11.2 `ElementAbstract._hydrate_node()` fallback: record the created node as `_node_cache` so a later `_get_node()`/render reuses it (previously the fallback created an orphan node and `_get_node()` → `_init_node()` created a second one, duplicating `_init_new_node` side effects — attributes, event handlers, ref binding — per unmatched element; activated by the repeat/switch partial-adoption paths). Regression: `test_hydration_fallback_creates_single_node`, `test_fallback_element_reuses_created_node`; elements delta spec gains a "Hydration fallback creates the node exactly once" scenario
- [x] 11.3 signal-value-transfer delta spec: document that module-identity auto keys assume package-structured modules (a `__main__` script's module name differs between the SSR checkout and the browser wheel bundle, so restoration is not guaranteed for single-file apps)
- [x] 11.4 Verification: `ruff check` + `ruff format --check` + `pyright` pass; full `pytest tests/`; E2E `docs-documents` (prod + static) passes

