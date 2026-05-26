## 1. Extract shared setup logic into _build.py

- [ ] 1.1 Create `webcompy/cli/_build.py` with `BuildArtifacts` dataclass containing all fields currently computed in both `_generate.py` and `_server.py`: `app_version`, `wheel_filename`, `extra_wheel_filenames`, `pyodide_package_names`, `wasm_local_urls`, `lockfile_url`, `runtime_serving`, `app_package_files` (dev mode), `wasm_asset_files`, `runtime_asset_files`, `static_file_routes`, `dist_dir` (SSG mode), `dev_mode`, `cdn_temp_dir_obj`
- [ ] 1.2 Implement `resolve_build_artifacts(app, build_config, *, dev_mode=False, dist_dir=None) -> BuildArtifacts` — move dependency resolution, lockfile handling, WASM/runtime asset downloading, wheel building, and CDN extraction from `_generate.py` lines 38-283 and `_server.py` lines 56-291 into this function. Preserve the exact same logic, just in one place. Include `cdn_temp_dir_obj` in `BuildArtifacts` so callers can manage its lifecycle.
- [ ] 1.3 Refactor `_server.py:create_asgi_app()` — replace ~230 lines of setup code with a call to `resolve_build_artifacts()`; use `artifacts.app_package_files`, `artifacts.wasm_asset_files`, etc. for route creation
- [ ] 1.4 Refactor `_generate.py:generate_static_site()` — replace ~240 lines of setup code with a call to `resolve_build_artifacts()`; use `artifacts.dist_dir`, `artifacts.wheel_filename`, etc. for file writing
- [ ] 1.5 Add unit tests for `resolve_build_artifacts()` — verify the dataclass is populated correctly with mocked dependency resolution

## 2. Make generate_html() async

- [ ] 2.1 Change `generate_html()` in `webcompy/cli/_html.py` from `def` to `async def`. The return type remains `str` but the function is now a coroutine. No logic changes inside the function body — this is a signature change only. The async rendering pipeline (from `feat/async-rendering-pipeline`) will later add `await` calls inside this function.
- [ ] 2.2 Update `_server.py:send_html()` — change from sync `HTMLResponse(html_generator())` to `async def send_html()` with `html = await html_generator(); return HTMLResponse(html)`. Update the history-mode handler (lines 299-310) and the hash-mode pre-rendering (lines 314-316).
- [ ] 2.3 Update hash-mode pre-rendering in `_server.py` — extract the `with app.di_scope: html = html_generator()` block into a separate async function `_pre_render_hash_mode_html(app)` that awaits `html_generator()` and caches the result. `create_asgi_app()` remains synchronous and returns an ASGI app that reads the cached HTML in the hash-mode handler.
- [ ] 2.4 Update `webcompy/testing/_asgi.py:create_test_asgi_app()` — since `html_generator` is now async, update the test ASGI handler to await it. Verify that `httpx.ASGITransport`-based tests still pass.
- [ ] 2.5 Run lint and type check to verify all callers of `generate_html()` are updated

## 3. Add mode parameter to create_asgi_app()

- [ ] 3.1 Add `mode: Literal["dev", "ssg"] = "dev"` parameter to `create_asgi_app()`. When `mode="ssg"`: skip SSE reload route, skip dev-mode cache headers, force `build_config.server.dev = False`. `create_asgi_app()` remains `def` (synchronous) — uvicorn.run() expects a synchronous app factory.
- [ ] 3.2 For hash-mode apps, add `_pre_render_hash_mode_html(app)` as a separate async function. It enters `app.di_scope`, sets the path to `/`, awaits `html_generator()`, and stores the cached HTML. `create_asgi_app()` returns a handler that reads the cached HTML.
- [ ] 3.3 Update `run_server()` in `_server.py` — call `create_asgi_app()` synchronously. For hash-mode, call `asyncio.run(_pre_render_hash_mode_html(app))` after creation.
- [ ] 3.4 Update the CLI entry point in `webcompy/cli/__main__.py` for the `start` command — no change needed, `run_server()` remains synchronous and passes the ASGI app to `uvicorn.run()`.
- [ ] 3.5 Add unit tests for `mode="ssg"` — verify that SSE route is excluded, dev cache headers are absent, and `build_config.server.dev` is forced to `False`

## 4. Restructure generate_static_site() to use ASGITransport

- [ ] 4.1 Change `generate_static_site()` from `def` to `async def` in `_generate.py`. The function now creates an ASGI app via `create_asgi_app()` and fetches routes via `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))`.
- [ ] 4.2 Implement the SSG route-fetching logic: for history-mode apps, iterate `app.routes`, compute expanded paths (handling `path_params`), fetch each via `client.get()`, and write HTML to `dist/{path}/index.html`. For hash-mode apps, fetch the root route and write to `dist/index.html`. For 404, set a special path and write `dist/404.html`.
- [ ] 4.3 Remove the old direct `html_generator()` call path from `_generate.py`. The `html_generator` partial is no longer created in `_generate.py` — it's handled by `create_asgi_app()`.
- [ ] 4.4 Update the CLI entry point for `generate` command in `webcompy/cli/__main__.py` — call `asyncio.run(generate_static_site())` instead of calling it synchronously.
- [ ] 4.5 Keep the dist directory creation, `.nojekyll`, `CNAME`, static file copying, and wheel/asset file writing in `_generate.py` — these are file-system operations that happen before or after the ASGI fetches.

## 5. Integration and verification

- [ ] 5.1 Update `webcompy/testing/_asgi.py:create_test_asgi_app()` — if `create_asgi_app()` signature changed, update the test utility accordingly. The test utility should still work with `httpx.ASGITransport`.
- [ ] 5.2 Run existing SSG tests — `tests/test_build_wheels.py`, `tests/test_build_standalone.py`, `tests/test_build_runtime_local.py` — to verify SSG output is unchanged
- [ ] 5.3 Run existing dev server tests to verify `create_asgi_app()` still works for dev mode
- [ ] 5.4 Run lint: `uv run ruff check .`
- [ ] 5.5 Run type check: `uv run pyright`
- [ ] 5.6 Run unit tests: `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs`
- [ ] 5.7 Run E2E tests: `scripts/run-e2e-tests.sh` to verify no regressions
- [ ] 5.8 Generate the docs site: `uv run python -m webcompy generate --config docs_app.webcompy_config` and verify output matches expected structure