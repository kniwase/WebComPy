# Design: Nested Routes

## Context

**Goal of this document**: enable a fresh session to implement nested routes correctly per intent, including the reuse rule that was deliberately chosen to eliminate stale-setup bugs.

### Current router internals (verified against origin/main @ 5f9c52d)

- `RouterPage` (`packages/webcompy/src/webcompy/router/_pages.py`): TypedDict `{component, path, path_params?, meta?}` — flat.
- `Router.__routes__: list[RouteType]` (`_router.py:24-28`): 5-tuples `(path_str, matcher_fn, path_param_names, component, page)`; matchers are full-path regexes (`_generate_route_matcher`, `_router.py:155-156`).
- Rendering: `RouterView` (`_view.py`) wraps ONE `SwitchElement(router.__cases__, router.__default__)`; `__cases__` (`_router.py:75-83`) maps every route to `(match_obj, generator)` against the current path; first truthy match wins. Every navigation regenerates the matched page component (full remount).
- `RouterContext` (`_context.py`): immutable snapshot built per navigation (`_generate_router_context`, `_router.py:128-153`).
- Lazy: `LazyComponentGenerator` per route; `preload_lazy_routes` iterates `__routes__` (`_router.py:177-200`).
- SSG: `webcompy_cli/_generate.py:132-151` iterates `app.routes` (= `router.__routes__`), unpacks the 5-tuple, expands `page.get("path_params")` variants with `p.format(**params)`. **Constraint: `__routes__` must keep this 5-tuple shape with full paths.**
- History reactivity: `HistoryPort` is `SignalBase[str]`; `__cases__` is a `computed_property`, so the switch refreshes on URL change.
- `RouterView` is a `DynamicElement` and already uses `_on_set_parent()` for initialization and preload scheduling.

### The reuse rule (decided, not open)

A level's component instance is preserved across a navigation **iff** at that level: (1) the matched route record is identical, (2) the accumulated `path_params` are identical, and (3) the `query` dict is identical. Otherwise that level and all deeper levels remount. Rationale: `RouterContext` is immutable; reusing a component whose context changed would silently skip setup (stale data). Under this rule, reuse only happens when the component observes nothing new — sibling navigation under a shared parent — which is exactly the layout use case. Parameter or query changes always re-run setup, consistent with today's flat-router behavior. Vue Router's "reuse + watch params" model was considered and rejected for v1 (requires reactive context; can be added opt-in later).

## Goals / Non-Goals

**Goals:**

- `children` nesting with joined paths and index (`""`) child routes.
- Depth-aware `RouterView` rendering per-level chain components; flat routes behave identically to today.
- The reuse rule above, implemented via signal equality (same instance → no refresh).
- Lazy loading / SSG / hooks preserved; SSG enumeration contract unchanged.

**Non-Goals:** route loaders, reactive RouterContext, parallel/named outlets, transitions, path converters, per-level 404.

## Decisions

### D1. Flatten the page tree into chains at Router construction

`_generate_routes` recursively walks `children`, producing one entry per **leaf** (pages without children, plus index children). Each entry retains its full **chain**: ordered levels `[RouteNode, ...]` where `RouteNode = (segment_path, matcher, param_names, component, page)`.

- Path joining: parent `/docs` + child `/guide` → `docs/guide` (strip/normalize slashes); child `""` (index) → parent path itself.
- `Router.__routes__` keeps the EXISTING 5-tuple shape `(full_path, full_matcher, full_param_names, leaf_component, leaf_page)` for SSG compatibility, and a parallel `__chains__: list[ChainEntry]` maps full path → chain levels. Flat pages produce single-level chains — behavior identical to today.
- A page with `children` is NEVER itself a leaf-renderable entry unless an index child exists; requesting a bare parent path with no index child falls through to the router-level default (documented; per-level 404 is a non-goal).

### D2. `Router.current_match` is a Computed over the history signal

```python
class RouteMatch(Protocol):
    path: str
    chain: tuple[RouteNode, ...]        # matched levels, root → leaf
    per_level_params: tuple[dict[str, str], ...]  # params extracted per level
    path_params: dict[str, str]         # accumulated merge (child wins)
    query: dict[str, str]
    state: dict[str, Any]
```

`current_match: Computed[RouteMatch | None]` re-evaluates on `history.value` change (lazy, equality-checked). `None` → router-level default (existing `__default__` path). Matching walks chains: for each chain, match each level's matcher against successive path segments; full match required. First matching chain wins (definition order), mirroring today's first-match-wins.

Level matching detail: compile each level's segment pattern as today (`_convert_to_regex_pattern`), but anchored per-segment rather than full-path; the chain consumes the path segment-by-segment. The full-path matcher for `__routes__` is still produced by joining level patterns (used by SSG and as the chain pre-filter).

### D3. RouterView depth = count of RouterView ancestors

`RouterView` walks `self._parent` links counting `RouterView` instances; that count is its depth `N` (root `RouterView` → 0). This needs no DI/ContextVar plumbing and is immune to component-setup timing (async two-phase setup) because the element tree already encodes nesting. A `RouterView` at depth N subscribes to a per-level holder (D4) and renders `chain[N]`'s component when the chain has more than N levels; otherwise it renders nothing (empty).

Edge cases: multiple `RouterView`s at the same depth (different branches) each render their level of the single current match — allowed, documented. A `RouterView` deeper than the chain renders empty (NOT an error), which makes conditional layouts safe.

**Implementation note (deviation from D3):** depth is NOT computed in `_on_set_parent()`. During component setup the parent chain is incomplete — a `RouterView`'s `_parent` links are assigned when its ancestor component renders, which happens later — so counting there would always yield 0 and break nesting. The shipped `RouterView` computes depth at match time via `_count_router_view_ancestors()` (called from `_get_or_create_component()` in `_on_match_changed()`/`_render()`), when the parent chain is fully wired.

### D4. Per-level component preservation via a holder Computed

Each `RouterView` maintains:

```python
self._mounted: Component | None          # currently mounted instance (plain attr)
self._level_component: Computed[Component | None]
```

The Computed reads `router.current_match` and:

1. If no match or chain too short → destroy `_mounted` (call its `_remove_element`/destroy path), return `None`.
2. If match: compare `(chain[N].record_identity, accumulated_params(0..N), query)` against the tuple captured when `_mounted` was created.
   - Identical → return `_mounted` (SAME object). Signal equality (`old is new`) suppresses downstream notification → **no re-render, setup not re-run, DOM/state preserved**.
   - Different → destroy `_mounted`, create `chain[N].component(props)` with `RouterContext(path=..., query=..., path_params=accumulated, state=...)`, capture the comparison tuple, return the new instance.

The `RouterView` renders via a `SwitchElement` whose single case tracks whether `_level_component.value is not None` and whose generator returns `_level_component.value`. (Reusing `SwitchElement` keeps deferred-`on_after_rendering` semantics from the async-rendering pipeline.)

`RouterContext.path_params` for level N = merge of `per_level_params[0..N]` (child wins on collision).

**Implementation note (deviation from D4):** the shipped `RouterView` does NOT render through a `SwitchElement`. It manages `_mounted_component` / `_mounted_identity` directly (destroy via `_remove_element()`, create via `node.component(context)`), which keeps component destruction side effects out of the holder Computed (a Computed should be pure/derived). The deferred-`on_after_rendering` semantics are preserved by wrapping the new component's `_render()` in `start_defer_after_rendering()` / `end_defer_after_rendering()` inside `_on_match_changed()`, mirroring `SwitchElement._refresh`.

### D7. Transient-creation guard (`_ancestor_will_remount`)

Without extra coordination, when a navigation changes an ANCESTOR level's identity (query change, ancestor param change), the old deeper `RouterView`'s `_on_match_changed` callback can fire before the remounting ancestor destroys the old subtree — creating a transient child instance that is immediately discarded (setup side effects run twice; the transient component is briefly rendered into the doomed subtree). Signal dispatch order is not guaranteed top-down, so this cannot be fixed by ordering.

The shipped implementation adds `RouterView._ancestor_will_remount(match)`: at the top of `_on_match_changed`, the view walks its `_parent` chain, and for each ancestor `RouterView` (depth k) compares the new match's identity at level k (`_build_identity`) against the ancestor's CURRENT (not yet updated) `_mounted_identity`. If any ancestor differs — or the chain is shorter than the ancestor's depth, or the match is `None` — the deeper view returns early: the ancestor will remount and its fresh subtree will recreate the deeper view exactly once.

- The guard is dispatch-order independent: it reads the ancestor's pre-navigation identity, which is stable until the ancestor's own callback runs; the comparison is identical to the ancestor's own mount decision, so a skip is always followed by the ancestor's remount.
- Depth-0 views always return `False` (no ancestors) and never skip.
- When all ancestors are preserved (sibling navigation, leaf param change), the guard returns `False` and the deeper view reacts on its own, preserving today's remount semantics.
- Net effect: each chain level is re-created at most once per navigation; `test_query_change_remounts_level` / `test_ancestor_param_change_remounts_descendants` assert the leaf is created exactly once (count 2, not 3).

### D5. Navigation, hooks, lazy, and SSG stay on existing paths

- `__set_path__` fires hooks once per navigation — untouched.
- `preload_lazy_routes` walks the page tree (all nodes, any depth) instead of the flat list.
- SSG: `webcompy_cli/_generate.py` expands each route via `Router.__route_variants__` (a parallel list to `__routes__`), which merges the `path_params` of ALL chain levels into a Cartesian product (child wins on collision). This is a review-driven change from the original "leaf-only" plan: a nested route such as `/users/{uid}` with a dynamic parent and `path_params` on the parent previously produced a literal `users/{uid}/docs` page. For flat routes the variants are identical to the old `page.get("path_params")` expansion, so behavior is unchanged. History-mode SSR of a full path resolves the chain via `current_match` identically to browser.
- Request-scoped routers: `RenderContext` clones the app router via `Router._clone_for_request()`, which now copies `before_route_change` / `after_route_change` / `on_route_error` (review-driven fix: hooks registered by plugins on `app.router` must also exist on the injected per-request router).
- Lazy components: `LazyComponentGenerator._resolve()` re-registers the resolved generator into the active render-context component store on every call (idempotent by name), and `preload_lazy_routes` traverses resolved lazies too — a component resolved during the first SSR/SSG request stays registered in later requests' fresh stores (scoped styles / template tag resolution preserved). `preload_lazy_routes` deduplicates shared `LazyComponentGenerator` instances across sibling branches (single `seen` set for the whole traversal).
- Hash mode: matching input is the hash path, same as today.
- Async navigation: `RouterView._on_match_changed()` tracks a per-view navigation generation; after awaiting the new component's `_render()` it skips the DOM commit / deferred `on_after_rendering` dispatch when a newer navigation superseded it, and `end_defer_after_rendering()` runs in a `finally` so a failed render cannot unbalance the defer scope (review-driven fixes).

### D6. Backward compatibility surface

Public API unchanged: `Router(...)`, `RouterPage` (new optional key only), `RouterView()`, `RouterLink`, `RouterContext` shape. Internals renamed freely (`__cases__` may be removed once `RouterView` uses `current_match`; it is double-underscore private). Existing flat-route tests must pass unmodified.

## Risks / Trade-offs

- [Chain matching order bugs with sibling patterns] → first-definition-wins, mirroring today; unit tests cover overlapping patterns (`/docs/new` vs `/docs/{name}`).
- [Holder Computed leaks destroyed components] → destruction happens inside the Computed on transition; destroyed components unsubscribe via the existing component/DI-scope disposal path.
- [Depth-by-ancestor-walk breaks under reparenting] → RouterViews are not reparented in practice; depth is recomputed at match time, so a reparented view would simply get a fresh depth on the next match.
- [Query-identity rule remounts pages on irrelevant query changes] → deliberate (context immutability); documented as current-behavior-consistent; apps can strip query keys via `before_route_change` redirects if needed.
- [Index route `""` collides with a sibling `"{param}"`] → definition order decides; spec scenario pins this.

## Migration Plan

No migration needed; flat definitions work unchanged. Docs app may adopt nested routes in a follow-up.

## Open Questions

None.
