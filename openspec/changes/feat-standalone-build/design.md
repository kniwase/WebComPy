# Design: Standalone Build — Same-Origin Serving of All Assets

## Design Decisions

### D1: `standalone` is opt-in, not default
The default mode continues to use CDN for PyScript/Pyodide. `standalone=True` must be explicitly set in `GenerateConfig` or `ServerConfig`, or via `--standalone` CLI flag.

### D2: Assets are downloaded at build time, not bundled in the framework
PyScript/Pyodide assets are fetched from CDN during `webcompy generate --standalone` or at dev server startup. They are not part of the WebComPy package itself.

### D3: Asset downloads are driven by `webcompy-lock.json`
The lock file's `pyodide_packages` section determines which Pyodide wheels to download. The `pyscript_version` and `pyodide_version` determine which Pyodide runtime files to download.

### D4: The lock file gains a `standalone_assets` section
When in standalone mode, the lock file records which Pyodide runtime files were downloaded (with SHA256 hashes for verification):

```jsonc
{
  "version": 1,
  "pyodide_version": "0.29.3",
  "pyscript_version": "2026.3.1",
  "pyodide_packages": { ... },
  "bundled_packages": { ... },
  "standalone_assets": {
    "core_js": { "url": "...", "sha256": "..." },
    "core_css": { "url": "...", "sha256": "..." },
    "pyodide_mjs": { "url": "...", "sha256": "..." },
    "pyodide_asm_wasm": { "url": "...", "sha256": "..." },
    "pyodide_asm_js": { "url": "...", "sha256": "..." },
    "python_stdlib_zip": { "url": "...", "sha256": "..." }
  }
}
```

### D5: HTML generation switches asset URLs to local paths
In standalone mode, `generate_html()` replaces CDN URLs with local paths:
- `https://pyscript.net/releases/2026.3.1/core.js` → `/_webcompy-assets/core.js`
- `https://pyscript.net/releases/2026.3.1/core.css` → `/_webcompy-assets/core.css`
- `py-config.packages` entries reference `/_webcompy-assets/packages/{filename}` for Pyodide wheels
- `py-config.lockFileURL` is set to `/_webcompy-assets/pyodide-lock.json`

### D6: Dev server serves standalone assets with immutable cache headers
In standalone dev mode, all assets in `/_webcompy-assets/` are served with `Cache-Control: max-age=86400, must-revalidate`.

## Architecture

### Build Pipeline (Standalone SSG)

```
webcompy generate --standalone
        │
        ▼
  Load/generate webcompy-lock.json
        │
        ▼
  Download PyScript assets (core.js, core.css)
  Download Pyodide runtime (pyodide.mjs, .wasm, .js, stdlib.zip)
  Download Pyodide wheels from lock file
  Build framework wheel
  Build app wheel (with bundled deps)
        │
        ▼
  dist/
  ├── _webcompy-assets/
  │   ├── core.js, core.css
  │   ├── pyodide.mjs, pyodide.asm.wasm, pyodide.asm.js
  │   ├── pyodide-lock.json
  │   ├── python_stdlib.zip
  │   └── packages/
  │       ├── numpy-2.2.5-...wasm32.whl
  │       └── ...
  ├── _webcompy-app-package/
  │   ├── webcompy-py3-none-any.whl
  │   └── myapp-py3-none-any.whl
  └── index.html (with local URLs)
```

### Build Pipeline (Standalone Dev Server)

```
webcompy start --dev --standalone
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
    /_webcompy-assets/packages/*
    /_webcompy-app-package/webcompy-py3-none-any.whl
    /_webcompy-app-package/myapp-py3-none-any.whl
```

## Config Changes

```python
@dataclass
class GenerateConfig:
    dist: str = "dist"
    cname: str = ""
    static_files_dir: str = "static"
    standalone: bool = False  # NEW

@dataclass
class ServerConfig:
    port: int = 8080
    dev: bool = False
    static_files_dir: str = "static"
    standalone: bool = False  # NEW
```

## CLI Changes

```bash
webcompy start --dev --standalone
webcompy generate --standalone
webcompy lock --standalone  # pre-download assets
```

## Non-goals (This Change)

- ServiceWorker generation
- PWA manifest generation
- Offline caching strategy
- Asset integrity verification (beyond SHA256 in lock file)
- Incremental asset updates