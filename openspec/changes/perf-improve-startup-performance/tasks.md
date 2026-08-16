## 1. Fix the profile=True browser crash

- [ ] 1.1 Add `_profile_data: dict[str, float]` owned by `WebComPyApp` in `packages/webcompy/src/webcompy/app/_app.py`: initialize the dict in `__init__` (empty dict always for simplicity, or only when `_profile` is True), move `_record_phase`/`_emit_profile_summary` to append/read from `self._profile_data`, and make `app.profile_data` return `self._profile_data if self._profile else None` so `ctx.profile_data` access is no longer required
- [ ] 1.2 Remove the `RenderContext._profile_data` / `RenderContext._record_phase` indirection: update `packages/webcompy/src/webcompy/app/_render_context.py` so `ctx._record_phase` and `profile_data` are no longer the source of truth (either delegate upward to the app or drop the per-context dict)
- [ ] 1.3 Update `_emit_profile_summary` pairs to include the two new phases from this change and keep the total line correct; verify the `[WebComPy Profile]` still prints via `browser.console.log` in Emscripten and `print()` otherwise
- [ ] 1.4 Confirm `packages/webcompy-server/src/webcompy_server/_html.py` bootstrap (`app._profile_data["pyscript_ready"] = _pyscript_ready`) now works without modification once the app owns the dict

## 2. Add the two profile phases

- [ ] 2.1 Record a `custom_elements_registered` phase around `AppDocumentRoot._ensure_custom_elements_defined()` via `app._record_phase` (first occurrence wins); ensure it is only recorded when profiling is enabled and skipped in non-pyscript environments where the method is a no-op
- [ ] 2.2 Record a `lazy_preloaded` phase around the `Router.preload_lazy_routes()` batch execution (wrap the scheduled batch function so wall time covers resolving all lazy route generators), first occurrence wins
- [ ] 2.3 Add the two phases to `_emit_profile_summary` adjacent-line pairs with sensible neighbors (e.g. `run_done → custom_elements_registered` and `custom_elements_registered → lazy_preloaded`), matching actual call order confirmed during implementation
- [ ] 2.4 Ensure `_record_phase` no-ops when `_profile` is False (zero overhead in default runs)

## 3. Tests

- [ ] 3.1 Extend `packages/tests/test_profiling.py` (or `tests/test_profiling.py`) to cover: `app._profile_data` exists when `profile=True`, `app.profile_data` returns the dict when enabled and `None` when disabled, new phases appear in the summary output, and phases are recorded at most once
- [ ] 3.2 Add/update a test proving `profile=True` runs in the browser/bootstrap path without `AttributeError` (simulate the generated bootstrap assignment `app._profile_data["pyscript_ready"] = ...` succeeding)
- [ ] 3.3 Run the full unit test suite (`uv run python -m pytest tests/ --tb=short`) and fix any regressions from removing the render-context profile indirection

## 4. Docs and measurement summary

- [ ] 4.1 Update the profiling guidance in `docs_app/documents/` (the startup/profile document and any quickstart example) to: use `WebComPyAppConfig(profile=True)`, list the two new phases, and document that custom-element registration is measured <50 ms and is not a startup bottleneck
- [ ] 4.2 Record the startup measurement conclusion in the docs_app documents or a design note so future work targets runtime transfer/init instead of custom elements

## 5. Runtime-transfer investigation (follow-up basis)

- [ ] 5.1 Investigate the dominant startup cost (transferred size: `pyodide.asm.wasm` ~8.6 MB, `python_stdlib.zip` ~2.4 MB, js ~1.3 MB) and document delivery-mode options: `wasm_serving`/`runtime_serving` (cdn vs local), `standalone`, cache headers, wheel split — capture findings in this change's notes or a follow-up change
- [ ] 5.2 Optionally attempt a low-risk, reversible delivery improvement (e.g. cache headers) and re-run the `.tmp/measure/measure.py` startup measurement to quantify; if the effect is material and behavior-affecting, open a separate change rather than expanding this one

## 6. Validation

- [ ] 6.1 Run `uv run python -m webcompy start` on docs_app with `profile=True` enabled (via temporary config edit) and confirm `[WebComPy Profile]` prints to the browser console without crashing (inspect via `webcompy inspect console`)
- [ ] 6.2 Run `uv run ruff check .` and `uv run pyright` on changed packages
- [ ] 6.3 Confirm `openspec validate` passes for this change and specs are consistent with `app-lifecycle` and `app-config`