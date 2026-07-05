## Why

Unit tests and E2E tests currently coexist under `tests/` (`tests/e2e/`, `tests/e2e_docs/`). `pyproject.toml` declares `testpaths = ["tests"]`, so a plain `uv run pytest` discovers both suites — developers must remember `--ignore=tests/e2e --ignore=tests/e2e_docs` every time they want only unit tests. Conversely, E2E tests look syntactically identical to unit tests, so contributors (and AI agents) repeatedly invoke `pytest tests/e2e/test_xxx.py` directly, bypassing `scripts/run-e2e-tests.sh` and wasting time on missing ports, env vars, and Playwright setup. The two execution paths must be structurally distinct so that accidents are impossible, not merely discouraged.

## What Changes

- Move `tests/e2e/` → `e2e/core/` (framework-level E2E suite, including `my_app/`, `webcompy_config.py`, and `static/`).
- Move `tests/e2e_docs/` → `e2e/docs/` (docs_app E2E suite).
- Add a new root conftest at `e2e/conftest.py` that aborts collection with a helpful error unless the `WEBCOMPY_RUN_E2E=1` environment variable is set.
- Update `scripts/run-e2e-tests.sh` to inject `WEBCOMPY_RUN_E2E=1` into the pytest invocation, so the script remains the canonical E2E entry point.
- Update `.github/workflows/ci.yml`:
  - `e2e-matrix` group `files:` paths → `e2e/core/...` and `e2e/docs/...`.
  - `test` job: drop `--ignore=tests/e2e --ignore=tests/e2e_docs` (no longer needed; `testpaths = ["tests"]` excludes `e2e/` by default).
  - Upload-artifact paths for `.e2e-server.log` and `.e2e-docs-server.log` → new locations.
- Update `pyproject.toml` `[tool.pyright]` to exclude `e2e/**` (E2E tests are not type-checked).
- Update `AGENTS.md`, `CONTRIBUTING.md`, `CONTRIBUTING.ja.md`, `README.md`, `README.ja.md` to reflect new paths and the canonical E2E invocation.

## Capabilities

### New Capabilities
- `test-execution-paths`: Defines the physical separation between unit tests (`tests/`) and E2E tests (`e2e/`), and the opt-in mechanism (`WEBCOMPY_RUN_E2E=1` env var) that gates E2E collection. Establishes `scripts/run-e2e-tests.sh` as the canonical E2E entry point.

### Modified Capabilities
- `e2e-testing`: Path references update from `tests/e2e/` to `e2e/core/`; scenarios that say "developer runs `pytest tests/e2e/`" now reflect the gated opt-in flow.
- `docs-e2e`: Path references update from `tests/e2e_docs/` to `e2e/docs/`; the "separate test directory" requirement is updated to point at the new location and acknowledge the shared `e2e/conftest.py` opt-in guard.

## Impact

- **Directory layout**: `tests/e2e/` and `tests/e2e_docs/` are relocated under a new top-level `e2e/` directory. `tests/` contains only unit tests.
- **`pyproject.toml`**: `testpaths = ["tests"]` unchanged (now correctly restrictive); `[tool.pyright]` exclude gains `e2e/**`.
- **`scripts/run-e2e-tests.sh`**: Group file paths rewritten; `WEBCOMPY_RUN_E2E=1` injected into the pytest env.
- **`.github/workflows/ci.yml`**: Matrix `files:` rewritten; `test` job simplified (no `--ignore` flags); artifact upload paths updated.
- **Developer commands**:
  - `uv run pytest` → unit tests only (no flags needed).
  - `uv run pytest e2e/` → fails with a usage error pointing to the script.
  - `WEBCOMPY_RUN_E2E=1 uv run pytest e2e/...` → advanced direct invocation (still works).
  - `scripts/run-e2e-tests.sh [group]` → canonical E2E path (unchanged UX).
- **OpenSpec specs**: `e2e-testing` and `docs-e2e` updated to reflect new paths; new `test-execution-paths` spec introduced.
- **No breaking changes to test assertions or E2E fixture behavior**: Existing conftests (`e2e/core/conftest.py`, `e2e/docs/conftest.py`) keep their fixtures; only their filesystem location changes (and all `__file__`-relative path resolution continues to work).

## Known Issues Addressed

- None. (This change does not relate to any of the known issues listed in the project context — signal system, component IDs, element diffing, etc.)

## Non-goals

- Changing E2E test assertions, fixtures, or the `--serving-mode` parametrize behavior.
- Adding new E2E test cases or removing existing ones.
- Refactoring `scripts/run-e2e-tests.sh` beyond path and env-var updates (no new flags, no restructuring).
- Migrating unit tests out of `tests/` (e.g., into `tests/unit/`) — unit tests stay flat under `tests/`.
- Introducing a `pytest` marker-based gate (`@pytest.mark.e2e`) as the primary enforcement mechanism. The env-var guard at `e2e/conftest.py` is the gate; existing `@pytest.mark.e2e` markers remain as informational metadata only.
- Changing the `pre-commit` hooks or the `webcompy_testing` package API.
