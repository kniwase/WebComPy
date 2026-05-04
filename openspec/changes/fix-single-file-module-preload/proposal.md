## Why

When SSG-deployed `docs_app` is accessed a second time (cached Pyodide runtime), lazy route preloading crashes because single-file modules like `six` are not bundled in the app wheel. The preload triggers at `setTimeout(0)` — fast enough to race ahead of package installation when the runtime is cached. This causes a `ModuleNotFoundError: No module named 'six'` on every subsequent access.

## What Changes

- **Spike A**: Extend `_discover_packages()` and `_collect_package_files()` in `_wheel_builder.py` to detect and bundle single-file Python modules (e.g., `six.py`, `.py` files without an `__init__.py` sibling) alongside package-directory modules in the app wheel.
- **Spike B**: Move browser-side lazy route preloading from `RouterView._on_set_parent()` (which fires during component init, before `app.run()` completes) to `AppDocumentRoot._render()` — scheduled after the loading screen is removed and the initial render is complete.
- **Spike C**: Add error handling in `LazyComponentGenerator._preload()` and the `_do_preload` closure in `Router.preload_lazy_routes()` so that a failed preload does not crash the application. Failed preloads mark `_resolve_error = True` for diagnostic visibility.

## Known Issues Addressed

- **Wheel Builder**: Previously did not account for single-file modules (no `__init__.py`), causing transitive dependencies like `six` to be silently omitted from the app wheel.
- **Router**: Preload timing was tied to `RouterView` init rather than `app.run()` completion, creating a race condition when the Pyodide runtime is cached.

## Non-goals

- No change to the public API of `lazy()`, `Router`, `RouterView`, or `AppDocumentRoot`.
- No change to how Pyodide packages are declared or loaded — the lockfile and `<py-config>` contract remains unchanged.
- No new test infrastructure — existing tests cover the affected code paths.

## Capabilities

### Modified Capabilities

- `wheel-builder`: Single-file `.py` modules (without `__init__.py`) are now discovered and bundled into the app wheel identically to package-directory modules.
- `router`: Browser-side lazy route preloading is deferred until after the initial render completes, removing the race condition with Pyodide package installation. Failed preloads no longer crash the application.

## Impact

- `webcompy/cli/_wheel_builder.py` — `_discover_packages()` and `_collect_package_files()` gain single-file module support.
- `webcompy/router/_view.py` — `_on_set_parent()` restricts immediate preloading to non-browser environments.
- `webcompy/app/_root_component.py` — `_render()` schedules `preload_lazy_routes()` after loading-screen removal in browser.
- `webcompy/router/_router.py` — `_do_preload` closure wraps `_preload()` with `contextlib.suppress(Exception)`.
- `webcompy/router/_lazy.py` — `_preload()` wraps `_resolve()` with try/except; adds `_resolve_error` flag.
- Generated `docs/` — Regenerated with the fix applied.
