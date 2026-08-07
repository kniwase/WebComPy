# Proposal: Async Route Guards and Redirects

## Why

WebComPy's navigation guards (`router.before_route_change`) are synchronous and can only cancel: a guard returns `False` to block, anything else to allow. The two most common real-world guard use cases are impossible today:

1. **Async checks** — authentication/authorization typically requires an async operation (validating a token, fetching a user profile via `FetchPort`). A sync guard cannot await, so apps must either preload all auth state before app start (bad UX) or implement ad-hoc post-navigation checks with flickering protected content.
2. **Redirects** — the idiomatic "not logged in → go to `/login`" flow. Today a guard can only cancel, leaving the user stuck on the current page with no built-in way to send them elsewhere. Vue Router (`return '/login'` / `next('/login')`), React Router (`redirect()`), Angular (`UrlTree` from `CanActivate`), and SvelteKit (`redirect()`) all treat redirect as a first-class guard outcome.

Investigation during proposal revealed a related wart: `RouterLink` performs `window.history.pushState` *before* guards run (`router/_link.py:111`), so a cancelled navigation already mutated the address bar, and programmatic `set_path` never updates the address bar at all (only `RouterLink` calls `pushState`). Async guards would make this divergence worse, so this change also moves browser URL ownership into the navigation pipeline.

## What Changes

- **Guard signature extended**: `before_route_change` callables become `Callable[[str, str], bool | str | Awaitable[bool | str] | None]`:
  - `None` / `True` → allow (unchanged)
  - `False` → cancel (unchanged)
  - `str` → **redirect**: cancel the current navigation and start a fresh navigation to the returned path (full guard chain re-runs on the target; redirect depth bounded at 10 to detect loops)
  - `Awaitable[bool | str | None]` → **awaited**; the resolved value is interpreted as above
- **Sync fast-path stays synchronous**: when every guard returns a non-awaitable, `__set_path__` completes fully synchronously — existing apps see zero behavior change beyond the URL fix below. When a guard returns an awaitable, the remainder of the chain and the navigation complete asynchronously via the framework's existing `resolve_async` dual-environment machinery.
- **Latest-wins for concurrent navigations**: each navigation attempt gets a monotonic token; when a new navigation starts while an async guard chain is pending, the superseded chain abandons without navigating or firing `after_route_change` (Vue Router cancellation semantics). Sync chains can never be superseded (they complete atomically).
- **Redirect uses URL replacement**: a redirect replaces (not pushes) the browser history entry, so Back never lands on a URL that just redirects again.
- **Browser URL ownership moves into the pipeline**: `HistoryPort` gains `push_url(path, state)` / `replace_url(path, state)`; the URL is updated only AFTER guards pass. Consequences:
  - Cancelled navigations no longer touch the address bar (fix).
  - Programmatic `set_path` now updates the address bar like `RouterLink` clicks (fix, intentional behavior change).
  - `RouterLink` drops its manual `pushState` call; `href` generation for the anchor is unchanged (right-click/open-in-new-tab unaffected).
- **Guard exceptions** route to `router.on_route_error` (existing); an unhandled guard exception cancels the navigation.
- **`after_route_change` unchanged**: sync callbacks, fired only after a navigation actually applies — for async guard chains, after the chain resolves.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `router-hooks`: guard result semantics (redirect, awaitable), async dispatch model with latest-wins, redirect loop bound, exception routing. The existing "hooks dispatch synchronously" requirement is revised to the sync fast-path contract.
- `port-abstraction`: `HistoryPort.push_url` / `replace_url`.
- `router`: `RouterLink` no longer calls `pushState` itself; URL updates flow through the pipeline (including `base_url`/hash-mode prefixing in the browser history port).

## Impact

- **Code**: `router/_router.py` (`__set_path__` pipeline, navigation token, redirect loop bound); `ports/_history.py` + `ports/_browser/_history.py` (URL methods; browser impl gains optional `base_url` for URL building); `ports/_server` + `webcompy_testing` fakes (no-op/recording impls); `router/_link.py` (remove manual `pushState`).
- **Specs**: deltas to `router-hooks`, `port-abstraction`, `router`.
- **Docs**: router page in `docs_app` gains guard examples (async auth guard, login redirect).
- **Tests**: unit tests server-side (async guards run fine in standard Python): redirect, redirect loop bound, async allow/cancel, latest-wins supersession, sync fast-path synchronicity, URL push/replace recording via fakes; e2e login-redirect scenario.
- **Behavior changes (intentional)**: programmatic `set_path` updates the address bar; cancelled `RouterLink` navigations no longer mutate the address bar. Both are bug-fix-class changes; no migration needed.

## Known Issues Addressed

- Guards cannot perform async checks (auth validation requires workarounds).
- Guards cannot redirect (cancel-only semantics).
- Cancelled navigation still rewrites the browser address bar (`pushState` before guards).
- Programmatic `set_path` never updates the browser address bar.

## Non-goals

- **Per-route / declarative guards** (guards attached to route definitions or page components, Vue's `beforeEnter`): the global hook list remains the only registration mechanism in this change.
- **In-component leave guards** (`on_route_leave` / "unsaved changes" prompts): separate change.
- **Async `after_route_change` / `on_route_error`**: remain synchronous notification callbacks.
- **True coroutine cancellation** of a superseded guard chain mid-await: superseded chains check a token at continuation points only; user code already running completes (documented).
- Parallel guard execution: guards remain strictly sequential, matching short-circuit semantics.
