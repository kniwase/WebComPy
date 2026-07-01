## 1. Workspace Setup

- [x] 1.1 Create root `pyproject.toml` as uv workspace with `members = ["packages/*"]`
- [x] 1.2 Create `packages/webcompy/pyproject.toml` with zero runtime dependencies and extras for server/cli/testing/full
- [x] 1.3 Create `packages/webcompy-server/pyproject.toml` with dependencies: `webcompy`, `httpx`
- [x] 1.4 Create `packages/webcompy-cli/pyproject.toml` with dependencies: `webcompy`, `webcompy-server`, `starlette`, `uvicorn`, `sse-starlette`, `aiofiles`; optional: `playwright`, `packaging`
- [x] 1.5 Create `packages/webcompy-testing/pyproject.toml` with dependencies: `webcompy`, `webcompy-server`, `starlette`, `beautifulsoup4`
- [x] 1.6 Create `src/` layout for all four packages with `__init__.py` stubs
- [x] 1.7 Move files directly to final destinations in one pass:
    - `webcompy/` → `packages/webcompy/src/webcompy/` (keep all files except `cli/`, `testing/`, `ports/_server/`)
    - `webcompy/ports/_server/` → `packages/webcompy-server/src/webcompy_server/ports/`
    - `webcompy/cli/_html.py` → `packages/webcompy-server/src/webcompy_server/_html.py`
    - `webcompy/cli/` (remaining) → `packages/webcompy-cli/src/webcompy_cli/`
    - `webcompy/testing/` → `packages/webcompy-testing/src/webcompy_testing/`
- [x] 1.8 Update `webcompy/_version.py` to remove server-only dependencies reference

## 2. RenderContext ABC Refactoring

- [x] 2.1 Add `ABC` base to `RenderContext` in `webcompy/app/_render_context.py`
- [x] 2.2 Extract `_register_ports()` as `@abstractmethod` from current port provisioning logic
- [x] 2.3 Create `BrowserRenderContext(RenderContext)` subclass in core that implements `_register_ports()` with all seven `Browser*Port` instances (incl. `BrowserMediaQueryPort` from main #178)
- [x] 2.4 Add `render_html()` override to `BrowserRenderContext` that raises `WebComPyException` (sync, since it just raises)
- [x] 2.5 Remove `Server*Port` imports and `else` branch from `RenderContext.__init__`; keep `self._initial_theme` and `self._cookie_header` initialization and theme startup logic in base
- [x] 2.6 Add `_render_context_class` parameter to `WebComPyApp.__init__` (default `None`)
- [x] 2.7 Update `WebComPyApp.create_render_context()` to use `self._render_context_class or BrowserRenderContext`
- [x] 2.8 Update `WebComPyApp.dispose()` to remove `ENVIRONMENT` check for `_set_app_di_scope(None)` / `_set_app_instance(None)` — apply unconditionally

## 3. webcompy-server Package

- [x] 3.1 Verify server port files are at `packages/webcompy-server/src/webcompy_server/ports/` (moved in 1.7); update `__init__.py` to re-export all port classes
- [x] 3.2 Update imports within moved files: remove `_server` from internal relative imports, update `from webcompy.*` imports as needed
- [x] 3.3 Verify `_html.py` is at `packages/webcompy-server/src/webcompy_server/_html.py` (moved in 1.7)
- [x] 3.4 Update `_html.py` imports: replace `from webcompy.cli.*` with `from webcompy_server.*` where applicable
- [x] 3.5 Create `webcompy_server/_context.py` with `ServerRenderContext(RenderContext)` implementing `_register_ports()` (all 7 Server*Ports incl. `ServerMediaQueryPort` from main #178) and `async def render_html()` using `webcompy_server._html.generate_html`; `ServerCookiePort` receives `self._cookie_header` stored by base `__init__`
- [x] 3.6 Create `webcompy_server/__init__.py` exporting `configure_server_context(app)`, `ServerRenderContext`, `generate_html`, and all port/symbol re-exports
- [x] 3.7 Ensure `webcompy_server/ports/__init__.py` re-exports all Server*Port classes, VirtualDOMNode, and VirtualDOMEvent

## 4. webcompy-cli Package

- [x] 4.1 Verify remaining CLI files are at `packages/webcompy-cli/src/webcompy_cli/` (moved in 1.7)
- [x] 4.2 Update all `from webcompy.cli.*` intra-module imports to `from webcompy_cli.*`
- [x] 4.3 Update `_server.py` and `_generate.py`: import `configure_server_context` from `webcompy_server`, call it before `app.create_render_context()`
- [x] 4.4 Update `_server.py` and `_generate.py`: replace `from webcompy.cli._html import generate_html` with `from webcompy_server._html import generate_html`; note that `generate_html()` and request handlers are `async def` (added in main #177)
- [x] 4.5 Update `_lockfile.py`, `_lockfile_sync.py`, `_dependency_resolver.py`, `_pyodide_downloader.py`, `_pyodide_lock.py`, `_runtime_downloader.py`, `_static_files.py`, `_exception.py`: update internal imports
- [x] 4.6 Update `_wheel_builder.py`: remove `_BROWSER_ONLY_EXCLUDE`; browser wheel now contains only `webcompy` core
- [x] 4.7 Update `config/_build_config.py` and `config/_server_config.py`: adjust import paths
- [x] 4.8 Update `webcompy_cli/__init__.py` to re-export `create_asgi_app`, `run_server`, `generate_static_site`, `discover_config`, `run_inspect`
- [x] 4.9 Update `template_data/webcompy_config.py`: change `from webcompy.cli.config` to `from webcompy_cli.config`
- [x] 4.10 Update `_init_project.py` to use updated template

## 5. webcompy-testing Package

- [x] 5.1 Verify testing files are at `packages/webcompy-testing/src/webcompy_testing/` (moved in 1.7); ensure `_utils.py` with `run_sync` helper is included
- [x] 5.2 Update imports: `webcompy.ports._server._virtual_dom` → `webcompy_server.ports` (VirtualDOMNode, VirtualDOMEvent)
- [x] 5.3 Update imports: `webcompy.ports._server._dom` → `webcompy_server.ports._dom` (ServerDOMPort)
- [x] 5.4 Update `_asgi.py`: `from webcompy.cli._html import _HtmlElement, generate_html` → `from webcompy_server._html import _HtmlElement, generate_html`
- [x] 5.5 Update `_renderer.py`: `from webcompy.ports._server._dom import ServerDOMPort` → from `webcompy_server`; `format_html` import from updated path
- [x] 5.6 Update `_scope.py` imports for new package
- [x] 5.7 Update `webcompy_testing/__init__.py` to re-export all public symbols

## 6. Core Shim and Backward Compatibility

- [x] 6.1 Update `webcompy/__main__.py`: delegate to `webcompy_cli._argparser.main` with error message if `webcompy-cli` not installed
- [x] 6.2 Create `webcompy/cli/config/__init__.py` shim: re-export from `webcompy_cli.config` with deprecation warning
- [x] 6.3 Create `webcompy/testing/__init__.py` shim: re-export from `webcompy_testing` with deprecation warning
- [x] 6.4 Keep empty `webcompy/cli/__init__.py` and `webcompy/ports/_server/__init__.py` stubs that warn and re-export from new packages
- [x] 6.5 Update `webcompy/__init__.py`: remove conditional `cli` import (`if ENVIRONMENT == "other"`); import shim stubs instead

## 7. Configuration and CI Updates

- [x] 7.1 Update root `pyproject.toml`: remove old `dependencies`, `[tool.hatch.build]`, `[tool.pytest.ini_options]`; add `[tool.uv.workspace]`
- [x] 7.2 Update `pyright` config: adjust `include`/`exclude` for new package layout
- [x] 7.3 Update `ruff` config: adjust `known-first-party` for new package names
- [x] 7.4 Update `pytest` config: adjust `testpaths` for new layout
- [x] 7.5 Update `.github/workflows/ci.yml`: adjust paths, install commands, and matrix for multi-package
- [x] 7.6 Update `.opencode/agents/ci-review.md` if any framework invariants changed

## 8. README, CONTRIBUTING, and Documentation Updates

- [x] 8.1 Update `README.md`: installation instructions show `pip install webcompy[full]` / `webcompy[cli]` extras; CLI usage notes requirement of `webcompy-cli`
- [x] 8.2 Update `README.ja.md`: same changes in Japanese
- [x] 8.3 Update `CONTRIBUTING.md`: development setup references uv workspace; quick commands updated for workspace structure
- [x] 8.4 Update `CONTRIBUTING.ja.md`: same changes as CONTRIBUTING.md in Japanese
- [x] 8.5 Update `AGENTS.md`:
    - Project Structure: show `packages/` layout with 4 sub-packages; update path references
    - File→Spec Mapping: add rows for `webcompy_server/ports/`, `webcompy_cli/`, `webcompy_testing/`
    - Dual-Environment note: "single codebase" guarantee narrowed to `webcompy` core
- [x] 8.6 Update `docs_app/` imports and config to use new packages
- [x] 8.7 Update `scripts/run-e2e-tests.sh` for new package structure
- [x] 8.8 Run `uv lock` from workspace root to generate lockfile

## 9. Verification

- [x] 9.1 Run `uv run ruff check .` from workspace root — all packages lint clean
- [x] 9.2 Run `uv run pyright` from workspace root — type checking passes
- [x] 9.3 Run `uv run python -m pytest tests/ --tb=short` — unit tests pass (note: some tests create `RenderContext` directly and may need updates for the ABC hierarchy)
- [x] 9.4 Run `uv run python -m webcompy start --dev --app docs_app.bootstrap:app` — dev server starts
- [x] 9.5 Run `uv run python -m webcompy generate --app docs_app.bootstrap:app` — SSG produces output
- [x] 9.6 E2E tests: core 20/20 passed, docs 8/8 passed (fixed PYTHONPATH in conftest.py)
- [x] 9.7 Verify `pip install packages/webcompy` installs only core (no starlette, uvicorn, etc.)
- [x] 9.8 ~~Verify `pip install packages/webcompy[full]` installs all four packages~~ (skip: sub-packages not yet published to PyPI; workspace `uv sync` confirmed working)
- [x] 9.9 Verify `from webcompy.cli.config import WebComPyBuildConfig` works via shim with deprecation warning
- [x] 9.10 Verify `from webcompy.testing import TestRenderer` works via shim with deprecation warning
