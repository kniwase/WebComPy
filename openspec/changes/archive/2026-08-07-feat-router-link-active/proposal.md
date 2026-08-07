# Proposal: RouterLink Active State (`active_class` / `exact` / `aria-current`)

## Why

Navigation menus are the most common UI in any routed app, and every one of them needs "highlight the current page's link." WebComPy's `RouterLink` currently has no active-state support: developers must hand-subscribe to `router.current_match`, compute a class string, and merge it into `attrs` — boilerplate repeated in every nav component. Vue Router (`RouterLink` active/exact-active classes), React Router (`NavLink`), Angular (`routerLinkActive`), and SvelteKit (`aria-current` / `$page` comparison) all ship this built in. For an official release, WebComPy's `RouterLink` should too.

## What Changes

- **`RouterLink` gains two optional keyword arguments**:
  - `active_class: str | SignalBase[str] | None = None` — class name(s) applied while the link's target path matches the current route.
  - `exact: bool = False` — when `True`, require an exact path match; when `False` (default), a prefix match on path segments activates the link (a link to `/docs` is active on `/docs/getting-started`).
- **Matching rules** (Vue Router parity):
  - Comparison uses the path portion only (query string ignored).
  - The root target `/` is always matched exactly (a link to `/` is active only on `/`), so a "Home" link is not highlighted on every page.
  - No route match (`current_match is None`, e.g. 404) → never active.
- **`aria-current="page"`** is added to the rendered `<a>` while active (removed when inactive), for accessibility.
- **Reactive**: the link subscribes to `router.current_match` and re-renders its attributes on navigation, so active state follows client-side navigation without any user code.
- **SSR/SSG correct**: the initial render computes active state from the request path, so statically generated pages ship the correct class and `aria-current` in HTML; hydration then keeps it reactive.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `router`: adds RouterLink active-state support (matching rules, reactive updates, `aria-current`).

## Impact

- **Code**: `packages/webcompy/src/webcompy/router/_link.py` only (new kwargs, match computation, `Computed`-based `class`/`aria-current` attribute values reusing the element attr-updater mechanism, attr merging in `_generate_attrs`).
- **Specs**: delta to `openspec/specs/router/spec.md`.
- **Docs**: router documentation page in `docs_app` gains an active-link section.
- **Tests**: unit tests via `webcompy_testing` for each matching rule and reactive update; docs demo unaffected.
- No breaking changes: both new arguments are optional; existing `RouterLink` usage renders identically.

## Known Issues Addressed

- No built-in way to style the currently-active navigation link (per-app hand-rolled subscriptions to `router.current_match` are the only option).

## Non-goals

- A separate `exact_active_class` distinct from `active_class` (Vue Router has both; YAGNI — `exact=True` + `active_class` covers the use case).
- Active state on arbitrary wrapper elements (Vue's custom-render `v-slot` API); `RouterLink` renders its own `<a>` only.
- Applying active styles to ancestor menu items or auto-collapsing submenus (app-level concern).
