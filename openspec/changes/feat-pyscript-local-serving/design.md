# Design: PyScript Local Serving — Same-Origin Runtime Assets

## Design Decisions

### D1: `runtime_serving` is on AppConfig, not ServerConfig/GenerateConfig
`runtime_serving: Literal["cdn", "local"] = "cdn"` is on `AppConfig` alongside `wasm_serving` and `serve_all_deps`. This unifies all local-serving configuration in one dataclass. `ServerConfig` and `GenerateConfig` are NOT modified by this change.

### D2: `runtime_serving="local"` downloads PyScript core + Pyodide runtime at build time
Assets are fetched from CDN during `webcompy generate` or `webcompy start` when `runtime_serving="local"`. They are NOT part of the WebComPy package.

### D3: PyScript `py-config` gains `interpreter` and `lockFileURL` fields
When `runtime_serving="local"`, the generated `py-config` JSON includes:
- `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"` — local Pyodide interpreter
- `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"` — local lock file

This follows the official PyScript offline guide pattern. Without `runtime_serving="local"`, neither field is emitted.

### D4: Asset directory structure mirrors Pyodide's expected layout
Runtime assets are placed in `/_webcompy-assets/pyodide/` to match Pyodide's expectations:

```
dist/_webcompy-assets/
├── core.js
├── core.css
└── pyodide/
    ├── pyodide.mjs
    ├── pyodide.asm.wasm
    ├── pyodide.asm.js
    ├── python_stdlib.zip
    └── pyodide-lock.json
```

This subdirectory layout ensures Pyodide's relative path resolution works correctly.

### D5: Downloads are cached at `~/.cache/webcompy/runtime-assets/{pyodide_version}/`
Each runtime asset is cached with its filename as key. SHA256 verification uses hashes from the downloaded `pyodide-lock.json` for Pyodide files. PyScript core assets are verified against known hashes or version-pinned cache keys.

### D6: The lock file gains `runtime_serving` field and `runtime_assets` section
When `runtime_serving="local"`:
- `"runtime_serving": "local"` is recorded in the lock file
- `"runtime_assets"` section contains entries with `url` and `sha256` for each runtime file

When `runtime_serving="cdn"`:
- `"runtime_serving": "cdn"` is recorded (or field is omitted)
- `"runtime_assets"` is an empty object `{}`

### D7: `--runtime-serving` CLI flag
`webcompy start --runtime-serving` and `webcompy generate --runtime-serving` set `runtime_serving="local"`, overriding `AppConfig.runtime_serving`.

## Architecture

### Build Pipeline (SSG)

```
webcompy generate --runtime-serving
        │
        ▼
  Load/generate webcompy-lock.json
        │
        ▼
  Download PyScript core (core.js, core.css)
  Download Pyodide runtime (pyodide.mjs, .asm.wasm, .asm.js, stdlib.zip, lock.json)
  Build single bundled wheel (webcompy + app + pure-Py deps)
        │
        ▼
  dist/
  ├── _webcompy-assets/
  │   ├── core.js, core.css
  │   └── pyodide/
  │       ├── pyodide.mjs, pyodide.asm.wasm, pyodide.asm.js
  │       ├── python_stdlib.zip
  │       └── pyodide-lock.json
  ├── _webcompy-app-package/
  │   └── myapp-py3-none-any.whl
  └── index.html (with local URLs + interpreter + lockFileURL)
```

### Build Pipeline (Dev Server)

```
webcompy start --dev --runtime-serving
        │
        ▼
  Load/generate webcompy-lock.json
  Download assets (cached in ~/.cache/webcompy/runtime-assets/)
        │
        ▼
  Serve at:
    /_webcompy-assets/core.js
    /_webcompy-assets/core.css
    /_webcompy-assets/pyodide/pyodide.mjs
    /_webcompy-assets/pyodide/pyodide-lock.json
    /_webcompy-app-package/myapp-py3-none-any.whl
```

## Config Changes

```python
@dataclass
class AppConfig:
    ...
    runtime_serving: Literal["cdn", "local"] = "cdn"  # NEW
```

## CLI Changes

```bash
webcompy start --dev --runtime-serving
webcompy generate --runtime-serving
```

## HTML Generation Changes

When `runtime_serving="local"`, `generate_html()`:
1. `<script type="module" src="...">` → `/_webcompy-assets/core.js`
2. `<link rel="stylesheet" href="...">` → `/_webcompy-assets/core.css`
3. `py-config` gains `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"`
4. `py-config` gains `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"`

## Non-goals (This Change)

- ServiceWorker generation
- PWA manifest generation
- WASM package download from Pyodide CDN (separate change: `feat-wasm-local-serving`)
- Pure-Python dependency download from Pyodide CDN (already: `serve_all_deps=True`)
- Split/detached wheel mode (separate change: `feat-split-mode`)