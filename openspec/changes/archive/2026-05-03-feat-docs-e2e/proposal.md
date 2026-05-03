## Why

The documentation site (docs_app) currently has no automated end-to-end testing. As the framework's primary showcase application, it should be validated to ensure pages load correctly, no console errors occur, and interactive demos work. This change adds a comprehensive E2E test suite for the docs_app, running in both production and static serving modes, separate from the existing `tests/e2e/` suite.

## What Changes

- Add `tests/e2e_docs/` directory with per-page test files and shared conftest fixtures
- Test pages: Home, Documents, HelloWorld, FizzBuzz, ToDo, Matplotlib, Fetch (skipped until fixed)
- Support both `prod` and `static` serving modes via `--serving-mode` CLI option (same pattern as existing E2E tests)
- Use extended PyScript initialization timeout (300s) to accommodate matplotlib's heavy dependency loading
- Use text/role-based selectors (no `data-testid` attributes on the production docs_app)
- Add CI matrix entries for docs E2E tests in `.github/workflows/ci.yml`

## Capabilities

### New Capabilities

- `docs-e2e`: E2E testing of the docs_app site — page load verification, console error detection, navigation, and interactive demo testing across both serving modes

### Modified Capabilities

- `e2e-testing`: Extend to cover docs_app E2E test infrastructure alongside the existing my_app tests, adding requirements for dual-app E2E support, extended timeout configuration, and text/role-based element selection

## Impact

- **New test directory**: `tests/e2e_docs/` with conftest, per-page tests, and serving mode support
- **CI**: New matrix entries in `ci.yml` for docs E2E tests
- **Test infrastructure**: Shared patterns with `tests/e2e/conftest.py` but independent fixture configuration (different port, different app, longer timeout)
- **No changes to docs_app code**: Tests use existing element text and roles for assertions

## Known Issues Addressed

_(none)_

## Non-goals

- Adding `data-testid` attributes to docs_app components — tests use text/role-based selectors
- Testing the Fetch Sample page (skipped until `feat-docs-app-rename` fixes it)
- Running matplotlib E2E tests in CI if CDN access issues prevent Pyodide initialization — will be evaluated after initial CI run
- Modifying the existing `tests/e2e/` test suite or its conftest
