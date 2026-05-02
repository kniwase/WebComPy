## Context

The documentation site (`docs_app` after rename) is WebComPy's primary showcase application with 7 pages: Home, Documents, HelloWorld, FizzBuzz, ToDo, Matplotlib, and Fetch. Currently there are no automated tests verifying that this site loads correctly in a browser. The existing E2E test suite (`tests/e2e/`) tests a minimal `my_app` with purpose-built `data-testid` attributes. The docs_app is a production site without test hooks, requiring a different element selection strategy.

Key constraints:
- `docs_app` uses `dependencies_from="browser"` (micropip loads numpy, matplotlib, etc. at runtime)
- PyScript initialization with matplotlib dependencies can take 2-5 minutes in CI
- The Fetch Sample page is currently broken (fixed by `feat-docs-app-rename`)
- `docs_app` has no `data-testid` attributes — must use text/role-based selectors

## Goals / Non-Goals

**Goals:**
- Create a separate E2E test suite at `tests/e2e_docs/` for the docs_app
- Test page loads, console error detection, and basic interactivity for all pages
- Support both `prod` and `static` serving modes
- Integrate into CI with appropriate matrix configuration

**Non-Goals:**
- Adding `data-testid` attributes to docs_app components
- Testing the Fetch Sample page (skipped until `feat-docs-app-rename` fixes it)
- Modifying the existing `tests/e2e/` suite or its conftest
- Full visual regression testing or screenshot comparison

## Decisions

### Decision: Separate test directory `tests/e2e_docs/`

A separate directory rather than extending `tests/e2e/` because:
- Different app (docs_app vs my_app), different fixtures, different timeout requirements
- Different conftest configuration (port, app path, static site generation)
- Clear separation of concerns — `tests/e2e/` tests framework features, `tests/e2e_docs/` tests the showcase site

**Alternative considered**: Sharing conftest via imports — rejected to keep the suites independent and avoid coupling. The common patterns (console error detection, serving mode parametrize, page load waits) are simple enough to duplicate.

### Decision: Per-page test files

```
tests/e2e_docs/
├── conftest.py
├── test_home.py
├── test_documents.py
├── test_helloworld.py
├── test_fizzbuzz.py
├── test_todo.py
├── test_matplotlib.py
└── test_fetch.py
```

Per-page files allow CI matrix splitting and make it easy to skip individual pages.

### Decision: Text/role-based selectors (no `data-testid`)

Since docs_app is a production site, we avoid adding test-specific attributes. Instead:
- Use `page.get_by_text()`, `page.get_by_role()`, `page.locator("h2")`, etc.
- For interactive elements, use button text (e.g., `page.get_by_role("button", name="Add")`)
- For page identification, use headings (e.g., `page.get_by_text("What is WebComPy")`)
- For navigation links, use `page.get_by_role("link", name="...")` or RouterLink text

### Decision: Navigation testing via SPA router

Tests SHALL verify that client-side routing works by clicking navigation links and checking URL/content changes. Navigation tests use the `docs_app_page` fixture to avoid repeated PyScript initialization — the page stays loaded, and only the route changes.

The docs_app uses Bootstrap dropdowns for the "Demos" navigation item. Playwright cannot simply click a dropdown link because the dropdown menu is hidden by default. Two approaches:
1. Use `page.locator("[data-bs-toggle='dropdown']")` to click the dropdown toggle first, then click the menu link. Note: `data-bs-toggle` is a Bootstrap framework attribute, not a test hook — this is an intentional exception to the "no `data-testid`" principle since it's part of the component's normal markup.
2. Use `page_on("/sample/helloworld")` to navigate directly via URL, then test back-navigation via the "Home" link

The recommended approach is (1) for forward-navigation tests and (2) as a fallback if Bootstrap dropdown interaction is unreliable in CI.

### Decision: Extended timeout for matplotlib

The `PYSCRIPT_INIT_TIMEOUT` for docs_app tests will be 300 seconds (5 minutes) instead of the default 120 seconds. This accounts for micropip downloading and installing numpy + matplotlib in CI.

The `app_page` / `page_on` fixture waits for `#webcompy-loading` to become hidden and `#webcompy-app` to become visible, which is the same pattern as the existing E2E suite.

### Decision: Serving mode parametrize

Same pattern as existing E2E: `pytest_generate_tests` parametrizes `serving_mode` across `["prod", "static"]` with a `--serving-mode` CLI option.

**Prod server**: `uv run python -m webcompy start --app docs_app.bootstrap:app --port 8081`
**Static site**: `uv run python -m webcompy generate --app docs_app.bootstrap:app --dist .tmp/e2e-docs-static/dist` → SimpleHTTPServer

### Decision: Port 8081 for docs prod server

Port 8081 avoids conflict with the existing E2E suite's port 8088. Since CI matrix jobs run in separate containers, there is no actual port conflict in CI — this is only relevant for local development when running both suites simultaneously.

### Decision: Fetch test skipped with reason

`test_fetch.py` will use `pytest.mark.skip(reason="Fetch Sample requires sample.json static file - see feat-docs-app-rename")` to be enabled once the fix lands.

### Decision: CI matrix configuration

Add 4 groups to `e2e-matrix` in `ci.yml`:

```yaml
- name: docs-home
  files: tests/e2e_docs/test_home.py tests/e2e_docs/test_documents.py tests/e2e_docs/test_helloworld.py
- name: docs-demos
  files: tests/e2e_docs/test_fizzbuzz.py tests/e2e_docs/test_todo.py
- name: docs-matplotlib
  files: tests/e2e_docs/test_matplotlib.py
- name: docs-fetch
  files: tests/e2e_docs/test_fetch.py
```

If matplotlib E2E tests cause CI failures (CDN access issues, timeout), we can add `skipif` markers later.

## Risks / Trade-offs

- **[CI timeout]** → Matplotlib's micropip install can take 3-5 minutes in CI. The 300s timeout should cover this, but CDN availability issues (as seen with `test_runtime_local`) may require `skipif` markers. → Mitigation: Start with full CI runs, add skipif if needed.
- **[CI duration increase]** → Adding ~8 test files × 2 serving modes = ~16 test sessions. Each requires PyScript initialization (30-60s for light pages, 3-5min for matplotlib). → Mitigation: Matrix splitting keeps individual jobs short.
- **[Lock file auto-generation]** → docs_app has no `webcompy-lock.json`. The `webcompy start` and `webcompy generate` commands will auto-generate one, which requires CDN access. → Mitigation: Same behavior as current dev server usage; if CDN is down, the test suite fails at startup (same as existing E2E).
- **[Test flakiness]** → Text-based selectors are more fragile than `data-testid`. Page text changes will break tests. → Mitigation: Use stable, unlikely-to-change text (headings, button labels) rather than transient content.
