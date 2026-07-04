## 1. Extract shared setup logic into _build.py

- [x] 1.1 Create `packages/webcompy-cli/src/webcompy_cli/_build.py` with `BuildArtifacts` dataclass containing all fields currently computed in both `_generate.py` and `_server.py`: `app_version`, `wheel_filename`, `extra_wheel_filenames`, `pyodide_package_names`, `wasm_local_urls`, `lockfile_url`, `runtime_serving`, `app_package_files` (dev/prod mode), `wasm_asset_files`, `runtime_asset_files`, `dist_dir` (SSG mode), `dev_mode`, `cdn_temp_dir_obj`
- [x] 1.2 Implement `resolve_build_artifacts(app, build_config, *, dev_mode=False, dist_dir=None) -> BuildArtifacts` — move dependency resolution, lockfile handling, WASM/runtime asset downloading, wheel building, and CDN extraction from `_generate.py` lines 38-283 and `_server.py` lines 56-291 into this function. Preserve the exact same logic, just in one place. Include `cdn_temp_dir_obj` in `BuildArtifacts` so callers can manage its lifecycle.
- [x] 1.3 Refactor `_server.py:create_asgi_app()` — replace ~230 lines of setup code with a call to `resolve_build_artifacts()`; use `artifacts.app_package_files`, `artifacts.wasm_asset_files`, etc. for route creation
- [x] 1.4 Refactor `_generate.py:generate_static_site()` — replace ~240 lines of setup code with a call to `resolve_build_artifacts()`; use `artifacts.dist_dir`, `artifacts.wheel_filename`, etc. for file writing
- [x] 1.5 Add unit tests for `resolve_build_artifacts()` — verify the dataclass is populated correctly with mocked dependency resolution

## 2. Make generate_html() async

- [x] 2.1 Change `generate_html()` in `packages/webcompy-server/src/webcompy_server/_html.py` from `def` to `async def`. The return type remains `str` but the function is now a coroutine. No logic changes inside the function body — this is a signature change only. The async rendering pipeline (from `feat/async-rendering-pipeline`) will later add `await` calls inside this function.
- [x] 2.2 Update `_server.py:send_html()` — change from sync `HTMLResponse(html_generator())` to `async def send_html()` with `html = await html_generator(); return HTMLResponse(html)`. Update the history-mode handler and the hash-mode handler.
- [x] 2.3 Update hash-mode pre-rendering in `_server.py` — extract the render-and-cache block into a separate async function `_pre_render_hash_mode_html(app)` that awaits `html_generator()` and caches the result. `create_asgi_app()` remains synchronous and returns an ASGI app that reads the cached HTML in the hash-mode handler.
- [x] 2.4 Update `packages/webcompy-testing/src/webcompy_testing/_asgi.py:create_test_asgi_app()` — since `html_generator` is now async, update the test ASGI handler to await it. Verify that `httpx.ASGITransport`-based tests still pass.
- [x] 2.5 Run lint and type check to verify all callers of `generate_html()` are updated

## 3. Add prod/dev mode parameter to create_asgi_app()

- [x] 3.1 Change `mode` parameter type from `Literal["dev", "ssg"]` to `Literal["prod", "dev"]` with default `"prod"`. When `mode="dev"`: set `build_config.server.dev = True`, include SSE reload route, set dev-mode cache headers. When `mode="prod"`: set `build_config.server.dev = False`, exclude SSE reload route, exclude dev cache headers. `create_asgi_app()` remains `def` (synchronous).
- [x] 3.2 Update `run_server()` — select mode based on `--dev` CLI flag (`"dev"` if present, `"prod"` otherwise). Do not manipulate `build_config.server.dev` directly before calling `create_asgi_app()`. Read `build_config.server.dev` after `create_asgi_app()` returns for `uvicorn.run(reload=...)`.
- [x] 3.3 Update `generate_static_site()` — call `create_asgi_app(app, build_config, mode="prod")` instead of `mode="ssg"`.
- [x] 3.4 Update hash-mode pre-rendering — `_pre_render_hash_mode_html()` and hash-mode handler in `create_asgi_app()` remain unchanged (mode parameter only affects SSE and cache headers, not hash-mode behavior).
- [x] 3.5 Update unit tests for mode parameter — verify that `mode="dev"` includes SSE route, `mode="prod"` excludes SSE route, and `build_config.server.dev` is set correctly by each mode.
- [x] 3.6 CLI entry point — no change needed, `run_server()` remains synchronous and passes the ASGI app to `uvicorn.run()`.

## 4. Restructure generate_static_site() to use ASGITransport

- [x] 4.1 Change `generate_static_site()` from `def` to `async def` in `_generate.py`. The function now creates an ASGI app via `create_asgi_app(mode="prod")` and fetches routes via `httpx.AsyncClient(transport=ASGITransport(app=asgi_app))`.
- [x] 4.2 `create_asgi_app(mode="prod")` internally configures `ServerFetchPort` — no separate configure() call needed in `_generate.py`. The ASGI app handles self-site fetch requests during SSR, with blocked paths preventing infinite recursion.
- [x] 4.3 Implement the SSG route-fetching logic: for history-mode apps, iterate `app.routes`, compute expanded paths (handling `path_params`), fetch each via `client.get()`, and write HTML to `dist/{path}/index.html`. For hash-mode apps, fetch the root route and write to `dist/index.html`. For 404, fetch a dedicated path and write `dist/404.html`.
- [x] 4.4 Remove the old direct `html_generator()` call path from `_generate.py`. The `html_generator` partial is no longer created in `_generate.py` — it's handled by `create_asgi_app()`.
- [x] 4.5 Update the CLI entry point for `generate` command in `packages/webcompy/src/webcompy/__main__.py` — call `asyncio.run(generate_static_site())` instead of calling it synchronously.
- [x] 4.6 Keep the dist directory creation, `.nojekyll`, `CNAME`, static file copying, and wheel/asset file writing in `_generate.py` — these are file-system operations that happen before or after the ASGI fetches.

## 5. Integration and verification

- [x] 5.1 Update `packages/webcompy-testing/src/webcompy_testing/_asgi.py:create_test_asgi_app()` — if `create_asgi_app()` signature changed, update the test utility accordingly. The test utility should still work with `httpx.ASGITransport`.
- [x] 5.2 Run existing SSG tests — `tests/test_build_wheels.py`, `tests/test_build_standalone.py`, `tests/test_build_runtime_local.py` — to verify SSG output is unchanged
- [x] 5.3 Run existing dev server tests to verify `create_asgi_app()` still works for dev mode
- [x] 5.4 Run lint: `uv run ruff check .` ✓
- [x] 5.5 Run type check: `uv run pyright` ✓ (0 errors)
- [x] 5.6 Run unit tests: `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs` ✓ (1338 passed, 7 skipped)
- [x] 5.7 Run E2E tests: `scripts/run-e2e-tests.sh` to verify no regressions ✓ (all groups passed)
- [x] 5.8 Generate the docs site: `uv run python -m webcompy generate --config docs_app.webcompy_config` and verify output matches expected structure ✓
