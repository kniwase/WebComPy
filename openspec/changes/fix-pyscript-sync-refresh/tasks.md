# Tasks: fix-pyscript-sync-refresh

## 1. Core fix

- [x] 1.1 Add a Pyodide branch to `_run_refresh_sync` in `packages/webcompy/src/webcompy/elements/types/_dynamic.py` (line ~32-46): when `ENVIRONMENT == "pyscript"` and an event loop is running, schedule the refresh coroutine on the event loop via `aio_run` wrapped in a `_safe_refresh` coroutine that logs exceptions via `logging.error`, instead of calling `loop.run_until_complete`
- [x] 1.2 Keep the non-Pyodide path unchanged (`asyncio.run` without a running loop; `nest_asyncio` + `run_until_complete` with one)

## 2. Regression tests

- [x] 2.1 Add `tests/test_run_refresh_sync.py`: with `ENVIRONMENT` patched to `"pyscript"`, `_run_refresh_sync` returns immediately without executing the refresh, and the refresh runs (to completion) after the event loop is pumped
- [x] 2.2 Same file: in the Pyodide branch, an exception raised by the refresh is logged via `logging.error` and does not propagate to the caller
- [x] 2.3 Same file: in a non-Pyodide environment with a running loop, `_run_refresh_sync` completes the refresh synchronously (existing behavior pinned)
- [x] 2.4 Extend `e2e/docs/test_todo.py::test_todo_remove_done_items` with a `page.on("pageerror")` listener and assert no `pageerror` occurred during the checkbox/remove interaction (fails before the fix with "Cannot stack switch")
- [x] 2.5 Update immediate `is_visible()` assertions in `e2e/docs/test_todo.py` (`test_todo_add_item`, `test_todo_remove_done_items`) to Playwright auto-waiting `expect` assertions, since Pyodide refreshes are now asynchronous

## 3. Verification

- [x] 3.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [x] 3.2 Run `uv run python -m pytest tests/ --tb=short`
- [x] 3.3 Run full e2e suite via `scripts/run-e2e-tests.sh` (all groups, prod + static) and confirm all pass
- [x] 3.4 Run `openspec validate fix-pyscript-sync-refresh`
