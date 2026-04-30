# Proposal: Standalone — Orchestration Change for Complete Offline Capability

## Summary

Add a `standalone` configuration option to `AppConfig` that orchestrates all local-serving modes (`serve_all_deps`, `wasm_serving`, `runtime_serving`) to produce a fully self-contained application with zero external CDN requests. When enabled, all assets — PyScript runtime, Pyodide engine, WASM packages, and pure-Python packages — are downloaded at build time and served from the same origin.

## Motivation

1. **Single config option**: Developers typically want complete offline capability as one toggle, not three separate settings.
2. **PWA readiness**: Same-origin assets are a prerequisite for ServiceWorker caching and PWA manifest generation (future changes).
3. **Air-gapped deployment**: A single `webcompy generate --standalone` produces a fully self-contained `dist/` directory.

## Known Issues Addressed

None (new capability).

## Non-goals

- This does not implement ServiceWorker registration or PWA manifest generation — those are future enhancements.
- This does not implement split/detached wheel mode — that is `feat-split-mode`.
- This does not change the default build mode (CDN mode remains default).
- This does not add new download logic — all downloads are delegated to `feat-wasm-local-serving` and `feat-pyscript-local-serving`.

## Dependencies

- **Requires** `feat-deps-local-serving` (implemented) — provides `serve_all_deps` and CDN pure-Python download pipeline.
- **Requires** `feat-wasm-local-serving` — provides `wasm_serving` and WASM download pipeline.
- **Requires** `feat-pyscript-local-serving` — provides `runtime_serving` and runtime download pipeline.
- **Full offline requires all three**: `serve_all_deps=True` + `wasm_serving="local"` + `runtime_serving="local"`.

## Layered Architecture

```
Level 1: feat-dependency-bundling (implemented)
  WASM ─────── CDN (loaded by package name)
  Pure-Py ─────── Bundled (local install required)
  PyScript ── CDN

Level 2: feat-deps-local-serving (implemented)
  Pure-Py CDN ── Downloaded from Pyodide CDN → bundled into app wheel

Level 3: feat-wasm-local-serving
  WASM ─────── Downloaded from Pyodide CDN → same-origin serving
  lockFileURL ── Pyodide CDN URL

Level 4: feat-pyscript-local-serving
  PyScript/Pyodide ─ Downloaded from CDN → same-origin serving
  lockFileURL ── Local URL

Level 5: feat-standalone (this change)
  Everything served from same origin → complete offline ★
```

## Design

### Configuration

```python
@dataclass
class AppConfig:
    ...
    serve_all_deps: bool = True
    wasm_serving: Literal["cdn", "local"] | None = None
    runtime_serving: Literal["cdn", "local"] | None = None
    standalone: bool = False
```

`wasm_serving` and `runtime_serving` use `None` as a sentinel for "not explicitly set". At config resolution time, `None` is resolved to `"cdn"` (the default). This allows the standalone orchestration to distinguish between "still at default" (`None`) and "explicitly set to cdn" (`"cdn"`).

When `standalone=True`:
- `serve_all_deps` is forced to `True` (all pure-Python packages must be bundled).
- `wasm_serving` resolves to `"local"` if still `None` (explicit `"cdn"` overrides).
- `runtime_serving` resolves to `"local"` if still `None` (explicit `"cdn"` overrides).

### Orchestration Logic

```python
if config.standalone:
    if config.serve_all_deps is False:
        warn("standalone=True forces serve_all_deps=True")
    config.serve_all_deps = True  # forced — offline requires all deps bundled
    if config.wasm_serving is None:
        config.wasm_serving = "local"  # standalone default
    if config.runtime_serving is None:
        config.runtime_serving = "local"  # standalone default

# After standalone resolution, resolve remaining None defaults
if config.wasm_serving is None:
    config.wasm_serving = "cdn"
if config.runtime_serving is None:
    config.runtime_serving = "cdn"
```

The `standalone` flag does NOT introduce new download logic. It simply sets the three existing config fields to their local-serving values. All download and serving behavior is handled by `feat-wasm-local-serving` and `feat-pyscript-local-serving`.

### Build Pipeline (Standalone SSG)

```
webcompy generate --standalone
        │
        ▼
  Set: serve_all_deps=True, wasm_serving="local", runtime_serving="local"
        │
        ▼
  Delegate to feat-wasm-local-serving pipeline:
    Download WASM wheels → dist/_webcompy-assets/packages/
  Delegate to feat-pyscript-local-serving pipeline:
    Download PyScript core → dist/_webcompy-assets/
    Download Pyodide runtime → dist/_webcompy-assets/pyodide/
  Delegate to feat-deps-local-serving pipeline:
    Download CDN pure-Py → bundle into app wheel
  Build single bundled wheel → dist/_webcompy-app-package/
        │
        ▼
  dist/
  ├── _webcompy-assets/
  │   ├── core.js, core.css
  │   ├── pyodide/
  │   │   ├── pyodide.mjs, pyodide.asm.wasm, pyodide.asm.js
  │   │   ├── pyodide-lock.json
  │   │   └── python_stdlib.zip
  │   └── packages/
  │       └── numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl
  ├── _webcompy-app-package/
  │   └── myapp-py3-none-any.whl
  └── index.html (all local URLs, zero external requests)
```

### Generated HTML (Standalone Mode)

```json
{
  "interpreter": "/_webcompy-assets/pyodide/pyodide.mjs",
  "lockFileURL": "/_webcompy-assets/pyodide/pyodide-lock.json",
  "packages": [
    "/_webcompy-app-package/myapp-py3-none-any.whl",
    "/_webcompy-assets/packages/numpy-2.2.5-...wasm32.whl"
  ],
  "experimental_create_proxy": "auto"
}
```

### CLI

```bash
webcompy generate --standalone        # Full offline build
webcompy start --dev --standalone      # Dev server with offline assets
```

`--standalone` is equivalent to `--serve-all-deps --wasm-serving local --runtime-serving local`.

### Lock File

No new lock file section is needed. The `wasm_serving` and `runtime_serving` fields (added by `feat-wasm-local-serving` and `feat-pyscript-local-serving`) already capture the configuration. The `standalone` flag is reflected by the combination:
- `wasm_serving: "local"`
- `runtime_serving: "local"`

A `standalone: bool` field MAY be added to the lock file for informational purposes, but it does not add new asset data.

### PWA Extension (Future)

When `standalone=True`, future changes can add:
- `GenerateConfig.service_worker = True` → generate ServiceWorker script
- `GenerateConfig.manifest = {...}` → generate PWA manifest
- Offline caching strategies for same-origin assets

These are out of scope but `standalone=True` is the prerequisite.

## Specs Affected

- `app-config` — add `standalone: bool = False` to `AppConfig`
- `cli` — add `--standalone` CLI flag, orchestrate config defaults
