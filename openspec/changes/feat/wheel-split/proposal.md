# Proposal: Wheel Split — Browser-Only Framework Wheel, Dependency Bundling, and Browser Cache Strategy

## Summary

Split the current single bundled wheel (webcompy + app) into a browser-only webcompy framework wheel and a separate app wheel. The browser-only wheel excludes CLI-only code (`webcompy/cli/`, `webcompy/cli/template_data/`) that is never needed in the browser. Additionally, bundle user-specified pure-Python dependencies into the app wheel to reduce the number of Pyodide package installations. Leverage browser HTTP caching with stable URLs and proper cache headers to ensure repeated visits skip wheel re-downloads.

## Motivation

1. **Download size and caching**: The entire webcompy framework (~220KB of Python source) is currently bundled inside every app wheel. This means every app update requires re-downloading the entire framework. Splitting allows the framework wheel to be cached independently.

2. **Unnecessary browser code**: `webcompy/cli/` (server, generate, init, wheel builder, argparser) is never used in the browser but is included in the bundle. Removing it reduces the framework wheel size.

3. **Pyodide install overhead**: Each package listed in `py-config.packages` triggers a separate `micropip.install()` call. Bundling pure-Python dependencies into the app wheel reduces the number of install calls.

4. **Browser cache**: Currently, app versions change every second (`generate_app_version()` produces timestamps), meaning the wheel URL changes every time, defeating browser caching. Using stable URLs with content hashes or version-based paths enables the browser to cache wheels across visits.

## Known Issues Addressed

None directly (this is a new capability).

## Non-goals

- This does not use external CDN hosting. All wheels are served from the same origin (dev server or static site), leveraging the browser's built-in HTTP cache rather than a CDN.
- This does not bundle C-extension packages (numpy, matplotlib etc.) into wheels — Pyodide provides those as built-in packages.
- This does not change the `py-config` format beyond updating the packages list.
- This does not implement service workers or offline caching.

## Dependencies

- **Informed by** `feat/hydration-measurement` — profiling data will validate download/install time savings.

## Design

### Part 1: Browser-Only WebComPy Wheel

#### Current State

`make_webcompy_app_package()` in `_wheel_builder.py` creates a single wheel containing:
- `webcompy/` — entire framework source (including `cli/`)
- `{app_name}/` — application source
- Shared `.dist-info/`

#### Proposed State

Two separate wheels:

**WebComPy framework wheel** (browser-only):
```
webcompy-{version}-py3-none-any.whl
├── webcompy/
│   ├── app/
│   ├── components/
│   ├── elements/
│   ├── signal/
│   ├── router/
│   ├── di/
│   ├── _browser/
│   ├── aio/
│   ├── ajax/
│   ├── assets.py
│   ├── exception/
│   ├── logging.py
│   ├── utils/
│   ├── __init__.py
│   ├── __main__.py
│   ├── _version.py
│   └── py.typed
├── webcompy-{version}.dist-info/
│   ├── METADATA
│   ├── WHEEL
│   ├── top_level.txt    (contains: webcompy)
│   └── RECORD
```

**Application wheel** (app code + optional dependencies):
```
{app_name}-{version}-py3-none-any.whl
├── {app_name}/           (application source)
├── {dep1}/               (bundled pure-Python dependencies)
├── {dep2}/
├── {app_name}-{version}.dist-info/
│   ├── METADATA
│   ├── WHEEL
│   ├── top_level.txt    (contains: {app_name}\n{dep1}\n{dep2})
│   └── RECORD
```

#### New Function: `make_browser_webcompy_wheel()`

```python
_BROWSER_ONLY_EXCLUDE = {"cli", "cli"}

def make_browser_webcompy_wheel(
    webcompy_package_dir: pathlib.Path,
    dest: pathlib.Path,
    version: str,
) -> pathlib.Path:
    """Build a webcompy wheel excluding CLI-only modules."""
    # Collect webcompy files, excluding webcompy/cli/
    ...
```

#### Updated `make_webcompy_app_package()`

The app wheel no longer includes `webcompy/`. It bundles app code and pure-Python dependencies.

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
    return make_bundled_wheel(
        name=package_dir.name,
        package_dirs=package_dirs,
        dest=dest,
        version=app_version,
        package_data=package_data,
        extra_files=extra_files,
    )
```

### Part 2: Dependency Bundling

#### Strategy

Instead of listing pure-Python dependencies in `py-config.packages` (which triggers separate `micropip.install()` calls per package), bundle their source files directly into the app wheel.

This requires:

1. **Discovery**: Given `AppConfig.dependencies`, determine which are pure-Python (installable via `micropip`) vs. C-extension (provided by Pyodide).
2. **Resolution**: For pure-Python dependencies, locate their installed source files on the server.
3. **Bundling**: Include the dependency's package directory in the app wheel.

Since the dev server and SSG generator run in a standard Python environment, installed packages are available via `importlib.util.find_spec()`.

#### Implementation

```python
def _discover_dependency_package_dirs(
    dependencies: list[str],
) -> tuple[list[tuple[str, pathlib.Path]], list[str]]:
    """Resolve dependencies to package directories.
    
    Returns:
        (bundled, pyodide_builtin)
        - bundled: list of (package_name, package_dir) for pure-Python deps
        - pyodide_builtin: list of package names for C-extension deps (Pyodide built-ins)
    """
    bundled = []
    pyodide_builtin = []
    for dep in dependencies:
        try:
            spec = importlib.util.find_spec(dep)
            if spec and spec.origin:
                # Pure Python — include in bundle
                pkg_dir = pathlib.Path(spec.origin).parent
                bundled.append((dep, pkg_dir))
            else:
                # C extension or unavailable — defer to Pyodide
                pyodide_builtin.append(dep)
        except (ModuleNotFoundError, ValueError):
            pyodide_builtin.append(dep)
    return bundled, pyodide_builtin
```

#### Updated `py-config.packages`

The generated HTML's PyScript config will list:
1. The webcompy framework wheel URL
2. The app wheel URL (containing app code + bundled deps)
3. Only the C-extension / Pyodide built-in package names (e.g., `numpy`, `matplotlib`)

```json
{
  "packages": [
    "/_webcompy-app-package/webcompy-{ver}-py3-none-any.whl",
    "/_webcompy-app-package/{app_name}-{ver}-py3-none-any.whl",
    "numpy",
    "matplotlib"
  ]
}
```

### Part 3: Browser Cache Strategy

#### Problem

Currently, `generate_app_version()` produces a timestamp-based version like `25.107.43200`, which changes every second. This means every deploy/dev-server-restart produces a different wheel URL, defeating browser caching.

#### Solution

Use **content-addressable URLs** for framework wheels and **version-stable URLs** for app wheels.

**Framework wheel URL**: Since the webcompy framework changes infrequently, use a stable URL path that the browser can cache:

```
/_webcompy-app-package/webcompy-py3-none-any.whl
```

The same URL path always serves the current framework wheel. When the framework is updated, the file content changes but the URL stays the same — the browser revalidates using `ETag` / `Last-Modified` headers (set by Starlette's static file serving in dev mode, or by the hosting server in production).

**App wheel URL**: Similarly:

```
/_webcompy-app-package/{app_name}-py3-none-any.whl
```

#### Cache Headers (Dev Server)

In `create_asgi_app()`, set appropriate cache headers for wheel files:

- **Framework wheel**: `Cache-Control: max-age=86400, must-revalidate` — cache for 1 day, revalidate on next request
- **App wheel in dev mode**: `Cache-Control: no-cache` — always revalidate (app code changes frequently in dev)
- **App wheel in production (SSG)**: `Cache-Control: max-age=604800, immutable` — cache for 1 week (app version only changes on deploy)

#### Cache Headers (Static Site / GitHub Pages)

For SSG, the static files are served by GitHub Pages (or similar), which sets `ETag` and `Last-Modified` automatically. Since the wheel URLs are now stable (not versioned by timestamp), the browser will cache them and revalidate with `If-None-Match` / `If-Modified-Since`.

#### Version Tracking

The app version is still generated (for build metadata / cache busting when needed), but the wheel **filename** in the URL no longer includes it. Instead:

- The `AppConfig` or `GenerateConfig` can specify a `version` that becomes part of METADATA
- The URL path is stable: `/_webcompy-app-package/webcompy-py3-none-any.whl`
- Only when a full cache-bust is needed (e.g., after a major framework update), an optional `?v=` query parameter can be appended

### Updated HTML Generation

`generate_html()` in `_html.py` must be updated to reference two wheel URLs instead of one:

```python
def generate_html(app, dev_mode, prerender, app_version, app_package_name):
    # ...
    py_packages = [
        f"{app.config.base_url}_webcompy-app-package/webcompy-py3-none-any.whl",
        f"{app.config.base_url}_webcompy-app-package/{_normalize_name(app_package_name)}-py3-none-any.whl",
        *pyodide_builtin_deps,  # C-extension deps only
    ]
    # ...
```

### Server Route Updates

`create_asgi_app()` must serve both wheel files:

```python
# Build both wheels at startup
webcompy_wheel = make_browser_webcompy_wheel(
    get_webcompy_packge_dir(), temp_path, webcompy_version
)
app_wheel = make_webcompy_app_package(
    temp_path, package_dir, app_version, assets, bundled_deps
)

# Serve at stable URLs
app_package_files = {
    "webcompy-py3-none-any.whl": (webcompy_wheel_content, "application/zip"),
    f"{_normalize_name(app_name)}-py3-none-any.whl": (app_wheel_content, "application/zip"),
}
```

## Specs Affected

- `wheel-builder` — adds `make_browser_webcompy_wheel()`; updates `make_webcompy_app_package()` to accept `bundled_deps`
- `cli` — updates dev server and SSG to produce two wheels; updates cache headers; updates `generate_html()` to reference two wheels
- `app-config` — may add `version` field to `AppConfig` for explicit versioning
- `app-lifecycle` — no API changes
- `app` — no spec changes needed