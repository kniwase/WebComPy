# Proposal: feat-python314-support

## Why

GitHub Actions `ubuntu-latest` runners have moved to Ubuntu 26.04 with system CPython 3.14.4, breaking unpinned CI jobs: `nest-asyncio==1.6.0` (unmaintained) causes `asyncio.run()` shutdown (`loop.shutdown_default_executor()`) to raise `RuntimeError: Timeout should be used inside a task` at the end of `webcompy generate`, and `[dependency-groups] docs` pins `numpy==2.2.5`, which lacks Python 3.14 wheels and forces a multi-minute source build. With PyScript's latest stable release (`2026.7.3` / Pyodide `314.0.3`) also targeting Python 3.14, supporting CPython 3.14 and pinning the repository development and CI environment to Python 3.14 unblocks CI immediately and prepares the server and tooling layers for full Python 3.14 parity.

## What Changes

- Replace `nest-asyncio>=1.6.0` with the actively maintained Python 3.14-compatible fork `nest-asyncio2>=1.7.4` in `packages/webcompy-server/pyproject.toml`, root `pyproject.toml` (`[dependency-groups] dev`), `uv.lock`, and the three CPython nested event-loop call sites (`packages/webcompy/src/webcompy/aio/_aio.py`, `packages/webcompy/src/webcompy/elements/types/_dynamic.py`, and `packages/webcompy-testing/src/webcompy_testing/_utils.py`).
- Relax `[dependency-groups] docs` `numpy==2.2.5` to `numpy>=2.2.5,<3` in root `pyproject.toml` so `uv` resolves prebuilt wheels on Python 3.14 (aligning with Pyodide `314.0.3`'s `numpy 2.4.3`) while staying compatible with Python 3.12+.
- Pin the repository development and CI Python version to `3.14` via `.python-version` (`3.14`) and `python-version: "3.14"` on `astral-sh/setup-uv@v7` in `.github/actions/setup-environment/action.yml` and `.github/workflows/ci.yml` (`review` job).
- Keep `requires-python = ">=3.12"` and `[tool.ruff] target-version = "py312"` / `[tool.pyright] pythonVersion = "3.12"` so Python 3.12 and 3.13 remain supported for library consumers, and add `"Programming Language :: Python :: 3.14"` to `classifiers` in all four `packages/*/pyproject.toml`.
- Add Python 3.14 regression tests verifying clean `asyncio.run()` shutdown after nested loop execution via `nest_asyncio2`, and audit/fix any CPython 3.14 runtime incompatibilities (e.g., PEP 649 deferred annotations, `dis`, `tokenize`, `ast`) surfaced by running the full unit, browser, and E2E suites on Python 3.14.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `async-rendering`: Replace `nest-asyncio` / `nest_asyncio` with `nest-asyncio2` / `nest_asyncio2` in `_resolve_async_callback()` and `_refresh_sync` / `_run_refresh_sync` CPython nested-loop behavior, and verify clean `asyncio.run()` executor shutdown on Python 3.14+.
- `elements`: Update `_run_refresh_sync` nested event-loop requirement text from `nest_asyncio` to `nest_asyncio2`.
- `testing-module`: Update `run_sync(coro)` requirement from `nest_asyncio` to `nest_asyncio2` and verify clean `asyncio.run()` shutdown on Python 3.14+.

## Impact

- `packages/webcompy/src/webcompy/aio/_aio.py`, `packages/webcompy/src/webcompy/elements/types/_dynamic.py`, `packages/webcompy-testing/src/webcompy_testing/_utils.py`
- `packages/*/pyproject.toml`, `pyproject.toml`, `uv.lock`
- `.python-version`, `.github/actions/setup-environment/action.yml`, `.github/workflows/ci.yml`
- `tests/` (regression tests and any Python 3.14 compatibility fixes)
- Specs: `openspec/specs/async-rendering/spec.md`, `openspec/specs/elements/spec.md`, `openspec/specs/testing-module/spec.md`

## Known Issues Addressed

None of the open items in the project known-issues list are closed; this change resolves the unmaintained `nest-asyncio` incompatibility on CPython 3.14 that currently breaks `CI/generate`.

## Non-goals

- Upgrading the pinned browser runtime from PyScript `2026.3.1` (`Pyodide 0.29.3`) to `2026.7.3` (`Pyodide 314.0.3`), adding `pyodide.asm.mjs` downloader support, or regenerating `docs_app/webcompy-lock.json` (scoped to a dedicated follow-up change).
- Raising `requires-python` above `>=3.12` or dropping Python 3.12 / 3.13 support.
- Re-architecting synchronous SSR/test signal callbacks away from re-entrant event-loop patching.
- Modifying `docs_app/` content or PR #298 (`docs/home-refresh-getting-started`).
