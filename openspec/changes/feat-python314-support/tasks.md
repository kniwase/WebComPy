# Tasks: feat-python314-support

## 1. Python 3.14 Environment Pin & Dependency Updates

- [x] 1.1 Create `.python-version` (`3.14`) and add `"Programming Language :: Python :: 3.14"` to `classifiers` in all four `packages/*/pyproject.toml` while keeping `requires-python = ">=3.12"`, `[tool.ruff] target-version = "py312"`, and `[tool.pyright] pythonVersion = "3.12"`; verify `uv python find` selects 3.14
- [x] 1.2 Replace `nest-asyncio>=1.6.0` with `nest-asyncio2>=1.7.4` in `packages/webcompy-server/pyproject.toml` and root `pyproject.toml`, relax `[dependency-groups] docs` `numpy==2.2.5` to `numpy>=2.2.5,<3` in `pyproject.toml`, and run `uv lock && uv sync --all-groups` to verify lockfile resolution and prebuilt wheel installation on Python 3.14
- [x] 1.3 Pin `python-version: "3.14"` on `astral-sh/setup-uv@v7` in `.github/actions/setup-environment/action.yml` and `.github/workflows/ci.yml` (`review` job); verify workflow YAML parses cleanly

## 2. Migrate Nested Event-Loop Call Sites

- [ ] 2.1 Update `packages/webcompy/src/webcompy/aio/_aio.py`, `packages/webcompy/src/webcompy/elements/types/_dynamic.py`, and `packages/webcompy-testing/src/webcompy_testing/_utils.py` to import and apply `nest_asyncio2` (keeping the `_nest_asyncio_patched` guard), and verify no non-archive runtime/package references to `nest_asyncio` remain via `git grep`

## 3. Python 3.14 Regression Tests & Compatibility Audit

- [ ] 3.1 Add unit regression tests verifying that `asyncio.run(...)` exits cleanly without `RuntimeError: Timeout should be used inside a task` after `run_sync()`, `_resolve_async_callback()`, and `_run_refresh_sync()` patch a running loop on CPython 3.14+; run those tests under Python 3.14 to confirm pass
- [ ] 3.2 Run the full unit suite (`uv run python -m pytest tests/ --tb=short`) under Python 3.14, inspect any PEP 649, `dis`, `tokenize`, or `ast` regressions, and fix any compatibility issues discovered until the full unit suite passes

## 4. Full Local CI Verification on Python 3.14

- [ ] 4.1 Run lint, format, docstring, doc-spec-ref, browser-import, pydoclint, pyright, and wheel smoke checks under Python 3.14 (`uv run ruff check .`, `uv run ruff format --check .`, `uv run pydoclint ...`, `uv run python scripts/check-browser-imports.py`, `python3 scripts/check-docstrings.py`, `python3 scripts/check-doc-spec-refs.py`, `uv run pyright`, `uv build --package webcompy`) and confirm zero failures
- [ ] 4.2 Run `uv run python -m webcompy generate --config docs_app.webcompy_config`, `scripts/run-browser-tests.sh` (unit + `--probes`), and E2E groups affected or representative (`scripts/run-e2e-tests.sh docs-home docs-documents --parallel` and core E2E) under Python 3.14 and confirm all pass

## 5. Spec Sync & Archive

- [ ] 5.1 Sync delta specs (`async-rendering`, `elements`, `testing-module`, normalizing `testing-module`'s legacy `### ADDED:` header on the modified requirement to `### Requirement:`), verify `openspec/SPEC_INDEX.md` and `.agents/skills/webcompy-review/SKILL.md` remain accurate, archive `feat-python314-support`, and confirm `openspec validate --specs` and `openspec validate --changes` pass with zero active changes
