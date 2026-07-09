## Why

Async component setup functions (`async def` with `@define_component`) execute their body during `_render()`, not during `__setup()`. However, `_active_component_context` and `_active_scope` are set and immediately reset in `__setup()` — before the async body ever runs. This causes two bugs:

1. **Composables are broken in async setup**: `_active_component_context.get()` returns `None` during async body execution, so composables (`use_async_result`, future `use_state()`) cannot access the component context and silently degrade.
2. **Lifecycle hooks are silently lost**: hooks registered inside async setup bodies (`context.on_before_rendering(fn)`) are extracted in `__setup__()` before the body executes, resulting in empty hook registrations.

This fix is a prerequisite for the upcoming `use_state()` composable, which relies on `_active_component_context` during setup.

## What Changes

- Introduce a `component_context()` context manager (backed by `ContextVar`) that activates `_active_component_context` and `_active_scope` in a single `with` block with guaranteed cleanup via `finally`
- Introduce `ComponentRenderState` dataclass bundling `Context` and `EffectScope` for deferred re-activation
- In `Component.__setup()`: save the `ComponentRenderState` on `self` for async components (in addition to the existing set/reset cycle needed for Suspense coroutine observability)
- In `Component._render()`: re-activate context and effect scope via `component_context()` before awaiting `_pending_async_template`
- After the async body resolves (both self-resolution and Suspense-resolution paths): re-extract lifecycle hooks, `_async_results`, and `_transferable_signals` from the Context, updating `self._property` accordingly
- In `SuspenseElement._render()`: wrap each collected coroutine with `component_context()` so each async component body executes with its own context active during `asyncio.gather()` parallel resolution

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `async-component-setup`: Context and effect scope SHALL be re-activated during `_render()` for async components; lifecycle hooks, async results, and transferable signals SHALL be re-extracted from the Context after the async body resolves; Suspense SHALL wrap collected coroutines with per-component context activation

## Impact

- `packages/webcompy/src/webcompy/components/_component.py` — `__setup()` saves render state; `_render()` re-activates context and re-extracts hooks/signals after async body resolution
- `packages/webcompy/src/webcompy/components/_context_manager.py` (new) — `ComponentRenderState` dataclass and `component_context()` context manager
- `packages/webcompy/src/webcompy/elements/types/_suspense.py` — wrap coroutine resolution with `component_context()` per component
- All composables using `_active_component_context` will work correctly inside async setup bodies

## Known Issues Addressed

N/A — this fixes a newly discovered bug in async component setup. Async component setup functions silently lose lifecycle hooks and composable context access because `_active_component_context` and `_active_scope` are reset before the coroutine body executes.

## Non-goals

- Adding the `use_state()` composable (separate change: `feat-signal-composable`)
- Changing the Suspense detection mechanism (`_pending_async_template` observability window is preserved)
- Replacing `ContextVar` with a custom context management system
- Supporting module-level signal transfer
- Deprecating `ReactiveList` / `ReactiveDict`
