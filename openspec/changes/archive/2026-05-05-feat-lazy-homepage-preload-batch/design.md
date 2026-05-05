## Context

The docs app (`docs_app/router.py`) eagerly imports `HomePage` at the top of the file while all other page components are wrapped in `lazy()`. This inconsistency was likely a micro-optimization assumption that users always enter through `/`. However, in practice users may enter through deep links (e.g., `/documents`, `/sample/todo`). When they do, `HomePage` is loaded unnecessarily.

The router's `preload_lazy_routes()` method schedules one `browser.window.setTimeout(_do_preload, 0)` per unresolved lazy route. The signal effect system (`signal/_effect.py`) uses a more efficient pattern: batching all pending work into a single `setTimeout` callback. Aligning the router with this pattern reduces `setTimeout` scheduling overhead.

## Goals / Non-Goals

**Goals:**
1. Make the `/` route in `docs_app` consistent with other routes by using `lazy()`
2. Batch lazy route preloading into a single `setTimeout` call to match the framework's existing defer patterns

**Non-Goals:**
- Changing the `Router` API surface or default `preload=True` behavior
- Modifying how `LazyComponentGenerator` resolves or caches imports
- Changing the e2e test app router configuration
- Adding new spec-level requirements (these are implementation-level optimizations)

## Decisions

### Decision: Use `lazy()` for the `/` route

**Rationale:** The framework supports `lazy()` for any route path, including `/`. There is no technical constraint that prevents the root route from being lazy-loaded. Making it lazy ensures all entry points to the docs app benefit from deferred loading equally.

**Alternative considered:** Keep `HomePage` eager with a comment explaining it's a landing page optimization. Rejected because the optimization is speculative (not all users enter through `/`) and the inconsistency is unnecessary.

### Decision: Batch preloading into a single `setTimeout`

**Current code:**
```python
for route in self.__routes__:
    component = route[3]
    if isinstance(component, LazyComponentGenerator) and component._resolved is None:
        if browser:
            def _do_preload(c=component):
                c._preload()
            browser.window.setTimeout(_do_preload, 0)
```

**New code:**
```python
lazy_components = [
    route[3] for route in self.__routes__
    if isinstance(route[3], LazyComponentGenerator) and route[3]._resolved is None
]
if lazy_components:
    if browser:
        def _batch_preload(components=lazy_components):
            for c in components:
                c._preload()
        browser.window.setTimeout(_batch_preload, 0)
    else:
        for c in lazy_components:
            c._preload()
```

**Rationale:** Reduces `setTimeout` scheduling from O(n) to O(1) where n is the number of lazy routes. The `signal/_effect.py` module uses the same batching pattern (`_pending_effects` + single `setTimeout`). This improves consistency across the codebase.

**Alternative considered:** Use `queueMicrotask`. Rejected because `setTimeout(0)` is already the established defer mechanism in the framework, and `queueMicrotask` is not exposed by the `browser` wrapper. Switching would require broader changes and testing.

## Risks / Trade-offs

- [Risk] Batching changes the order/timing of individual preloads slightly (all happen in one callback instead of multiple). → Mitigation: The existing tests (`test_lazy_routing.py`) verify preload correctness but not timing granularity. The change preserves the observable behavior (all lazy routes are preloaded after render).
- [Risk] `docs_app` is both the live documentation site and serves as an example for users. Making `/` lazy signals that root routes can be lazy. → This is intentional and desirable.

## Migration Plan

No migration needed. This is a backward-compatible optimization:
1. Update `docs_app/router.py`
2. Update `webcompy/router/_router.py`
3. Run existing tests (`uv run pytest tests/`) to verify lazy routing behavior
4. Verify docs app dev server loads correctly (`uv run python -m webcompy start --dev --app docs_app.bootstrap:app`)
