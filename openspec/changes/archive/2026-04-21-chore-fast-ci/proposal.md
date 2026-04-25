## Why

The CI workflow (`ci.yml`) currently runs jobs with unnecessary sequential dependencies (`needs`) that create a critical path bottleneck. E2E tests are especially slow because they run all test files serially against both production and static serving modes within a single job. Reducing CI wall-clock time improves developer feedback loops and avoids idle minutes.

## What Changes

- Remove unnecessary `needs` for `lint`, `typecheck`, `generate`, and `test` so all pre-checks run in parallel.
- Parallelize E2E tests via a matrix strategy that groups tests by functional category and splits `serving_mode` into separate matrix axes.
- Extract shared environment setup into a reusable composite action to cache `uv sync` and `playwright install` across jobs.
- Guard heavy `e2e` execution with `if: !failure()` so it only runs when all pre-checks pass.

## Capabilities

### New Capabilities
- `fast-ci-matrix`: CI workflow supports parallel matrix execution for E2E test categories with independent `prod` and `static` serving modes.
- `shared-setup-action`: A reusable composite GitHub Action caches dependencies and Playwright browsers for all CI jobs.

### Modified Capabilities
- `e2e-testing`: Existing spec behavior changes — E2E tests must support standalone invocation per serving mode (removing `serving_mode` fixture parametrize in favor of matrix axes).

## Impact

- `.github/workflows/ci.yml` — job structure and matrix definitions.
- `.github/actions/setup-environment/action.yml` — new reusable composite action.
- `tests/e2e/conftest.py` — `serving_mode` fixture parametrize removed; per-mode selection controlled via CLI option or env var.
- CI wall-clock time drops from ~10+ minutes to ~3-4 minutes (estimated).

## Known Issues Addressed

- None.

## Non-goals

- Adding new E2E test cases or changing test assertions.
- Changing the `deploy-pages.yml` workflow (it is already minimal).
- Migrating to external CI services (CircleCI, etc.).
