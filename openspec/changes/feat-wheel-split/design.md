# Design: Wheel Split — Browser-Only Wheel, Dependency Bundling, and Browser Cache Strategy

## Design Decisions

### D1: Two separate wheels instead of one bundled wheel
The current single bundled wheel (framework + app) is split into:
- **WebComPy framework wheel** (browser-only, excludes `cli/`)
- **Application wheel** (app code + bundled pure-Python dependencies)

This allows the framework wheel to be cached independently across app updates.

### D2: Browser-only wheel excludes `cli/` directory
The `webcompy/cli/` subtree contains server-only tools (server, generate, init, wheel builder, argparser). It is never used in the browser but adds ~XXKB to the bundled wheel. The new `make_browser_webcompy_wheel()` excludes this directory.

### D3: Pure-Python dependencies are bundled into the app wheel
Instead of listing each pure-Python dependency in `py-config.packages` (triggering separate `micropip.install()` calls), their source files are included directly in the app wheel. Only C-extension packages (numpy, matplotlib, etc.) remain in `py-config.packages` as Pyodide built-ins.

### D4: Stable wheel URLs enable HTTP caching
Wheel filenames no longer include the timestamp-based version string. Instead, they use fixed URLs:
- `/_webcompy-app-package/webcompy-py3-none-any.whl`
- `/_webcompy-app-package/{app_name}-py3-none-any.whl`

The browser caches these using `ETag`/`Last-Modified` headers (dev server sets them automatically; GitHub Pages sets them for static files).

### D5: Dev server uses `no-cache` for app wheel, `must-revalidate` for framework wheel
- **Framework wheel** (`webcompy-*.whl`): `Cache-Control: max-age=86400, must-revalidate` — cache for 1 day, revalidate on next request.
- **App wheel (dev mode)**: `Cache-Control: no-cache` — always revalidate (app code changes frequently in dev).
- **App wheel (SSG/production)**: `Cache-Control: max-age=604800, immutable` — cache for 1 week (app version only changes on deploy).

### D6: `AppConfig` version field is optional and used for wheel METADATA only
The `version` field in `AppConfig` is an optional string. If unset, the existing `generate_app_version()` timestamp-based version is used as a fallback for wheel METADATA, but the wheel **URL path** remains stable.

## Architecture

### Build Pipeline (Current vs. Proposed)

```
CURRENT (make_webcompy_app_package — single wheel):
═══════════════════════════════════════════════════════════
  webcompy/                          ─┬─
  ├── app/                            │
  ├── elements/                       │  bundled into one wheel
  ├── cli/                            │  (including server-only code)
  ├── ...                             │
  app_package/                       ─┼─
  ├── __init__.py                     │
  └── ...                            ─┘

PROPOSED (two wheels):
═══════════════════════════════════════════════════════════
  Wheel A: webcompy-{ver}-py3-none-any.whl
  webcompy/                              ─┬─ browser-only
  ├── app/                                │  (excludes cli/)
  ├── elements/                           │
  ├── router/                             │
  └── ...                                ─┘

  Wheel B: {app_name}-{ver}-py3-none-any.whl
  {app_name}/                            ─┬─
  ├── __init__.py                         │ app + bundled deps
  └── ...                                ─┘
  {dep1}/                                 ─┬─ pure-Python deps
  └── ...                                ─┘
```

### PyScript Config (Current vs. Proposed)

```json
// CURRENT
{
  "packages": [
    "/_webcompy-app-package/myapp-25.107.43200-py3-none-any.whl",
    "numpy",
    "matplotlib"
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
    """Build a webcompy wheel excluding CLI-only modules."""
    # Collect files, excluding webcompy/cli/ and webcompy/cli/template_data/
    files_to_include = []
    for root, dirs, files in os.walk(webcompy_package_dir):
        rel = root.relative_to(webcompy_package_dir)
        if any(part in _BROWSER_ONLY_EXCLUDE for part in rel.parts):
            continue
        for f in files:
            ...
    return _make_wheel(name="webcompy", version=version, ...)
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
    package_dirs = [(package_dir.name, package_dir)]
    if bundled_deps:
        package_dirs.extend(bundled_deps)
    return _make_wheel(
        name=package_dir.name,
        package_dirs=package_dirs,
        dest=dest,
        version=app_version,
        ...
    )
```

### `_discover_dependency_package_dirs()`

```python
def _discover_dependency_package_dirs(
    dependencies: list[str],
) -> tuple[list[tuple[str, pathlib.Path]], list[str]]:
    bundled = []
    pyodide_builtin = []
    for dep in dependencies:
        try:
            spec = importlib.util.find_spec(dep)
            if spec and spec.origin:
                pkg_dir = pathlib.Path(spec.origin).parent
                bundled.append((dep, pkg_dir))
            else:
                pyodide_builtin.append(dep)
        except (ModuleNotFoundError, ValueError):
            pyodide_builtin.append(dep)
    return bundled, pyodide_builtin
```

### Dev Server Route Updates

`create_asgi_app()` must build and serve both wheels:

```python
def create_asgi_app(app=None, server_config=None):
    # ...
    webcompy_wheel = make_browser_webcompy_wheel(
        get_webcompy_package_dir(), temp_path, webcompy_version
    )
    app_wheel = make_webcompy_app_package(
        temp_path, package_dir, app_version, assets, bundled_deps
    )
    
    app_package_files = {
        "webcompy-py3-none-any.whl": (webcompy_wheel, "application/zip"),
        f"{_normalize_name(app_name)}-py3-none-any.whl": (app_wheel, "application/zip"),
    }
    
    @app.route("/_webcompy-app-package/{filename}")
    async def serve_wheel(request):
        ...
```

### SSG Route Updates

`generate_static_site()` must produce both wheels in the output:

```python
def generate_static_site(app=None, generate_config=None):
    ...
    webcompy_wheel = make_browser_webcompy_wheel(...)
    app_wheel = make_webcompy_app_package(...)
    
    dist = pathlib.Path(generate_config.dist)
    pkg_dir = dist / "_webcompy-app-package"
    shutil.copy(webcompy_wheel, pkg_dir / "webcompy-py3-none-any.whl")
    shutil.copy(app_wheel, pkg_dir / f"{_normalize_name(app_name)}-py3-none-any.whl")
```

### HTML Generation Updates

```python
def generate_html(app, dev_mode, app_version, app_package_name):
    bundled, pyodide_builtin = _discover_dependency_package_dirs(
        app.config.dependencies
    )
    py_packages = [
        f"{app.config.base_url}_webcompy-app-package/webcompy-py3-none-any.whl",
        f"{app.config.base_url}_webcompy-app-package/{_normalize_name(app_package_name)}-py3-none-any.whl",
        *[dep for dep in pyodide_builtin],  # C-extension deps only
    ]
    ...
```

## Browser Cache Headers

| Wheel | Dev Server Cache-Control | SSG/Production | Rationale |
|-------|-------------------------|---------------|-----------|
| Framework | `max-age=86400, must-revalidate` | `max-age=31536000, immutable` (via GitHub Pages ETag) | Framework changes infrequently |
| App (dev) | `no-cache` | N/A | App code changes frequently during development |
| App (SSG) | N/A | `max-age=604800, immutable` | App version changes only on deploy |

## Version Handling

- `AppConfig.version: str | None = None` (optional)
- If `version` is set, it becomes part of the wheel's METADATA (`Name: ...`, `Version: {version}`).
- The wheel **URL** is always stable: `...-py3-none-any.whl`.
- `generate_app_version()` continues to return a timestamp-based string, but it is only used as the METADATA version (fallback when `AppConfig.version` is None).
- **Cache busting:** If a full cache bust is needed (e.g., after a major framework update), the dev can append `?v={version}` to the wheel URL in the generated HTML. This is not automated but documented.

## Rollback Path

If the two-wheel approach introduces issues:
1. Set `SINGLE_WHEEL_MODE = True` in a config flag to revert to the old single-wheel bundling.
2. The `generate_html()` function can fall back to a single wheel URL if needed.

## Metrics Expected

| Metric | Before | After | Notes |
|--------|--------|-------|-------|
| Wheel download (first visit) | ~220KB + app | ~180KB + app + deps | CLI code removed from framework wheel |
| Wheel download (repeat visit) | ~220KB + app (timestamp defeats cache) | ~0KB (framework cached) + ~app (if changed) | Stable URLs enable browser cache |
| `micropip.install()` calls | N deps + 1 wheel | ~C-extension deps only | Pure-Python deps bundled in app wheel |
| Total startup network time | High (no cache) | Low (framework cached) | Significant on repeat visits |

## Dependencies

- **Informed by:** `feat/hydration-measurement` — profiling validates download/install time savings.

## Specs to Update

- `openspec/specs/wheel-builder/spec.md` — add `make_browser_webcompy_wheel()` and `bundled_deps` requirements.
- `openspec/specs/cli/spec.md` — update "The dev server shall serve application packages" requirement to mention two wheels and cache headers; update "Generated HTML shall include PyScript bootstrapping" requirement to mention two wheel URLs.
- `openspec/specs/app-config/spec.md` — add `AppConfig.version` field.
