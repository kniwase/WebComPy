## Why

The wheel filename normalization bug (PEP 427 violation) that broke webcompy.net was not caught by existing e2e tests because the test app package is named `app` (pure alphabetic, no underscores or hyphens). No current test verifies that the browser can actually import and render the app from either serving mode (dev server or static site). A parametrized e2e test suite that runs the same assertions against both serving modes would have caught this class of bug and will prevent similar regressions.

## What Changes

- **Rename e2e test app package from `app` to `my_app`** — an underscore-containing name that exercises the wheel filename normalization path
- **Add console error detection** to e2e tests — after PyScript initialization, check browser console logs for Python tracebacks/exceptions; this directly catches micropip parse failures like the InvalidVersion error
- **Parametrize existing e2e tests** to run against both the dev server and the static site, so a single test function validates both serving modes
- **Add a dedicated `test_no_python_errors` test** that explicitly verifies no Python exceptions appear in the browser console after app initialization

## Capabilities

### New Capabilities

- `e2e-testing`: End-to-end browser testing that validates the app loads and renders correctly in both dev-server and static-site serving modes, with console error detection for Python exceptions

### Modified Capabilities

_None_

## Impact

- `tests/e2e/app/` → `tests/e2e/my_app/` (directory rename)
- `tests/e2e/webcompy_config.py` (path reference update)
- `tests/e2e/test_static_site.py` (refactored — parametrize, rename, new tests)
- `tests/e2e/conftest.py` (new parametrized fixtures, console error detection)
- All other `tests/e2e/test_*.py` files (update fixture usage to parametrized versions)
- Test execution time will approximately double (same tests run twice: dev server + static site)

## Non-goals

- Adding new application features or behavioral tests beyond what currently exists
- Changing the framework code itself
- Testing browser-specific rendering differences between serving modes
- Optimizing test execution time (the doubling is acceptable for the regression coverage gained)