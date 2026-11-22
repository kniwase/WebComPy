# Proposal

## Why

After deploying PR #300 (`PYSCRIPT_VERSION = "2026.7.3"`, Pyodide `314.0.3`), returning visitors on the production site encountered `AttributeError: module '_pyodide._core_docs' has no attribute 'JsBigInt'` during `python2js` initialization.

Inspection of live Cloudflare Pages headers showed the root cause: `.mjs`, `.wasm`, and `.json` runtime files were served with `Cache-Control: public, max-age=0, must-revalidate`, whereas `python_stdlib.zip`, `core.js`, and `core.css` were cached for 4 hours (`public, max-age=14400, must-revalidate`). Because local runtime assets are served from unversioned `/_webcompy-assets/...` URLs, a returning browser loaded the new `314.0.3` `pyodide.asm.wasm` alongside a cached `0.29.3` `python_stdlib.zip` (or cached `2026.3.1` `core.js` referencing `core-BuLtL7jM.js`), crashing boot.

## What Changes

- Add `get_runtime_asset_prefix(pyscript_version: str = PYSCRIPT_VERSION) -> str` in `webcompy_server._html` returning `_webcompy-assets/{pyscript_version}`, and update `_generate_html_impl()` to emit versioned local URLs (`{base_url}_webcompy-assets/{PYSCRIPT_VERSION}/core.js`, `core.css`, `pyodide/pyodide.mjs`, `pyodide/pyodide-lock.json`).
- Update `webcompy_cli._generate` to copy local runtime assets into `dist/_webcompy-assets/{PYSCRIPT_VERSION}/`.
- Update `webcompy_cli._server` to mount local runtime assets at `/_webcompy-assets/{PYSCRIPT_VERSION}/{filename:path}` with `Cache-Control: public, max-age=31536000, immutable` in prod mode and `max-age=86400, must-revalidate` in dev mode.
- Update `webcompy_cli._pwa.RUNTIME_ASSET_PREFIX` to `{get_runtime_asset_prefix(PYSCRIPT_VERSION)}/` so automatic PWA precaching still excludes local runtime bundles unless `precache_runtime=True`.
- Update `webcompy_cli._browser_test_harness` to parameterize runtime routes and HTML/config paths by `pyscript_version`, preserving parity with generated HTML and `scripts/run-browser-version-sweep.sh`.
- Update `docs_app/static/_demos/standard.html` to dynamically resolve `core.js`, `core.css`, `interpreter`, and `lockFileURL` from `window.parent.document` with prefix allowlist validation instead of hardcoding `/_webcompy-assets/...`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `pyscript-bundle`: Serve local PyScript core and Pyodide runtime assets under versioned `_webcompy-assets/{PYSCRIPT_VERSION}/` paths, enforce versioned `Cache-Control` headers in ASGI serving, and reject unversioned `/_webcompy-assets/core.js` or mismatched versions.
- `project-local-cache`: Align dev-server streaming routes and SSG copy destinations with `_webcompy-assets/{pyscript_version}/` while keeping WASM wheels under `_webcompy-assets/packages/`.
- `demo-iframe-isolation`: Dynamically inherit versioned `core.js`, `core.css`, `interpreter`, and `lockFileURL` from the parent document in `standard.html` after validating allowed URL prefixes.
- `browser-test-harness`: Serve harness local runtime assets under `/_webcompy-assets/{pyscript_version}/` so HTML and `py-config` remain in parity with `webcompy_server._html`.
- `inspect-pyexec`: Update traced local boot URLs to `/_webcompy-assets/{PYSCRIPT_VERSION}/core.js`.

## Known Issues Addressed

- Eliminates cross-deployment runtime version skew (`JsBigInt` missing in stale `python_stdlib.zip`, or stale `core.js` importing a removed chunk hash) under CDN/browser HTTP caches.
- No entry in `openspec/config.yaml` Known Issues restricts URL layout changes for `_webcompy-assets/`.

## Non-goals

- Moving WASM package wheels out of `_webcompy-assets/packages/` (wheel filenames already embed package version and Emscripten ABI tags, e.g. `cp314-...wasm32.whl`).
- Changing PyScript/Pyodide CDN URLs when `runtime_serving="cdn"`.
- Adding host-specific header config files (such as Cloudflare Pages `_headers`) to `docs_app/static/`.

## Impact

- **Server HTML**: `packages/webcompy-server/src/webcompy_server/_html.py`.
- **CLI / Server / SSG / PWA / Harness**: `packages/webcompy-cli/src/webcompy_cli/_generate.py`, `_server.py`, `_pwa.py`, `_browser_test_harness.py`.
- **Docs App**: `docs_app/static/_demos/standard.html`.
- **Tests**: Unit tests in `tests/test_html_generation.py`, `test_runtime_local_integration.py`, `test_pwa_sw_generation.py`, `test_build_runtime_local.py`, `test_build_standalone.py`, `test_browser_test_harness.py`, `test_cli_resource_endpoint.py`, and E2E tests `e2e/core/test_standalone.py`, `e2e/core/test_runtime_local.py`.
