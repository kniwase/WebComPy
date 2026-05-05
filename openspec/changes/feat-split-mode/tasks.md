# Tasks: Split Mode — Detached Wheel Serving for Browser Cache Optimization

**Strategy**: Multiple local wheel URLs in `py-config.packages` (confirmed working by experiment 2026-05-05).

- [x] **Task 0: Experiment to determine viable loading strategy**
  - Built minimal test with 2-4 local wheels in `.tmp/experiment/dist/` served by static HTTP server
  - Tested Strategy A (`packages` with multiple local URLs): ✅ works cleanly, no timeout
  - Tested Strategy B serial (`files` + `micropip.install`): ❌ micropip filename parsing fails
  - Tested Strategy B parallel (`asyncio.gather`): ❌ Pyodide `set_wheel_metadata` error
  - Tested Strategy C (`files` + `emfs://` URL): ❌ micropip cannot parse `emfs://` scheme
  - **Decision**: Strategy A confirmed as the only viable approach

---

- [x] **Task 1: Add `wheel_mode` to AppConfig**
  **Estimated time: ~30 min**
  - Add `wheel_mode: Literal["bundled", "split"] = "bundled"` to `AppConfig` dataclass in `webcompy/app/_config.py`
  - Update `test_config_dataclasses.py` with tests for default and explicit values
  - No CLI flag needed initially — `wheel_mode` is set in `AppConfig` only

- [x] **Task 2: Add `--wheel-mode` CLI flag**
  **Estimated time: ~20 min**
  - Add `--wheel-mode` argument (choices: `bundled`, `split`) to `start` and `generate` subcommands in `webcompy/cli/_argparser.py`
  - Override `app.config.wheel_mode` from CLI flag in `_server.py:run_server()` and `_generate.py:generate_static_site()`

- [x] **Task 3: Reintroduce `make_browser_webcompy_wheel()`**
  **Estimated time: ~45 min**
  - Reference implementation: `d474c65` on `feat/wheel-split` branch
  - Add function to `webcompy/cli/_wheel_builder.py`:
    - Takes `webcompy_package_dir`, `dest`, `version`
    - Filters out any path with `cli` in its parts
    - Produces `webcompy-py3-none-any.whl` (stable filename, no hash)
  - Add `get_stable_wheel_filename(name: str) -> str` helper: `{normalized_name}-py3-none-any.whl`
  - Write unit tests in `tests/test_wheel_builder.py`

- [x] **Task 4: Update `make_webcompy_app_package()` for split mode**
  **Estimated time: ~30 min**
  - In split mode: produce app-only wheel (with content-hash, no webcompy bundled)
  - In bundled mode: existing behavior unchanged
  - `_server.py` and `_generate.py` call the right variant based on `wheel_mode`

- [x] **Task 5: Implement per-dependency wheel generation**
  **Estimated time: ~30 min**
  - Use existing `make_wheel()` with stable filenames for each pure-Python dependency
  - Each dep wheel: `{dep_name}-py3-none-any.whl`
  - Handle both locally-installed deps and CDN-downloaded pure-Python packages

- [x] **Task 6: Update HTML generation for split mode**
  **Estimated time: ~45 min**
  - Update `generate_html()` signature to accept list of wheel filenames instead of single filename
  - Construct `py_packages` with framework URL, dep URLs, app URL (content-hash), WASM names
  - Example output:
    ```
    packages = [
        "/_.../webcompy-py3-none-any.whl",
        "/_.../flask-py3-none-any.whl",
        "/_.../myapp-0+sha.{hash8}-py3-none-any.whl",
        "numpy",  # WASM CDN
    ]
    ```
  - Write unit tests

- [x] **Task 7: Update dev server for multi-wheel serving**
  **Estimated time: ~1 hour**
  - Build all wheels (framework + deps + app) in `create_asgi_app()`
  - Serve all from `/_webcompy-app-package/{filename}`
  - Set cache headers per wheel type:
    - `webcompy-py3-none-any.whl` → `Cache-Control: max-age=86400, must-revalidate`
    - `{dep}-py3-none-any.whl` → `Cache-Control: max-age=86400, must-revalidate`
    - `{app}-{hash}-py3-none-any.whl` → `Cache-Control: no-cache` (dev only)
  - Reference: `d474c65` cache header logic

- [x] **Task 8: Update SSG for multi-wheel output**
  **Estimated time: ~30 min**
  - Write all wheel files to `dist/_webcompy-app-package/`
  - Update HTML generation to reference all wheel URLs

- [x] **Task 9: Update E2E tests for split mode**
  **Estimated time: ~1 hour**
  - Update `static_site` fixture to expect 2+ wheel files (not exactly 1)
  - Add split-mode specific tests:
    - Framework wheel filename is stable
    - App wheel has content-hash in filename
    - Both wheel URLs appear in generated HTML
    - Dep wheels present when dependencies are configured
  - Test dev server and static serving paths

- [x] **Task 10: Lint, typecheck, and test validation**
  **Estimated time: ~20 min**
  - `uv run ruff check .`
  - `uv run pyright`
  - `uv run python -m pytest tests/ --tb=short`
