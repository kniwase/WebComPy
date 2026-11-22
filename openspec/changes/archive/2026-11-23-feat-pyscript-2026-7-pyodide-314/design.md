# Design

## Context

See `proposal.md` for motivation and scope. Upstream verification against `pyscript.net` and `cdn.jsdelivr.net` establishes the concrete runtime layout for PyScript `2026.7.3` and Pyodide `314.0.3`:

- **PyScript `2026.7.3`** (`offline_2026.7.3.zip`, 72 archive entries):
  - `core.js` imports `./core-7nKZylPm.js` (replacing `2026.3.1`'s `./core-BuLtL7jM.js`).
  - `offline/pyscript/pyodide_graph-Ci-wK1d9.js`, `offline/pyscript/pyodide/pyodide.js`, and `offline/pyscript/core-7nKZylPm.js` all pin Pyodide `314.0.3`.
  - `offline/pyscript/pyodide/` contains `pyodide.mjs`, `pyodide.asm.mjs`, `pyodide.asm.wasm`, `python_stdlib.zip`, and `pyodide-lock.json` (`pyodide.asm.js` no longer exists).
- **Pyodide `314.0.3` CDN** (`https://cdn.jsdelivr.net/pyodide/v314.0.3/full/`):
  - `pyodide.mjs` (17,880 B), `pyodide.asm.wasm` (9,596,462 B), `pyodide.asm.mjs` (1,249,447 B), `python_stdlib.zip`, and `pyodide-lock.json` (113,804 B) return HTTP 200; `pyodide.asm.js` returns HTTP 404.
  - `pyodide-lock.json` metadata: `abi_version = "2026_0"`, `arch = "wasm32"`, `platform = "emscripten_5_0_3"`, `python = "3.14.0"`, 354 packages.
  - All packages required by `docs_app` (`numpy` `2.4.3`, `matplotlib` `3.10.8`, `pillow` `12.2.0`, `kiwisolver` `1.5.0`, `contourpy` `1.3.3`) and the browser test harness (`micropip` `0.11.1`, `httpx` `0.28.1`, `starlette` `1.0.0`, `anyio` `4.13.0`) are present, with WASM wheel filenames using `-pyemscripten_2026_0_wasm32.whl` (matched by the existing `"wasm32" in file_name` check in `_dependency_resolver.py`).
- **MIME types**: Both Python 3.14 `mimetypes.guess_type("pyodide.asm.mjs")` (`"text/javascript"`) used by `_server.py` and the explicit `filename.endswith((".js", ".mjs"))` check (`"application/javascript"`) in `_browser_test_harness.py` already serve `.mjs` with a JavaScript media type.

## Goals / Non-Goals

**Goals:**
- Support both Pyodide `0.29.x` (`pyodide.asm.js`) and Pyodide `314.x` (`pyodide.asm.mjs`) cleanly in runtime asset downloading, lockfile generation, and local serving.
- Prevent stale cached `webcompy-lock.json` files from pinning `2026.3.1` / `0.29.3` after `PYSCRIPT_VERSION` is upgraded to `2026.7.3`.
- Validate Python 3.14 browser semantics via `scripts/run-browser-version-sweep.sh 2026.7.3` (17 probes + optional dual-run comparison) before changing the pinned `PYSCRIPT_VERSION`.
- Eliminate hardcoded PyScript chunk hash and version assumptions in tests so future upgrades do not break unrelated assertions.

**Non-Goals:**
- Changing runtime asset extraction rules beyond Pyodide filename resolution (`.js`/`.css` extraction from `offline/pyscript/` in `download_pyscript_bundle` already works identically for `2026.7.3`).
- Overriding `pyodide_version` independently of `pyscript.net`'s bundled Pyodide `314.0.3`.

## Decisions

### 1. Retain `2026.3.1` → `0.29.3` in `PYSCRIPT_TO_PYODIDE` alongside `2026.7.3` → `314.0.3`
- **Choice**: Add `"2026.7.3": "314.0.3"` to `PYSCRIPT_TO_PYODIDE` in `packages/webcompy-cli/src/webcompy_cli/_pyodide_lock.py` while keeping `"2026.3.1": "0.29.3"`. Also fix the stale path hint in `get_pyodide_version()`'s `ValueError` message (`webcompy/cli/_pyodide_lock.py` → `webcompy_cli/_pyodide_lock.py`).
- **Rationale**: `scripts/run-browser-version-sweep.sh` compares the currently pinned version against a candidate version before promotion and relies on `get_pyodide_version()` succeeding for both versions. Keeping historical entries also ensures old lockfiles or explicit tests remain resolvable without special-casing.
- **Alternative rejected**: Replacing `"2026.3.1"` in place — would break the pre-promotion sweep workflow and downgrade diagnostics.

### 2. Version-aware `get_pyodide_runtime_assets(pyodide_version)` helper
- **Choice**: Add `get_pyodide_runtime_assets(pyodide_version: str) -> list[str]` in `packages/webcompy-cli/src/webcompy_cli/_runtime_downloader.py`, returning `["pyodide.mjs", "pyodide.asm.wasm", asm_entry, "python_stdlib.zip", "pyodide-lock.json"]`, where `asm_entry` is `"pyodide.asm.js"` when parsed `(major, minor) < (0, 30)` and `"pyodide.asm.mjs"` otherwise (covering both `0.30+` and Pyodide's new CalVer/Python-aligned `314.0.3+` versioning). Update `PYODIDE_RUNTIME_ASSETS` to list `"pyodide.asm.mjs"`, and update both `download_runtime_assets()` and `generate_lockfile()` (`_lockfile.py`) to call `get_pyodide_runtime_assets(pyodide_version)`. Also replace the hardcoded `"0.29.3"` fallback in `packages/webcompy-cli/src/webcompy_cli/_build.py` (`download_runtime_assets(lockfile.pyodide_version if lockfile else get_pyodide_version(PYSCRIPT_VERSION), ...)`).
- **Rationale**: Allows `2026.3.1` (`0.29.3`) during the pre-promotion sweep and `2026.7.3` (`314.0.3`) afterward to download the exact files that exist on jsDelivr without HTTP 404 failures, while updating the exported constant `PYODIDE_RUNTIME_ASSETS` to reflect the active runtime. Note that `get_pyodide_runtime_assets` lives under `packages/*/src` and must carry a complete Google-style docstring (`api-docstrings`).
- **Alternative rejected**: Probing jsDelivr with HTTP fallback from `pyodide.asm.js` to `pyodide.asm.mjs` — adds unnecessary network requests, fails offline in tests, and leaves `generate_lockfile()` recording nonexistent URLs.

### 3. Lockfile invalidation on `pyscript_version` / `pyodide_version` mismatch
- **Choice**: Extend `resolve_lockfile()` in `packages/webcompy-cli/src/webcompy_cli/_lockfile.py` (or a version check helper called alongside `validate_lockfile()`) so an existing lockfile is reused only when dependencies match AND `existing.pyscript_version == pyscript_version` AND `existing.pyodide_version == get_pyodide_version(pyscript_version)`.
- **Rationale**: In `resolve_build_artifacts()` (`_build.py`) and `webcompy lock` (`_lock.py`), `resolve_lockfile()` is called with `PYSCRIPT_VERSION`. Currently, if a developer or CI workspace has a pre-existing `webcompy-lock.json` on disk (e.g., `docs_app/webcompy-lock.json` from a previous build), `resolve_lockfile()` returns it unchanged even after `PYSCRIPT_VERSION` bumps, causing `docs_app` or E2E apps to continue referencing `0.29.3` wheels with `2026.7.3` or failing `verify_and_update_runtime_assets()`. Keeping `validate_lockfile(lockfile, dependencies)`'s existing 2-arg signature preserves backward compatibility for existing callers/tests, while adding runtime version checking inside `resolve_lockfile()` (with optional override parameter if needed cleanly).
- **Alternative rejected**: Mutating `validate_lockfile()`'s required positional parameters — would break existing unit tests calling `validate_lockfile(lockfile, dependencies)` directly.

### 4. Pre-promotion probe sweep gate and brittle assertion cleanup
- **Choice**:
  1. Run `scripts/run-browser-version-sweep.sh 2026.7.3` while `PYSCRIPT_VERSION` is still `"2026.3.1"` so the regression gate compares `2026.3.1` vs `2026.7.3` directly across all 17 probes in `tests/browser/probes/**`.
  2. Only after confirming 0 regressions (`regressions == []`), bump `PYSCRIPT_VERSION = "2026.7.3"` in `packages/webcompy-server/src/webcompy_server/_html.py`.
  3. Update `tests/test_pwa_sw_generation.py` to check `f"{PYSCRIPT_BASE_URL}/core.js"` instead of hardcoding `"2026.3.1"`, and update `e2e/core/test_standalone.py` to extract the `./core-*.js` import specifier from `core.js` instead of hardcoding `"core-BuLtL7jM.js"`.
- **Rationale**: Respects the version-sweep governance in `browser-probes/spec.md` and keeps future PyScript bumps free of brittle hash updates.

## Risks / Trade-offs

- **[Risk] Behavioral deltas in Pyodide `314.0.3` / CPython `3.14.0` (WebLoop ordering, `create_proxy`/`destroy`, `js.undefined`, PEP 649 annotations, UTF-16 DOM)**: `2026.7.3` updates Emscripten to `5.0.3` and Python to `3.14.0`.
  -> **Mitigation**: Run `scripts/run-browser-version-sweep.sh 2026.7.3` (17 environment probes), inspect `WEBCOMPY_RUN_DUAL=1` output via `scripts/run-browser-tests.sh --dual`, and run the entire core + docs E2E suite before committing the promotion.
- **[Risk] Pyodide `314.0.3` uses `pyemscripten_2026_0_wasm32` wheel tags instead of `pyodide_2025_0_wasm32`**: Package classification or bundled wheel extraction could misclassify WASM packages if it checks `"pyodide"` in the wheel tag.
  -> **Mitigation**: Verified `_classify_from_pyodide_lock()` checks `"wasm32" in file_name`, which matches `pyemscripten_2026_0_wasm32`. Verified all `docs_app` and harness dependencies exist in Pyodide `314.0.3`'s lockfile.
- **[Risk] Pre-existing `.webcompy_modules` / `webcompy-lock.json` caches in developer or E2E workspaces**: Stale caches might interfere if `resolve_lockfile()` still reuses old versions.
  -> **Mitigation**: Invalidating lockfiles on `pyscript_version` / `pyodide_version` mismatch ensures clean regeneration; runtime assets are already namespaced by `runtime-assets/{pyscript_version}/` and `pyodide-packages/{pyodide_version}/`.
- **[Risk] Transient jsDelivr / pyscript.net network timeouts when downloading `offline_2026.7.3.zip` and `314.0.3` assets**: Initial local cache population makes multiple CDN requests.
  -> **Mitigation**: Run `scripts/run-browser-version-sweep.sh` first so assets populate `.webcompy_modules` cleanly; ensure `tests/test_*` unit tests mock all network calls cleanly.
