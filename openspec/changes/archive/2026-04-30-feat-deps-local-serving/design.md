# Design: Deps Local Serving — Same-Origin Pure-Python Package Serving

## Design Decisions

### D1: `serve_all_deps: bool = True` controls delivery mode
When `True` (default), all pure-Python packages that the WebComPy server can provide are served from the same origin — either bundled from local installation or downloaded from the Pyodide CDN and then bundled. When `False`, pure-Python packages available in the Pyodide CDN are loaded from the CDN by name via `py-config.packages`, and only packages not available from the CDN are bundled.

The field name emphasizes the intent (serving from the server) rather than the mechanism (bundling into a wheel). This accommodates future `feat-split-mode` where packages may be served as separate wheels without changing the configuration semantics.

### D2: Pure-Python Pyodide CDN packages are always classified as pure-Python, not as CDN packages
In the current code, packages found in the Pyodide lock are classified as `source="pyodide_cdn"` regardless of whether they are WASM or pure-Python. This conflates the Pyodide lock data source with the delivery mechanism. In the new design, `ClassifiedDependency` separates these concerns:
- `is_wasm: bool` — determines whether the package MUST come from the CDN (cannot be bundled)
- `in_pyodide_cdn: bool` — indicates the package exists in the Pyodide CDN (available for download or CDN loading)
- `source: Literal["explicit", "transitive"]` — whether the developer listed it or it was auto-discovered

The delivery mechanism is determined at build time by `serve_all_deps`, not at classification time.

### D3: Lock file v2 collapses `pyodide_packages` and `bundled_packages` into `wasm_packages` and `pure_python_packages`
The v1 schema placed pure-Python CDN packages in `pyodide_packages` (with `is_wasm=False`), which created ambiguity about whether they should be bundled or loaded from the CDN. The v2 schema cleanly separates:
- `wasm_packages` — WASM-only, always loaded from CDN by name
- `pure_python_packages` — all pure-Python packages, regardless of CDN availability

Each `pure_python_packages` entry includes `in_pyodide_cdn` (bool) and, when True, `pyodide_file_name` and `pyodide_sha256` for download. This allows the build system to decide at build time whether to download-and-bundle (`serve_all_deps=True`) or defer to CDN (`serve_all_deps=False`).

### D4: Pyodide CDN wheel download with SHA256 verification and caching
Downloaded wheels are cached at `~/.cache/webcompy/pyodide-packages/{pyodide_version}/{file_name}`. The download URL is constructed from the Pyodide CDN base URL plus `file_name`: `https://cdn.jsdelivr.net/pyodide/v{pyodide_version}/full/{file_name}`. Each download is verified against the SHA256 hash from `pyodide-lock.json` to ensure integrity.

WASM vs. pure-Python detection uses the `package_type` field from `pyodide-lock.json` when available (e.g., `"package_type": "shared_library"` indicates WASM), falling back to filename heuristics (`"pyodide" in file_name or "wasm32" in file_name`) for lock files that lack this field.

### D5: Downloaded wheels are extracted and passed to `make_webcompy_app_package()`
When `serve_all_deps=True`, CDN-available pure-Python packages are downloaded, verified, extracted to a temporary directory, and added to `bundled_deps` in `make_webcompy_app_package()`. This reuses the existing bundle pipeline — no changes to the wheel builder are needed.

### D6: Local installation validation is relaxed for CDN-available packages
When `serve_all_deps=True`, pure-Python packages with `in_pyodide_cdn=True` do not need to be installed locally for bundling. However, they may still be needed for SSR (server-side rendering), so a warning (not an error) is reported if they are missing locally. The `validate_local_environment()` function checks `in_pyodide_cdn` and `serve_all_deps` to determine whether a missing local package is an error or a warning.

### D7: Local `importlib.metadata` is a best-effort fallback for non-CDN transitive dependencies
For packages not in the Pyodide CDN (e.g., `flask`), transitive dependencies are discovered via `importlib.metadata.requires()` if the package is installed locally. If discovery fails (package not installed or metadata unavailable), a warning is reported and the developer must list the dependency explicitly. This does not require local installation — it only uses it when available.

### D8: Backward compatibility is not maintained for lock file v1
Since WebComPy is pre-release, v1 lock files are treated as invalid by `load_lockfile()` (returns `None`), triggering a full regeneration. No migration path is provided.

## Architecture

### Delivery Mode Comparison

```
serve_all_deps = True (default):
  Pure-Py in Pyodide CDN   -> CDN download -> extract -> bundle into app wheel
  Pure-Py NOT in CDN       -> local install -> bundle into app wheel
  WASM in Pyodide CDN      -> CDN by name (py-config.packages)
  PyScript/Pyodide runtime -> CDN (future: feat-pyscript-local-serving)

serve_all_deps = False:
  Pure-Py in Pyodide CDN   -> CDN by name (py-config.packages)
  Pure-Py NOT in CDN       -> local install -> bundle into app wheel
  WASM in Pyodide CDN      -> CDN by name (py-config.packages)
  PyScript/Pyodide runtime -> CDN
```

### Dependency Classification Flow (Revised)

```
AppConfig.dependencies = ["flask", "numpy", "httpx"]
        |
        v
  Fetch pyodide-lock.json (with cache)
        |
        v
  Classify each dependency:
  ┌───────────────────────────────────┐
  │ numpy: is_wasm=True               │ -> wasm_packages
  │ httpx: in_pyodide_cdn=True        │ -> pure_python_packages (with download info)
  │ flask: in_pyodide_cdn=False       │ -> pure_python_packages (requires local install)
  └───────────────────────────────────┘
        |
        v
  Resolve transitive dependencies:
  ┌───────────────────────────────────┐
  │ httpx depends -> httpcore, h2,   │
  │   certifi (via Pyodide lock)       │
  │ httpcore: in_pyodide_cdn=True    │ -> pure_python_packages
  │ h2: in_pyodide_cdn=True          │ -> pure_python_packages
  │ certifi: in_pyodide_cdn=True     │ -> pure_python_packages
  │                                   │
  │ flask: NOT in Pyodide lock,      │
  │   try importlib.metadata fallback │
  │   -> click, itsdangerous, jinja2 │
  │   click: NOT in lock, local found -> pure_python_packages
  │   itsdangerous: local fallback failed -> warning
  │   jinja2: in_pyodide_cdn=True     -> pure_python_packages
  └───────────────────────────────────┘
        |
        v
  Build:
  if serve_all_deps=True:
    Download CDN packages -> extract -> bundle
    Bundle local packages
    wasm_packages -> py-config.packages (names only)

  if serve_all_deps=False:
    CDN packages -> py-config.packages (names only)
    Bundle local-only packages
    wasm_packages -> py-config.packages (names only)
```

### `ClassifiedDependency` (Revised)

```python
@dataclass
class ClassifiedDependency:
    name: str
    version: str
    source: Literal["explicit", "transitive"]
    is_wasm: bool
    is_pure_python: bool
    in_pyodide_cdn: bool
    pyodide_file_name: str | None = None
    pyodide_sha256: str | None = None
    pkg_dir: pathlib.Path | None = None
```

The `is_bundled` and `is_cdn_package` properties are removed. Build-time code determines delivery based on `is_wasm`, `is_pure_python`, `in_pyodide_cdn`, and `serve_all_deps`.

### Lock File v2 Schema

```jsonc
{
  "version": 2,
  "pyodide_version": "0.29.3",
  "pyscript_version": "2026.3.1",
  "wasm_packages": {
    // WASM-only packages — always loaded from CDN via py-config.packages
    "numpy": {
      "version": "2.2.5",
      "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
      "source": "explicit"
    }
  },
  "pure_python_packages": {
    // All pure-Python packages
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
    },
    "click": {
      "version": "8.2.1",
      "source": "transitive",
      "in_pyodide_cdn": false
    }
  },
  "standalone_assets": {}
}
```

### Download and Cache

```
CACHE_DIR = ~/.cache/webcompy/pyodide-packages/{pyodide_version}/

Download flow:
  1. Check cache: {CACHE_DIR}/{file_name}
  2. If cached, verify SHA256
  3. If valid, use cached file
  4. If missing or invalid, download from:
     https://cdn.jsdelivr.net/pyodide/v{pyodide_version}/full/{file_name}
  5. Verify SHA256 after download
  6. Save to cache
  7. Extract .whl (ZIP) to temporary directory
  8. Add extracted directory to bundled_deps
```

### HTML Generation Changes

```python
# serve_all_deps = True:
wasm_names = get_wasm_package_names(lockfile)     # ["numpy", "matplotlib"]
py_packages = [app_wheel_url, *wasm_names]
# CDN-available pure-Python packages are bundled — NOT in py_packages

# serve_all_deps = False:
wasm_names = get_wasm_package_names(lockfile)     # ["numpy", "matplotlib"]
cdn_pp_names = get_cdn_pure_python_package_names(lockfile)  # ["httpx", "anyio"]
py_packages = [app_wheel_url, *wasm_names, *cdn_pp_names]
# Pure-Python CDN packages loaded from CDN by name
```

### `validate_local_environment` Behavior

| Package | `serve_all_deps=True` | `serve_all_deps=False` |
|---------|----------------------|------------------------|
| CDN-available pure-Python (`in_pyodide_cdn=true`) | Warning if missing (SSR may need it) | Warning if missing (CDN loads it in browser) |
| Local-only pure-Python (`in_pyodide_cdn=false`) | Error if missing (must bundle) | Error if missing (must bundle) |
| WASM | No check (CDN-loaded) | No check (CDN-loaded) |

## Specs to Update

- `app-config` — add `serve_all_deps` field
- `cli` — download logic, wheel extraction, HTML generation, `--serve-all-deps` flag
- `lockfile` — v2 schema with `wasm_packages` and `pure_python_packages`
- `dependency-resolver` — simplified `ClassifiedDependency`, Pyodide CDN metadata