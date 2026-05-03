# Design: Standalone — Orchestration Change for Complete Offline PWA Support

## Design Decisions

### D1: `standalone` is a convenience toggle that sets all local-serving defaults
`standalone=True` sets the following defaults:
- `serve_all_deps=True` (forced — pure-Python packages must be bundled for offline operation)
- `wasm_serving="local"` (WASM packages downloaded and served locally)
- `runtime_serving="local"` (PyScript/Pyodide runtime served locally)

The `serve_all_deps=True` is **forced** because in a standalone build, CDN access is unavailable — pure-Python packages cannot be loaded from the Pyodide CDN by name. If `serve_all_deps=False` was explicitly set alongside `standalone=True`, a warning SHALL be emitted indicating that `standalone=True` forces `serve_all_deps=True`.

### D2: Individual local-serving configs override standalone defaults
If `standalone=True` but an individual config is explicitly set (not `None`), the explicit value takes precedence for `wasm_serving` and `runtime_serving`. However, `serve_all_deps=True` is always forced when `standalone=True` (offline operation requires all deps bundled).

`wasm_serving` and `runtime_serving` use `None` as a sentinel default on `AppConfig` to distinguish "not explicitly set" from "explicitly set to cdn". The CLI and `standalone` orchestration resolve `None` to an effective value:

```python
if config.standalone:
    if config.serve_all_deps is False:
        warn("standalone=True forces serve_all_deps=True")
    config.serve_all_deps = True  # forced
    if config.wasm_serving is None:    # not explicitly set
        config.wasm_serving = "local"  # standalone default
    if config.runtime_serving is None: # not explicitly set
        config.runtime_serving = "local"  # standalone default

# After standalone resolution, resolve remaining None to "cdn"
if config.wasm_serving is None:
    config.wasm_serving = "cdn"
if config.runtime_serving is None:
    config.runtime_serving = "cdn"
```

### D3: Lock file records the orchestration state
The lock file records `standalone: true` as a convenience field. The actual serving behavior is determined by the combination of `wasm_serving`, `runtime_serving`, and `serve_all_deps`. The `standalone` field is informational and does not need a separate `standalone_assets` section — the `runtime_assets` section (from `feat-pyscript-local-serving`) already captures runtime asset metadata.

### D4: `--standalone` CLI flag is a shortcut
`--standalone` on the CLI sets `standalone=True` on `AppConfig`, which triggers the orchestration logic in D1/D2. Individual `--wasm-serving` and `--runtime-serving` flags take precedence over `--standalone`.

### D5: No separate download orchestration code
`standalone=True` simply configures the individual local-serving modes. The download and serving logic for each mode is handled by their respective implementations (`feat-wasm-local-serving`, `feat-pyscript-local-serving`, `feat-deps-local-serving`). There is no separate "standalone download pipeline" — the individual pipelines run in sequence.

## Architecture

```
standalone=True config resolution:
  ┌─────────────────────────────────────────────┐
  │ AppConfig(standalone=True)                  │
  │                                             │
  │  ┌──────────────┐   ┌─────────────────────┐ │
  │  │ serve_all_deps│──▶│ True (forced)       │ │
  │  └──────────────┘   └─────────────────────┘ │
  │  ┌──────────────┐   ┌─────────────────────┐ │
  │  │ wasm_serving │──▶│ "local" (default)    │ │
  │  └──────────────┘   │ "cdn" if explicitly  │ │
  │                     │ set                  │ │
  │                     └─────────────────────┘ │
  │  ┌──────────────┐   ┌─────────────────────┐ │
  │  │runtime_serving│──▶│ "local" (default)  │ │
  │  └──────────────┘   │ "cdn" if explicitly  │ │
  │                     │ set                  │ │
  │                     └─────────────────────┘ │
  └─────────────────────────────────────────────┘

Build pipeline (standalone=True):
  1. Lock file generation (if needed)
  2. Pure-Python CDN packages → download + bundle (feat-deps-local-serving)
  3. WASM packages → download + serve locally (feat-wasm-local-serving)
  4. PyScript/Pyodide runtime → download + serve locally (feat-pyscript-local-serving)
  5. Build single bundled wheel (webcompy + app + pure-Py deps)
  6. Generate HTML with all local URLs

  dist/
  ├── _webcompy-assets/
  │   ├── core.js, core.css                          (PyScript)
  │   ├── pyodide/
  │   │   ├── pyodide.mjs
  │   │   ├── pyodide.asm.wasm
  │   │   ├── pyodide.asm.js
  │   │   ├── python_stdlib.zip
  │   │   └── pyodide-lock.json
  │   └── packages/
  │       └── numpy-2.2.5-...wasm32.whl              (WASM)
  ├── _webcompy-app-package/
  │   └── myapp-py3-none-any.whl                     (webcompy + app + pure-Py)
  └── index.html (all local URLs, zero external requests)
```

## CLI Changes

```bash
webcompy start --dev --standalone
webcompy generate --standalone
```

`--standalone` sets `AppConfig.standalone = True`, which resolves to the local-serving defaults per D1/D2.

## Non-goals (This Change)

- ServiceWorker generation
- PWA manifest generation
- Offline caching strategy
- Asset integrity verification (beyond what's in individual changes)
- Incremental asset updates
- Split/detached wheel mode (separate change: `feat-split-mode`)

## Dependencies

- **Requires** `feat-deps-local-serving` (implemented) — pure-Python CDN package download and bundling
- **Requires** `feat-wasm-local-serving` — WASM package local serving
- **Requires** `feat-pyscript-local-serving` — PyScript/Pyodide runtime local serving
