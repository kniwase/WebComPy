# Proposal: Dependency Bundling — Dependency Resolution, Lock File, Stable URLs, and Browser Cache Strategy

## Summary

Introduce dependency classification using the Pyodide lock file to determine which packages are WASM (loaded from CDN) vs pure-Python (bundled locally). Pure-Python packages are always bundled into the app wheel and served from the WebComPy server, regardless of CDN availability. Generate a `webcompy-lock.json` file for reproducible builds. Use stable URLs and cache headers for browser caching. The webcompy framework (excluding `cli/`) remains bundled inside the single app wheel, avoiding PyScript initialization issues with multiple local wheel URLs.

## Motivation

1. **Unnecessary browser code**: `webcompy/cli/` is never used in the browser but is currently included in the bundle. Excluding it reduces wheel size.

2. **Pyodide package optimization**: WASM packages (like `numpy`, `matplotlib`) must come from the Pyodide CDN. Pure-Python packages available in the Pyodide CDN are still bundled locally to avoid CDN dependency and PyScript compatibility issues with multiple local wheel URLs.

3. **Browser cache**: Currently, app versions change every second (timestamp-based), defeating browser caching. Stable URLs with proper cache headers enable efficient caching.

4. **Reproducibility**: A lock file (`webcompy-lock.json`) records exact package versions and classification, ensuring consistent builds across environments.

## Known Issues Addressed

- Fixes the stale-wheel-URL bug in hash mode dev server (stable URLs eliminate the version-mismatch issue on hot reload).

## Non-goals

- Standalone/PWA build mode (serving PyScript/Pyodide from same origin) — future `feat-standalone-build`
- Service Worker caching strategy — future
- CDN hosting of wheels (same-origin only)
- C extension package bundling (Pyodide provides these)
- `use_cdn` option (pure-Python packages are always bundled locally)
- Lock file version sync with uv/poetry lock files — future enhancement

## Dependencies

- **Informed by** `feat/hydration-measurement` — profiling data will validate download/install time savings.

## Design

### Part 1: Dependency Classification

See design.md D3–D4. Dependencies are classified by consulting `pyodide-lock.json` first, then local package inspection. Pure-Python packages from the Pyodide CDN are always bundled. Only WASM packages are loaded from the CDN. Transitive dependencies are resolved via `importlib.metadata`.

### Part 2: Lock File

See design.md D5. A `webcompy-lock.json` file records all dependency classifications for reproducible builds.

### Part 3: Browser Cache Strategy

See design.md D6–D7. Stable URLs and `Cache-Control` headers.

### Part 4: Standalone Mode (Future)

See design.md D8. The lock file schema includes a `standalone_assets` placeholder for future PWA support.

## Specs Affected

- `app-config` — adds `version` field, removes `use_cdn`
- `cli` — updates dev server/SSG for lock file integration, cache headers
- `wheel-builder` — adds `bundled_deps`, stable URLs, cli exclusion
- `lockfile` — new spec
- `dependency-resolver` — new spec