## Why

The docs app's homepage (`/`) route is eagerly imported while all other routes use `lazy()` for deferred loading. This inconsistency means users entering the app through any other route (e.g., `/documents`) still pay the cost of loading the home page module upfront, even though the framework's router already supports lazy loading for any route including `/`.

Additionally, `Router.preload_lazy_routes()` currently schedules one `setTimeout(0)` call per unresolved lazy route. With many lazy routes, this creates unnecessary overhead and is inconsistent with the signal effect system's pattern of batching deferred work into a single callback.

## What Changes

1. **Lazy-load the `/` route in docs_app**: Change `docs_app/router.py` to use `lazy("docs_app.pages.home:HomePage", __file__)` instead of an eager `import` at the top of the file.
2. **Batch lazy route preloading**: Change `Router.preload_lazy_routes()` to collect all unresolved lazy routes into a list and schedule a single `setTimeout(0)` callback that preloads them all, rather than scheduling one callback per route.

## Capabilities

### New Capabilities
- (none)

### Modified Capabilities
- (none — these are an implementation optimization and an application configuration change that use existing capabilities without altering observable behavior)

## Impact

- `docs_app/router.py`: `/` route configuration changes from eager to lazy
- `webcompy/router/_router.py`: `preload_lazy_routes()` implementation batched
- `tests/e2e/my_app/router.py`: **Not changed** — the e2e test app intentionally uses eager loading for all routes to keep tests simple and deterministic

## Non-goals

- Changing the `preload` API or default behavior (`preload=True` remains the default)
- Introducing `queueMicrotask` or alternative defer mechanisms
- Modifying the e2e test app router configuration
- Adding new tests for the batching behavior (the existing lazy routing tests already cover preload correctness; the batching is an implementation detail with no observable behavior change)

## Known Issues Addressed

- (none)
