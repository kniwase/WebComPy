## Context

WebComPy's reactive system uses a global `ReactiveStore` singleton that tracks all reactive instances and their callbacks. When a `Reactive` value changes, `_change_event` immediately fires all `on_after_updating` / `on_before_updating` callbacks registered against that instance. `Computed` captures its dependencies once at initialization via `detect_dependency()` and subscribes to each via `on_after_updating(self._compute)`, meaning dependency changes from conditional branching are never updated. Element types (TextElement, Element, SwitchElement, RepeatElement) manually subscribe via `on_after_updating` and clean up via `ReactiveStore.remove_callback(callback_id)`.

This architecture has several well-documented problems: eager recomputation of Computed values even when unread, diamond dependency graphs causing duplicate updates, no equality checks on write, dynamic dependency tracking failure, and the global singleton making scoped cleanup impossible. The `__purge_reactive_members__` method in `ReactiveReceivable` is a no-op, and several subscriptions (TypedRouterLink, AppDocumentRoot) are never cleaned up.

Angular Signals and Vue 3's reactivity system demonstrate proven patterns that address these problems. Angular's push/pull with version tracking, lazy computed evaluation, and graph-based cleanup provide a model that maps directly to WebComPy's `.value`-based API. Vue 3's composable pattern (`useXxx`) shows how reactive primitives can be composed into reusable stateful logic when supported by a properly scoped reactive graph.

## Goals / Non-Goals

**Goals:**

- Replace the eager push callback model with a push/dirty-flag + pull/recompute model so that Computed values only recompute when read and skip propagation when the result is unchanged
- Implement equality checks so that writing the same value to a Reactive does not trigger downstream notifications
- Implement dynamic dependency tracking for Computed so that conditional branches correctly update the producer set on each re-evaluation
- Replace the global ReactiveStore singleton with per-node graph state (ReactiveNode + ReactiveEdge linked lists) with deterministic `consumerDestroy()` cleanup
- Introduce a graph-level `effect()` primitive that automatically tracks dependencies, supports cleanup via `on_cleanup`, and enables batched/scheduled execution
- Enable composable (`useXxx`) functions that return reactive primitives with automatic lifecycle-bound cleanup
- Preserve full backward compatibility of the public API (`Reactive`, `Computed`, `ReactiveList`, `ReactiveDict`, `computed`, `computed_property`, `readonly`, `on_after_updating`, `on_before_updating`)
- Fix all known subscription leaks (TypedRouterLink, AppDocumentRoot, Component._head_props)

**Non-Goals:**

- Property-level reactivity for collections (Vue 3's `reactive()` Proxy approach is impossible in Python)
- Virtual DOM diffing
- `linkedSignal` or `resource()` async primitives (separate future change)
- Signal-based component inputs (`input()`, `output()`, `model()`)
- Public custom `equal` function API (internal equality only)
- Strict `_in_notification_phase` read prohibition during push propagation (warn only in Phase 1)

## Decisions

### Decision 1: Linked list graph over dict/set for ReactiveNode edges

**Choice:** Angular-style linked list (`ReactiveEdge` with `next_producer` / `prev_consumer` / `next_consumer` pointers)

**Alternatives considered:**

- **Dict-based edges (Angular v15 approach):** Uses `Map<id, ReactiveEdge>` indexed by node ID. Simpler to implement in Python, but requires `trackingVersion` for stale edge detection and does not support incremental dependency rebuilding as naturally.
- **Set-based edges:** `producers: set[ReactiveNode]`, `consumers: set[ReactiveNode]`. Simplest implementation, but requires full rebuild of dependency sets on each Computed re-evaluation and provides no ordering guarantees for diamond resolution.

**Rationale:** Linked lists enable Angular's incremental producer list rebuilding during Computed re-evaluation — as the computation runs, producers are verified or replaced in-place rather than rebuilt from scratch. This is critical for dynamic dependency tracking (conditional branches). Python's object overhead per edge node (~56 bytes) is acceptable because edge counts are typically 1–10 per node and DOM operations dominate runtime cost. The linked list approach also aligns with Angular's current implementation, making it easier to port bug fixes and optimizations.

### Decision 2: Global epoch counter for fast skip checks

**Choice:** Maintain a global `_epoch` counter incremented on every writable signal write. Each ReactiveNode stores `last_clean_epoch`. If `last_clean_epoch == _epoch`, the node is guaranteed clean regardless of dirty flags.

**Alternatives considered:**

- **Version-only checks (no epoch):** Compare `seen_version` against `producer.version` for each edge. Correct but requires traversing the entire producer chain on every read.
- **No caching at all:** Always recompute. Simplest but defeats the purpose of lazy evaluation.

**Rationale:** Epoch-based skip is an O(1) check that short-circuits polling entirely when no signals have been set since the last read. This is especially valuable in WebComPy's browser environment where PyScript execution is slow — every avoided Python function call matters.

### Decision 3: `on_after_updating` / `on_before_updating` backward compatibility via CallbackConsumerNode

**Choice:** Implement `on_after_updating` and `on_before_updating` as `CallbackConsumerNode` instances (special `ReactiveNode` subclasses with `consumer_is_always_live = True`) that immediately invoke their callback in `consumer_marked_dirty()`.

**Alternatives considered:**

- **Deprecate and remove:** Break backward compatibility, force all callers to migrate to `effect()`. Clean but causes large migration burden.
- **Schedule callbacks via microtask:** Queue callback invocation like Angular's `effect()` scheduler. Maintains semantics but changes timing from synchronous to asynchronous, breaking existing code that relies on synchronous notification.

**Rationale:** The immediate-invoke approach preserves exact timing semantics of the current system (synchronous callback after value change), which element subscriptions and user code depend on. The Diamond Problem (duplicate Computed evaluation) is NOT solved by this approach — that requires the `effect()` scheduler in Phase 3. This is explicitly accepted as a non-goal for this change: Phase 1 preserves existing semantics including the Diamond glitch, while establishing the graph infrastructure that makes Phase 3 possible.

**Diamond behavior in Phase 1:**
```
price = Reactive(10)
tax = Computed(lambda: price.value * 0.1)
shipping = Computed(lambda: 5 if price.value > 0 else 0)
total = Computed(lambda: tax.value + shipping.value)

price.value = 20
# tax's CallbackConsumerNodes fire immediately (as today)
# shipping's CallbackConsumerNodes fire immediately (as today)
# total recomputes twice if both tax and shipping have on_after_updating callbacks
# → same glitch as current system, NOT worse
```

### Decision 4: Equality check strategy

**Choice:**

- `Reactive`: `equal = lambda a, b: a is b or a == b` (identity then equality). This means setting the same value object skips propagation; setting a different object with equal value also skips.
- `ReactiveList` / `ReactiveDict`: Mutating methods (`append`, `__setitem__`, etc.) always propagate (they mutate in-place, so identity check alone is insufficient). `set_value(new_list)` on ReactiveList uses the same `is or ==` check.
- `Computed`: After recomputation, if `new_value == old_value`, do not increment version (skip propagation to consumers).

**Alternatives considered:**

- **Identity-only (`is`):** Most conservative. Would cause `Reactive(1).value = 1` (different int object) to propagate unnecessarily. Python interns small integers, but not larger ones or strings.
- **Custom `equal` parameter per instance:** Maximum flexibility but adds API surface and mental model complexity. Deferred to future change.
- **No equality check:** Current behavior. Every `set_value` triggers full propagation.

**Rationale:** The `is or ==` check balances correctness and simplicity. For primitives and small collections, `==` is fast. For large collections, the comparison cost is offset by avoiding unnecessary DOM updates. The ReactiveList/ReactiveDict mutating methods bypass equality because they represent semantic changes (the in-place mutation already happened).

### Decision 5: `effect()` scheduling model

**Choice:** `effect()` registers a `ReactiveNode` with `consumer_is_always_live = True`. On dependency change, `consumer_marked_dirty()` is called synchronously. The effect function itself is queued for execution via `browser.window.setTimeout(fn, 0)` (microtask batching), ensuring Diamond dependencies resolve before the effect runs.

**Alternatives considered:**

- **Synchronous execution:** Run effect immediately in `consumer_marked_dirty()`. Simplest but causes Diamond glitches and re-entrancy problems.
- **Angular-zone-style integration:** Batch with change detection cycle. Requires a change detection system WebComPy doesn't have.

**Rationale:** Microtask batching via `setTimeout(fn, 0)` is the simplest scheduling that resolves Diamond glitches. All pending dirty flags settle before any effect runs, so effects see a consistent state. This matches the pattern WebComPy already uses for `on_after_rendering` callbacks in `SwitchElement`. Non-browser (SSG) execution runs effects synchronously since there is no event loop to schedule on.

### Decision 6: Vue 3 composable pattern integration with existing ContextVar scope

**Choice:** Composable functions (`useXxx`) are plain Python functions that create and return `Reactive` / `Computed` instances. Automatic cleanup is achieved by calling `effect()` within the composable, which inherits the current component's scope registration. The scope mechanism reuses the existing `_active_component_context` ContextVar already established by `_hooks.py` for `on_before_rendering` / `on_after_rendering` / `on_before_destroy`. A new `create_effect_scope()` function works within this ContextVar pattern: when called inside `Component.__setup()` (which already sets `_active_component_context`), effects are automatically collected for cleanup on component destruction.

**Alternatives considered:**

- **No scope management:** Composables return reactive values that are never cleaned up. Simplest but leaks subscriptions.
- **Explicit `on_cleanup` registration:** Composable authors manually register cleanup callbacks. Works but error-prone (current `useAsyncResult.watch` uses this pattern with `on_before_destroy`).
- **Separate scope stack:** Introduce a new scope stack independent of `_active_component_context`. Would duplicate scope tracking and risk inconsistencies.

**Rationale:** The framework already uses `contextvars.ContextVar` for scope management in `_hooks.py`. Reusing `_active_component_context` for effect scope registration avoids parallel scope systems, ensures effects are automatically scoped to the component that creates them, and leverages the existing lifecycle hook cleanup mechanism (`on_before_destroy`). The `Component.__setup()` method already wraps component setup in `_active_component_context.set/reset`, which is the natural integration point for `effect()` scope management. This approach also means existing composables like `useAsyncResult` can migrate their manual `on_after_updating` + `ReactiveStore.remove_callback` cleanup to `effect()` without changing scope semantics.

### Decision 7: ReactiveStore backward-compatible shell

**Choice:** `ReactiveStore` class is retained as a thin shell that delegates to the new graph infrastructure. Its `add_reactive_instance`, `add_on_after_updating`, `add_on_before_updating`, `remove_callback`, `callback_after_updating`, `callback_before_updating`, and `detect_dependency` methods continue to work by creating/managing `CallbackConsumerNode` instances or calling the appropriate graph operations.

**Rationale:** Multiple external files import from `webcompy.reactive._base` directly (tests, router, aio, element types, app). A full removal would require touching 20+ files in a single change. The shell approach allows gradual migration while keeping all existing tests passing.

## Risks / Trade-offs

**[Risk: CallbackConsumerNode preserves Diamond glitch in Phase 1]** → Mitigation: Document this as known limitation; Phase 3 (effect-based element subscriptions) will resolve it completely. The glitch behavior is identical to the current system — no regression.

**[Risk: Equality check changes callback contract semantics]** → Mitigation: `on_after_updating` callbacks currently receive the return value of the mutating method (`None` for `append`, popped value for `pop`, new value for `set_value`). The new `CallbackConsumerNode` will receive `producer._value` (the current value of the reactive). For `Reactive.set_value` this is the same; for mutating methods on `ReactiveList`/`ReactiveDict` the callback argument changes from `None`/popped-value to the full list/dict. Tests that assert on callback argument value need updating, but element code (TextElement, SwitchElement, RepeatElement) already ignores arguments with `*args`. User-facing documentation will note this change.

**[Risk: Performance overhead of linked list operations in PyScript]** → Mitigation: Profile before and after using the existing todo app demo. Linked list edge manipulation occurs O(dependencies) times per Computed evaluation, typically 1–5 edges. This is negligible compared to DOM operations and PyScript interpreter overhead. If profiling reveals issues, the linked list can be swapped for a dict-based approach without changing the public API.

**[Risk: Global `_active_consumer` and `_in_notification_phase` state]** → Mitigation: These are module-level variables in `_graph.py` (equivalent to Angular's `activeConsumer` and `inNotificationPhase`). Tests must reset globals between runs. A `reset_graph_state()` function is provided for test fixtures. PyScript's single-threaded model means no concurrency concerns.

**[Risk: Migration scope affects 30+ files]** → Mitigation: Phase the implementation. Phase 1 (this change) covers `_graph.py`, `_base.py`, `_computed.py`, `_container.py`, `_readonly.py`, and test files. Element and component files are migrated to use the new `effect()` pattern but keep working via `CallbackConsumerNode` compatibility. A separate change (Phase 3) handles the full element migration and Diamond glitch resolution.

## Open Questions

- **Scope push/pop API:** Should `create_effect_scope()` be a context manager (`with effect_scope(): ...`) or a decorator (`@component_template` handles it internally)? Vue uses `setup()` implicit scoping; Angular uses injection context. Need to decide on ergonomics.
- **`on_before_updating` semantics in the new model:** The current `on_before_updating` fires before the value changes with the old value. In a push/pull model, the "before" moment is during the push phase (dirty flag propagation). Should `on_before_updating` fire at the start of `consumer_marked_dirty` with the old value, or should it be deprecated in favor of `effect()` with value comparison?
- **SSG (static site generation) path:** The current code has server-side reactive subscription paths in `SwitchElement._on_set_parent` (no browser) and no subscription in `RepeatElement._on_set_parent`. The graph-based model needs to work in both browser and SSG contexts. The `effect()` callback scheduling must be synchronous in SSG (no `setTimeout`).

## Migration Plan

### Phase 1 (this change): Internal graph + backward compatibility

1. Create `_graph.py` with `ReactiveNode`, `ReactiveEdge`, and all graph operations
2. Rewrite `ReactiveBase`, `Reactive`, `Computed`, `ReadonlyReactive` internals to use `ReactiveNode` graph
3. Implement `CallbackConsumerNode` as backward-compatible `on_after_updating` wrapper
4. Implement `effect()` primitive with `effect_scope` context manager
5. Add equality checks to `Reactive.set_value`, `Computed`, `ReactiveList`/`ReactiveDict` mutating methods
6. Convert `ReactiveStore` to a thin delegation shell
7. Update tests: add graph operation tests, lazy evaluation tests, dynamic dependency tests, equality tests; adjust callback contract tests for new argument semantics
8. Verify all existing element/component/router/app code works unchanged

### Phase 2 (future change): Element subscription migration

- Migrate TextElement, Element, SwitchElement, RepeatElement from `on_after_updating` to `effect()`-based subscriptions
- Remove `CallbackConsumerNode` for element-level subscriptions (keep for user-facing `on_after_updating` backward compatibility)

### Phase 3 (future change): Diamond glitch resolution + effect scheduler

- Introduce batched effect execution to guarantee glitch-free propagation
- Resolve the `on_after_updating` Diamond problem by deprecating eager callback firing in favor of scheduled effects

### Rollback strategy

Each phase is independently deployable. If Phase 1 introduces regressions, `ReactiveStore` can be restored as the actual implementation (not just a shell) by reverting `_base.py` and `_computed.py` while keeping `_graph.py` as unused code. The public API does not change, so no user-facing code needs modification.