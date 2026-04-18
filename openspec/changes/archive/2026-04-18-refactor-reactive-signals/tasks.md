## 1. Reactive Graph Core

- [x] 1.1 Create `webcompy/reactive/_graph.py` with global state (`_active_consumer`, `_in_notification_phase`, `_epoch`), `ReactiveNode` class (fields: `version`, `last_clean_epoch`, `dirty`, `recomputing`, `producers`, `producers_tail`, `consumers`, `consumers_tail`, `consumer_is_always_live`) and `ReactiveEdge` class (fields: `producer`, `consumer`, `last_read_version`, `prev_consumer`, `next_consumer`, `next_producer`)
- [x] 1.2 Implement graph operation functions: `set_active_consumer()`, `get_active_consumer()`, `producer_accessed()`, `producer_notify_consumers()`, `producer_update_value_version()`, `producer_mark_clean()`, `consumer_mark_dirty()`, `consumer_poll_producers_for_change()`, `consumer_before_computation()`, `consumer_after_computation()`, `finalize_consumer_after_computation()`, `consumer_destroy()`
- [x] 1.3 Implement helper functions: `producer_add_live_consumer()`, `producer_remove_live_consumer_link()`, `consumer_is_live()`, `_is_valid_link()`
- [x] 1.4 Add `reset_graph_state()` test utility function that resets `_active_consumer`, `_in_notification_phase`, and `_epoch`
- [x] 1.5 Write unit tests for graph operations in `tests/test_graph.py`: producer/consumer edge creation, consumer destruction, dynamic dependency rebuilding, epoch-based skip checks, diamond topology notification, live vs non-live consumer distinction

## 2. ReactiveBase Rewrite

- [x] 2.1 Refactor `ReactiveBase` in `_base.py` to inherit from `ReactiveNode`, replacing `__reactive_id__` and `_store` ClassVar with per-node graph fields. Keep `value` property getter decorated with `_get_event` and `value` setter. Add `version` field, `dirty` field, and `producer_must_recompute`/`producer_recompute_value` stubs
- [x] 2.2 Refactor `Reactive.set_value` to perform equality check (`a is b or a == b`), increment `_epoch` and `self.version` on actual change, and call `producer_notify_consumers()` instead of `ReactiveStore.callback_after_updating()`. Keep `on_after_updating` / `on_before_updating` via `CallbackConsumerNode`
- [x] 2.3 Refactor `_get_event` decorator to call `producer_accessed()` instead of `ReactiveStore.register()`, using `_active_consumer` global context
- [x] 2.4 Implement `CallbackConsumerNode` as a `ReactiveNode` subclass with `consumer_is_always_live = True`, storing a callback function and optional callback_id. In `consumer_marked_dirty()`, call `producer_update_value_version()` on the producer then invoke the callback with `producer._value`
- [x] 2.5 Implement `on_after_updating(func)` and `on_before_updating(func)` as factory methods that create `CallbackConsumerNode` instances, register them as live consumers of the producer node via `producer_add_live_consumer()`, and return the `CallbackConsumerNode` instance for cleanup via `consumer_destroy()`
- [x] 2.6 Remove `ReactiveStore` singleton, `_callback_registry`, `_callback_id_counter`, `_make_singleton` helper, `DeprecationWarning` shell, `remove_callback` module function, and `_find_callback_consumer_by_id`. Change `on_after_updating` / `on_before_updating` return type from `int` to `CallbackConsumerNode`. Migrate all callers from `ReactiveStore.remove_callback(cid)` to `consumer_destroy(node)`
- [x] 2.7 Write/update tests for `Reactive`: equality skip (same value, equal value), version increment on change, `on_after_updating` still fires on actual change, `on_before_updating` fires before change, `consumer_destroy()` removes callback

## 3. Computed Rewrite

- [x] 3.1 Refactor `Computed` to use `consumer_before_computation()` / `consumer_after_computation()` for lazy evaluation. Remove `_dependencies` list and `_dependency_callback_ids`. Implement `producer_must_recompute()` to return `self.dirty or self._value is sentinel`, and `producer_recompute_value()` to re-evaluate `self.__calc()` with dynamic dependency tracking
- [x] 3.2 Implement lazy recomputation in `Computed.value` getter: check `dirty` flag and `last_clean_epoch`, call `producer_update_value_version()` which triggers `consumer_poll_producers_for_change()` and conditionally re-evaluates, then return cached `_value`
- [x] 3.3 Implement equality check in `Computed.producer_recompute_value()`: after recomputation, compare `new_value == old_value` (using `==`); if equal, do not increment `version` (prevents downstream notification)
- [x] 3.4 Write tests for `Computed`: lazy evaluation (no recomputation when unread), recomputation on read after change, equality skip (result unchanged → no downstream propagation), diamond dependency (A→B, A→C, B→D, C→D — D computed only once per read)
- [x] 3.5 Write tests for dynamic dependency tracking: `Computed(lambda: a.value if flag.value else b.value)` switches producers when `flag` changes, stale producer `a` is removed from graph

## 4. Collections and AsyncCompat

- [x] 4.1 Update `ReactiveList` mutating methods (`append`, `extend`, `pop`, `insert`, `sort`, `remove`, `clear`, `reverse`, `__setitem__`) to always increment `version` and call `producer_notify_consumers()` (bypassing equality check for in-place mutations). Keep `_change_event` as the notification wrapper that handles `on_before_updating` / `on_after_updating` callbacks
- [x] 4.2 Update `ReactiveDict` mutating methods (`__setitem__`, `__delitem__`, `pop`, `clear`) similarly — always propagate for in-place mutations
- [x] 4.3 Update `ReactiveList.set_value()` and `ReactiveDict` (if applicable) to use equality check: `is or ==` comparison before propagating via `producer_notify_consumers()`
- [x] 4.4 Update `AsyncComputed` in `aio/_aio.py`: `_resolver` and `_error` methods use `_change_event` — update to use graph notification. `value`, `error`, `done` properties use `_get_event` — update to use `producer_accessed()`
- [x] 4.5 Update `AsyncResult` in `aio/_async_result.py`: its internal `Reactive` and `Computed` instances (`_state`, `_data`, `_error`, `is_pending`, `is_loading`, `is_success`, `is_error`) will be automatically affected by the graph rewrite. Verify that `_MISSING` sentinel pattern works correctly with the equality check (`is or ==` comparison must handle the sentinel object identity)
- [x] 4.6 Update `Location` in `router/_change_event_handler.py`: `set_mode`, `__set_path__` use `_change_event`; `value`, `state` use `_get_event` — update to graph-based equivalents
- [x] 4.6 Write/update tests for `ReactiveList` and `ReactiveDict`: callback contract (mutation methods always fire, set_value with same list/dict does not fire), `_last_mutation` metadata still works, `len()`, `__getitem__`, `__iter__` still track via `producer_accessed()`

## 5. Effect Primitive

- [x] 5.1 Implement `effect(fn, on_cleanup=None)` in `webcompy/reactive/_effect.py`: creates a `ReactiveNode` with `consumer_is_always_live=True`, runs `fn` inside `consumer_before_computation/after_computation` to track dependencies. Returns an `EffectHandle` with a `dispose()` method
- [x] 5.2 Implement `EffectScope` class with `create_effect_scope()` context manager that sets a scope context, collects all effects created within it, and provides `dispose()` to call `consumer_destroy()` on each. Handle nesting via a scope stack
- [x] 5.3 Implement effect scheduling: in browser context, use `browser.window.setTimeout(fn, 0)` for batched execution. In non-browser context (SSG), execute synchronously. Dirty effects are queued and deduplicated before execution
- [x] 5.4 Implement cleanup: `on_cleanup` callback registration, automatic invocation on re-execution and on scope disposal. Support returning cleanup function from effect body (Vue 3 pattern)
- [x] 5.5 Write tests for `effect()`: immediate execution, automatic dependency tracking, re-execution on dependency change, dynamic dependency changes, cleanup callback invocation on re-execution and scope disposal, batched execution in browser mock, synchronous execution in non-browser

## 6. Composable Pattern

- [x] 6.1 Create `webcompy/reactive/_composable.py` with documentation and conventions for `useXxx` functions. No new classes needed — composables are plain functions returning tuples of reactive primitives. Document the pattern: function creates `Reactive`/`Computed`/`effect` instances and returns them for consumer use
- [x] 6.2 Integrate `create_effect_scope()` with component lifecycle using the existing `_active_component_context` ContextVar from `webcompy/components/_hooks.py`. In `Component.__setup()`, the existing `_active_component_context.set(ctx)` / `reset(token)` pattern establishes the scope. Extend this to also set an effect scope that collects effects created during setup. On component destruction (via `on_before_destroy`), dispose the effect scope which calls `consumer_destroy()` on all collected effects. No changes to `ComponentAbstract` (deleted) or `_abstract.py` (deleted) — integration point is `_component.py` and `_hooks.py` only
- [x] 6.3 Write example composable `use_counter(initial=0)` returning `(count: Reactive[int], increment: Callable, decrement: Callable)` and a test demonstrating auto-cleanup on scope disposal

## 7. Cleanup and Deprecation

- [x] 7.1 Replace `ReactiveReceivable.__purge_reactive_members__()` no-op with actual `consumer_destroy()` calls on all tracked reactive members (note: `__purge_reactive_members__` is defined in `webcompy/reactive/_container.py` on `ReactiveReceivable`, not the deleted `_abstract.py`). Update `ElementAbstract._remove_element` and `DynamicElement._remove_element` (now has a custom override with `_position_element_nodes` for nested DynamicElement support — preserve this logic) to use `consumer_destroy()` on `_callback_nodes` instead of `ReactiveStore.remove_callback`
- [x] 7.2 Fix untracked subscription leaks: (a) `TypedRouterLink.__init__` (`self._to.on_after_updating(self._refresh)` without `_set_callback_id`) — register via `_set_callback_id`; (b) `AppDocumentRoot.__init__` (`Component._head_props.title.on_after_updating(updte_title)` — now in the refactored function-style component, same fix); (c) `useAsyncResult` in `_hooks.py` (`reactive.on_after_updating(result.refetch)` + `ReactiveStore.remove_callback(cid)` in `on_before_destroy` cleanup) — migrate to `consumer_destroy()` for cleanup
- [x] 7.3 Remove `ReactiveStore` singleton, `_callback_registry`, `_callback_id_counter`, `_make_singleton`, `DeprecationWarning` code, `remove_callback` module function, and `_find_callback_consumer_by_id`. Change `on_after_updating` / `on_before_updating` return type from `int` to `CallbackConsumerNode`. Rename `_callback_ids: set[int]` to `_callback_nodes: list[Any]` on element types. Migrate all test code from `ReactiveStore.remove_callback(callback_id)` to `consumer_destroy(callback_node)`
- [x] 7.4 Remove `_get_event` and `_change_event` decorators from public API surface. They become internal implementation details of `_graph.py`. Existing decorated methods (`Reactive.value.getter`, `Reactive.value.setter`, `ReactiveList.append`, etc.) continue to work but the decorators are renamed/internal

## 8. Integration Tests and Validation

- [x] 8.1 Run existing test suite (`tests/test_reactive.py`, `tests/test_list_mutation.py`, `tests/test_dict_mutation.py`, `tests/test_switch.py`, `tests/test_repeat.py`, `tests/test_keyed_repeat.py`, `tests/test_nested_dynamic.py`, `tests/test_elements.py`, `tests/test_hooks.py`, `tests/test_async_result.py`, `tests/test_components.py`) and fix any regressions caused by callback argument semantics change (on_after_updating now receives `_value` instead of method return value)
- [x] 8.2 Run linter (`uv run ruff check .`) and type checker (`uv run pyright`) on all modified files
- [ ] 8.3 Start dev server (`uv run python -m webcompy start --dev`) and manually verify: todo app, fizzbuzz app, hello world app — all reactive behavior works (state changes update UI, list mutations propagate, conditional rendering switches)
- [ ] 8.4 Run existing e2e tests (`tests/e2e/test_reactive.py`) with Playwright to verify browser-side behavior