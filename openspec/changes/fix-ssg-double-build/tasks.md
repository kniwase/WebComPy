## 1. Expose BuildArtifacts via _ServingApp

- [x] 1.1 Add `artifacts: BuildArtifacts` typed field to `_ServingApp` class in `_server.py`
- [x] 1.2 Update `_ServingApp.__init__()` to accept and store `artifacts`
- [x] 1.3 Pass `artifacts` to `_ServingApp()` constructor in `create_asgi_app()`
- [x] 1.4 Remove `app_version` from `html_generator` partial binding (unused parameter)

## 2. Eliminate duplicate resolve_build_artifacts() call in _generate.py

- [x] 2.1 Reorder `_generate.py`: call `create_asgi_app()` before static file operations that need artifacts
- [x] 2.2 Remove standalone `resolve_build_artifacts()` call (line 69)
- [x] 2.3 Replace `artifacts.app_package_files` with `serving.artifacts.app_package_files` for wheel file writing
- [x] 2.4 Replace `artifacts.wasm_asset_files` with `serving.artifacts.wasm_asset_files`
- [x] 2.5 Replace `artifacts.runtime_asset_files` with `serving.artifacts.runtime_asset_files`
- [x] 2.6 Remove `cdn_temp_dir_obj` variable and finally-block cleanup (handled by `create_asgi_app()`)

## 3. Make generate_app_version() deterministic

- [x] 3.1 Replace `datetime.now()` with `"0.0.0"` in `generate_app_version()` in `_utils.py`
- [x] 3.2 Remove unused `datetime` import if no longer needed

## 4. Remove unused app_version from generate_html()

- [x] 4.1 Remove `app_version` parameter from `generate_html()` signature in `_html.py`
- [x] 4.2 Remove `app_version` parameter from `_generate_html_impl()` signature
- [x] 4.3 Remove `app_version` from `generate_html()` argument forwarding to `_generate_html_impl()`

## 5. Verification

- [x] 5.1 Run `uv run ruff check .` — ensure no lint errors
- [x] 5.2 Run `uv run ruff format --check .` — ensure formatting is correct
- [x] 5.3 Run `uv run pyright` — ensure no new type errors
- [x] 5.4 Run `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs` — ensure all unit tests pass
- [x] 5.5 Run `scripts/run-e2e-tests.sh --serving-mode=static` — verify E2E tests pass in static mode
- [x] 5.6 Run `scripts/run-e2e-tests.sh --serving-mode=prod` — verify E2E tests pass in prod mode
