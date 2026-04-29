# Proposal: Deps Local Serving — Same-Origin Pure-Python Package Serving

## Summary

Add a `serve_all_deps` configuration option that controls how pure-Python packages available in the Pyodide CDN are delivered to the browser. When `True` (default), all such packages are downloaded from the Pyodide CDN at build time and bundled into the app wheel, served from the same origin. When `False`, they are loaded from the Pyodide CDN by name via `py-config.packages`. This change also fixes the existing bug where pure-Python Pyodide CDN packages are neither bundled nor loaded from the CDN, making them unavailable in the browser.

## Motivation

1. **Same-origin serving**: Bundling pure-Python packages into the app wheel enables same-origin delivery, which is a prerequisite for offline PWA support and ServiceWorker caching. Even without full offline support, same-origin delivery eliminates external CDN requests during app initialization.

2. **Complete transitive resolution without local installation**: When `serve_all_deps=True`, the Pyodide CDN provides wheel files and dependency metadata, enabling full transitive dependency resolution without requiring packages to be installed locally. This eliminates the build-environment limitation of `feat-dependency-bundling`.

3. **Bug fix**: Pure-Python packages available in the Pyodide CDN (e.g., `httpx`) are currently classified as `pyodide_cdn` but never bundled into the app wheel and never added to `py-config.packages`. This means they are completely unavailable in the browser. This change fixes this by either bundling them (`serve_all_deps=True`) or loading them from the CDN (`serve_all_deps=False`).

4. **Reproducibility**: Downloading specific Pyodide-validated wheel versions ensures the exact same packages work in the browser as tested by Pyodide.

## Known Issues Addressed

- Fixes the bug where pure-Python Pyodide CDN packages are neither bundled nor loaded from the CDN, making them unavailable in the browser.
- Fixes the limitation where pure-Python packages must be installed locally before building (when `serve_all_deps=True`).

## Non-goals

- This does not change WASM package handling (that is `feat-wasm-local-serving`).
- This does not download the PyScript/Pyodide runtime (that is `feat-pyscript-local-serving`).
- This does not implement split/detached wheel mode (that is `feat-split-mode`).
- This does not implement ServiceWorker or PWA manifest generation.
- This does not guarantee transitive dependency resolution for packages not in the Pyodide CDN and not installed locally (best-effort only).

## Dependencies

- **Requires** `feat-dependency-bundling` — the lock file and dependency classification are prerequisites.

## Design

### `AppConfig.serve_all_deps` Controls Delivery Mode

```python
@dataclass
class AppConfig:
    serve_all_deps: bool = True
```

When `serve_all_deps=True` (default):
- Pure-Python packages in the Pyodide CDN are downloaded from the CDN and bundled into the app wheel
- Pure-Python packages NOT in the Pyodide CDN are bundled from local installation
- Only WASM packages are loaded from the Pyodide CDN by name

When `serve_all_deps=False`:
- Pure-Python packages in the Pyodide CDN are loaded from the CDN by name via `py-config.packages`
- Pure-Python packages NOT in the Pyodide CDN are bundled from local installation
- WASM packages are loaded from the Pyodide CDN by name

### Transitive Resolution via Pyodide Lock

The `depends` field in `pyodide-lock.json` entries lists immediate dependencies. Transitive dependencies are resolved by recursively walking the `depends` field:

```
AppConfig.dependencies = ["httpx"]
    |
    v
httpx (in_pyodide_cdn=True, is_wasm=False)
  depends: ["httpcore", "certifi", "h2"]
    |
    +-- httpcore (in_pyodide_cdn=True) -> resolved
    +-- certifi (in_pyodide_cdn=True) -> resolved
    +-- h2 (in_pyodide_cdn=True, hypothetical; actual availability depends on Pyodide version)
          depends: ["hpack", "hyperframe"]
            +-- hpack (in_pyodide_cdn=True) -> resolved
            +-- hyperframe (in_pyodide_cdn=True) -> resolved

Result: httpx, httpcore, certifi, h2, hpack, hyperframe -> CDN-downloaded (serve_all_deps=True) or CDN-loaded (False)
```

For packages not in the Pyodide CDN, local `importlib.metadata` is used as a best-effort fallback for discovering transitive dependencies. If resolution fails, a warning is reported and the developer must list the dependency explicitly.

### Lock File v2

The lock file schema is redesigned to cleanly separate WASM and pure-Python packages:

```jsonc
{
  "version": 2,
  "pyodide_version": "0.29.3",
  "pyscript_version": "2026.3.1",
  "wasm_packages": {
    "numpy": {
      "version": "2.2.5",
      "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
      "source": "explicit"
    }
  },
  "pure_python_packages": {
    "httpx": {
      "version": "0.28.1",
      "source": "explicit",
      "in_pyodide_cdn": true,
      "pyodide_file_name": "httpx-0.28.1-py3-none-any.whl",
      "pyodide_sha256": "3123bf6c7e7623667b39d31f8b2bf4eac925b49ea79dfdf520560db2e1cf87a9"
    },
    "flask": {
      "version": "3.1.0",
      "source": "explicit",
      "in_pyodide_cdn": false
    }
  },
  "standalone_assets": {}
}
```

Version 1 lock files are not backwards-compatible and will be regenerated on next build.

### CLI Flag

```bash
python -m webcompy start --serve-all-deps     # True (default)
python -m webcompy start --no-serve-all-deps  # False
```

## Specs Affected

- `app-config` — add `serve_all_deps` field, update pure-Python CDN package requirements
- `cli` — download logic, wheel extraction, HTML generation updates, `--serve-all-deps` flag
- `lockfile` — v2 schema with `wasm_packages` and `pure_python_packages`
- `dependency-resolver` — simplified `ClassifiedDependency`, Pyodide CDN metadata propagation