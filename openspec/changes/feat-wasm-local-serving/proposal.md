# Proposal: WASM Local Serving — Same-Origin WASM Package Serving

## Summary

Download WASM packages from the Pyodide CDN at build time and serve them from the same origin as the WebComPy application. This enables offline operation of WASM-dependent apps and eliminates external CDN requests for WASM packages when combined with `feat-deps-local-serving` and `feat-pyscript-local-serving`.

## Motivation

1. **Offline capability for WASM-dependent apps**: Apps using `numpy`, `matplotlib`, etc. currently require internet access for the Pyodide CDN. Local serving enables offline operation.

2. **Air-gapped environments**: Intranet deployments or environments without internet access need WASM packages served locally.

3. **PWA/ServiceWorker**: Same-origin WASM assets can be cached by a ServiceWorker. Cross-origin CDN resources cannot.

4. **Privacy/compliance**: No external CDN requests for WASM packages.

## Known Issues Addressed

None (new capability).

## Non-goals

- This does not change pure-Python package handling (that is `feat-deps-local-serving`).
- This does not download the PyScript/Pyodide runtime (that is `feat-pyscript-local-serving`).
- This does not implement split/detached wheel mode (that is `feat-split-mode`).

## Dependencies

- **Requires** `feat-dependency-bundling` — the lock file and dependency classification identify which packages are WASM.

## Layered Architecture

```
Level 1: feat-dependency-bundling (prerequisite)
  WASM ────── CDN (packages名で読み込み)
  純Py ────── バンドル(ローカルインストール前提)
  PyScript ── CDN

Level 4: feat-wasm-local-serving (this change)
  WASM ────── 同一オリジン配信(Pydide CDNからDL)
  純Py ────── (feat-deps-local-servingに依存)
  PyScript ── CDN (変更なし)
```

## Design

### Overview

```
DEFAULT MODE (no WASM local serving):
  Pyodide CDN ─────── numpy-2.2.5-...wasm32.whl, matplotlib-3.8.4-...wasm32.whl
  py-config.packages = ["numpy", "matplotlib"]

WASM LOCAL SERVING (this change):
  WebComPy server ─── /_webcompy-assets/packages/numpy-2.2.5-...wasm32.whl
                       /_webcompy-assets/packages/matplotlib-3.8.4-...wasm32.whl
  py-config.packages = ["/_webcompy-assets/packages/numpy-2.2.5-...wasm32.whl",
                        "/_webcompy-assets/packages/matplotlib-3.8.4-...wasm32.whl"]
```

### Implementation Sketch

- `AppConfig` gains a `wasm_serving: Literal["cdn", "local"] = "cdn"` field.
- When `wasm_serving="local"`:
  1. Download WASM wheels from the Pyodide CDN using URLs from `pyodide-lock.json`.
  2. Place them in `dist/_webcompy-assets/packages/` (SSG) or serve from memory (dev server).
  3. `py-config.packages` references local wheel URLs instead of CDN package names.

### Download Strategy

WASM wheel URLs are constructed from the Pyodide lock:
```
https://cdn.jsdelivr.net/pyodide/v0.29.3/full/{file_name}
```

Where `file_name` comes from `pyodide-lock.json` entries (e.g., `numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl`).

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

**Note**: This replaces CDN package names with local wheel URLs. PyScript/micropip resolves dependencies from the local `pyodide-lock.json` (via `lockFileURL`). This may require the `lockFileURL` config to be set, which is handled by `feat-pyscript-local-serving`.

### Lock File Changes

The lock file gains a `wasm_serving` field:

```jsonc
{
  "version": 1,
  "pyodide_version": "0.29.3",
  "pyscript_version": "2026.3.1",
  "wasm_serving": "local",
  "pyodide_packages": { ... },
  "bundled_packages": { ... }
}
```

## Specs Affected

- `app-config` — add `wasm_serving` field
- `cli` — download WASM wheels, serve from local paths
- `lockfile` — add `wasm_serving` field