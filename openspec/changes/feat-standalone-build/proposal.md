# Proposal: Standalone Build — Same-Origin Serving of All Assets for PWA/Offline Support

## Summary

Add a standalone build mode that serves PyScript runtime, Pyodide engine, and all Python packages from the same origin (the WebComPy server or static site), eliminating all external CDN dependencies. This enables PWA/ServiceWorker configuration and full offline support.

## Motivation

1. **Offline capability**: Current builds depend on CDN availability for PyScript/Pyodide. A standalone build enables offline PWA applications.

2. **PWA/ServiceWorker**: Same-origin assets are required for ServiceWorker caching and `Cache-Control` policies. Cross-origin CDN resources cannot be cached by a ServiceWorker in many configurations.

3. **Air-gapped environments**: Intranet deployments or environments without internet access need all assets served locally.

4. **Privacy/compliance**: No external requests means no CDN tracking or data leakage.

## Known Issues Addressed

None (new capability).

## Non-goals

- This does not change the default build mode (CDN mode remains default).
- This does not implement ServiceWorker registration or PWA manifest generation — those are future enhancements.
- This does not bundle C extension packages not available in the Pyodide CDN (they would need separate Pyodide wheel hosting).

## Dependencies

- **Requires** `feat-wheel-split` — the lock file and dependency classification are prerequisites for knowing which Pyodide CDN assets to download.

## Design

### Overview

```
DEFAULT MODE (feat-wheel-split):
  PyScript CDN ────── core.js, core.css
  Pyodide CDN ─────── numpy-2.2.5-...wasm32.whl, httpx-0.28.1-py3-none-any.whl, ...
  WebComPy server ─── framework wheel, app wheel

STANDALONE MODE (feat-standalone-build):
  WebComPy server ─── core.js, core.css, pyodide.mjs, pyodide-lock.json,
                       numpy-2.2.5-...wasm32.whl, httpx-0.28.1-py3-none-any.whl,
                       framework wheel, app wheel
                       (ALL assets from same origin)
```

### Implementation Sketch

- `GenerateConfig` and `ServerConfig` gain a `standalone: bool = False` field.
- When `standalone=True`:
  1. PyScript `core.js`, `core.css` are downloaded at build time and served locally.
  2. Pyodide `pyodide.mjs`, `pyodide.asm.wasm`, `pyodide.asm.js`, `python_stdlib.zip` are downloaded and served locally.
  3. `pyodide-lock.json` is served locally (so micropip resolves against it).
  4. All Pyodide CDN wheels (WASM and pure-Python) referenced in the lock file are downloaded and served locally.
  5. Generated HTML references all assets via same-origin URLs.
  6. `py-config` `lockFileURL` is pointed at the local `pyodide-lock.json`.

### Asset Size Estimate

- PyScript core.js: ~170KB
- Pyodide runtime: ~8MB (wasm + js + stdlib)
- Pyodide packages: varies (typically 100KB–10MB per package)
- Framework wheel: ~180KB
- App wheel: varies

Total standalone build could be 10–30MB depending on dependencies.

### Download Strategy

At build time, `webcompy generate --standalone` (or equivalent) downloads all required assets from CDN and places them in `dist/_webcompy-assets/`:

```
dist/
├── _webcompy-assets/
│   ├── core.js
│   ├── core.css
│   ├── pyodide.mjs
│   ├── pyodide.asm.wasm
│   ├── pyodide.asm.js
│   ├── pyodide-lock.json
│   ├── python_stdlib.zip
│   └── packages/
│       ├── numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl
│       ├── httpx-0.28.1-py3-none-any.whl
│       └── ...
├── _webcompy-app-package/
│   ├── webcompy-py3-none-any.whl
│   └── myapp-py3-none-any.whl
├── index.html
└── ...
```

### PWA Extension (Future)

A subsequent change could add:
- `GenerateConfig.service_worker = True` to generate a ServiceWorker script.
- `GenerateConfig.manifest = {...}` to generate a PWA manifest.
- Offline caching strategies for same-origin assets.

These are explicitly out of scope for this change but the standalone mode is a prerequisite.

## Specs Affected

- `cli` — add `standalone` flag, asset download logic
- `app-config` — add `standalone` to `GenerateConfig` and `ServerConfig`
- `lockfile` — add `standalone_assets` lock file section