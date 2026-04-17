## 1. Investigate and Reproduce

- [x] 1.1 Start the dev server and navigate to the Fetch Sample page via router link to confirm the error
- [x] 1.2 Navigate to the same Fetch Sample page via direct URL to confirm it works
- [x] 1.3 Capture the exact error message and stack trace from the browser console

## 2. Core Fix — Defer `on_after_rendering` in SwitchElement

- [x] 2.1 Modify `Component._render()` to support a mode where `on_after_rendering` is collected rather than executed immediately (e.g., add a `_defer_after_rendering` flag or separate `_render_dom()` / `_fire_after_rendering()` methods)
- [x] 2.2 Modify `SwitchElement._refresh()` to: (a) set the deferral flag on new Component children before rendering, (b) render all children, (c) collect all deferred `on_after_rendering` callbacks, (d) schedule them via `browser.window.setTimeout(callback, 0)` in browser env or call synchronously in SSG
- [x] 2.3 Ensure `on_before_rendering` still fires synchronously before rendering (no change needed, just verify)

## 3. Server-Side Rendering Compatibility

- [x] 3.1 Verify that the `_on_set_parent` path in `SwitchElement` (used during SSG) still calls `on_after_rendering` synchronously — no deferral needed since there's no browser event loop
- [x] 3.2 Run `uv run python -m webcompy generate` to confirm SSG still works correctly

## 4. Verification

- [x] 4.1 Start the dev server, navigate to the Fetch Sample page via router link, and confirm it works without errors
- [x] 4.2 Navigate between multiple pages using RouterLinks to confirm no regressions
- [x] 4.3 Test browser back/forward navigation to confirm route restoration works
- [x] 4.4 Run `uv run python -m pytest tests/ --tb=short` to confirm no test regressions
- [x] 4.5 Run `uv run ruff check .` and `uv run pyright` to confirm lint and type check pass