# Design: PyScript Local Serving — Same-Origin Runtime Assets

## Design Decisions

### D1: `runtime_serving` is on AppConfig, not ServerConfig/GenerateConfig
`runtime_serving: Literal["cdn", "local"] | None = None` is on `AppConfig` alongside `wasm_serving` and `serve_all_deps`. When `None` (default), the effective value is `"cdn"`. When `standalone=True`, `None` resolves to `"local"`. Explicit `"cdn"` is preserved even when `standalone=True`. This unifies all local-serving configuration in one dataclass. `ServerConfig` and `GenerateConfig` are NOT modified by this change.

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

### D5: Downloads are cached at `~/.cache/webcompy/runtime-assets/{pyscript_version}/`
Each runtime asset is cached with its filename as key. SHA256 hashes are computed at download time and recorded in the lock file's `runtime_assets` section. On subsequent builds, downloaded files are verified against the hashes stored in the lock file. First-build verification is skipped (no prior hashes exist). The `pyodide-lock.json` `packages` section does not contain entries for runtime files (`pyodide`, `pyodide_asm`, `python_stdlib`), so it cannot be used as a hash source for runtime asset verification.

### D6: The lock file gains `runtime_serving` field and `runtime_assets` section
When `runtime_serving="local"`:
- `"runtime_serving": "local"` is recorded in the lock file
- `"runtime_assets"` section contains entries with `url` and `sha256` for each runtime file

When `runtime_serving="cdn"`:
- `"runtime_serving": "cdn"` is recorded
- `"runtime_assets"` section is not present

### D7: `--runtime-serving` CLI flag (value argument)
`--runtime-serving <mode>` (where `<mode>` is `cdn` or `local`) overrides `AppConfig.runtime_serving`. Example: `webcompy start --dev --runtime-serving local` sets `runtime_serving="local"`.

## Architecture

### Build Pipeline (SSG)

```
webcompy generate --runtime-serving local
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
webcompy start --dev --runtime-serving <mode>
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
    runtime_serving: Literal["cdn", "local"] | None = None  # NEW
```

When `runtime_serving` is `None` (default), it resolves to `"cdn"`. Using `None` as the default allows `standalone=True` to distinguish between "not explicitly set" (should be overridden to `"local"`) and "explicitly set to 'cdn'" (should be preserved).

## CLI Changes

```bash
webcompy start --dev --runtime-serving <mode>
webcompy generate --runtime-serving <mode>
# where <mode> is "cdn" or "local"
```

## HTML Generation Changes

When `runtime_serving="local"`, `generate_html()`:
1. `<script type="module" src="...">` → `/_webcompy-assets/core.js`
2. `<link rel="stylesheet" href="...">` → `/_webcompy-assets/core.css`
3. `py-config` gains `"interpreter": "/_webcompy-assets/pyodide/pyodide.mjs"`
4. `py-config` gains `"lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json"`

## Migration: `standalone_assets` → `runtime_assets`

The current `Lockfile.to_dict()` outputs a `standalone_assets: {}` placeholder (added as a forward-compatibility field before this design). This field is superseded by `runtime_assets` in this change. During implementation:

1. Rename `standalone_assets` → `runtime_assets` in `Lockfile.to_dict()`.
2. In `load_lockfile()`, accept both `standalone_assets` and `runtime_assets` keys for backward compatibility with existing v2 lock files. If `standalone_assets` is present and `runtime_assets` is absent, treat `standalone_assets` as `runtime_assets`.
3. The `standalone_assets` key should be considered deprecated. A future change may remove backward-compatibility handling.

## Non-goals (This Change)

- ServiceWorker generation
- PWA manifest generation
- WASM package download from Pyodide CDN (separate change: `feat-wasm-local-serving`)
- Pure-Python dependency download from Pyodide CDN (already: `serve_all_deps=True`)
- Split/detached wheel mode (separate change: `feat-split-mode`)