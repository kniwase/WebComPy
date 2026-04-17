## Context

The e2e test app at `tests/e2e/app/` provides a complete WebComPy application with router navigation, multiple page components, and Playwright-based e2e tests. The recent fix for deferring `on_after_rendering` during reactive SwitchElement refresh changed how `Component._render()` and `SwitchElement._refresh()` interact — `on_after_rendering` callbacks are now deferred via `setTimeout(fn, 0)` when triggered by a route change.

Currently, the e2e test app has no page that uses async operations in `on_after_rendering`. The closest is `LifecyclePage`, which only increments a counter synchronously. To verify the fix works, we need a test page that demonstrates the exact pattern that was broken: async operations (like `HttpClient.get()` or `resolve_async()`) in `on_after_rendering` triggered by router navigation.

## Goals / Non-Goals

**Goals:**
- Add a test page component that uses async operations in `on_after_rendering`
- Verify via e2e tests that navigating to this page via RouterLink works without errors
- Verify that the async data is fetched and displayed correctly
- Verify that direct URL access also works
- Follow existing e2e test conventions (data-testid, fixtures, assertion patterns)

**Non-Goals:**
- Changing framework behavior or adding new framework features
- Modifying the Fetch Sample demo page
- Adding unit tests for the deferral mechanism
- Testing `RepeatElement` with async operations

## Decisions

### Decision 1: Use `resolve_async` + `HttpClient.get` in the test page

**Rationale**: The original bug involved async operations in `on_after_rendering` during route navigation. The Fetch Sample demo uses both `AsyncWrapper`/`HttpClient.get()` and `resolve_async`. We should test with `HttpClient.get()` since it's the most realistic scenario — it fetches data from a served static JSON file.

**Approach**: Create a static JSON file at `tests/e2e/static/async_nav_data.json` that the test page fetches via `HttpClient.get()` in `on_after_rendering`. The page will display the fetched data using reactive values.

### Decision 2: Use class-style component for the test page

**Rationale**: The `LifecyclePage` already demonstrates `on_after_rendering` with class-style components (`@on_after_rendering` decorator). Using the same pattern ensures consistency and directly tests the decorator-based hook that the fix targets.

### Decision 3: Test both navigation via RouterLink and direct URL access

**Rationale**: The bug only manifested during RouterLink navigation (reactive update path), not direct URL access (hydration path). Testing both ensures we verify the fix and prevent regression. The existing test patterns use `app_page` for RouterLink navigation and `page_on` for direct URL access.

### Decision 4: Use `data-testid` attributes for test selectors

**Rationale**: All existing e2e tests use `data-testid` for element selection. This is the established pattern and must be followed.

## Risks / Trade-offs

- **[PyScript init timeout]** → The async fetch adds a small delay after navigation. Using `page.wait_for_selector` with appropriate timeout should handle this. Mitigation: the existing `PYSCRIPT_INIT_TIMEOUT` of 120s is generous.

- **[Static file serving]** → The JSON file must be served correctly by the dev server. The `static/` directory already has a `.gitkeep`, confirming the StaticFiles middleware is configured. Mitigation: verify the file is accessible before writing tests that depend on it.