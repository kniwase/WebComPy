# Design: feat-python314-support

## Context

See `proposal.md` for motivation. Currently:
- The workspace specifies `requires-python = ">=3.12"` across `pyproject.toml`, `docs_app/pyproject.toml`, and all four `packages/*/pyproject.toml`, with classifiers listing Python `3.12` and `3.13` and linter/typechecker target versions set to `3.12`.
- No `.python-version` file exists, and `.github/actions/setup-environment/action.yml` and `.github/workflows/ci.yml` do not pass `python-version` to `astral-sh/setup-uv@v7`, causing CI runners on Ubuntu 26.04 (`ubuntu-latest`) to execute with CPython `3.14.4`.
- CPython nested event-loop execution for synchronous signal callbacks and test helpers is implemented at three sites (`packages/webcompy/src/webcompy/aio/_aio.py`, `packages/webcompy/src/webcompy/elements/types/_dynamic.py`, and `packages/webcompy-testing/src/webcompy_testing/_utils.py`) using `nest-asyncio>=1.6.0`. In CPython 3.14, `nest-asyncio==1.6.0` fails to preserve `asyncio.current_task()` across re-entrant loop runs, breaking `asyncio.Runner.close()` → `loop.shutdown_default_executor()` (`asyncio/timeouts.py` raises `RuntimeError: Timeout should be used inside a task`).
- Root `pyproject.toml` `[dependency-groups] docs` pins `numpy==2.2.5`, which has no prebuilt Python 3.14 wheels on PyPI and forces a slow source compilation on CI.

## Goals / Non-Goals

**Goals:**
- Make CPython 3.14 a first-class, CI-verified runtime for WebComPy server, CLI, testing, and docs tooling while preserving `requires-python = ">=3.12"` compatibility for downstream users.
- Pin the development and CI Python version to `3.14` cleanly across local tooling (`uv`) and GitHub Actions workflows.
- Eliminate the `numpy==2.2.5` source-build bottleneck on Python 3.14 without regressing `docs_app` demo generation or matplotlib compatibility.

**Non-Goals:**
- Upgrading the browser PyScript/Pyodide runtime to `2026.7.3` / `314.0.3` (handled in a separate Stage 2 change so browser runtime asset changes stay isolated from CPython CI fixes).
- Raising `requires-python` or ruff/pyright target syntax levels above `3.12`.
- Consolidating `packages/webcompy-testing` onto private `packages/webcompy` internals (cross-package internal imports are avoided; the three small conditional guards remain independent).

## Decisions

1. **Replace `nest-asyncio` with `nest-asyncio2>=1.7.4`**
   - `nest-asyncio2` is the actively maintained fork of the archived `nest_asyncio` repository that fixes CPython 3.12–3.14 task context tracking (`asyncio.current_task()`) and re-entrant `asyncio.timeout()` handling.
   - Alternative considered: replacing re-entrant loop patching with a worker-thread runner or rewriting all synchronous signal callbacks to async. Rejected because `async-rendering` and `testing-module` intentionally rely on synchronous in-thread completion during SSG/SSR and `TestRenderer` assertions (and a thread hop would break non-thread-safe state and `ContextVar`/DI scope assumptions).
   - Keep the existing `getattr(loop, "_nest_asyncio_patched", False)` guard on the loop object across all three call sites so repeated re-entrant invocations patch each loop once.

2. **Pin repository dev/CI Python to `3.14` while keeping `requires-python = ">=3.12"`**
   - Add `.python-version` containing `3.14` at the repository root so local `uv sync` / `uv run` automatically selects Python 3.14.
   - Pass `python-version: "3.14"` to `astral-sh/setup-uv@v7` in `.github/actions/setup-environment/action.yml` (which serves `lint`, `typecheck`, `generate`, `test`, `browser-tests`, `wheel-smoke`, `e2e-matrix`, `docs-e2e`, and `browser-version-sweep.yml`) and in `.github/workflows/ci.yml`'s `review` job.
   - Keep `requires-python = ">=3.12"`, `[tool.ruff] target-version = "py312"`, and `[tool.pyright] pythonVersion = "3.12"` so library code cannot accidentally adopt 3.13/3.14-only syntax or stdlib APIs without compatibility shims. Add `"Programming Language :: Python :: 3.14"` to `classifiers` in all four `packages/*/pyproject.toml`.
   - Alternative considered: pinning CI back to `3.12`. Rejected because GitHub's default runner has already moved to 3.14, PyScript's latest stable line (`2026.7.3` / Pyodide `314.0.3`) also uses Python 3.14, and pinning forward surfaces 3.14 issues immediately rather than masking them.

3. **Relax `[dependency-groups] docs` `numpy` pin to `numpy>=2.2.5,<3`**
   - Updating `numpy==2.2.5` to `numpy>=2.2.5,<3` allows `uv lock` to resolve prebuilt `cp314` wheels (such as `2.4.x`, matching Pyodide `314.0.3`'s `numpy 2.4.3`) while staying within the NumPy 2.x ABI already paired with `matplotlib>=3.9.0,<4`.
   - Alternative considered: pinning `numpy==2.4.3` directly. Rejected because `>=2.2.5,<3` matches the style of `matplotlib>=3.9.0,<4` right above it and remains flexible across platforms.

4. **Audit Python 3.14 runtime areas before merging**
   - Python 3.14 introduces PEP 649 (deferred evaluation of annotations) and minor bytecode/stdlib updates. During implementation on CPython 3.14, run the complete unit, docstring, lint, typecheck, SSG generate, browser test/probe, and E2E suites locally, paying attention to `typing.get_type_hints` (`typed-api-client`, `rpc-contracts`), `dis.get_instructions` (`composables` auto-key generation), `tokenize` (`syntax-highlight-lexers`), and `ast` (`scripts/check-docstrings.py`, dual-run classifier).

## Risks / Trade-offs

- **[Hidden CPython 3.14 regressions in stdlib behavior (PEP 649 / `dis` / `tokenize`)]** → Run the full unit, browser, and E2E test suites locally under CPython 3.14 before pushing and fix any failures within this change.
- **[`requires-python = ">=3.12"` tested on 3.14 only in PR CI]** → Ruff (`target-version = "py312"`) and Pyright (`pythonVersion = "3.12"`) statically prevent 3.14-only syntax/API usage; consumer behavior on 3.12/3.13 stays guarded statically without multiplying the CI matrix.
- **[Legacy `### ADDED:` header in `openspec/specs/testing-module/spec.md`]** → At archive/spec-sync time, update the requirement block cleanly to standard `### Requirement:` format while preserving its requirement text and scenarios.

## Migration Plan

1. Merge Stage 1 (`feat/python314-support`) into `main`.
2. Rebase PR #298 (`docs/home-refresh-getting-started`) onto updated `main` so its CI passes on Python 3.14 with prebuilt `numpy` wheels.
3. Follow up with Stage 2 (`feat-pyscript-2026-7-pyodide-314`) to align the browser PyScript/Pyodide runtime on Python 3.14 as well.
