# Proposal: Nested Routes (`children`)

## Why

The router currently supports only a flat list of pages: every route is a full path matched independently, and `RouterView` swaps the entire page on every navigation. This makes shared layouts impossible — a common parent UI (docs sidebar, settings tabs, authenticated shell) must be re-declared inside every page component, and it is destroyed and re-created on every navigation, losing its state (scroll position, open/closed UI, in-progress inputs). Nested routes solve this by letting a parent route component render a nested `RouterView` for its children, so the parent persists across child navigation. This is the framework's layout mechanism, aligned with the component-composition philosophy (no separate template-inheritance system).

A key design constraint decided up front: **component reuse must never skip setup when anything the component observes has changed**. `RouterContext` is immutable, so reuse is only safe when the matched route record and all context values (`path_params`, `query`) at that level are identical to the previous navigation. Parameter changes always remount — preserving today's "setup runs on every navigation" semantics and avoiding stale-data bugs.

## What Changes

- `RouterPage` accepts an optional recursive `children: list[RouterPage]`. Child paths are joined under the parent's path (`/docs` + `/guide` → `/docs/guide`). A child with path `""` is the **index route** rendered when the parent path matches exactly.
- Route matching produces a **match chain**: the ordered list of matched route records from root to leaf, with per-level path params.
- `RouterView` becomes depth-aware: it determines its depth by counting `RouterView` ancestors in the element tree and renders the component at that chain level. The app root's `RouterView` is depth 0; a layout component renders a nested `RouterView` for depth 1, and so on.
- **Reuse rule**: a chain level's component instance is preserved across navigations only when that level's route record, accumulated `path_params`, and `query` are all identical; otherwise that level (and all deeper levels) are destroyed and re-created. Reuse leverages signal equality (the preserved instance is the same object, so no downstream refresh fires).
- `RouterContext.path_params` accumulates params from all ancestor levels (child wins on name collision).
- Lazy loading and preloading work per route node (existing `lazy()` components may appear at any level); SSG enumerates full paths of all leaf chains through the existing `Router.__routes__` structure (unchanged shape).
- Router hooks (`before_route_change`/`after_route_change`/`on_route_error`) fire once per navigation, not per level.
- Flat page definitions (no `children`) behave exactly as today: chains of length 1 rendered by the depth-0 `RouterView`.

## Capabilities

### New Capabilities

(none — behavior lands in the existing `router` capability)

### Modified Capabilities

- `router`: adds nested route definitions, match-chain resolution, depth-aware `RouterView`, level-reuse rule, index routes, and ancestor param accumulation; keeps flat-route behavior and the SSG route-enumeration contract unchanged.

## Impact

- **Code**: `packages/webcompy/src/webcompy/router/_pages.py` (recursive `children`), `packages/webcompy/src/webcompy/router/_router.py` (tree flattening, chain matching, `current_match` Computed replacing per-route `__cases__` for rendering; `__routes__` full-path list preserved for SSG), `packages/webcompy/src/webcompy/router/_view.py` (depth-aware RouterView with per-level instance preservation), `packages/webcompy/src/webcompy/router/_lazy.py` (preload traversal over the tree).
- **Specs**: `openspec/specs/router/spec.md`.
- **Tests**: unit tests for flattening/matching/reuse semantics; e2e nested-layout scenario (parent state preserved across sibling navigation, remount on param change).
- No breaking changes to public API (`Router`, `RouterPage`, `RouterView`, `RouterLink`, `RouterContext` usage patterns unchanged for flat routes).

## Known Issues Addressed

- Indirectly addresses the flat-only routing gap noted in the router spec's "does not yet provide" section (nested routes); route guards already exist via router-hooks.

## Non-goals

- Route-level data loaders (`load()` functions à la SvelteKit) — follow-up; data fetching stays in components via `use_async_result`.
- Reactive `RouterContext` (params updating in-place on reused components) — unnecessary under the identical-match reuse rule; revisit only if opt-in param-change reuse is added later.
- Parallel/named `RouterView`s (multiple outlets at the same depth rendering different branches) — v1 renders the single match chain.
- Route-level transitions/animations — separate planned change.
- Path converters/typed params (`{id:int}`) — separate follow-up.
- Per-level (nested) default/404 components — v1 uses the router-level default only.
