# Proposal: PyScript Local Serving — Same-Origin PyScript Runtime for Offline PWA Support

## Summary

Download and serve the PyScript runtime (core.js, core.css) and Pyodide engine (pyodide.mjs, pyodide.asm.wasm, python_stdlib.zip) from the same origin as the WebComPy application. This is the final level of local serving, enabling complete offline PWA support when combined with the dependency and WASM local serving changes.

## Motivation

1. **Offline capability**: Even with dependencies served locally (levels 3 and 4), the app still depends on the PyScript CDN for the runtime. Serving the runtime locally enables complete offline operation.

2. **PWA/ServiceWorker**: Same-origin runtime assets are required for ServiceWorker caching. Cross-origin CDN resources cannot be cached by a ServiceWorker in many configurations.

3. **Air-gapped environments**: Intranet deployments or environments without internet access need all assets served locally, including the runtime.

4. **Privacy/compliance**: No external requests for the JavaScript runtime means no CDN tracking.

## Known Issues Addressed

None (new capability).

## Non-goals

- This does not change the default build mode (CDN mode remains default).
- This does not implement ServiceWorker registration or PWA manifest generation — those are future enhancements.
- This does not implement split/detached wheel mode — that is `feat-split-mode`.

## Dependencies

- **Requires** `feat-dependency-bundling` — the lock file and single-bundle wheel are prerequisites.
- **Benefits from** `feat-deps-local-serving` — pure-Python packages served locally.
- **Benefits from** `feat-wasm-local-serving` — WASM packages served locally.
- These three changes together enable **complete offline operation**.

## Layered Architecture

```
Level 1: feat-dependency-bundling (current)
  WASM ─────────── CDN (loaded by package name)
  Pure-Py ────────── Bundled (local install required)
  PyScript/Pyodide ─ CDN

Level 2: feat-split-mode
  Wheel split (framework/app/dependencies)
  Cache efficiency improvement

Level 3: feat-deps-local-serving
  WASM ─────────── CDN
  Pure-Py ────────── Same-origin serving (downloaded from Pyodide CDN)
  PyScript/Pyodide ─ CDN

Level 4: feat-wasm-local-serving
  WASM ─────────── Same-origin serving (downloaded from Pyodide CDN)
  Pure-Py ────────── Same-origin serving
  PyScript/Pyodide ─ CDN

Level 5: feat-pyscript-local-serving (this change)
  WASM ─────────── Same-origin serving
  Pure-Py ────────── Same-origin serving
  PyScript/Pyodide ─ Same-origin serving ★
  → Complete offline operation possible
```

## Design

### Overview

```
DEFAULT MODE (no local serving):
  PyScript CDN ────── core.js, core.css
  Pyodide CDN ─────── numpy (WASM only — pure-Py packages bundled)
  WebComPy server ─── single bundled wheel

PYSRIPT LOCAL SERVING (this change):
  WebComPy server ─── core.js, core.css, pyodide.mjs, pyodide.asm.wasm,
                        pyodide.asm.js, python_stdlib.zip, pyodide-lock.json
                       (ALL runtime assets from same origin)
```

### Implementation Sketch

- `GenerateConfig` and `ServerConfig` gain a `standalone: bool = False` field.
- When `standalone=True`:
  1. PyScript `core.js`, `core.css` are downloaded at build time and served locally.
  2. Pyodide `pyodide.mjs`, `pyodide.asm.wasm`, `pyodide.asm.js`, `python_stdlib.zip` are downloaded and served locally.
  3. `pyodide-lock.json` is served locally (so micropip resolves against it).
  4. Generated HTML references all runtime assets via same-origin URLs.
  5. `py-config` `lockFileURL` is pointed at the local `pyodide-lock.json`.

### Download Strategy

At build time, `webcompy generate --standalone` (or equivalent) downloads all required runtime assets from CDN and places them in `dist/_webcompy-assets/`:

```
dist/
├── _webcompy-assets/
│   ├── core.js
│   ├── core.css
│   ├── pyodide.mjs
│   ├── pyodide.asm.wasm
│   ├── pyodide.asm.js
│   ├── pyodide-lock.json
│   └── python_stdlib.zip
├── _webcompy-app-package/
│   └── myapp-py3-none-any.whl
├── index.html
└── ...
```

(When combined with `feat-deps-local-serving` and `feat-wasm-local-serving`, the `_webcompy-assets/packages/` directory is also populated.)

### PWA Extension (Future)

A subsequent change could add:
- `GenerateConfig.service_worker = True` to generate a ServiceWorker script.
- `GenerateConfig.manifest = {...}` to generate a PWA manifest.
- Offline caching strategies for same-origin assets.

These are explicitly out of scope for this change but this change is a prerequisite.

## Specs Affected

- `cli` — add `standalone` flag, runtime asset download logic
- `app-config` — add `standalone` to `GenerateConfig` and `ServerConfig`
- `lockfile` — add `standalone_assets` lock file section