## Context

Current e2e tests use a test app named `app` (pure alphabetic, no separators). The wheel filename normalization bug (`_normalize_name` using hyphens instead of underscores) was not caught because the `app` package name produces the same normalized name regardless of separator choice. The existing e2e tests also only test the dev server mode; the static site has only a single test (`test_app_loads_in_browser`) that verifies visibility of `#webcompy-app`.

The test infrastructure uses:
- `conftest.py`: session-scoped `dev_server` fixture, function-scoped `app_page` and `page_on` fixtures
- `test_static_site.py`: session-scoped `static_site` and `static_server` fixtures, `static_page` fixture
- Playwright for browser automation with a 120-second PyScript init timeout

```
Current fixture hierarchy:

  dev_server (session)          static_site (session) → static_server (session)
       ↓                               ↓
  app_page (function)              static_page (function)
  page_on (function)                   
       ↓                               ↓
  test_bootstrap.py                 test_app_loads_in_browser
  test_reactive.py                  (only 1 test!)
  test_event.py
  test_router.py
  ... (all dev-server only)
```

## Goals / Non-Goals

**Goals:**
- Parametrize e2e tests so the same test logic runs against both dev server and static site
- Rename test app package from `app` to `my_app` to exercise underscore-containing package names
- Add console error detection to catch Python exceptions (like micropip parse failures) in the browser
- Maintain backward compatibility with `pytest -m e2e` marker-based filtering

**Non-Goals:**
- Adding new behavioral test cases (only restructuring existing ones + console error check)
- Changing any framework source code
- Optimizing test execution time
- Adding visual regression or screenshot comparison tests

## Decisions

### Decision 1: Use pytest parametrize with indirect fixtures

**Choice**: Use `pytest.mark.parametrize("serving_mode", ["dev", "static"], indirect=["serving_mode"])` with a unified `app_page` fixture that resolves to either dev-server or static-site URL based on the parameter.

**Rationale**: This approach runs every test function twice (once per mode) with minimal test code duplication. The test file only writes assertions once.

**Alternatives considered**:
- **Separate test files per mode**: Duplicates all assertions, high maintenance burden
- **Shared test base class with two subclasses**: More Python ceremony, harder to discover which class runs which mode
- **Custom pytest plugin**: Over-engineering for this use case

The parametrize approach is idiomatic pytest and makes it immediately clear from test output which mode failed.

### Decision 2: Session-scoped server fixtures remain independent

**Choice**: Keep `dev_server` and `static_server` as session-scoped fixtures. The parametrized `app_page` fixture (function-scoped) selects which server URL to navigate to.

**Rationale**: Both servers need to be running for the full test session. Session scope avoids restarting servers per test. The `static_site` fixture generates the static site once, which takes noticeable time.

### Decision 3: Console error detection via Playwright `page.on("console")` listener

**Choice**: Collect console messages during PyScript initialization using Playwright's event listener API, then assert no Python tracebacks appear after `#webcompy-loading` is hidden.

**Rationale**: Playwright's `page.on("console", handler)` captures all console output including errors from PyScript/micropip. Python tracebacks in the browser console always appear as `console.error` messages. This directly catches the `InvalidVersion` error from micropip.

**Alternatives considered**:
- **Check `#webcompy-app` visibility only**: Already exists; insufficient because it only proves the loading screen disappeared, not that no errors occurred. However, this would catch the current bug as a timeout (PyScript init never completes when micropip fails).
- **Parse browser logs via CDP**: More powerful but unnecessary complexity for this use case.
- **Assert no console.error at all**: Too strict — browsers emit harmless errors from extensions, CORS, etc. Filtering for Python tracebacks is more targeted.

### Decision 4: Rename `app/` → `my_app/` 

**Choice**: Rename the e2e test app directory from `app` to `my_app`.

**Rationale**: `my_app` contains an underscore, exercising the `_normalize_name` code path that was broken. This ensures wheel filename normalization is tested end-to-end. Since all internal imports are relative (`.layout`, `.router`, `.pages.*`), no code changes inside the app package are needed.

### Decision 5: Merge `test_static_site.py` tests into the parametrized framework

**Choice**: The wheel-related assertions (filename matches HTML, valid zip) are static-site-only and remain in `test_static_site.py`. The browser-rendering assertion (`test_app_loads_in_browser`) is subsumed by the parametrized `test_app_loads` that runs against both modes. A new `test_no_python_errors` assertion is added to the parametrized suite.

**Rationale**: Wheel file integrity checks don't need a browser — they only need the generated static site. Browser-based tests benefit from parametrization.

```
Proposed fixture hierarchy:

  dev_server (session)        static_site (session) → static_server (session)
       ↓                               ↓
  ┌─────────────────────────────────────────────────────┐
  │  app_page fixture (function, parametrized)          │
  │  "dev"    → navigate to dev_server URL               │
  │  "static" → navigate to static_server URL            │
  └─────────────────────────────────────────────────────┘
       ↓
  test_bootstrap.py    (2 variants: dev, static)
  test_reactive.py     (2 variants: dev, static)
  test_event.py        (2 variants: dev, static)
  test_router.py       (2 variants: dev, static)
  ...
  + test_no_python_errors (2 variants: dev, static)
  
  test_static_site.py  (not parametrized — wheel-only checks)
```

## Risks / Trade-offs

- **[Medium] Test execution time doubles**: Same tests run twice (dev + static). PyScript initialization takes 30-120 seconds per page load. **Mitigation**: Both servers are session-scoped so startup is a one-time cost. The `static_site` generation also happens once per session.
- **[Low] Flaky console errors**: Browser extensions or network issues may cause spurious console errors. **Mitigation**: Filter specifically for Python tracebacks (lines starting with `Traceback` or containing `Error:` from Python modules), not all console.error messages.
- **[Low] Static site generation adds complexity**: The `static_site` fixture runs `webcompy generate` as a subprocess, which can fail in CI. **Mitigation**: The existing `test_static_site.py` already does this and works in CI. We're reusing the same fixture pattern.