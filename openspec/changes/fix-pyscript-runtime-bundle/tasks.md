## 1. Implement PyScript Offline Bundle Download

- [x] 1.1 Add `PYSCRIPT_OFFLINE_URL_TEMPLATE = "https://pyscript.net/releases/{pyscript_version}/offline_{pyscript_version}.zip"` constant and `download_pyscript_bundle(pyscript_version, modules_dir)` function to `_runtime_downloader.py`. The function downloads the ZIP, extracts all `.js` and `.css` files from the `pyscript/` directory (excluding `.map`, `.d.ts`, `micropython/` subdirectory, `pyodide/` subdirectory, `service-worker.js`, `mini-coi-fd.js`, `index.html`), caches them in `modules_dir/runtime-assets/{pyscript_version}/pyscript/`, computes SHA256 for each, and returns `dict[str, tuple[Path, str]]` mapping filenames (e.g. `core.js`, `core-BuLtL7jM.js`) to `(path, sha256)`.
- [x] 1.2 Add caching: if `modules_dir/runtime-assets/{pyscript_version}/pyscript/core-BuLtL7jM.js` exists (a file NOT in the old `PYSCRIPT_CORE_ASSETS` list), skip download and return cached files with computed sha256. Cache key: presence of any `.js` file beyond `core.js` indicates the full bundle was previously extracted.
- [x] 1.3 Replace `PYSCRIPT_CORE_ASSETS` list usage in `download_runtime_assets()` with a call to `download_pyscript_bundle()`. Remove `PYSCRIPT_CORE_ASSETS` constant. The Pyodide runtime asset download loop remains unchanged.

## 2. Verify Downstream Integration (No Code Changes Expected)

- [x] 2.1 Verify lockfile integration: `generate_lockfile()` still records `core.js`/`core.css` initially (no change needed). After `download_runtime_assets()` returns expanded results, `verify_and_update_runtime_assets()` replaces `lockfile.runtime_assets` with all files — this is existing behavior (`lockfile.runtime_assets = {}` then rebuild from results). Confirm by running `webcompy lock && webcompy generate` and inspecting the lockfile.
- [x] 2.2 Verify SSG asset copying: `_generate.py` already copies all entries from `runtime_asset_results` to `dist/_webcompy-assets/` (flat structure). Confirm expanded file list is copied correctly by running `generate_static_site()` and inspecting output. Add assertion to test if needed.
- [x] 2.3 Verify dev server asset serving: `_server.py` builds `runtime_asset_files` dict from download results and serves all entries at `/_webcompy-assets/{filename:path}`. Confirm by starting dev server with `runtime_serving="local"` and checking `/_webcompy-assets/core-BuLtL7jM.js` returns 200.

## 3. Tests

- [x] 3.1 Add unit tests for `download_pyscript_bundle()` verifying: correct file filtering (exclude `.map`, `.d.ts`, `micropython/`, `pyodide/`, `service-worker.js`), SHA256 computation, cache hit behavior (skips re-download on second call), and that return dict includes `core-BuLtL7jM.js` alongside `core.js`.
- [x] 3.2 Update `test_runtime_downloader.py` to reflect removal of `PYSCRIPT_CORE_ASSETS` and the new ZIP-based download approach.
- [x] 3.3 Verify existing E2E tests (`test_runtime_local.py`, `test_standalone.py`) pass with the new bundle download approach.

## 4. Lockfile Regeneration and Local Verification

- [x] 4.1 Delete `docs_app/webcompy-lock.json` and regenerate with `webcompy lock --app docs_app.bootstrap:app`.
- [x] 4.2 Run `generate_static_site()` and verify docs site initializes correctly by running a local static server and opening in a browser (check PyScript loads without console errors, Pyodide starts, app renders).
- [x] 4.3 Run docs E2E tests locally with `DOCS_DIST_DIR` to confirm they complete successfully.