---
title: Project Configuration
description: Structure browser and server settings across pyproject.toml and webcompy_config.py, configure resource allow-lists, and manage webcompy-lock.json.
---

# Project Configuration

WebComPy separates browser-visible runtime configuration (`WebComPyAppConfig` on `WebComPyApp`), dependency declarations (`pyproject.toml`), and server/build configuration (`WebComPyBuildConfig` in `webcompy_config.py`). Keeping build concerns out of the `webcompy` core package ensures server paths, mount callables, and lockfile settings never ship into the browser wheel.

Use this page when configuring how dependencies resolve, which package files are exposed as resources, and how `webcompy-lock.json` stays synchronized with your project manifest.

## The two-file configuration model

A standard WebComPy project splits configuration across two Python/TOML files plus the application object:

| File / object | Owns | Included in browser wheel? |
|---|---|---|
| `pyproject.toml` | Package metadata, `[project.dependencies]`, optional browser dependency group (e.g. `browser = [...]`) | No |
| `webcompy_config.py` (`WebComPyBuildConfig`, `WebComPyServerConfig`, `PWAConfig`, `LockfileSyncConfig`) | Where `app` lives, dependency source, wheel & asset serving mode, resource globs, `dist/`, `mounts`, `pwa` | No |
| `app/app.py` (`WebComPyAppConfig`) | `base_url`, mount `selector`, `hydrate`, `scroll_restoration`, `loading`, `theme`, `plugins`, `scripts`, `compression_threshold`, `on_error`, `profile` | Yes |

### Config discovery rules

The CLI calls `discover_config(module_path=None)` from `webcompy_cli`:

- When `--config` is omitted, WebComPy imports the top-level module `webcompy_config`.
- When `--config my_project.webcompy_config` is passed, WebComPy imports that dotted module path.
- The imported module must export a top-level variable named `config` holding a `WebComPyBuildConfig` instance; otherwise `WebComPyCliException` is raised.

Here is a complete `webcompy_config.py` combining browser dependency discovery, lockfile sync, resource filtering, and a custom server port:

```python
import my_app.app as app_module
from webcompy_cli.config import (
    LockfileSyncConfig,
    PWAConfig,
    WebComPyBuildConfig,
    WebComPyServerConfig,
)

config = WebComPyBuildConfig(
    app_module,
    app_var="app",
    dependencies=None,
    dependencies_from="browser",
    resource_exclude=["**/drafts/**"],
    resource_transfer="used",
    dist="dist",
    static_files_dir="static",
    lockfile_sync_config=LockfileSyncConfig(sync_group="browser"),
    server=WebComPyServerConfig(port=8080),
    pwa=PWAConfig(enabled=False),
)
```

## `WebComPyBuildConfig` field reference

All fields live on `WebComPyBuildConfig` (`webcompy_cli.config`):

| Field | Default | Purpose |
|---|---|---|
| `app_module` | required | Imported Python module containing your `WebComPyApp` instance |
| `app_var` | `"app"` | Attribute name of the `WebComPyApp` inside `app_module` |
| `dependencies` | `None` | Explicit list of browser package names; when `None`, resolved from `pyproject.toml` |
| `dependencies_from` | `None` | Optional group name under `[project.optional-dependencies]` in `pyproject.toml`; when `None`, reads `[project.dependencies]` |
| `resources` | `None` | Glob patterns for package resource allow-list; `None` uses default extensions, `[]` disables resources |
| `resource_exclude` | `None` | Glob patterns excluding matched paths from the resource allow-list |
| `version` | `None` | Application version embedded into generated wheels and service workers (`None` uses `"0.0.0"`) |
| `serve_all_deps` | `True` | Bundle all pure-Python browser dependencies (including CDN-available ones) into the app wheel |
| `wasm_serving` | `None` | `"cdn"` or `"local"` for WASM wheels; defaults via `standalone` when `None` |
| `runtime_serving` | `None` | `"cdn"` or `"local"` for PyScript/Pyodide runtime files; defaults via `standalone` when `None` |
| `standalone` | `False` | Serve runtime, WASM packages, and pure-Python dependencies locally without external CDNs |
| `wheel_mode` | `"bundled"` | `"bundled"` (single combined wheel) or `"split"` (separate framework and app wheels) |
| `resource_transfer` | `"used"` | `"used"` embeds only per-route loaded resources; `"all-text"` embeds all allow-listed text resources during SSG |
| `dist` | `"dist"` | Output directory path for `webcompy generate` (resolved relative to `app_package_path` unless `--dist` overrides) |
| `static_files_dir` | `"static"` | Static asset directory relative to `app_package_path` |
| `lockfile_sync_config` | `None` | Optional `LockfileSyncConfig` governing `requirements.txt` and `pyproject.toml` sync |
| `server` | `WebComPyServerConfig()` | Serving options (`port`, `dev`, `mounts`) |
| `pwa` | `PWAConfig()` | Progressive Web App manifest, service worker, and runtime caching rules (see [Progressive Web App](/documents/advanced/pwa)) |

In `__post_init__`, `WebComPyBuildConfig` validates `resource_transfer` (`"used"` or `"all-text"`), computes `app_package_path = Path(app_module.__file__).parent`, resolves `app = getattr(app_module, app_var)`, and calls `resolve_standalone()` so CLI overrides re-evaluate cleanly.

## `WebComPyServerConfig` and `LockfileSyncConfig`

### `WebComPyServerConfig`

| Field | Default | Purpose |
|---|---|---|
| `port` | `8080` | TCP port used by `python -m webcompy start` when `--port` is omitted |
| `dev` | `False` | Enables `/_webcompy_reload` SSE endpoint and uvicorn reload (overridden by `--dev`) |
| `mounts` | `None` | Zero-argument callable returning `dict[str, ASGIApp]` mapping URL prefixes to mounted ASGI sub-apps |

See [ASGI Integration](/documents/server/asgi-integration#mounting-asgi-apps-under-webcompy) for mount prefix rules and SSR/SSG behavior.

### `LockfileSyncConfig`

| Field | Default | Purpose |
|---|---|---|
| `requirements_path` | `None` | Path (absolute or relative to `app_package_path`) to `requirements.txt`; `None` discovers `requirements.txt` beside `pyproject.toml` |
| `sync_group` | `None` | Optional group under `[project.optional-dependencies]` checked by `webcompy lock --sync`; aligns with `dependencies_from` |

Setting `dependencies_from="browser"` and `LockfileSyncConfig(sync_group="browser")` keeps generation and `--sync` checks targeting the exact same `pyproject.toml` dependency list; mismatches between the two print a warning to `stderr`.

### Runtime vs build configuration boundary

Settings that affect HTML/DOM hydration or browser behavior live on `WebComPyAppConfig` (`webcompy`):

- `base_url` (defaults to `"/"`, normalized to leading + trailing slash)
- `selector` (`"#webcompy-app"`)
- `hydrate` (`True`) and `compression_threshold` (`1024`, `None` or `0` disables gzip payload compression)
- `scroll_restoration` (`True`)
- `theme`, `loading`, `plugins`, `scripts`, `on_error`, `profile`

Because `WebComPyAppConfig` travels into the browser wheel while `WebComPyBuildConfig` never does, host secrets, server mount callbacks, and build paths remain strictly server-side.

## Resource allow-list and static files

WebComPy distinguishes verbatim static assets from application resources:

- **Static files (`static_files_dir`)**: Served directly at `/<relative_path>` (and `{base_url}<relative_path>` when `base_url` is non-root) and copied unchanged into `dist/`. Put stylesheets, images, favicons, and `robots.txt` here.
- **Package resources (`resources` + `resource_exclude`)**: Walked inside `app_package_path` at startup/build to construct an explicit allow-list for `ServerResourcePort` (`load_text` / `load_bytes`) and `/_webcompy-resource/{path}`:
  - When `resources=None`, the default allow-list matches `**/*.html`, `**/*.css`, `**/*.md`, `**/*.svg`, and `**/*.txt` (matching both top-level files and nested subdirectories).
  - Setting `resources=[]` disables resource scanning and yields an empty allow-list.
  - Directories named `__pycache__`, `.git`, and `.webcompy_modules` plus `.pyc` and `.tmp` files are always excluded.
  - Requests for paths outside the allow-list receive HTTP `404`, and traversal outside `app_package_path` is rejected with `403`.
  - Setting `resource_transfer="all-text"` pre-embeds allow-listed text files (`.md`, `.markdown`, `.txt`, `.json`, `.csv`, `.yaml`, `.yml`, `.toml`, `.svg`, `.html`, `.xml`) into every SSG HTML payload so route transitions avoid extra network requests (emitting a warning if any single text file exceeds 256 KiB or the combined set exceeds 1 MiB).

## Lockfile lifecycle (`webcompy-lock.json`)

Running `python -m webcompy lock` (or letting `start`/`generate` initialize the build) writes `webcompy-lock.json` inside `app_package_path` using lockfile schema **version 2**:

```json
{
  "version": 2,
  "pyodide_version": "314.0.3",
  "pyscript_version": "2026.7.3",
  "wasm_serving": "cdn",
  "runtime_serving": "cdn",
  "standalone": false,
  "wasm_packages": {},
  "pure_python_packages": {}
}
```

Key lifecycle guarantees:

1. **Automatic staleness detection**: At build time, WebComPy verifies that `version == 2`, that the union of `explicit` packages in `wasm_packages` and `pure_python_packages` matches resolved `dependencies`, and that `pyscript_version` and `pyodide_version` match the active runtime pin. Version 1 lockfiles or mismatched dependency/runtime pins trigger automatic regeneration.
2. **Environment validation**: Non-CDN pure-Python packages missing locally or matching a different installed version fail the build with exact `pip install <pkg>==<ver>` remediation instructions. CDN pure-Python or WASM version differences emit `stderr` warnings noting the local version runs during SSR/SSG while the locked version runs in the browser.
3. **Version control and cache files**: Commit `webcompy-lock.json` alongside your code for reproducible builds. Build caches live separately in `<app_package_path>/.webcompy_modules/`, where WebComPy automatically writes a `.gitignore` containing `*`.

## Next steps

- Review the directory layout created by `webcompy init` in [Project Structure](/documents/getting-started/project-structure).
- Inspect all flags for `lock`, `start`, and `generate` in [CLI Reference](/documents/server/cli-reference).
- Configure CDN vs offline asset delivery in [Serving Modes](/documents/server/serving-modes).
- Tune resource transfer and payload compression in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
- Add manifest and offline worker settings via `PWAConfig` in [Progressive Web App](/documents/advanced/pwa).
