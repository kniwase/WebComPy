## Why

WebComPy's standalone mode (`runtime_serving="local"` / `wasm_serving="local"`) currently downloads runtime assets and WASM wheels into `~/.cache/webcompy/`, a global cache outside the project directory. This has three problems:

1. **No isolation**: Multiple projects sharing the same cache is not useful in practice because each project has different dependency sets.
2. **Hidden state**: Users cannot see or manage what has been downloaded without digging into their home directory.
3. **Memory waste**: The dev server loads all downloaded assets into memory (`read_bytes()` into `Response(content=bytes)`) rather than streaming from disk.

We should move the cache into the project directory as a hidden folder `.webcompy_modules/` inside each app package, and serve files directly from disk.

## What Changes

- **Create `.webcompy_modules/` inside each app package directory** (`app.config.app_package_path / ".webcompy_modules"`), automatically generating a `.gitignore` with `*` so it is never tracked by git.
- **Replace `~/.cache/webcompy/` usage entirely** in `_pyodide_downloader.py`, `_runtime_downloader.py`, and `_pyodide_lock.py`.
- **Serve runtime and WASM assets from disk** in dev server mode using `FileResponse` instead of loading bytes into memory.
- **Copy from `.webcompy_modules/` to `dist/` during SSG** instead of downloading into `TemporaryDirectory` first.
- **Add `ensure_webcompy_modules_dir()` utility** in `_utils.py` for consistent directory setup across CLI commands.
- **Update tests** to mock the project-local cache directory instead of `~/.cache/webcompy/`.

## Capabilities

### New Capabilities
- `project-local-cache`: Project-local dependency cache (`.webcompy_modules/`) that replaces the global `~/.cache/webcompy/` cache. Each app package has its own isolated cache, and downloaded assets are served from disk rather than kept in memory.

### Modified Capabilities
- `cli`: Dev server and static site generator behavior changes — files are now served from disk (`FileResponse`) and SSG copies from `.webcompy_modules/` instead of temporary directories.

## Impact

- **Affected files**:
  - `webcompy/cli/_pyodide_downloader.py`
  - `webcompy/cli/_runtime_downloader.py`
  - `webcompy/cli/_pyodide_lock.py`
  - `webcompy/cli/_server.py`
  - `webcompy/cli/_generate.py`
  - `webcompy/cli/_utils.py`
  - `tests/test_runtime_downloader.py`
- **Breaking changes**: None for end-user code. Existing `~/.cache/webcompy/` will be left untouched but no longer used.
- **Behavior change**: First dev server / SSG run after this change will re-download assets into `.webcompy_modules/` even if `~/.cache/webcompy/` has cached copies.

## Known Issues Addressed

None directly.

## Non-goals

- **No automatic migration** of existing `~/.cache/webcompy/` contents. Old cache is simply abandoned.
- **No cache size limits or LRU eviction**. Users can `rm -rf .webcompy_modules/` manually if needed.
- **No customization** of `.webcompy_modules/` location. It is always placed inside `app.config.app_package_path`.
- **No change** to how CDN pure Python wheels are extracted for bundling (`serve_all_deps=True`). This still uses a temporary directory for wheel extraction before bundling into the app package wheel.
