## Why

The recent fix that defers `on_after_rendering` during reactive SwitchElement refresh (router navigation) currently lacks e2e test coverage. Without automated verification, regressions could go undetected — particularly the scenario where navigating to a page via a RouterLink triggers async operations in `on_after_rendering` that previously failed when called synchronously within the reactive callback chain.

## What Changes

- Add a new e2e test page component that performs an async operation (using `AsyncWrapper`/`HttpClient` or `resolve_async`) in `on_after_rendering`
- Add a new route and navigation link for the test page in the e2e test app
- Add e2e test cases that verify: (1) navigating to the async page via RouterLink works without errors, (2) the async data is fetched and displayed correctly after navigation, (3) direct URL access to the async page also works, (4) navigating away and back resets state correctly

## Capabilities

### New Capabilities

_None_

### Modified Capabilities

_None_

## Impact

- `tests/e2e/app/pages/` — new async test page component
- `tests/e2e/app/router.py` — new route
- `tests/e2e/app/layout.py` — new navigation link
- `tests/e2e/` — new test file for async navigation scenarios

## Known Issues Addressed

- Addresses the lack of automated test coverage for the router async navigation fix (`fix/fetch-sample-router-error`)

## Non-goals

- Changing the framework's async, router, or component behavior
- Adding unit tests (only e2e tests are in scope)
- Testing `RepeatElement` with async operations (not related to the router fix)
- Modifying the Fetch Sample demo page