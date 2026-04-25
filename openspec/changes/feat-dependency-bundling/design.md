# Design: Dependency Bundling — Dependency Resolution, Lock File, Stable URLs, and Browser Cache Strategy

## Design Decisions

### D1: Single bundled wheel (framework + app + dependencies)
The current single bundled wheel design is retained. The wheel contains the webcompy framework (excluding `cli/`), application code, and all pure-Python dependencies. WASM-only packages from the Pyodide CDN are loaded by name via `py-config.packages`. Pure-Python packages from the Pyodide CDN are also bundled and served locally — there is no `use_cdn` option.

This avoids the PyScript initialization timeout issue when passing multiple local wheel URLs in `packages`.

### D2: Browser-only wheel excludes `cli/` directory
The `webcompy/cli/` subtree (including `webcompy/cli/template_data/`) contains server-only tools (server, generate, init, wheel builder, argparser). It is never used in the browser. The `make_webcompy_app_package()` function excludes this directory by filtering the webcompy package source. Since `template_data` is under `cli/`, it is automatically excluded.

### D3: Dependency classification — pure-Python always bundled, WASM from CDN
Dependencies listed in `AppConfig.dependencies` are classified by consulting `pyodide-lock.json` first:
1. **WASM in Pyodide lock** → loaded by name from Pyodide CDN via `py-config.packages`
2. **Pure-Python in Pyodide lock** → `bundled` (included in app wheel, served locally)
3. **Not in Pyodide lock** → resolved locally:
   - Pure Python (no `.so`/`.pyd` files) → `bundled` (included in app wheel)
   - C extension → `error` (not usable in browser, user is notified)

There is no `use_cdn` option — pure-Python packages are always bundled locally to avoid CDN dependency and PyScript compatibility issues with local wheel URLs.

This avoids the `importlib.util.find_spec()` heuristic alone, which misclassifies `numpy` as pure Python. The Pyodide lock file is fetched from `https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json` and cached locally. The cache directory follows XDG conventions: `$XDG_CACHE_HOME/webcompy/` (defaulting to `~/.cache/webcompy/`).

The Pyodide version is derived from the PyScript version via a hardcoded mapping:
```
PYSCRIPT_TO_PYODIDE = {"2026.3.1": "0.29.3"}
```

**Tradeoff**: This mapping requires manual updates on every PyScript/Pyodide version bump. Unknown PyScript versions raise `ValueError`, prompting the developer to update the mapping. This is acceptable because WebComPy pins the PyScript version (`PYSCRIPT_VERSION = "2026.3.1"`) and updates are infrequent and deliberate.

### D4: Transitive dependency resolution — local + Pyodide lock hybrid

Transitive dependencies are resolved using a hybrid approach:

**Step 1: Pyodide lock `depends` field** — When a package is in the Pyodide lock, its `depends` list provides immediate transitive dependencies. These are walked recursively within the lock. Each dependency found in the lock is classified (WASM → CDN, pure-Python → bundled).

**Step 2: Local `importlib.metadata` fallback** — For dependencies not found in the Pyodide lock (or when the lock is unavailable), `importlib.metadata` is used to walk `Requires-Dist` metadata recursively from locally-installed packages.

**Limitation**: If a transitive dependency is not in the Pyodide lock AND not installed locally, the build reports an error. The developer must install it locally or add it to `AppConfig.dependencies`. Complete transitive resolution without local installation is a goal of the standalone build mode (`feat-standalone-build`), which will download wheels from the Pyodide CDN.

The `source` field in the lock file distinguishes user-specified (`explicit`) from auto-resolved (`transitive`) dependencies, enabling clean updates when the user removes a dependency.

### D5: `webcompy-lock.json` ensures reproducibility and offline capability
A lock file at the project root (next to `webcompy_config.py`) records:
- Pyodide version and package versions from CDN
- Bundled package names, versions, and sources (explicit/transitive)
- Whether each bundled package is pure Python

The lock file is version-controlled (like `uv.lock` or `poetry.lock`). It is auto-generated on `webcompy start` and `webcompy generate` if missing or stale, and can be explicitly generated/updated via `webcompy lock`.

### D6: Stable wheel URLs enable HTTP caching
The wheel URL no longer includes a version suffix:
- Application: `/_webcompy-app-package/{app_name}-py3-none-any.whl`

Cache headers:
| Wheel | Dev Server | Production (SSG) | Rationale |
|-------|-----------|-------------------|-----------|
| App (dev) | `no-cache` | N/A | Changes frequently |
| App (SSG) | N/A | ETag by hosting | Changes on deploy |

**Note**: With a single wheel, there is no separate framework wheel to cache independently. The stable URL ensures the browser can cache effectively with proper cache headers.

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
  webcompy/ (excl. cli/) + app_package/ + bundled/ ──→ single wheel ──→ stable URL
  WASM Pyodide CDN packages                    ──→ py-config.packages (by name)

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
                        ┌────┴─────┐                importlib.util.find_spec()
                        │          │                      │                │
                     is_wasm   is_pure_python        .so/.pyd found    Pure Python
                        │          │                      │                │
                   pyodide_cdn  bundled               ERROR             bundled
                   (CDN name    (app wheel)         (notify user)     (app wheel)
                    in packages)
                                                 Resolve transitive deps
                                                 via importlib.metadata
                                                 (classify each the same way)

                                               ┌─── is_wasm in lock ──→ pyodide_cdn (CDN)
                                               ├─── is_pure_python ──→ bundled (transitive)
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

// PROPOSED (single bundled wheel, pure-Python deps not in packages)
{
  "packages": [
    "/_webcompy-app-package/myapp-py3-none-any.whl",
    "numpy",
    "matplotlib"
  ]
}
```

Note: `numpy` and `matplotlib` remain in packages because they are WASM packages that cannot be bundled. Pure-Python packages from the Pyodide CDN (like `httpx`) would NOT appear in `packages` — they are bundled into the wheel instead.

### `make_webcompy_app_package()` update

The existing `make_webcompy_app_package()` continues to bundle webcompy (excluding cli/) with the app. The new `bundled_deps` parameter adds pure-Python dependency directories.

```python
def make_webcompy_app_package(
    dest: pathlib.Path,
    webcompy_package_dir: pathlib.Path,
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
    // WASM packages only — loaded from CDN via py-config.packages
    "numpy": {
      "version": "2.2.5",
      "file_name": "numpy-2.2.5-cp313-cp313-pyodide_2025_0_wasm32.whl",
      "is_wasm": true
    }
  },
  "bundled_packages": {
    // Pure-Python packages — bundled into the app wheel
    "flask": {
      "version": "3.1.0",
      "source": "explicit",
      "is_pure_python": true
    },
    "click": {
      "version": "8.2.1",
      "source": "transitive",
      "is_pure_python": true
    },
    // Pure-Python packages available in Pyodide CDN are also bundled
    "httpx": {
      "version": "0.28.1",
      "source": "explicit",
      "is_pure_python": true
    }
  }
}
```

Note: Pure-Python packages from the Pyodide CDN (like `httpx`) are listed in `bundled_packages`, not `pyodide_packages`. Only WASM packages go in `pyodide_packages`.

### Dev Server Route Updates

```python
def create_asgi_app(app, server_config=None):
    lockfile = resolve_lockfile(app.config)

    # get_bundled_deps now always bundles pure-Python Pyodide packages
    bundled_deps = get_bundled_deps(lockfile)
    pyodide_package_names = get_pyodide_package_names(lockfile)  # WASM only

    app_wheel = make_webcompy_app_package(
        ...,
        bundled_deps=bundled_deps or None,
    )

    app_package_files = {
        f"{_normalize_name(app_name)}-py3-none-any.whl": (app_wheel_bytes, "application/zip"),
    }
```

### SSG Updates

```python
def generate_static_site(app, generate_config=None):
    lockfile = resolve_lockfile(app.config)
    bundled_deps = get_bundled_deps(lockfile)
    pyodide_package_names = get_pyodide_package_names(lockfile)  # WASM only

    app_wheel = make_webcompy_app_package(..., bundled_deps=bundled_deps or None)

    dist = pathlib.Path(generate_config.dist)
    pkg_dir = dist / "_webcompy-app-package"
    # single wheel file
```

### HTML Generation Updates

```python
def generate_html(app, dev_mode, prerender, app_version, app_package_name,
                  pyodide_package_names=None):
    app_wheel_url = (
        f"{app.config.base_url}_webcompy-app-package/"
        f"{_normalize_name(app_package_name)}-py3-none-any.whl"
    )
    if pyodide_package_names is not None:
        py_packages = [
            app_wheel_url,
            *pyodide_package_names,  # WASM package names only
        ]
    else:
        py_packages = [
            *app.config.dependencies,
            app_wheel_url,
        ]
```

## Dependency Resolution Implementation

### `_pyodide_lock.py`

```python
PYODIDE_LOCK_URL_TEMPLATE = (
    "https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide-lock.json"
)
CACHE_DIR = pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "webcompy"

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
    source: Literal["pyodide_cdn", "fallback_cdn", "explicit", "transitive"]
    is_pure_python: bool
    is_wasm: bool
    pkg_dir: pathlib.Path | None
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
def generate_lockfile(dependencies, pyscript_version, pyodide_version=None) -> tuple[Lockfile, list[str], list[str]]: ...
def validate_lockfile(lockfile, dependencies) -> list[str]: ...
```

## Browser Cache Headers

| Wheel | Dev Server Cache-Control | SSG/Production | Rationale |
|-------|-------------------------|---------------|-----------|
| Framework | `max-age=86400, must-revalidate` | ETag by hosting | Changes infrequently |
| App (dev) | `no-cache` | N/A | Changes frequently during development |
| App (SSG) | N/A | ETag by hosting | Changes only on deploy |

**Note on SSG hosting**: The "ETag by hosting" column assumes the hosting provider (GitHub Pages, Cloudflare Pages, etc.) supports ETag/Last-Modified headers. Some static hosting providers do not set cache headers. For those, the stable URL design means the browser will at worst re-download the wheel on each visit (same as the current timestamp-based approach), but never fail with a 404.

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

- `openspec/specs/app-config/spec.md` — add `version` field, remove `use_cdn`
- `openspec/specs/cli/spec.md` — update for single-wheel serving, lock file CLI, cache headers
- `openspec/specs/wheel-builder/spec.md` — add `bundled_deps`, stable URLs, cli exclusion in bundling
- `openspec/specs/lockfile/spec.md` — new spec for lock file
- `openspec/specs/dependency-resolver/spec.md` — new spec for dependency classification

## Non-goals

- Standalone/PWA build mode (future `feat-standalone-build`)
- Service Worker caching strategy (future)
- CDN hosting of wheels (same-origin only)
- C extension package bundling (Pyodide provides these)
- `py-config` format changes beyond `packages` list