## Why

When `standalone=True` (or `runtime_serving="local"`), WebComPy downloads only `core.js` and `core.css` from the PyScript release. However, PyScript 2026.3.1's `core.js` dynamically imports `./core-BuLtL7jM.js`, which in turn imports 15+ additional `.js` files via relative `import()` calls. Because these transitive dependencies are not downloaded, the browser cannot resolve them, causing PyScript initialization to hang indefinitely. This makes standalone mode completely non-functional.

## What Changes

- Replace the hardcoded `PYSCRIPT_CORE_ASSETS = ["core.js", "core.css"]` list with dynamic resolution that downloads the PyScript offline bundle (`offline_{version}.zip`) and extracts all required runtime files
- Download and extract the full PyScript core bundle (all `.js` and `.css` files from the offline zip's `pyscript/` directory, excluding `.map` and `.d.ts` files, `micropython/` and `pyodide/` subdirectories), preserving the flat directory structure so relative imports work correctly. The existing `_webcompy-assets/` path prefix is already correct — no HTML generation changes needed.
- Update the lockfile `runtime_assets` to record all PyScript core assets (not just `core.js` and `core.css`). This happens progressively: initial lockfile generation records only `core.js`/`core.css`, then `verify_and_update_runtime_assets()` populates the full file list with SHA256 after actual download.

## Capabilities

### New Capabilities

- `pyscript-bundle`: Download and serve the complete PyScript offline bundle (all core `.js`/`.css` files) for local/offline usage

### Modified Capabilities

- `cli`: The `generate` and `start` commands shall download the PyScript offline bundle instead of individual `core.js`/`core.css` files when `runtime_serving="local"`
- `lockfile`: The lockfile shall record all PyScript core bundle files in `runtime_assets`, not just `core.js` and `core.css`

## Impact

- `webcompy/cli/_runtime_downloader.py` — Major rewrite: replace individual file download with zip download and extraction (new `download_pyscript_bundle()`, replace `PYSCRIPT_CORE_ASSETS` usage)
- `webcompy/cli/_lockfile.py` — `generate_lockfile()` keeps current behavior (records `core.js`/`core.css` initially); `verify_and_update_runtime_assets()` already handles full-population after download, no code changes needed
- `webcompy/cli/_generate.py` — Existing asset copying loop iterates over `runtime_asset_results` dict; automatically handles expanded file list, no code changes needed
- `webcompy/cli/_server.py` — Existing route `/_webcompy-assets/{filename:path}` already serves all `runtime_asset_files` entries; automatically handles expanded file list, no code changes needed
- `docs_app/webcompy-lock.json` — Must be deleted and regenerated to pick up full bundle file list
- E2E tests — Existing `test_runtime_local.py` and `test_standalone.py` should continue passing; docs E2E tests will now work correctly

## Known Issues Addressed

None — this is a new bug discovered during standalone mode testing.

## Non-goals

- Changing the PyScript CDN serving mode (`runtime_serving="cdn"`) — this continues to reference `https://pyscript.net/releases/{version}/core.js` directly
- Adding MicroPython support — the offline bundle includes MicroPython files but WebComPy only uses Pyodide
- Modifying the PyScript runtime itself — we only download and serve the official distribution
- Supporting offline zip extraction without network access — the zip must be downloaded from `pyscript.net`; once cached locally via `modules_dir`, subsequent runs are offline-capable