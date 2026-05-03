## 1. Downloader Modules

- [x] 1.1 Update `_pyodide_lock.py`: remove `CACHE_DIR` constant, add `modules_dir: pathlib.Path` parameter to `fetch_pyodide_lock()`, update cache path to `modules_dir / "pyodide-lock" / f"pyodide-lock-{pyodide_version}.json`
- [x] 1.2 Update `_runtime_downloader.py`: remove `CACHE_DIR` constant, add `modules_dir: pathlib.Path` parameter to `download_runtime_assets()`, use `modules_dir / "runtime-assets" / {pyscript_version}` as cache root, preserve SHA256 verification logic
- [x] 1.3 Update `_pyodide_downloader.py`: remove `CACHE_DIR` constant, add `modules_dir: pathlib.Path` parameter to `download_pyodide_wheel()` and `download_wasm_wheels()`, use `modules_dir / "pyodide-packages" / {pyodide_version}` as cache root, preserve SHA256 verification and cache-hit logic

## 2. Utility Function

- [x] 2.1 Add `ensure_webcompy_modules_dir(modules_dir: pathlib.Path) -> None` to `_utils.py` that creates the directory and `.gitignore` file with content `*` if they don't exist
- [x] 2.2 Import and call `ensure_webcompy_modules_dir()` in `_server.py` and `_generate.py` at the start of `create_asgi_app()` and `generate_static_site()` respectively

## 3. Dev Server

- [x] 3.1 Update `_server.py`: pass `app.config.app_package_path / ".webcompy_modules"` to all downloader functions
- [x] 3.2 Replace `TemporaryDirectory` for runtime assets with direct use of `.webcompy_modules/runtime-assets/`: remove `with TemporaryDirectory()` block, call `download_runtime_assets()` with `modules_dir` directly
- [x] 3.3 Replace in-memory asset serving with `FileResponse`: change `runtime_asset_files` from `dict[str, tuple[bytes, str]]` to `dict[str, pathlib.Path]`, update route handlers to use `FileResponse` instead of `Response(content=bytes)`
- [x] 3.4 Replace in-memory WASM wheel serving with `FileResponse`: change `wasm_asset_files` from `dict[str, tuple[bytes, str]]` to `dict[str, pathlib.Path]` or serve directly from cache paths
- [x] 3.5 Update CDN pure-Python wheel extraction to still use `TemporaryDirectory` (unchanged behavior, just passes `modules_dir` to downloader)
- [x] 3.6 Update Pyodide lock fetching call to pass `modules_dir`

## 4. Static Site Generation

- [x] 4.1 Update `_generate.py`: pass `app.config.app_package_path / ".webcompy_modules"` to all downloader functions
- [x] 4.2 Replace `TemporaryDirectory` for runtime assets: remove `runtime_temp_dir_obj`, call `download_runtime_assets()` with `modules_dir` directly, copy from `.webcompy_modules/runtime-assets/` to `dist/_webcompy-assets/`
- [x] 4.3 Replace `TemporaryDirectory` for WASM wheels: call `download_pyodide_wheel()` with `modules_dir`, copy from `.webcompy_modules/pyodide-packages/` to `dist/_webcompy-assets/packages/`
- [x] 4.4 Update Pyodide lock fetching call to pass `modules_dir`
- [x] 4.5 Clean up: remove any remaining `TemporaryDirectory` usage for runtime/WASM assets, keep only for CDN pure-Python wheel extraction

## 5. Tests

- [x] 5.1 Update `tests/test_runtime_downloader.py`: replace `CACHE_DIR` monkeypatch with `modules_dir` parameter passing, adjust all test assertions
- [x] 5.2 Update `tests/test_pyodide_lock.py`: replace `CACHE_DIR` monkeypatch with `modules_dir` parameter passing
- [x] 5.3 Update `tests/test_lockfile.py`: replace `CACHE_DIR` monkeypatch with `modules_dir` parameter passing for `generate_lockfile` tests
- [x] 5.4 Update `tests/test_pyodide_downloader.py`: replace `CACHE_DIR` monkeypatch with `modules_dir` parameter passing
- [x] 5.5 Run `uv run python -m pytest tests/test_runtime_downloader.py tests/test_pyodide_lock.py tests/test_lockfile.py tests/test_pyodide_downloader.py -v --tb=short` and fix any failures
- [x] 5.6 Run `uv run ruff check .` and fix lint issues
- [x] 5.7 Run `uv run pyright` and fix type errors

## 6. Integration Verification

- [x] 6.1 Run `uv run python -m webcompy start --dev --app docs_app.bootstrap:app --runtime-serving local` and verify `.webcompy_modules/` is created with correct structure
- [x] 6.2 Verify dev server serves runtime assets from disk with `FileResponse`
- [x] 6.3 Run `uv run python -m webcompy generate --app docs_app.bootstrap:app --runtime-serving local` and verify `dist/_webcompy-assets/` is populated from `.webcompy_modules/`
- [x] 6.4 Verify `.gitignore` is created in `.webcompy_modules/` and `git status` does not show it as untracked
