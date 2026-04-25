# Proposal: Deps Local Serving — Same-Origin Pure-Python Package Serving

## Summary

Download pure-Python dependency wheels from the Pyodide CDN at build time and serve them from the same origin as the WebComPy application. This eliminates the need for build-environment installation of pure-Python packages and enables complete transitive dependency resolution using the Pyodide lock.

## Motivation

1. **Build environment independence**: In `feat-dependency-bundling`, pure-Python packages must be installed locally (`pip install httpx`) for bundling. This change allows downloading wheels from the Pyodide CDN instead, removing the local-installation requirement.

2. **Complete transitive resolution**: The Pyodide lock's `depends` field and wheel metadata enable resolving the full dependency tree without local installation, fixing the limitation where missing transitive dependencies cause build errors.

3. **Reproducibility**: Downloading specific Pyodide-validated wheel versions ensures the exact same packages work in the browser as tested by Pyodide.

## Known Issues Addressed

- Fixes the limitation where pure-Python packages must be installed locally before building.

## Non-goals

- This does not change WASM package handling (that is `feat-wasm-local-serving`).
- This does not implement split/detached wheel mode (that is `feat-split-mode`).
- This does not download the PyScript/Pyodide runtime (that is `feat-pyscript-local-serving`).

## Dependencies

- **Requires** `feat-dependency-bundling` — the lock file and dependency classification are prerequisites.

## Layered Architecture

```
Level 1: feat-dependency-bundling (prerequisite)
  Pure-Py ──────── Bundled (local install required)
  WASM ──────── CDN
  PyScript ────── CDN

Level 3: feat-deps-local-serving (this change)
  Pure-Py ──────── Same-origin delivery (downloaded from Pyodide CDN)
                   Bundled or detached wheels
  WASM ──────── CDN (unchanged)
  PyScript ────── CDN (unchanged)
```

## Design

### Two Delivery Modes for Pure-Python Packages

When pure-Python packages are downloaded from the Pyodide CDN, they can be delivered in two ways:

**Option A: Bundled (default)** — Downloaded wheels are extracted and bundled into the single app wheel, just like locally-installed packages. No change to `packages` in HTML.

**Option B: Separate wheels (requires `feat-split-mode`)** — Downloaded wheels are served as separate files. Requires the split-mode mechanism for multiple wheels.

This change initially implements Option A only, since Option B depends on `feat-split-mode`.

### Transitive Resolution via Pyodide Lock

The `depends` field in `pyodide-lock.json` entries lists immediate dependencies. For pure-Python packages in the Pyodide CDN, transitive dependencies are resolved by recursively walking the `depends` field:

```
AppConfig.dependencies = ["httpx"]
    │
    ▼
httpx (pyodide_cdn, is_wasm=False)
  depends: ["httpcore", "sniffio", "h2"]
    │
    ├── httpcore (pyodide_cdn, is_wasm=False)
    │     depends: ["hpack"]
    │       └── hpack (pyodide_cdn, is_wasm=False) → bundle
    ├── sniffio (not in Pyodide lock) → download or error
    └── h2 (pyodide_cdn, is_wasm=False)
          depends: ["hpack", "hyperframe"]
            ├── hpack → already resolved
            └── hyperframe (pyodide_cdn, is_wasm=False) → bundle

Result: httpx, httpcore, h2, hpack, hyperframe → bundled
        sniffio → error (not in Pyodide lock, not installed locally)
```

### Configuration

```python
@dataclass
class AppConfig:
    ...
    deps_serving: Literal["bundled", "local-cdn"] = "bundled"
```

When `deps_serving="local-cdn"`:
- Pure-Python packages are downloaded from the Pyodide CDN and extracted into the app wheel.
- Transitive dependencies are resolved via the Pyodide lock `depends` field.
- Missing dependencies (not in lock, not installed locally) cause a build error.

### Lock File Changes

The lock file gains a `deps_serving` field and downloads section:

```jsonc
{
  "version": 1,
  "pyodide_version": "0.29.3",
  "pyscript_version": "2026.3.1",
  "deps_serving": "local-cdn",
  "pyodide_packages": { ... },
  "bundled_packages": { ... },
  "downloaded_packages": {
    "httpx": {
      "url": "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/httpx-0.28.1-py3-none-any.whl",
      "sha256": "...",
      "source": "explicit"
    }
  }
}
```

## Specs Affected

- `app-config` — add `deps_serving` field
- `cli` — download logic, wheel extraction
- `lockfile` — add `downloaded_packages` section
- `dependency-resolver` — add Pyodide lock-based transitive resolution