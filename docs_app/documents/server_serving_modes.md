---
title: Serving Modes
description: Understand dependency classification, CDN vs local runtime/WASM serving, standalone builds, bundled vs split wheel modes, and offline deployments.
---

# Serving Modes

Every WebComPy deployment delivers three distinct runtime layers to the browser: the PyScript/Pyodide JavaScript and WebAssembly runtime, third-party Python dependencies (pure-Python or WASM-compiled), and your application plus `webcompy` core wheels.

Use `WebComPyBuildConfig` fields (or matching `start` / `generate` CLI flags) to trade CDN caching speed during open-internet deployments against full self-hosting for firewalled, air-gapped, or offline environments.

## Dependency classification

When generating `webcompy-lock.json`, WebComPy inspects your declared dependencies against the pinned Pyodide package lock (`pyscript_version` / `pyodide_version`) and assigns each package to one of three mutually exclusive `PackageKind` categories:

| `PackageKind` | How it is detected | How it ships to the browser |
|---|---|---|
| `WASM` | Listed in the Pyodide lock with a `wasm32` wheel filename (for example `numpy`) | Loaded by Pyodide as a WASM wheel (from Pyodide CDN or `/_webcompy-assets/packages/`) |
| `CDN_PURE_PYTHON` | Listed in the Pyodide lock without `wasm32` (for example `packaging` or `httpx`) | Extracted and bundled into the app wheel when `serve_all_deps=True`, or loaded from CDN when `False` |
| `LOCAL_PURE_PYTHON` | Not in the Pyodide lock and contains no `.so`, `.pyd`, or `.dylib` native extensions | Always bundled from your local Python environment into the app wheel |

If an explicit dependency is missing from both the Pyodide lock and the local environment — or exists locally with compiled `.so` / `.pyd` / `.dylib` extensions and no Pyodide WASM build — lock resolution fails with an actionable error before any server starts or static site builds. Transitive dependencies are walked recursively across both the Pyodide lock and local package metadata.

## Runtime, WASM, and dependency serving matrix

Four options on `WebComPyBuildConfig` (all overridable on `python -m webcompy start` and `generate`) govern where browser assets load from:

| Option | Default | Effect |
|---|---|---|
| `runtime_serving` | `"cdn"` (or `"local"` under `standalone=True`) | `"cdn"` loads PyScript CSS/JS and Pyodide core from external CDN; `"local"` downloads, verifies, and serves them under `/_webcompy-assets/{pyscript_version}/` |
| `wasm_serving` | `"cdn"` (or `"local"` under `standalone=True`) | `"cdn"` fetches `WASM` wheels and `pyodide-lock.json` from CDN; `"local"` serves downloaded WASM wheels from `/_webcompy-assets/packages/` |
| `serve_all_deps` | `True` | `True` downloads, SHA-256 checks, and bundles `CDN_PURE_PYTHON` packages into the app wheel; `False` delegates them to `py-config.packages` on CDN |
| `standalone` | `False` | Convenience switch: forces `serve_all_deps=True` and sets any unset `wasm_serving` or `runtime_serving` field to `"local"` |

Explicitly passing `wasm_serving="cdn"` or `runtime_serving="cdn"` alongside `standalone=True` honors the explicit field override while keeping `serve_all_deps=True` (passing `standalone=True` with `serve_all_deps=False` forces `serve_all_deps=True` with a warning on `stderr`).

Common deployment profiles:

| Scenario | Recommended settings | External network requests at browser boot? |
|---|---|---|
| Standard web deploy (fast small app wheel, CDN runtime) | `standalone=False`, `runtime_serving="cdn"`, `wasm_serving="cdn"`, `serve_all_deps=True` | Yes (PyScript CDN + Pyodide WASM wheels if any) |
| Minimal app wheel (rely on Pyodide CDN for pure-Python deps) | `serve_all_deps=False` (`--no-serve-all-deps`) | Yes (PyScript CDN + Pyodide CDN pure-Python & WASM) |
| Full self-hosted / zero-CDN deploy | `standalone=True` (`--standalone`) | **No** (all HTML, runtime, WASM, UI CSS, and wheels served from same origin) |

In production mode (`mode="prod"`), locally served runtime assets carry `Cache-Control: public, max-age=31536000, immutable` keyed under the pinned `pyscript_version` prefix (`/_webcompy-assets/{pyscript_version}/`). Locally served WASM wheels (`/_webcompy-assets/packages/`) and content-hashed browser wheels (`/_webcompy-app-package/`) also emit `Cache-Control: public, max-age=31536000, immutable` in production mode, while framework UI stylesheets (`/_webcompy-ui/`) and static files receive deterministic `?v=<hash>` cache-busting query parameters in production SSR and SSG HTML (and inside `/_webcompy-ui/index.css`'s `@import` rules).

## Wheel modes: `bundled` vs `split`

Set `wheel_mode` on `WebComPyBuildConfig` (or `--wheel-mode bundled|split`) to control how PEP 427 browser wheels are emitted under `/_webcompy-app-package/`:

| Mode | Emitted wheels | Trade-offs |
|---|---|---|
| `"bundled"` (default) | Single `<app>.whl` containing your app, `webcompy` core, and bundled pure-Python dependencies | Single wheel HTTP request at startup; any app code edit rebuilds and invalidates the full archive |
| `"split"` | Separate framework `webcompy-<version>.whl` (`extra_wheel_filenames`) and lighter `<app>.whl` | Better caching when application code changes more often than `webcompy`; during `webcompy start --dev`, the framework wheel uses `Cache-Control: max-age=86400, must-revalidate` while the app wheel uses `Cache-Control: no-cache` |

Static generation (`webcompy generate`) copies every wheel produced by either mode into `dist/_webcompy-app-package/`. Only `webcompy` core and bundled browser dependencies enter the browser wheels — `webcompy-server`, `webcompy-cli`, and `webcompy-testing` remain server-only.

## Cache integrity and `.webcompy_modules/`

WebComPy caches downloaded Pyodide locks, CDN wheels, WASM wheels, and PyScript/Pyodide runtime assets inside `<app_package_path>/.webcompy_modules/`, automatically ensuring a `.gitignore` file ignores its contents.

When `runtime_serving="local"` runs, `verify_and_update_runtime_assets()` hashes every runtime file (`SHA-256`) and verifies it against hashes previously recorded under `runtime_assets` in `webcompy-lock.json` (raising `RuntimeDownloadError` on mismatch before writing any output). WASM wheels and `CDN_PURE_PYTHON` wheels are likewise verified against `pyodide_sha256` / `sha256` from the lockfile during download.

## Offline and firewall deployment checklist

Follow this checklist when deploying inside corporate firewalls, air-gapped networks, or offline-capable PWAs:

1. **Enable standalone delivery**: Set `standalone=True` in `webcompy_config.py` (or pass `--standalone` to `start`/`generate`). Combine with `wheel_mode="split"` and `PWAConfig(precache_runtime=True)` when browsers also need offline restarts:

```python
import my_app.app as app_module
from webcompy_cli.config import ManifestConfig, PWAConfig, WebComPyBuildConfig

config = WebComPyBuildConfig(
    app_module,
    standalone=True,
    wheel_mode="split",
    pwa=PWAConfig(
        enabled=True,
        manifest=ManifestConfig(name="Intranet Console"),
        precache_runtime=True,
    ),
)
```

2. **Generate lock and warm cache on a connected build machine**: Run `python -m webcompy lock` followed by `python -m webcompy generate` so `.webcompy_modules/` caches all runtime assets and `webcompy-lock.json` records `runtime_assets` SHA-256 checksums.
3. **Inspect generated `dist/` HTML**: Verify generated `<script>` and `<link>` tags point only to same-origin `/_webcompy-assets/...`, `/_webcompy-app-package/...`, and `/_webcompy-ui/...` paths (no external CDN URLs remain).
4. **Test offline boot in headless Chromium**: With `PWAConfig(enabled=True, precache_runtime=True)`, verify Service Worker registration and cached reload while disconnected (see [Progressive Web App](/documents/advanced/pwa)).

## Next steps

- See an isolated iframe loading NumPy and Matplotlib WASM wheels on demand in the [Matplotlib](/documents/examples/matplotlib) example.
- Pair self-hosted serving with precaching and runtime cache rules in [Progressive Web App](/documents/advanced/pwa).
- Configure `standalone`, `wheel_mode`, and `lockfile_sync_config` in [Project Configuration](/documents/server/project-configuration).
- Override serving flags per run from the CLI in [CLI Reference](/documents/server/cli-reference).
- Reduce initial page payload and navigation requests with `resource_transfer="all-text"` in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
- Full API: [Server, CLI, RPC & Ports API](/documents/api/server-and-cli).
