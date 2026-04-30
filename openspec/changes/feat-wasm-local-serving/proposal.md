# Proposal: WASM Local Serving — Same-Origin WASM Package Serving

## Summary

Download WASM packages from the Pyodide CDN at build time and serve them from the same origin as the WebComPy application. This enables offline operation of WASM-dependent apps and eliminates external CDN requests for WASM packages. When WASM packages are served locally, `py-config.lockFileURL` is set to the Pyodide CDN URL so that Pyodide/micropip can resolve inter-package dependencies correctly.

## Motivation

1. **Offline capability for WASM-dependent apps**: Apps using `numpy`, `matplotlib`, etc. currently require internet access for the Pyodide CDN. Local serving enables offline operation when combined with `feat-pyscript-local-serving`.

2. **Air-gapped environments**: Intranet deployments or environments without internet access need WASM packages served locally.

3. **PWA/ServiceWorker**: Same-origin WASM assets can be cached by a ServiceWorker. Cross-origin CDN resources cannot.

4. **Privacy/compliance**: No external CDN requests for WASM packages.

## Known Issues Addressed

None (new capability).

## Non-goals

- This does not change pure-Python package handling (that is `feat-deps-local-serving`, already implemented).
- This does not download the PyScript/Pyodide runtime (that is `feat-pyscript-local-serving`).
- This does not implement split/detached wheel mode (that is `feat-split-mode`).
- This does not provide a `standalone` convenience flag (that is `feat-standalone`).
- This does not set `lockFileURL` to a local path — that requires `feat-pyscript-local-serving`. Instead, this change sets `lockFileURL` to the Pyodide CDN URL.

## Dependencies

- **Requires** `feat-deps-local-serving` (implemented) — the lock file v2 schema, `ClassifiedDependency`, and download infrastructure are prerequisites.
- **Benefits from** `feat-pyscript-local-serving` — when the runtime is also served locally, `lockFileURL` points to a local `pyodide-lock.json` instead of the CDN URL.

## Layered Architecture

```
Level 1: feat-dependency-bundling (implemented)
  WASM ─────────── CDN (loaded by package name)
  Pure-Py ──────── Bundled (local install required)
  PyScript ─────── CDN

Level 3: feat-deps-local-serving (implemented)
  Pure-Py CDN ──── Downloaded from Pyodide CDN → bundled into app wheel
  WASM ─────────── CDN
  PyScript ─────── CDN

Level 4: feat-wasm-local-serving (this change)
  WASM ─────────── Same-origin serving (downloaded from Pyodide CDN)
  Pure-Py ──────── (unchanged from Level 3)
  PyScript ─────── CDN
  lockFileURL ──── Pyodide CDN URL (for micropip dependency resolution)

Level 5: feat-pyscript-local-serving
  PyScript/Pyodide ─ Same-origin serving
  lockFileURL ──── Local URL (pyodide-lock.json served locally)

Level 6: feat-standalone
  Everything served from same origin → complete offline operation
```

## Design

### Overview

```
DEFAULT MODE (wasm_serving="cdn"):
  Pyodide CDN ─────── numpy (WASM via package name in py-config.packages)
  py-config.packages = ["numpy"]

WASM LOCAL SERVING (wasm_serving="local"):
  WebComPy server ─── /_webcompy-assets/packages/numpy-2.2.5-...wasm32.whl
  py-config.packages = ["/_webcompy-assets/packages/numpy-2.2.5-...wasm32.whl"]
  py-config.lockFileURL = "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/pyodide-lock.json"
```

### Implementation Sketch

- `AppConfig` gains a `wasm_serving: Literal["cdn", "local"] = "cdn"` field.
- When `wasm_serving="local"`:
  1. Download WASM wheel files from the Pyodide CDN using `file_name` and `sha256` from `pyodide-lock.json`.
  2. Place them in `dist/_webcompy-assets/packages/` (SSG) or serve from memory (dev server).
  3. `py-config.packages` references local wheel URLs instead of CDN package names.
  4. `py-config.lockFileURL` is set to the Pyodide CDN URL so micropip can resolve dependencies.

### Why lockFileURL is Required

When WASM packages are specified as local URLs in `py-config.packages`, Pyodide uses micropip to install them. Micropip consults `pyodide-lock.json` to resolve transitive dependencies between packages. Without `lockFileURL`, Pyodide uses its built-in lock, which may not match the Pyodide version used by the WASM wheels.

Setting `lockFileURL` to the CDN URL (`https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json`) ensures correct dependency resolution without requiring the full runtime to be served locally.

### Download Strategy

WASM wheel URLs are constructed from the Pyodide lock:
```
https://cdn.jsdelivr.net/pyodide/v{version}/full/{file_name}
```

Where `file_name` comes from `pyodide-lock.json` entries. Downloads reuse the existing `_pyodide_downloader.py` infrastructure with caching at `~/.cache/webcompy/pyodide-packages/{version}/`.

### WASM Packages and `py-config.packages`

In default mode:
```json
"packages": ["/_webcompy-app-package/myapp-py3-none-any.whl", "numpy", "matplotlib"]
```

In WASM local serving mode:
```json
"packages": [
  "/_webcompy-app-package/myapp-py3-none-any.whl",
  "/_webcompy-assets/packages/numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
  "/_webcompy-assets/packages/matplotlib-3.8.4-cp313-cp313-pyodide_2025_0_wasm32.whl"
]
```

### Config Location

`wasm_serving` is placed on `AppConfig` (not `ServerConfig`/`GenerateConfig`) because:
- It affects the HTML output (py-config contents), which is shared between dev server and SSG.
- It is a developer-facing decision about dependency delivery, not an infrastructure concern.
- It follows the same pattern as `serve_all_deps`.

### Lock File Changes

The lock file gains a `wasm_serving` field:

```jsonc
{
  "version": 2,
  "pyodide_version": "0.29.3",
  "pyscript_version": "2026.3.1",
  "wasm_serving": "local",
  "wasm_packages": { ... },
  "pure_python_packages": { ... }
}
```

## Specs Affected

- `app-config` — add `wasm_serving` field to `AppConfig`
- `cli` — download WASM wheels, serve from local paths, set `lockFileURL` in py-config
- `lockfile` — add `wasm_serving` field