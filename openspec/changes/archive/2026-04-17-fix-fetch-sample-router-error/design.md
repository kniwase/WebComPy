## Context

The Fetch Sample page in the demo app uses `AsyncWrapper`-wrapped functions and `resolve_async` in its `on_after_rendering` lifecycle hook to fetch data from the server. When navigating to this page via a `RouterLink` click, the following chain executes synchronously:

1. `RouterLink._on_click` → `history.pushState()` + `Router.__set_path__()` 
2. `Location.__set_path__` has `@_change_event`, which calls `ReactiveStore.callback_after_updating()`
3. This triggers `Router.__cases__` recomputation (a `computed_property` depending on `Location._value`)
4. The computed cases change triggers `SwitchElement._refresh()` 
5. `_refresh()` destroys old children, creates new children, and calls `child._render()` for each
6. `Component._render()` calls `on_before_rendering()`, then `super()._render()` (mounts DOM nodes), then `on_after_rendering()`
7. `on_after_rendering` fires `AsyncWrapper.__call__` → `resolve_async()` → `aio_run()` (`asyncio.get_event_loop().run_until_complete()`)

The problem is that step 7 runs **synchronously within the reactive callback chain** initiated in step 2. In Emscripten/PyScript, `run_until_complete` within an already-running event loop context can cause errors or unexpected behavior. Additionally, if there's an error during the DOM manipulation phase (steps 5-6) — for example, a `DynamicElement._get_node()` being called on a parent whose node isn't yet ready — it will throw during the navigation path but not during direct URL access.

On direct URL access, the component renders during initial hydration (not inside a reactive callback chain), so the event loop isn't nested and lifecycle hooks fire in a clean context.

## Goals / Non-Goals

**Goals:**
- Ensure that `on_after_rendering` lifecycle hooks that initiate async operations work correctly when triggered by route navigation (SwitchElement refreshing due to reactive change)
- Fix the root cause so that any component's `on_after_rendering` doesn't fail regardless of whether it's called during initial hydration or reactive navigation

**Non-Goals:**
- Adding virtual DOM diffing or key-based reconciliation
- Changing the async execution model (replacing `run_until_complete`)
- Adding route guards, lazy-loading, or navigation lifecycle hooks
- Fixing `AsyncComputed._done`/`None` ambiguity

## Decisions

### Decision 1: Defer `on_after_rendering` in `SwitchElement._refresh` to after the reactive update completes

**Rationale**: The core issue is that `on_after_rendering` fires synchronously inside `ReactiveStore.callback_after_updating()`. When `SwitchElement._refresh()` is invoked as a reactive callback, any side effects in `on_after_rendering` (especially async operations) run in a context where the reactive system hasn't finished propagating changes.

**Approach**: Instead of calling `Component._render()` (which fires `on_after_rendering`) directly within `_refresh()`, we schedule the `on_after_rendering` callbacks to run after the current reactive update finishes. We can do this by:

1. Collecting `on_after_rendering` callbacks during `_refresh()` instead of executing them immediately
2. After all reactive propagation has settled (using `browser.window.setTimeout(fn, 0)` or equivalent in Emscripten), execute the collected callbacks

However, a simpler and more targeted approach is: **Move `on_after_rendering` to fire after a microtask/timeout in the browser environment, specifically when called from within a reactive callback chain.**

**Alternative considered**: Add a batching mechanism to `ReactiveStore` that queues `on_after_updating` callbacks. This would be more invasive and affect the entire reactive system.

**Chosen approach**: The simplest fix is to make `SwitchElement._refresh()` defer `on_after_rendering` calls. When `_refresh()` is triggered by a reactive callback (which it always is during navigation), it should schedule `on_after_rendering` hooks via `browser.window.setTimeout(callback, 0)` so they run after the event loop clears the current microtask queue. This ensures the DOM is fully updated and the reactive system has finished propagating before any side effects run.

Specifically, modify `SwitchElement._refresh()` to:
1. Still render children synchronously (DOM mounting must happen immediately)
2. Collect `on_after_rendering` callbacks from newly created `Component` instances
3. If in browser environment, schedule all collected `on_after_rendering` callbacks via `setTimeout(..., 0)`
4. If not in browser (SSG), call them synchronously as before

This also means modifying `Component._render()` or providing a way to separate DOM rendering from lifecycle hook execution.

### Decision 2: Separate `Component._render()` into render and lifecycle phases

**Rationale**: Currently `Component._render()` does:
```python
def _render(self):
    self._property["on_before_rendering"]()
    super()._render()  # mounts DOM nodes + renders children
    self._property["on_after_rendering"]()  # side effects
```

We need to be able to render the DOM without immediately firing `on_after_rendering`, so that `SwitchElement._refresh()` can defer it.

**Approach**: Add a `_render_without_lifecycle()` method or a parameter to `_render()` that skips `on_after_rendering`. Then `_refresh()` can:
1. Call `child._render()` which mounts DOM nodes but collects (doesn't fire) `on_after_rendering`
2. Schedule the collected callbacks via `setTimeout`

**Chosen approach**: Add a `_defer_after_rendering` flag to `Component`. When this flag is set, `_render()` records the `on_after_rendering` callback instead of executing it immediately. The `SwitchElement._refresh()` method sets this flag on new Component children, renders them, then schedules all deferred callbacks via `setTimeout`.

Actually, even simpler: we can just have `SwitchElement._refresh()` schedule the `on_after_rendering` call via `setTimeout` directly when in the browser environment. We don't need to change `Component._render()` at all — we just need to move the `on_after_rendering` call out of the synchronous reactive chain.

The cleanest implementation:
1. In `Component._render()`, separate the after-rendering hook
2. In `SwitchElement._refresh()`, after rendering new children, collect `on_after_rendering` callbacks and schedule them

### Decision 3: Also handle `RepeatElement` consistently

**Rationale**: `RepeatElement` also regenerates children when its reactive list changes. If a similar issue occurs with `RepeatElement`, we should apply the same fix. However, `RepeatElement` is less commonly used with async operations in its child components' lifecycle hooks during reactive updates.

**Chosen approach**: For now, only fix `SwitchElement._refresh()` since that's the one triggered by route navigation. The same pattern can be applied to `RepeatElement` in a future change if needed.

## Risks / Trade-offs

- **[setTimeout timing]** → `setTimeout(fn, 0)` runs on the next macrotask, which means `on_after_rendering` fires slightly later than before. This could affect components that expect `on_after_rendering` to run synchronously after rendering. Mitigation: this is a minor timing difference and is actually more correct behavior — lifecycle hooks shouldn't assume they're in the synchronous reactive chain.

- **[Server-side rendering]** → SSG calls `_render()` in non-browser context where `setTimeout` isn't available. The fix only applies the deferral in the browser environment, so SSG behavior remains unchanged.

- **[Global state in ReactiveStore]** → We could add batching to `ReactiveStore` itself, but this would be a larger change with broader impact. The targeted approach in `SwitchElement._refresh()` is safer and more contained.