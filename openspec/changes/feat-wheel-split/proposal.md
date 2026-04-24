# Proposal: Wheel Split — Browser-Only Framework Wheel, Dependency Resolution, Lock File, and Browser Cache Strategy

## Summary

Split the current single bundled wheel into a browser-only webcompy framework wheel (excluding `cli/`) and a separate application wheel (app code + bundled pure-Python dependencies). Introduce dependency classification using the Pyodide lock file to determine which packages come from the CDN vs. which are bundled locally. Generate a `webcompy-lock.json` file for reproducible builds. Use stable URLs and cache headers for browser caching.

## Motivation

1. **Download size and caching**: The entire webcompy framework is currently bundled inside every app wheel. Splitting allows the framework wheel to be cached independently across app updates.

2. **Unnecessary browser code**: `webcompy/cli/` is never used in the browser but is included in the bundle. Removing it reduces the framework wheel size.

3. **Pyodide package optimization**: Packages available in the Pyodide CDN (like `numpy`, `httpx`) should be served from the CDN rather than bundled. Only packages not in the CDN need bundling, reducing the app wheel size and installation calls.

4. **Browser cache**: Currently, app versions change every second (timestamp-based), defeating browser caching. Stable URLs with proper cache headers enable efficient caching.

5. **Reproducibility**: A lock file (`webcompy-lock.json`) records exact package versions and classification, ensuring consistent builds across environments.

## Known Issues Addressed

- Fixes the stale-wheel-URL bug in hash mode dev server (stable URLs eliminate the version-mismatch issue on hot reload).

## Non-goals

- Standalone/PWA build mode (serving PyScript/Pyodide from same origin) — future `feat-standalone-build`
- Service Worker caching strategy — future
- CDN hosting of wheels (same-origin only)
- C extension package bundling (Pyodide provides these)
- Lock file version sync with uv/poetry lock files — future enhancement

## Dependencies

- **Informed by** `feat/hydration-measurement` — profiling data will validate download/install time savings.

## Design

### Part 1: Browser-Only WebComPy Wheel

See design.md D1–D2. The framework wheel excludes `webcompy/cli/` and is served at a stable URL.

### Part 2: Dependency Classification

See design.md D3–D4. Dependencies are classified by consulting `pyodide-lock.json` first, then local package inspection. Transitive dependencies are resolved via `importlib.metadata`.

### Part 3: Lock File

See design.md D5. A `webcompy-lock.json` file records all dependency classifications for reproducible builds.

### Part 4: Browser Cache Strategy

See design.md D6–D7. Stable URLs and `Cache-Control` headers.

### Part 5: Standalone Mode (Future)

See design.md D8. The lock file schema includes a `standalone_assets` placeholder for future PWA support.

## Specs Affected

- `app-config` — adds `version` field
- `cli` — updates dev server/SSG for two-wheel serving, lock file CLI, cache headers
- `wheel-builder` — adds `make_browser_webcompy_wheel()`, `bundled_deps`, stable URLs
- `lockfile` — new spec
- `dependency-resolver` — new spec