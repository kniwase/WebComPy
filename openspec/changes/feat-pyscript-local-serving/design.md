# Design: PyScript Local Serving — Same-Origin Runtime Assets

## Design Decisions

### D1: "runtime_serving" is opt-in, not default
The default mode continues to use CDN for PyScript/Pyodide. `runtime_serving="local"` must be explicitly set in `GenerateConfig` or `ServerConfig`, or via `--runtime-serving` CLI flag.

### D2: Assets are downloaded at build time, not bundled in the framework
PyScript/Pyodide assets are fetched from CDN during `webcompy generate --runtime-serving` or at dev server startup. They are not part of the WebComPy package itself.

### D3: Asset downloads are driven by `webcompy-lock.json`
The lock file's `pyscript_version` and `pyodide_version` determine which Pyodide runtime files to download. The `pyodide_packages` section determines which packages to download (when combined with `feat-wasm-local-serving`).

### D4: The lock file gains a `runtime_assets` section
When in runtime-local mode, the lock file records which Pyodide runtime files were downloaded (with SHA256 hashes for verification):

```jsonc
{
  "version": 1,
  "pyodide_version": "0.29.3",
  "pyscript_version": "2026.3.1",
  "pyodide_packages": { ... },
  "bundled_packages": { ... },
  "runtime_assets": {
    "core_js": { "url": "...", "sha256": "..." },
    "core_css": { "url": "...", "sha256": "..." },
    "pyodide_mjs": { "url": "...", "sha256": "..." },
    "pyodide_asm_wasm": { "url": "...", "sha256": "..." },
    "pyodide_asm_js": { "url": "...", "sha256": "..." },
    "python_stdlib_zip": { "url": "...", "sha256": "..." }
  }
}
```

### D5: HTML generation switches runtime asset URLs to local paths
In runtime-local mode, `generate_html()` replaces CDN URLs with local paths:
- `https://pyscript.net/releases/2026.3.1/core.js` → `/_webcompy-assets/core.js`
- `https://pyscript.net/releases/2026.3.1/core.css` → `/_webcompy-assets/core.css`
- `py-config.lockFileURL` is set to `/_webcompy-assets/pyodide-lock.json`

### D6: Dev server serves local-serving assets with immutable cache headers
In local-serving dev mode, all assets in `/_webcompy-assets/` are served with `Cache-Control: max-age=86400, must-revalidate`.

### D7: Single bundled wheel in runtime-local mode
The single bundled wheel (`{app_name}-py3-none-any.whl`) contains webcompy (excl. cli), the app, and all pure-Python dependencies — the same as default mode. No separate framework wheel is needed.

## Architecture

### Build Pipeline (Standalone SSG)

```
webcompy generate --runtime-serving
        │
        ▼
  Load/generate webcompy-lock.json
        │
        ▼
  Download PyScript assets (core.js, core.css)
  Download Pyodide runtime (pyodide.mjs, .wasm, .js, stdlib.zip)
  Build single bundled wheel (webcompy + app + pure-Py deps)
        │
        ▼
  dist/
  ├── _webcompy-assets/
  │   ├── core.js, core.css
  │   ├── pyodide.mjs, pyodide.asm.wasm, pyodide.asm.js
  │   ├── pyodide-lock.json
  │   └── python_stdlib.zip
  ├── _webcompy-app-package/
  │   └── myapp-py3-none-any.whl
  └── index.html (with local URLs)
```

### Build Pipeline (Standalone Dev Server)

```
webcompy start --dev --runtime-serving
        │
        ▼
  Load/generate webcompy-lock.json
  Download assets (cached in ~/.cache/webcompy/)
        │
        ▼
  Serve at:
    /_webcompy-assets/core.js
    /_webcompy-assets/core.css
    /_webcompy-assets/pyodide.mjs
    /_webcompy-assets/pyodide-lock.json
    /_webcompy-app-package/myapp-py3-none-any.whl
```

## Config Changes

```python
@dataclass
class GenerateConfig:
    dist: str = "dist"
    cname: str = ""
    static_files_dir: str = "static"
    local-serving: bool = False  # NEW

@dataclass
class ServerConfig:
    port: int = 8080
    dev: bool = False
    static_files_dir: str = "static"
    local-serving: bool = False  # NEW
```

## CLI Changes

```bash
webcompy start --dev --runtime-serving
webcompy generate --runtime-serving
webcompy lock --runtime-serving  # pre-download runtime assets
```

## Non-goals (This Change)

- ServiceWorker generation
- PWA manifest generation
- Offline caching strategy
- Asset integrity verification (beyond SHA256 in lock file)
- Incremental asset updates
- Split/detached wheel mode (separate change: `feat-split-mode`)
- Pure-Python dependency download from Pyodide CDN (separate change: `feat-deps-local-serving`)
- WASM package download from Pyodide CDN (separate change: `feat-wasm-local-serving`)