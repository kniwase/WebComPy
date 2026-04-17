## Why

When navigating to the Fetch Sample page via the router (clicking a RouterLink), async operations like `HttpClient.get()` and `AsyncWrapper`-wrapped functions called from `on_after_rendering` cause errors. The same page works correctly when accessed directly via URL. This is because `on_after_rendering` fires synchronously within the reactive update chain triggered by route changes, and async operations initiated there run into issues with DOM node availability or event loop re-entrancy during that synchronous cascade.

## What Changes

- Fix the `SwitchElement._refresh()` method to defer component lifecycle hooks (`on_after_rendering`) until after the DOM update batch completes, so that async operations in `on_after_rendering` are not invoked during a reactive callback chain
- Ensure that when a route change triggers `SwitchElement._refresh()`, the new component's `on_after_rendering` fires only after the DOM is fully updated and the reactive propagation has settled
- Update the Fetch Sample demo to confirm the fix resolves the issue

## Capabilities

### New Capabilities

_None_

### Modified Capabilities

- `components`: `on_after_rendering` must fire only after reactive propagation has settled, not synchronously during a `callback_after_updating` cascade triggered by a route change
- `elements`: `SwitchElement._refresh()` must not invoke component lifecycle hooks (like `on_after_rendering`) synchronously within the reactive callback chain — the DOM must be fully attached before any side effects run

## Impact

- `webcompy/elements/types/_switch.py` — `_refresh()` method timing
- `webcompy/components/_component.py` — `_render()` lifecycle hook timing
- `webcompy/router/_router.py` — route change propagation
- `webcompy/aio/_aio.py` — `resolve_async` / `aio_run` behavior during reactive updates
- `docs_src/templates/demo/fetch_sample.py` — verification of the fix

## Known Issues Addressed

- This change does not directly address a listed known issue, but it relates to the router singleton pattern and the reactive system's callback propagation.

## Non-goals

- Adding virtual DOM diffing or key-based reconciliation for SwitchElement
- Changing the async execution model (replacing `run_until_complete` with a different mechanism)
- Adding route guards or lazy-loading
- Fixing `AsyncComputed._done` / `None` ambiguity