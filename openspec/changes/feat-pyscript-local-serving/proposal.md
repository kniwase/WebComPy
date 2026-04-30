# Proposal: PyScript Local Serving — Same-Origin PyScript/Pyodide Runtime for Offline PWA Support

## Summary

Download and serve the PyScript runtime (core.js, core.css) and Pyodide engine (pyodide.mjs, pyodide.asm.wasm, python_stdlib.zip, pyodide-lock.json) from the same origin as the WebComPy application. When `runtime_serving="local"`, the generated HTML uses local asset paths and configures `py-config` with `interpreter` and `lockFileURL` pointing to same-origin URLs. This is the highest level of local serving, enabling complete offline PWA support when combined with the dependency and WASM local serving changes.

## Motivation

1. **Offline capability**: Even with dependencies served locally (feat-deps-local-serving and feat-wasm-local-serving), the app still depends on the PyScript CDN for the runtime. Serving the runtime locally enables complete offline operation.

2. **PWA/ServiceWorker**: Same-origin runtime assets are required for ServiceWorker caching. Cross-origin CDN resources cannot be cached by a ServiceWorker in many configurations.

3. **Air-gapped environments**: Intranet deployments or environments without internet access need all assets served locally, including the runtime.

4. **Privacy/compliance**: No external requests for the JavaScript runtime means no CDN tracking.

## Known Issues Addressed

None (new capability).

## Non-goals

- This does not change the default build mode (CDN mode remains default).
- This does not implement ServiceWorker registration or PWA manifest generation — those are future enhancements.
- This does not implement split/detached wheel mode — that is `feat-split-mode`.
- This does not handle WASM package serving — that is `feat-wasm-local-serving`.
- This does not handle pure-Python dependency download/bundling — that is `feat-deps-local-serving` (already implemented).

## Dependencies

- **Requires** `feat-deps-local-serving` (implemented) — the lock file v2 and download infrastructure are prerequisites.
- **Benefits from** `feat-wasm-local-serving` — when both are enabled, `lockFileURL` points to a local file instead of a CDN URL.
- **Orchestrated by** `feat-standalone` — `standalone=True` enables this change along with `feat-wasm-local-serving`.

## Layered Architecture

```
Level 1: feat-dependency-bundling (implemented)
  WASM ──────────── CDN (loaded by package name)
  Pure-Py ────────── Bundled (local install required)
  PyScript/Pyodide ─ CDN

Level 2: feat-deps-local-serving (implemented)
  Pure-Py CDN ────── Downloaded from Pyodide CDN → bundled into app wheel
  WASM ──────────── CDN
  PyScript/Pyodide ─ CDN

Level 3: feat-wasm-local-serving
  WASM ──────────── Downloaded from CDN → same-origin serving
  Pure-Py ────────── (unchanged from Level 2)
  PyScript/Pyodide ─ CDN
  lockFileURL ────── Pyodide CDN URL

Level 4: feat-pyscript-local-serving (this change)
  WASM ──────────── Same-origin serving (when feat-wasm-local-serving enabled)
  Pure-Py ────────── (unchanged from Level 2)
  PyScript/Pyodide ─ Same-origin serving ★
  lockFileURL ────── Local URL (pyodide-lock.json served locally)
  → Complete offline operation possible (with feat-wasm-local-serving)

Level 5: feat-standalone
  Everything served from same origin
  → Single config option for complete offline
```

### Configuration

```python
@dataclass
class AppConfig:
    ...
    runtime_serving: Literal["cdn", "local"] | None = None
```

`runtime_serving` uses `None` as a sentinel to distinguish "not explicitly set" from `"cdn"` (the effective default). This enables `feat-standalone` to detect whether the developer explicitly chose a value. The effective value is resolved as:
- `None` → `"cdn"` (effective default)
- `"cdn"` → `"cdn"` (explicitly chosen CDN)
- `"local"` → `"local"` (explicitly chosen local)

## Design

### Overview

```
DEFAULT MODE (runtime_serving="cdn"):
  PyScript CDN ────── core.js, core.css
  Pyodide CDN ─────── pyodide.mjs, .wasm, .js, python_stdlib.zip
  WebComPy server ─── single bundled wheel
  py-config: { packages: [...], experimental_create_proxy: "auto" }

RUNTIME LOCAL SERVING (runtime_serving="local"):
  WebComPy server ─── core.js, core.css
                       pyodide.mjs, pyodide.asm.wasm, pyodide.asm.js
                       python_stdlib.zip, pyodide-lock.json
  py-config: {
    interpreter: "/_webcompy-assets/pyodide/pyodide.mjs",
    lockFileURL: "/_webcompy-assets/pyodide/pyodide-lock.json",
    packages: [...],
    experimental_create_proxy: "auto"
  }
```

### py-config Changes

When `runtime_serving="local"`, the generated `py-config` gains two new fields:

- **`interpreter`**: Points to the local Pyodide entry point: `/_webcompy-assets/pyodide/pyodide.mjs`. This is the official PyScript mechanism for specifying a local Pyodide installation (see PyScript offline documentation).

- **`lockFileURL`**: Points to the local Pyodide lock file: `/_webcompy-assets/pyodide/pyodide-lock.json`. This is required for Pyodide to resolve package dependencies against the locally-served runtime.

When `runtime_serving="local"` and `wasm_serving="cdn"` (only runtime is local), `lockFileURL` still points to the local `pyodide-lock.json` because the runtime files are served locally.

When `runtime_serving="cdn"` but `wasm_serving="local"`, `lockFileURL` points to the CDN `pyodide-lock.json` (handled by `feat-wasm-local-serving`).

### Download Strategy

At build time, the CLI downloads all required runtime assets from CDN and places them in `_webcompy-assets/pyodide/`:

```
dist/
├── _webcompy-assets/
│   ├── core.js
│   ├── core.css
│   └── pyodide/
│       ├── pyodide.mjs
│       ├── pyodide.asm.wasm
│       ├── pyodide.asm.js
│       ├── python_stdlib.zip
│       └── pyodide-lock.json
├── _webcompy-app-package/
│   └── myapp-py3-none-any.whl
└── index.html
```

PyScript assets are downloaded from `https://pyscript.net/releases/{version}/`.
Pyodide runtime assets are downloaded from `https://cdn.jsdelivr.net/pyodide/v{version}/full/`.

(When combined with `feat-wasm-local-serving`, the `_webcompy-assets/packages/` directory is also populated.)

### PWA Extension (Future)

A subsequent change could add:
- `AppConfig.service_worker = True` to generate a ServiceWorker script.
- `AppConfig.manifest = {...}` to generate a PWA manifest.
- Offline caching strategies for same-origin assets.

These are explicitly out of scope for this change but this change is a prerequisite.

## Specs Affected

- `app-config` — add `runtime_serving` to `AppConfig`
- `cli` — add `--runtime-serving` CLI flag, runtime asset download logic, `interpreter`/`lockFileURL` in py-config
- `lockfile` — add `runtime_serving` field and `runtime_assets` section