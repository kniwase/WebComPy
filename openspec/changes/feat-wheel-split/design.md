# Design: Wheel Split — Browser-Only Wheel, Dependency Resolution, Lock File, and Browser Cache Strategy

## Design Decisions

### D1: Two separate wheels instead of one bundled wheel
The current single bundled wheel (framework + app) is split into:
- **WebComPy framework wheel** (browser-only, excludes `cli/`)
- **Application wheel** (app code + bundled pure-Python dependencies not in Pyodide CDN)

This allows the framework wheel to be cached independently across app updates.

### D2: Browser-only wheel excludes `cli/` directory
The `webcompy/cli/` subtree contains server-only tools (server, generate, init, wheel builder, argparser). It is never used in the browser but adds ~size to the bundled wheel. The new `make_browser_webcompy_wheel()` excludes this directory.

### D3: Dependency classification uses Pyodide lock as primary source
Dependencies listed in `AppConfig.dependencies` are classified by consulting `pyodide-lock.json` first:
1. **In Pyodide lock** → `pyodide_cdn` (listed by name in `py-config.packages`, Pyodide CDN provides the wheel)
2. **Not in Pyodide lock** → resolved locally:
   - Pure Python (no `.so`/`.pyd` files) → `bundled` (included in app wheel)
   - C extension → `error` (not usable in browser, user is notified)

This avoids the `importlib.util.find_spec()` heuristic alone, which misclassifies `numpy` as pure Python. The Pyodide lock file is fetched from `https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json` and cached locally at `~/.cache/webcompy/pyodide-lock-{version}.json`.

The Pyodide version is derived from the PyScript version via a mapping:
```
PYSCRIPT_TO_PYODIDE = {"2026.3.1": "0.29.3"}
```

### D4: Transitive dependency resolution via importlib.metadata
Packages not in the Pyodide CDN need their transitive dependencies resolved. `importlib.metadata` is used to walk `Requires-Dist` metadata recursively. Each transitive dependency is then classified using the same logic (Pyodide lock → local .so check).

The `source` field in the lock file distinguishes user-specified (`explicit`) from auto-resolved (`transitive`) dependencies, enabling clean updates when the user removes a dependency.

### D5: `webcompy-lock.json` ensures reproducibility and offline capability
A lock file at the project root (next to `webcompy_config.py`) records:
- Pyodide version and package versions from CDN
- Bundled package names, versions, and sources (explicit/transitive)
- Whether each bundled package is pure Python

The lock file is version-controlled (like `uv.lock` or `poetry.lock`). It is auto-generated on `webcompy start` and `webcompy generate` if missing or stale, and can be explicitly generated/updated via `webcompy lock`.

### D6: Stable wheel URLs enable HTTP caching
Wheel URLs no longer include version suffixes:
- Framework: `/_webcompy-app-package/webcompy-py3-none-any.whl`
- Application: `/_webcompy-app-package/{app_name}-py3-none-any.whl`

Cache headers:
| Wheel | Dev Server | Production (SSG) | Rationale |
|-------|-----------|-------------------|-----------|
| Framework | `max-age=86400, must-revalidate` | ETag by hosting | Changes infrequently |
| App (dev) | `no-cache` | N/A | Changes frequently |
| App (SSG) | N/A | ETag by hosting | Changes on deploy |

### D7: `AppConfig.version` is optional, for METADATA only
The `version` field in `AppConfig` is an optional string. If unset, `generate_app_version()` provides a timestamp-based fallback. The version is used in wheel METADATA only, not in URLs.

### D8: Standalone build mode is a future extension
The current design supports a single-server mode where PyScript/Pyodide assets are loaded from CDN. A future `standalone` mode will serve all assets from the same origin, enabling PWA/offline support. The lock file schema includes a `standalone_assets` placeholder for this.

## Architecture

### Build Pipeline

```
CURRENT:
════════════════════════════════════════════════════════════════════
  webcompy/ + app_package/ ──→ single wheel ──→ served at timestamp URL

PROPOSED:
════════════════════════════════════════════════════════════════════
  webcompy/ (excl. cli/)  ──→ framework wheel ──→ stable URL
  app_package/ + bundled/  ──→ app wheel       ──→ stable URL
  Pyodide CDN packages    ──→ py-config.packages (by name)

  webcompy-lock.json  ──→ classification cache ──→ reproducible builds
```

### Dependency Classification Flow

```
AppConfig.dependencies = ["flask", "numpy"]
        │
        ▼
  ┌─ webcompy-lock.json exists? ─┐
  │                               │
  YES                             NO
  │                               │
  ▼                               ▼
  Validate against             Fetch pyodide-lock.json
  current dependencies          from CDN (with cache)
  │                               │
  ├─ valid ──→ use lock          ▼
  │                          Classify each dependency:
  └─ stale ──→ regenerate    ┌────────────────────────────┐
                             │                            │
                        In Pyodide lock?                 Not in lock
                             │                            │
                        pyodide_cdn                importlib.util.find_spec()
                        (micropip installs         │                │
                         from CDN)            .so/.pyd found    Pure Python
                                                │                │
                                             ERROR             bundled
                                            (notify user)     (app wheel)
                                                    │
                                              Resolve transitive deps
                                              via importlib.metadata
                                              (classify each the same way)

                                            ┌─── In Pyodide lock ──→ pyodide_cdn
                                            ├─── Pure Python ──────→ bundled (transitive)
                                            └─── C extension ──────→ ERROR
```

### PyScript Config (Current vs Proposed)

```json
// CURRENT
{
  "packages": [
    "numpy",
    "matplotlib",
    "/_webcompy-app-package/myapp-25.107.43200-py3-none-any.whl"
  ]
}

// PROPOSED
{
  "packages": [
    "/_webcompy-app-package/webcompy-py3-none-any.whl",
    "/_webcompy-app-package/myapp-py3-none-any.whl",
    "numpy",
    "matplotlib"
  ]
}
```

### `make_browser_webcompy_wheel()`

```python
_BROWSER_ONLY_EXCLUDE = {"cli"}

def make_browser_webcompy_wheel(
    webcompy_package_dir: pathlib.Path,
    dest: pathlib.Path,
    version: str,
) -> pathlib.Path:
    pass
```

### `make_webcompy_app_package()` update

```python
def make_webcompy_app_package(
    dest: pathlib.Path,
    package_dir: pathlib.Path,
    app_version: str,
    assets: dict[str, str] | None = None,
    bundled_deps: list[tuple[str, pathlib.Path]] | None = None,
) -> pathlib.Path:
    pass
```

### `webcompy-lock.json` Schema

```jsonc
{
  "version": 1,
  "pyodide_version": "0.29.3",
  "pyscript_version": "2026.3.1",
  "pyodide_packages": {
    "numpy": {
      "version": "2.2.5",
      "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl"
    },
    "httpx": {
      "version": "0.28.1",
      "file_name": "httpx-0.28.1-py3-none-any.whl"
    }
  },
  "bundled_packages": {
    "flask": {
      "version": "3.1.0",
      "source": "explicit",
      "is_pure_python": true
    },
    "click": {
      "version": "8.2.1",
      "source": "transitive",
      "is_pure_python": true
    }
  }
}
```

### Dev Server Route Updates

```python
def create_asgi_app(app, server_config=None):
    lockfile = resolve_lockfile(app.config)
    classified = classify_from_lockfile(lockfile)

    webcompy_wheel = make_browser_webcompy_wheel(...)
    app_wheel = make_webcompy_app_package(
        ...,
        bundled_deps=[(name, path) for name, (ver, path) in classified.bundled.items()],
    )

    app_package_files = {
        "webcompy-py3-none-any.whl": (webcompy_wheel_bytes, "application/zip"),
        f"{_normalize_name(app_name)}-py3-none-any.whl": (app_wheel_bytes, "application/zip"),
    }

    # Cache headers per wheel type
```

### SSG Updates

```python
def generate_static_site(app, generate_config=None):
    lockfile = resolve_lockfile(app.config)
    classified = classify_from_lockfile(lockfile)

    webcompy_wheel = make_browser_webcompy_wheel(...)
    app_wheel = make_webcompy_app_package(...)

    dist = pathlib.Path(generate_config.dist)
    pkg_dir = dist / "_webcompy-app-package"
    shutil.copy2(webcompy_wheel, pkg_dir / "webcompy-py3-none-any.whl")
    shutil.copy2(app_wheel, pkg_dir / f"{_normalize_name(app_name)}-py3-none-any.whl")
```

### HTML Generation Updates

```python
def generate_html(app, dev_mode, prerender, app_version, app_package_name,
                  pyodide_package_names=None):
    wheel_urls = [
        f"{app.config.base_url}_webcompy-app-package/webcompy-py3-none-any.whl",
        f"{app.config.base_url}_webcompy-app-package/{_normalize_name(app_package_name)}-py3-none-any.whl",
    ]
    py_packages = [
        *wheel_urls,
        *(pyodide_package_names or []),
    ]
```

## Dependency Resolution Implementation

### `_pyodide_lock.py`

```python
PYODIDE_LOCK_URL_TEMPLATE = (
    "https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json"
)
CACHE_DIR = pathlib.Path.home() / ".cache" / "webcompy"

PYSCRIPT_TO_PYODIDE = {
    "2026.3.1": "0.29.3",
}

def fetch_pyodide_lock(pyodide_version: str) -> dict: ...
def get_pyodide_version(pyscript_version: str) -> str: ...
```

### `_dependency_resolver.py`

```python
@dataclass
class ClassifiedDependency:
    name: str
    version: str
    source: Literal["pyodide_cdn", "explicit", "transitive"]
    is_pure_python: bool
    pkg_dir: pathlib.Path | None

def classify_dependencies(
    dependencies: list[str],
    pyodide_lock: dict,
) -> tuple[list[ClassifiedDependency], list[str]]: ...

def _resolve_transitive_deps(package_name: str) -> list[str]: ...
def _is_pure_python_package(pkg_dir: pathlib.Path) -> bool: ...
def _find_package_dir(package_name: str) -> pathlib.Path | None: ...
```

### `_lockfile.py`

```python
LOCKFILE_VERSION = 1
LOCKFILE_NAME = "webcompy-lock.json"

@dataclass
class Lockfile:
    pyodide_version: str
    pyscript_version: str
    pyodide_packages: dict[str, PyodidePackageEntry]
    bundled_packages: dict[str, BundledPackageEntry]

def load_lockfile(path: pathlib.Path) -> Lockfile | None: ...
def save_lockfile(lockfile: Lockfile, path: pathlib.Path) -> None: ...
def generate_lockfile(dependencies, pyscript_version, pyodide_version=None) -> tuple[Lockfile, list[str]]: ...
def validate_lockfile(lockfile, dependencies) -> list[str]: ...
```

## Browser Cache Headers

| Wheel | Dev Server Cache-Control | SSG/Production | Rationale |
|-------|-------------------------|---------------|-----------|
| Framework | `max-age=86400, must-revalidate` | ETag by hosting | Changes infrequently |
| App (dev) | `no-cache` | N/A | Changes frequently during development |
| App (SSG) | N/A | ETag by hosting | Changes only on deploy |

## Version Handling

- `AppConfig.version: str | None = None` (optional)
- If `version` is set, it becomes the wheel METADATA version
- The wheel URL is always stable (no version suffix)
- `generate_app_version()` is the fallback when `version` is `None`
- Version is used only in METADATA and for lock file records

## Hot Reload Fix (Incidental)

The current dev server builds the wheel once at startup and caches HTML in hash mode. With stable URLs, the wheel filename no longer changes between restarts, fixing the stale-URL bug in hash mode. The app wheel content changes on restart, and `Cache-Control: no-cache` ensures the browser revalidates.

## Standalone Mode (Future Extension)

The lock file schema includes `standalone_assets` as a placeholder. A future `feat-standalone-build` change will:
- Download PyScript/Pyodide assets at build time
- Serve all assets from the same origin
- Add `GenerateConfig.standalone` flag
- Enable PWA/ServiceWorker configuration

This is out of scope for the current change but the schema is designed to accommodate it.

## Specs to Update

- `openspec/specs/app-config/spec.md` — add `version` field requirement (already in delta)
- `openspec/specs/cli/spec.md` — update for two-wheel serving, lock file CLI, cache headers
- `openspec/specs/wheel-builder/spec.md` — add `make_browser_webcompy_wheel()`, `bundled_deps`
- `openspec/specs/lockfile/spec.md` — new spec for lock file
- `openspec/specs/dependency-resolver/spec.md` — new spec for dependency classification

## Non-goals

- Standalone/PWA build mode (future `feat-standalone-build`)
- Service Worker caching strategy (future)
- CDN hosting of wheels (same-origin only)
- C extension package bundling (Pyodide provides these)
- `py-config` format changes beyond `packages` list