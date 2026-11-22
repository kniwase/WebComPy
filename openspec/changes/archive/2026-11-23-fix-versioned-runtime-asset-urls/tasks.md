# Tasks

## 1. Core versioned runtime path prefix and server/CLI alignment

- [x] 1.1 Add `get_runtime_asset_prefix(pyscript_version: str = PYSCRIPT_VERSION)` in `packages/webcompy-server/src/webcompy_server/_html.py`, update `_generate_html_impl()` to emit `{base_url}{runtime_prefix}/...` URLs when `runtime_serving="local"`, and update `tests/test_html_generation.py` and `tests/test_runtime_local_integration.py` (preserving `tests/.dualrun/ineligible.json` line pins).
- [x] 1.2 Update `packages/webcompy-cli/src/webcompy_cli/_generate.py`, `_server.py` (versioned route + `Cache-Control` headers for prod `immutable` and dev `max-age=86400`), and `_pwa.py` (`RUNTIME_ASSET_PREFIX`); update `tests/test_pwa_sw_generation.py`, `tests/test_build_runtime_local.py`, `tests/test_build_standalone.py`, and add ASGI runtime-asset header/404 tests in `tests/test_cli_resource_endpoint.py`.
- [x] 1.3 Parameterize `packages/webcompy-cli/src/webcompy_cli/_browser_test_harness.py` (`build_py_config`, `generate_harness_html`, `create_harness_server`) with `pyscript_version` using `get_runtime_asset_prefix()`, and update/extend `tests/test_browser_test_harness.py`.

## 2. Docs demo iframe inheritance and E2E updates

- [x] 2.1 Update `docs_app/static/_demos/standard.html` to dynamically resolve and validate `core.js`, `core.css`, `interpreter`, and `lockFileURL` from the parent document, update `e2e/core/test_standalone.py` and `e2e/core/test_runtime_local.py` for versioned paths, and verify `standalone`, `runtime-local`, `docs-home`, `docs-demos`, and `docs-matplotlib` E2E suites.

## 3. Full verification

- [x] 3.1 Run all static, docstring, and type checks (`ruff check .`, `ruff format --check .`, `pydoclint`, `check-browser-imports.py`, `check-docstrings.py`, `check-doc-spec-refs.py`, `pyright`) and the full CPython unit test suite (`uv run python -m pytest tests/ --tb=short`), confirming zero failures.
- [x] 3.2 Run browser-tier tests (`scripts/run-browser-tests.sh --tb=short`, `--probes --tb=short`), verify `docs_app` SSG output (`dist/_webcompy-assets/{PYSCRIPT_VERSION}/...` present and unversioned `dist/_webcompy-assets/core.js` absent), and verify the full E2E suite (`scripts/run-e2e-tests.sh --parallel`).

## 4. Spec synchronization and archive

- [x] 4.1 Archive `fix-versioned-runtime-asset-urls`, sync delta specs to `openspec/specs/`, update the legacy unversioned runtime path references in `openspec/specs/cli/spec.md`, and verify `openspec validate --specs`, `openspec validate --changes`, `scripts/check-doc-spec-refs.py`, and `scripts/check-docstrings.py` all pass.
