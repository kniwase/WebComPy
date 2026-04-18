## Why

The current reactive system has fundamental architectural limitations: Computed values re-evaluate eagerly on dependency change (even if nobody reads the result), dependencies captured at initialization cannot adapt to conditional branches, equal-value writes trigger full propagation, and the global ReactiveStore singleton makes testing and component-level cleanup impractical. These issues cause unnecessary DOM updates, prevent glitch-free propagation in diamond dependency graphs, and leak reactive subscriptions when elements are removed. Angular's Signals architecture — push/pull version tracking, lazy computed evaluation, dynamic dependency tracking, and graph-based cleanup — provides a proven pattern that maps naturally to WebComPy's `.value`-based API. Vue 3's composable pattern (`useXxx`) further demonstrates how reactive primitives can be composed into reusable stateful logic when backed by a properly scoped reactive graph. This change redesigns the reactive internals to adopt these patterns while preserving the existing public API.

## What Changes

- Replace the global `ReactiveStore` singleton with a per-node reactive graph (ReactiveNode + ReactiveEdge) where each node holds its own version counter, dirty flag, producer/consumer linked lists, and epoch tracking
- Implement push/pull propagation: dependency changes push dirty flags (no immediate recomputation), computed values pull/recompute lazily on read, and version checks skip unchanged values
- Implement equality checks on write: `Reactive.value = same_value` skips propagation entirely; `Computed` results that compare equal skip downstream notification
- Implement dynamic dependency tracking: `Computed` rebuilds its producer edges on each re-evaluation, accommodating conditional branching that changes which reactive values are read
- Introduce `effect()` primitive as a first-class live consumer with automatic dependency tracking, lifecycle-bound cleanup (`on_cleanup`), and scheduled execution — replacing the need for manual `on_after_updating` / `on_before_updating` registration in element code
- Replace `CallbackConsumerNode` (the compatibility layer for `on_after_updating`) with proper graph-attached consumers that support `consumerDestroy()` for deterministic cleanup, fixing the `__purge_reactive_members__` no-op and untracked subscription leaks
- Preserve the existing public API (`Reactive`, `Computed`, `computed`, `computed_property`, `ReactiveList`, `ReactiveDict`, `readonly`, `on_after_updating`, `on_before_updating`) as backward-compatible wrappers over the new graph
- Add `effect(fn, on_cleanup=None)` as a new public API: declares a side-effect function that automatically tracks its reactive dependencies and re-executes when they change, with automatic cleanup on component destruction
- Add composable pattern support (`useXxx`-style functions): functions returning `Reactive` / `Computed` tuples that are automatically scoped and cleaned up when the owning component is destroyed, enabled by the graph-based cleanup mechanism

## Known Issues Addressed

- No element-level reactivity in ReactiveList/ReactiveDict — partial mitigation: equality checks prevent unnecessary propagation on same-value writes; element-level granularity remains a separate concern
- `__purge_reactive_members__` in ReactiveReceivable is a no-op — replaced by `consumerDestroy()` on the reactive graph, providing deterministic cleanup of all producer/consumer edges
- Multiple global singletons (ReactiveStore) — ReactiveStore eliminated as a functional singleton; retained only as a backward-compatible import shell; graph state lives on individual nodes
- Computed captures dependencies at init only (dynamic branching bug) — fixed by incremental dependency rebuilding on each re-evaluation

## Non-goals

- Element-level reactivity for ReactiveList/ReactiveDict (property-level tracking like Vue 3's Proxy-based `reactive()`) — Python lacks JS Proxy semantics; this remains a separate future change
- Virtual DOM diffing — this change does not alter the direct DOM manipulation strategy
- Angular-style `linkedSignal` or `resource()` primitives — these are higher-level async patterns that can be introduced in a later change
- Signal-based component inputs (`input()`, `output()`, `model()`) — depends on component system changes; separate future change
- Custom `equal` function API — internal equality check uses `is` identity for mutable objects and `==` for immutables; public custom equality is deferred
- Strict `_in_notification_phase` enforcement during push propagation — Phase 1 logs warnings instead of raising; strict enforcement deferred to avoid breaking existing callback patterns

## Capabilities

### New Capabilities

- `effect`: First-class reactive side-effect primitive with automatic dependency tracking, lifecycle-bound cleanup, and batched execution scheduling
- `composable`: Pattern and conventions for composing reactive state into reusable functions (useXxx) with automatic scoping and cleanup via the reactive graph

### Modified Capabilities

- `reactive`: Change propagation semantics from eager immediate callbacks to push/dirty-flag notification with lazy pull recomputation; add equality checks to skip same-value writes; add dynamic dependency tracking for Computed; replace ReactiveStore singleton with per-node graph; deterministic cleanup via consumerDestroy()
- `components`: Component lifecycle integration with effect cleanup; __purge_reactive_members__ replaced by graph-based consumer disconnect on component destruction
- `elements`: Element subscriptions migrate from on_after_updating to effect-based pattern; attribute and text updates use the graph's version-based equality to skip unnecessary DOM operations

## Impact

- **Core reactive module** (`webcompy/reactive/`): Full internal rewrite — `_base.py`, `_computed.py`, `_container.py` replaced; new `_graph.py` added; `_readonly.py` updated; `_list.py` and `_dict.py` updated for new change propagation
- **Element system** (`webcompy/elements/types/`): `_abstract.py`, `_element.py`, `_text.py`, `_switch.py`, `_repeat.py`, `_dynamic.py` — subscription pattern migration from `on_after_updating` to `effect()`; `_dynamic.py` now has custom `_remove_element()` and `_position_element_nodes()` for nested DynamicElement support which must be preserved during migration; `_base.py` — reactive attribute processing update
- **Component system** (`webcompy/components/`): `_component.py` — lifecycle integration with effect cleanup via `_active_component_context` ContextVar; `_hooks.py` — `useAsyncResult.watch` cleanup migration from `on_after_updating` + `ReactiveStore.remove_callback` to `effect()` or `consumerDestroy()`; `_abstract.py` (DELETED) — references removed; `__purge_reactive_members__` on `ReactiveReceivable` (`_container.py`) replaced by `consumerDestroy()`
- **Async module** (`webcompy/aio/`): `_aio.py` — `AsyncComputed` updated for new change propagation; `_async_result.py` — `AsyncResult` (new) also uses `Reactive`/`Computed` internally and must be migrated
- **Router** (`webcompy/router/`): `_link.py`, `_change_event_handler.py` — subscription cleanup fix (currently untracked)
- **App root** (`webcompy/app/`): `_root_component.py` — subscription cleanup fix (currently untracked)
- **Public API**: Fully backward-compatible — `Reactive`, `Computed`, `ReactiveList`, `ReactiveDict`, `computed`, `computed_property`, `readonly`, `on_after_updating`, `on_before_updating` all preserved; `effect` and `composable` are new additions
- **Tests**: `test_reactive.py`, `test_list_mutation.py`, `test_dict_mutation.py` — callback contract assertions adjusted (argument semantics change); new tests for lazy evaluation, dynamic dependencies, equality skipping, effect lifecycle, and graph operations