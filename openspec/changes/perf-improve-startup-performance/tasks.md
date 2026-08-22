## 1. Fix the profile=True browser crash

- [ ] 1.1 Add `_profile_data: dict[str, float]` owned by `WebComPyApp` in `packages/webcompy/src/webcompy/app/_app.py`: declare the class attribute, create the empty dict unconditionally in `__init__`, make `app.profile_data` return `self._profile_data if self._profile else None`, and move `_record_phase`/`_emit_profile_summary` to operate on `self._profile_data` (no ContextVar delegation). `_record_phase` keeps only the first occurrence per phase name and no-ops when `_profile` is False
- [ ] 1.2 Remove the `RenderContext._profile_data` / `RenderContext._record_phase` indirection from `packages/webcompy/src/webcompy/app/_render_context.py`: delete `_profile_data`, `profile_data`, `_record_phase`; route internal phase calls (`init_start`/`imports_done`/`init_done`) through `self._app._record_phase(...)`; drop the now-unused `import time` if nothing else uses it. Do not touch the hydration-reporter state added on main
- [ ] 1.3 Update `_emit_profile_summary` to use the new pair list (`pyscript_ready → imports_done`, `imports_done → init_done`, `init_done → custom_elements_defined`, `custom_elements_defined → run_done`, `run_done → loading_removed`, `run_done → lazy_preloaded`) plus a non-negative guard (skip a pair whose end precedes its start); keep the `[WebComPy Profile]` output via `browser.console.log` in Emscripten and `print()` otherwise
- [ ] 1.4 Confirm `packages/webcompy-server/src/webcompy_server/_html.py` bootstrap (`app._profile_data["pyscript_ready"] = _pyscript_ready`) works without modification once the app owns the dict

## 2. Add the two profile phases and deferred emission

- [ ] 2.1 Record a `custom_elements_defined` phase right after `AppDocumentRoot._ensure_custom_elements_defined()` completes in `packages/webcompy/src/webcompy/app/_root_component.py` via `app._record_phase` (only runs in the browser hydrate path; first occurrence wins)
- [ ] 2.2 Record a `lazy_preloaded` phase when the preload batch finishes: inside `_batch_preload` in `packages/webcompy/src/webcompy/router/_router.py` (browser macro task) and after the synchronous loop (server), reached via `inject(_APP_KEY, default=None)`; must work under the new `preload_lazy_routes(*, force=False)` signature regardless of `force`
- [ ] 2.3 In `_root_component`, replace the synchronous `app._emit_profile_summary()` call at loading removal with `inject(HOST_PORT_KEY).schedule_macro_task(self._app._emit_profile_summary)` so the summary prints after any scheduled lazy-preload batch (FIFO timer ordering); import `HOST_PORT_KEY`
- [ ] 2.4 Ensure `_record_phase` no-ops when `_profile` is False (zero overhead in default runs)

## 3. Tests

- [ ] 3.1 Rewrite `tests/test_profiling.py` for app-owned data: patch target moves to `webcompy.app._app.time.perf_counter`; cover `app.profile_data` dict when enabled / `None` when disabled, `app._record_phase` population, no-op when disabled, first-occurrence-wins, monotonic init phases, and summary output containing the new pair labels plus `Total:`
- [ ] 3.2 Add a bootstrap-compat test proving `app._profile_data["pyscript_ready"] = ...` (the generated HTML assignment) succeeds without `AttributeError` when `profile=True`
- [ ] 3.3 Add a unit test that a server-side render with a lazy router records `lazy_preloaded` into `app._profile_data` (reference patterns from `tests/test_ssg_lazy_preload.py`)
- [ ] 3.4 Run the full unit test suite (`uv run python -m pytest tests/ --tb=short`) and fix any regressions from removing the render-context profile indirection

## 4. Record measurement conclusions in design.md (no docs_app changes)

- [ ] 4.1 Record the measurement conclusions in this change's `design.md`: custom-element registration measured <50 ms (not a startup bottleneck); dominant cost is PyScript/Pyodide runtime transfer (~12.8 MB) and initialization (~2–3 s); primary evidence lives in `.tmp/measure/report.md` (gitignored, referenced only)
- [ ] 4.2 Note in `design.md` that future startup work should target runtime transfer/init rather than custom-element registration or binding

## 5. Runtime-transfer investigation (follow-up basis)

- [ ] 5.1 Document delivery-mode options in `design.md` as follow-up candidates: `wasm_serving`/`runtime_serving` (CDN vs local), `standalone`, cache headers, wheel split — with trade-offs; no code change in this change
- [ ] 5.2 Confirm no delivery behavior changes here (per D4): record explicitly in `design.md` that any material delivery improvement becomes its own change reusing the restored profiler for validation

## 6. Validation

- [ ] 6.1 Run the dev/prod server on docs_app with `profile=True` enabled (temporary edit to `docs_app/app.py`, reverted afterwards) and confirm `[WebComPy Profile]` prints to the browser console without crashing and includes the new phases (via `webcompy inspect console`)
- [ ] 6.2 Run `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright`
- [ ] 6.3 Confirm `openspec validate --changes` passes and the delta spec is consistent with `app-lifecycle` and `app-config`
- [ ] 6.4 Run all E2E groups in both serving modes via `scripts/run-e2e-tests.sh --parallel` and confirm success
