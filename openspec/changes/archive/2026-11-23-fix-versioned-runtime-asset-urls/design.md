# Design

## Context

`pyodide.mjs` derives `indexURL` from its own module URL and loads `pyodide.asm.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, and `pyodide-lock.json` relative to that directory. Similarly, PyScript's `core.js` imports `./core-*.js` chunks relative to its directory. Serving all local runtime files under a path containing `PYSCRIPT_VERSION` atomically isolates every file in a runtime release at a distinct immutable URL whenever `PYSCRIPT_VERSION` changes.

## Decisions

### 1. Canonical prefix helper in `webcompy_server._html`

`get_runtime_asset_prefix(pyscript_version: str = PYSCRIPT_VERSION) -> str` returns `f"_webcompy-assets/{pyscript_version}"`. Placing it alongside `PYSCRIPT_VERSION` and `PYSCRIPT_BASE_URL` lets `webcompy-server` and `webcompy-cli` (`_generate.py`, `_server.py`, `_pwa.py`, `_browser_test_harness.py`) derive the exact same path segment without duplicating string formatting.

### 2. SSG destination, ASGI route, and `Cache-Control` headers

- SSG copies `artifacts.runtime_asset_files` into `dist_dir / get_runtime_asset_prefix(PYSCRIPT_VERSION) / rel_path`. Unversioned `dist/_webcompy-assets/core.js` is no longer emitted.
- ASGI registers `/{get_runtime_asset_prefix(PYSCRIPT_VERSION)}/{filename:path}` in `_server.py`. Responses include `Cache-Control: public, max-age=31536000, immutable` when `artifacts.dev_mode` is `False` (versioned path makes assets content-addressed per release) and `Cache-Control: max-age=86400, must-revalidate` when `artifacts.dev_mode` is `True`.
- `wasm_asset_files` stays at `/_webcompy-assets/packages/{file_name}` (`dist/_webcompy-assets/packages/`) because wheel filenames already contain package versions and Python/ABI tags.

### 3. PWA precache exclusion parity

`webcompy_cli._pwa.RUNTIME_ASSET_PREFIX` changes from `"_webcompy-assets/"` to `f"{get_runtime_asset_prefix(PYSCRIPT_VERSION)}/"`. Because `build_precache_entries` checks membership against `{RUNTIME_ASSET_PREFIX}{rel}` where `rel` comes from `runtime_asset_files`, local runtime assets continue to be excluded when `precache_runtime=False` and included when `precache_runtime=True`, while WASM wheels under `_webcompy-assets/packages/` remain auto-precached.

### 4. Browser test harness parameterization

`build_py_config()`, `generate_harness_html()`, and `create_harness_server()` in `webcompy_cli._browser_test_harness` accept `pyscript_version: str = PYSCRIPT_VERSION` and compute routes and URLs via `get_runtime_asset_prefix(pyscript_version)`. This keeps shape parity with `webcompy_server._html` while allowing `scripts/run-browser-version-sweep.sh` to boot candidate PyScript versions side by side.

### 5. Dynamic parent inheritance in `docs_app/static/_demos/standard.html`

`standard.html` currently hardcodes `/_webcompy-assets/core.js`, `/_webcompy-assets/core.css`, `config.interpreter`, and `config.lockFileURL`. Instead, its bootstrap script inspects `window.parent.document` (same-origin) to read:

- `script[type="py"][config]`: extracts the framework wheel URL, `interpreter`, and `lockFileURL`.
- `script[type="module"][src*="core.js"]` and `link[rel="stylesheet"][href*="core.css"]`: extracts parent core asset URLs.

Extracted URLs are validated against strict prefix allowlists before DOM injection:

- Local runtime URLs (`interpreter`, `lockFileURL`): `^\/_webcompy-assets\/[A-Za-z0-9._-]+\/`
- Core assets (`core.js`, `core.css`): `^(\/_webcompy-assets\/|https:\/\/pyscript\.net\/releases\/)[A-Za-z0-9._-]+\/`

`<script type="py">` is configured synchronously with `src` and `config` BEFORE dynamically appending `<link rel="stylesheet">` to `<head>` and `<script type="module" src="...">` to `<body>`, preserving PyScript boot ordering and guaranteeing identical browser cache URLs with the parent page.
