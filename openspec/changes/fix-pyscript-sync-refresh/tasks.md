# Tasks: fix-pyscript-sync-refresh

## 1. Core fix

- [x] 1.1 Add a Pyodide branch to `_run_refresh_sync` in `packages/webcompy/src/webcompy/elements/types/_dynamic.py` (line ~32-46): when `ENVIRONMENT == "pyscript"` and an event loop is running, schedule the refresh coroutine on the event loop via `aio_run` wrapped in a `_safe_refresh` coroutine that logs exceptions via `_log_error` (formatted traceback), instead of calling `loop.run_until_complete`
- [x] 1.2 Keep the non-Pyodide path unchanged (`asyncio.run` without a running loop; `nest_asyncio` + `run_until_complete` with one)

## 2. Regression tests

- [x] 2.1 Add `tests/test_run_refresh_sync.py`: with `ENVIRONMENT` patched to `"pyscript"`, `_run_refresh_sync` returns immediately without executing the refresh, and the refresh runs (to completion) after the event loop is pumped
- [x] 2.2 Same file: in the Pyodide branch, an exception raised by the refresh is logged as a formatted traceback via `_log_error` and does not propagate to the caller
- [x] 2.3 Same file: in a non-Pyodide environment with a running loop, `_run_refresh_sync` completes the refresh synchronously (existing behavior pinned)
- [x] 2.4 Extend `e2e/docs/test_todo.py::test_todo_remove_done_items` with a `page.on("pageerror")` listener and assert no `pageerror` occurred during the checkbox/remove interaction (fails before the fix with "Cannot stack switch")
- [x] 2.5 Update immediate `is_visible()` assertions in `e2e/docs/test_todo.py` (`test_todo_add_item`, `test_todo_remove_done_items`) to Playwright auto-waiting `expect` assertions, since Pyodide refreshes are now asynchronous

## 3. Review-follow-up fixes

- [x] 3.1 Replace `logging.error(err)` with `_log_error(err)` in the Pyodide `_safe_refresh` branch (`_dynamic.py`), so refresh failures are logged with a formatted traceback; remove the redundant local `from webcompy import logging` import (module-level import already exists)
- [x] 3.2 Update `tests/test_run_refresh_sync.py::test_pyscript_logs_refresh_errors` to assert the logged message is a string containing `"Traceback (most recent call last):"` and `"ValueError: boom"` (formatted-traceback contract via `_log_error`)
- [x] 3.3 Add `openspec/changes/fix-pyscript-sync-refresh/specs/async-rendering/spec.md` delta with two MODIFIED requirements ("Dynamic element refresh shall be async with a sync signal wrapper in _render() only" and "Async signal callbacks shall execute with environment-dependent semantics"), replacing the pinned `run_until_complete`-in-both-environments wording with the Pyodide scheduling semantics
- [x] 3.4 Update the `elements` delta requirement to pin that refresh exceptions are logged with a formatted traceback via `_log_error`
- [x] 3.5 Update `design.md` (D1 code block, risks) and `proposal.md` (What Changes, Impact) to reflect `_log_error` and the `async-rendering` delta

## 4. Verification

- [x] 4.1 Run `uv run ruff check . && uv run ruff format --check . && uv run pyright`
- [x] 4.2 Run `uv run python -m pytest tests/ --tb=short`
- [x] 4.3 Run full e2e suite via `scripts/run-e2e-tests.sh` (all groups, prod + static) and confirm all pass
- [x] 4.4 Run `openspec validate fix-pyscript-sync-refresh`
