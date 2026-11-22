# Tasks

## 1. Multi-version PyScript/Pyodide mapping and runtime asset downloader

- [x] 1.1 Update `PYSCRIPT_TO_PYODIDE` in `packages/webcompy-cli/src/webcompy_cli/_pyodide_lock.py` to map `"2026.7.3": "314.0.3"` alongside `"2026.3.1": "0.29.3"` (and fix the error message module path hint to `webcompy_cli/_pyodide_lock.py`), add/update unit tests in `tests/test_pyodide_lock.py`, and verify with `uv run python -m pytest tests/test_pyodide_lock.py -q`.
- [x] 1.2 Add `get_pyodide_runtime_assets(pyodide_version)` (with Google-style docstring) and update `PYODIDE_RUNTIME_ASSETS` in `packages/webcompy-cli/src/webcompy_cli/_runtime_downloader.py` so Pyodide `< 0.30` uses `pyodide.asm.js` and `>= 0.30` / `>= 314.0.0` uses `pyodide.asm.mjs`; wire `get_pyodide_runtime_assets()` into `download_runtime_assets()` and `generate_lockfile()` (`packages/webcompy-cli/src/webcompy_cli/_lockfile.py`), replace the hardcoded `"0.29.3"` fallback in `packages/webcompy-cli/src/webcompy_cli/_build.py` with `get_pyodide_version(PYSCRIPT_VERSION)`, update `tests/test_runtime_downloader.py`, and verify with `uv run python -m pytest tests/test_runtime_downloader.py -q`.
- [x] 1.3 Update `resolve_lockfile()` in `packages/webcompy-cli/src/webcompy_cli/_lockfile.py` to invalidate and regenerate an existing `webcompy-lock.json` when its recorded `pyscript_version` or `pyodide_version` differs from the active `pyscript_version` / `get_pyodide_version(pyscript_version)`, add unit tests covering mismatched versions in `tests/test_lockfile.py`, and verify with `uv run python -m pytest tests/test_lockfile.py tests/test_pyodide_downloader.py tests/test_build_runtime_local.py tests/test_build_standalone.py -q`.

## 2. Pre-promotion browser probe sweep (2026.3.1 vs 2026.7.3)

- [x] 2.1 Run `scripts/run-browser-version-sweep.sh 2026.7.3` while `PYSCRIPT_VERSION` is still `"2026.3.1"`, inspect `artifacts/browser-version-sweep.json` and `artifacts/probes-candidate.json`, and verify `regressions == []` with all 17 probes in `tests/browser/probes/**` passing at candidate `2026.7.3`.

## 3. Promote pinned PyScript version and generalize brittle tests

- [ ] 3.1 Update `PYSCRIPT_VERSION = "2026.7.3"` in `packages/webcompy-server/src/webcompy_server/_html.py` and verify `uv run python -c "from webcompy_server._html import PYSCRIPT_VERSION, PYSCRIPT_BASE_URL; print(PYSCRIPT_VERSION, PYSCRIPT_BASE_URL)"` outputs `2026.7.3 https://pyscript.net/releases/2026.7.3`.
- [ ] 3.2 Update brittle version/chunk-hash assertions in `tests/test_pwa_sw_generation.py` (assert `f"{PYSCRIPT_BASE_URL}/core.js"`) and `e2e/core/test_standalone.py` (resolve the `./core-*.js` import from `dist/_webcompy-assets/core.js` instead of hardcoding `core-BuLtL7jM.js`), and verify both tests pass via `uv run python -m pytest tests/test_pwa_sw_generation.py -q` and `scripts/run-e2e-tests.sh standalone --serving-mode=static`.

## 4. End-to-end, browser-tier, SSG, and static verification

- [ ] 4.1 Run all static and docstring checks (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pydoclint packages/webcompy/src/webcompy packages/webcompy-server/src/webcompy_server packages/webcompy-cli/src/webcompy_cli packages/webcompy-testing/src/webcompy_testing`, `uv run python scripts/check-browser-imports.py`, `python3 scripts/check-docstrings.py`, `python3 scripts/check-doc-spec-refs.py`, `uv run pyright`) and verify zero errors.
- [ ] 4.2 Run the full CPython unit test suite (`uv run python -m pytest tests/ --tb=short`) and wheel smoke build (`uv build --package webcompy` and verify `webcompy/template/__init__.py` is present), confirming all unit tests pass.
- [ ] 4.3 Run browser-tier tests (`scripts/run-browser-tests.sh --tb=short`, `scripts/run-browser-tests.sh --probes --tb=short`, and informational `--dual` sweep), verify `docs_app` SSG regeneration (`uv run python -m webcompy generate --config docs_app.webcompy_config` producing `docs_app/webcompy-lock.json` pinned to `2026.7.3` / `314.0.3` and Python 3.14 wheels), and verify core + docs E2E suites pass via `scripts/run-e2e-tests.sh --parallel`.

## 5. Spec synchronization and change archive

- [ ] 5.1 Confirm `openspec/SPEC_INDEX.md` and `.agents/skills/webcompy-review/SKILL.md` align with the modified `dependency-resolver`, `pyscript-bundle`, and `lockfile` specs, sync delta specs to `openspec/specs/`, archive `feat-pyscript-2026-7-pyodide-314`, and verify `/home/kniwase/.npm-global/bin/openspec validate --specs`, `/home/kniwase/.npm-global/bin/openspec validate --changes`, `python3 scripts/check-docstrings.py`, and `python3 scripts/check-doc-spec-refs.py` all pass.
