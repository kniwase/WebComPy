## Context

The async component setup feature (`async def` with `@define_component`) uses a two-phase initialization:

1. **Phase 1 (`__setup()`)**: The setup function `component_def(context)` is called. For async definitions, this creates a coroutine object but does NOT execute the body. `_active_component_context` and `_active_effect_scope` are set and immediately reset within `__setup()`.

2. **Phase 2 (`_render()`)**: The stored coroutine is awaited, executing the async body. At this point, `_active_component_context` and `_active_effect_scope` have already been reset to `None`.

The coroutine must be created in `__setup()` (not deferred to `_render()`) because `SuspenseElement` traverses the element tree to detect `_pending_async_template` before rendering begins. Deferring creation would break Suspense's ability to detect and batch-resolve async components.

### Current bugs

- **Composables broken in async setup**: Any composable using `_active_component_context.get()` (e.g., `use_async_result`) returns `None` during async body execution, silently degrading to non-component behavior.
- **Lifecycle hooks lost**: `__setup()` extracts hooks via `context.__get_lifecyclehooks__()` before the async body runs. Hooks registered inside the body (`context.on_before_rendering(fn)`) are silently ignored.
- **Async results lost**: `__setup()` copies `context._async_results` before the body runs, capturing an empty list.

## Goals / Non-Goals

**Goals:**
- Make `_active_component_context` and `_active_effect_scope` available during async setup body execution
- Ensure lifecycle hooks registered in async setup bodies are correctly extracted and invoked
- Ensure `_async_results` and `_transferable_signals` are correctly collected after async body resolution
- Centralize ContextVar activation in a single context manager to prevent future fragility
- Preserve the Suspense detection mechanism (`_pending_async_template` observability window)

**Non-Goals:**
- Adding the `use_state()` composable (separate change)
- Changing how Suspense detects pending async components
- Replacing `ContextVar` with a custom context system
- Deferring coroutine creation to `_render()` (incompatible with Suspense)

## Decisions

### Decision 1: Re-activate context in `_render()` via context manager

**Choice**: Save `ComponentRenderState` (Context + EffectScope) in `__setup()`, then re-activate via `component_context()` context manager in `_render()` before awaiting the coroutine.

**Alternatives considered**:

- **Defer coroutine creation to `_render()`**: Would eliminate save/restore entirely. Rejected because Suspense must detect `_pending_async_template` before rendering — the coroutine must exist during `__init__()`.
- **Replace `ContextVar` with custom dict/thread-local**: Rejected because `ContextVar` is the only standard library mechanism that is async-safe. Dict-based approaches fail under task switching; thread-local fails under single-threaded async.
- **Manual set/reset in `_render()`**: Works but fragile — 5 manual steps, any omission breaks. The context manager centralizes this into a single `with` block.

**Rationale**: The context manager approach keeps `ContextVar` (async-safe, standard) while eliminating manual save/restore. New ContextVars added in the future only require updating `component_context()`.

### Decision 2: `ComponentRenderState` bundles Context and EffectScope

**Choice**: A dataclass holds both the `Context` and `EffectScope` objects, stored on `self._render_state` during `__setup()`.

**Rationale**: These two objects must always be activated together. Bundling them prevents partial activation (e.g., activating context but forgetting scope). The `component_context()` manager takes a `ComponentRenderState` and activates both.

### Decision 3: Re-extract hooks/signals after async body resolution

**Choice**: After the coroutine body resolves (in both self-resolution and Suspense-resolution paths), re-extract lifecycle hooks, `_async_results`, and `_transferable_signals` from the saved Context.

**Implementation**: The re-extraction logic is idempotent — for sync components (where hooks were already extracted in `__setup()`), re-extraction yields the same result. For async components, re-extraction captures hooks/results registered during body execution.

**Suspense path**: When `SuspenseElement._render()` resolves coroutines, it must wrap each coroutine with `component_context()` so the body executes with context active. After `asyncio.gather()` completes, `Component._render()` re-extracts hooks from the Context.

### Decision 4: Suspense wraps coroutines with per-component context

**Choice**: In `SuspenseElement._render()`, each collected coroutine is wrapped in an async helper that activates `component_context()` before awaiting:

```python
async def _resolve_with_context(component):
    with component_context(component._render_state):
        return await component._pending_async_template
```

Then `asyncio.gather(*[_resolve_with_context(c) for c in components])` resolves them in parallel. Each task inherits a copy of the current context, and the `with` block modifies only that task's copy.

**Rationale**: `asyncio.gather()` creates separate tasks that share the same context. Without wrapping, all coroutines would see the same (unmodified) context. The wrapper ensures each task activates its own component's context.

## Risks / Trade-offs

- **[Double extraction overhead]** Re-extracting hooks/signals adds a small overhead per async component render. → Mitigation: extraction is idempotent and cheap (dict lookups). Only async components incur the cost.

- **[Suspense coupling]** The fix requires Suspense to be aware of `component_context()`. → Mitigation: This is a minimal coupling — Suspense already accesses `_pending_async_template` on components. The wrapper is a thin adapter.

- **[State lifecycle]** `ComponentRenderState` holds references to Context and EffectScope, extending their lifetime until `_render()` completes. → Mitigation: These objects already live this long (they're used during rendering). No new lifetime extension.

- **[Re-extraction timing for Suspense path]** In the Suspense path, `Component._render()` must detect that the body has already resolved (by checking `_pending_async_template is None`) and perform re-extraction. → Mitigation: A `_hooks_needs_refresh` flag or checking `self._render_state is not None and self._property["template"] is None` before `__init_component` runs.

## Open Questions

- Should `_active_di_scope` also be part of `ComponentRenderState`? Currently it's managed separately by `AppDocumentRoot._render()` and is already active during `_render()`. Including it in `ComponentRenderState` might cause confusion about ownership. **Tentative answer: No** — DI scope is managed at the render-context level, not the component level.
