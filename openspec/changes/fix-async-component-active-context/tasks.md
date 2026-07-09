## 1. ComponentRenderState and component_context()

- [x] 1.1 Create `packages/webcompy/src/webcompy/components/_context_manager.py` with `ComponentRenderState` dataclass (`context: Context[Any]`, `effect_scope: EffectScope`)
- [x] 1.2 Implement `component_context(state: ComponentRenderState)` context manager that activates `_active_component_context` and `_active_effect_scope` on entry and resets on exit (including exceptions)
- [x] 1.3 Export `ComponentRenderState` and `component_context` from `packages/webcompy/src/webcompy/components/__init__.py`
- [x] 1.4 Write unit tests for `component_context()` — activation, reset, exception safety, nested activation

## 2. Component.__setup() changes

- [x] 2.1 In `Component.__setup()`, create a `ComponentRenderState` from the `Context` and `EffectScope` and store it on `self._render_state` for all components (sync and async)
- [x] 2.2 Wrap the sync `component_def(context)` call in `with component_context(state):` so the body executes within the context manager (replaces the manual `set`/`reset` token pattern)
- [x] 2.3 Verify that hook extraction, `_async_results` copy, and `_transferable_signals` merge still work correctly for sync components after the refactor

## 3. Component._render() re-activation for async components

- [x] 3.1 In `Component._render()`, when `self._pending_async_template is not None` and not under Suspense (`SUSPENSE_RESOLVING_KEY` is falsy), wrap the `await self._pending_async_template` call in `with component_context(self._render_state):`
- [x] 3.2 After the async body resolves (coroutine awaited), re-extract lifecycle hooks from `self._render_state.context.__get_lifecyclehooks__()` and update `self._property["on_before_rendering"]` and `self._property["on_after_rendering"]`
- [x] 3.3 After the async body resolves, re-copy `self._render_state.context._async_results` into `self._async_results`
- [x] 3.4 After the async body resolves, re-merge `self._render_state.context._transferable_signals` into `self.__signal_members__`
- [x] 3.5 For the Suspense path (`SUSPENSE_RESOLVING_KEY` is truthy, coroutine already resolved), perform the same re-extraction of hooks/async_results/transferable_signals from `self._render_state.context`

## 4. SuspenseElement context wrapping

- [x] 4.1 In `SuspenseElement._render()`, wrap each collected `_pending_async_template` coroutine in an async helper that activates `component_context(component._render_state)` before awaiting
- [x] 4.2 Ensure `asyncio.gather()` resolves the wrapped coroutines so each body executes with its own context active
- [x] 4.3 Verify that after `asyncio.gather()` completes, the resolved components have their hooks/signals registered in their respective Contexts (ready for re-extraction by `Component._render()`)

## 5. Tests

- [x] 5.1 Write a test verifying `_active_component_context` is non-None during async setup body execution (use a composable that reads it)
- [x] 5.2 Write a test verifying lifecycle hooks registered in async setup body are correctly invoked during `_render()`
- [x] 5.3 Write a test verifying `_async_results` registered in async setup body are collected by `collect_transfer_data()`
- [x] 5.4 Write a test verifying async component under Suspense has context active during body execution
- [x] 5.5 Write a test verifying parallel Suspense resolution does not cross-contaminate component contexts
- [x] 5.6 Write a test verifying effects created by composables (e.g. `use_state()`) inside async body are tracked by the component's EffectScope and cleaned up on destroy
- [x] 5.7 Write a test verifying sync component behavior is unchanged (no regression)
- [x] 5.8 Run existing E2E tests for async components and Suspense to verify no regressions

## 6. Review follow-up

- [x] 6.1 Fix Suspense server path: call `Component._refresh_async_setup_results()` in `SuspenseElement._resolve_component_templates()` after each template resolves
- [x] 6.2 Introduce `_async_setup_extracted` flag on `Component` to make re-extraction robust across server/browser Suspense paths without relying solely on `SUSPENSE_RESOLVING_KEY`
- [x] 6.3 Add tests verifying Suspense async body hooks (`on_before_rendering`, `on_after_rendering`, `on_before_destroy`) fire correctly
- [x] 6.4 Add test verifying Suspense async body `useAsyncResult` is collected in `child._async_results` and included in `collect_transfer_data()` payload
- [x] 6.5 Update `proposal.md` and `design.md` to use `_active_scope` instead of the removed `_active_effect_scope`
- [x] 6.6 Update `design.md` and spec delta to document `ComponentRenderState.framework_cleanup` and the `_async_setup_extracted` re-extraction strategy

## 7. Lint, Type Check, and Validation

- [x] 7.1 Run `uv run ruff check .` and `uv run ruff format .`
- [x] 7.2 Run `uv run pyright`
- [x] 7.3 Run `uv run python -m pytest tests/ --tb=short`
- [x] 7.4 Run `openspec validate fix-async-component-active-context`
