# Proposal

## Why

Stage 1 (`feat-python314-support`, PR #299) added CPython 3.14 support and pinned server, CLI, unit test, and CI environments to Python 3.14, while keeping the browser runtime pinned at PyScript `2026.3.1` / Pyodide `0.29.3` (CPython 3.13.x). Running CPython 3.14 on the server and Python 3.13 in the browser leaves a two-version runtime split where CPython 3.14 syntax, standard library behavior, and PEP 649 annotation semantics cannot yet execute in PyScript.

PyScript `2026.7.3` ships with Pyodide `314.0.3` (CPython `3.14.0`, `emscripten_5_0_3`, ABI `2026_0`), which aligns the browser runtime with the Python 3.14 toolchain already running on the server and in CI. Upgrading to `2026.7.3` / `314.0.3` requires two supporting fixes discovered in the toolchain and lockfile subsystems:

1. Pyodide `314.0.3` renamed `pyodide.asm.js` to `pyodide.asm.mjs` (`pyodide.asm.js` returns HTTP 404 on jsDelivr and is absent from `offline_2026.7.3.zip`). The runtime downloader and lockfile asset generator currently hardcode `pyodide.asm.js`.
2. `resolve_lockfile()` currently only checks whether explicit dependency names changed; it reuses an existing `webcompy-lock.json` even when its recorded `pyscript_version` (or resolved `pyodide_version`) does not match the active `PYSCRIPT_VERSION`.

## What Changes

- Add `"2026.7.3": "314.0.3"` to `PYSCRIPT_TO_PYODIDE` in `webcompy_cli._pyodide_lock` while retaining `"2026.3.1": "0.29.3"` so `scripts/run-browser-version-sweep.sh` can evaluate both versions side by side.
- Introduce version-aware Pyodide runtime asset resolution (`get_pyodide_runtime_assets(pyodide_version)`) in `webcompy_cli._runtime_downloader` so Pyodide `< 0.30` (e.g., `0.29.3`) resolves `pyodide.asm.js` and Pyodide `>= 0.30` / `>= 314.0.0` (e.g., `314.0.3`) resolves `pyodide.asm.mjs`; update `PYODIDE_RUNTIME_ASSETS`, `download_runtime_assets()`, and `generate_lockfile()` accordingly.
- Replace the hardcoded `"0.29.3"` fallback in `webcompy_cli._build` with `get_pyodide_version(PYSCRIPT_VERSION)`.
- Update `resolve_lockfile()` in `webcompy_cli._lockfile` so an existing `webcompy-lock.json` whose `pyscript_version` differs from the active `pyscript_version` (or whose `pyodide_version` differs from `get_pyodide_version(pyscript_version)`) is treated as stale and regenerated automatically.
- Gate promotion on `scripts/run-browser-version-sweep.sh 2026.7.3` (confirming zero regressions across all 17 environment probes in `tests/browser/probes/**`), then promote `PYSCRIPT_VERSION = "2026.7.3"` in `webcompy_server._html`.
- Update brittle version/hash-hardcoded test assertions in `tests/test_pwa_sw_generation.py` (use `PYSCRIPT_BASE_URL`) and `e2e/core/test_standalone.py` (resolve the hashed core chunk `./core-*.js` imported by `core.js` dynamically rather than hardcoding `core-BuLtL7jM.js`).

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `dependency-resolver`: Extend the PyScript-to-Pyodide version mapping table specification with `2026.7.3` → `314.0.3` alongside `2026.3.1` → `0.29.3`.
- `pyscript-bundle`: Specify version-aware selection between `pyodide.asm.js` (`< 0.30`) and `pyodide.asm.mjs` (`>= 0.30`), and replace the hardcoded bundle chunk filename example/assertion (`core-BuLtL7jM.js`) with relative chunk import verification from `core.js`.
- `lockfile`: Require `resolve_lockfile()` to invalidate and regenerate existing `webcompy-lock.json` files when `pyscript_version` or `pyodide_version` mismatches the active `PYSCRIPT_VERSION`.

## Known Issues Addressed

- Completes browser-side parity with Stage 1 (`feat-python314-support`), eliminating the CPython 3.14 (server) vs. Python 3.13 (browser) runtime split.
- No existing item under `openspec/config.yaml` Known Issues applies to browser/Pyodide packaging behavior (the PyPI git-URL install and PyScript PyPI-resolution notes remain unchanged).

## Non-goals

- Raising `requires-python` above `>=3.12` (already settled in Stage 1).
- Overriding PyScript `2026.7.3`'s bundled Pyodide `314.0.3` to a standalone Pyodide release (e.g., `314.0.8`) or changing `pyscript.net` CDN hosting.
- Checking generated `webcompy-lock.json` files into git (still excluded via `.gitignore` and regenerated dynamically at build/test time).
- Altering MicroPython or non-Pyodide runtime support.
- Reorganizing or expanding `docs_app/` content (tracked on separate `docs/*` branches).

## Impact

- **Server / HTML generation**: `packages/webcompy-server/src/webcompy_server/_html.py` (`PYSCRIPT_VERSION = "2026.7.3"`), changing CDN runtime URLs, local runtime asset cache keys, and Service Worker CDN precache URLs (`_pwa.py`).
- **CLI / Lockfile / Downloader**: `packages/webcompy-cli/src/webcompy_cli/_pyodide_lock.py`, `_runtime_downloader.py`, `_lockfile.py`, `_build.py`.
- **Browser Test & Probe Infrastructure**: `tests/browser/**` and `scripts/run-browser-version-sweep.sh` (verifying WebLoop ordering, proxy lifecycle, JS FFI interop, UTF-16 DOM, and PyScript execution under Python 3.14).
- **Tests**: Unit tests in `tests/test_pyodide_lock.py`, `tests/test_runtime_downloader.py`, `tests/test_lockfile.py`, `tests/test_pwa_sw_generation.py`, and E2E test `e2e/core/test_standalone.py`.
- **Dependencies in Pyodide `314.0.3`**: All browser packages used by `docs_app` (`numpy` `2.4.3`, `matplotlib` `3.10.8`, `pillow` `12.2.0`, `kiwisolver` `1.5.0`, `contourpy` `1.3.3`) and the browser harness (`micropip` `0.11.1`, `httpx` `0.28.1`, `starlette` `1.0.0`, `anyio` `4.13.0`) are present in Pyodide `314.0.3` `pyodide-lock.json` (`pyemscripten_2026_0_wasm32` wheels still match `"wasm32" in file_name`).
