## Context

With the async rendering pipeline (`feat/async-rendering-pipeline`), the rendering pipeline is fully async: `ElementAbstract._render()`, `Component._render()`, and component setup functions can all be `async`. This enables components to `await` async operations during setup (e.g., fetching data from an API before rendering).

However, developers still need a way to:
- Show loading UI while async children are resolving
- Automatically swap to real content when async operations complete
- In SSR/SSG, wait for async data so it's included in the HTML output

`Suspense` fills this gap by providing a declarative boundary between loading and resolved states.

## Goals / Non-Goals

**Goals:**
- Provide a `Suspense` dynamic element that shows fallback while children are loading
- Swap fallback for children when async operations in the children subtree complete
- In SSR/SSG, await children completion (with configurable timeout) so data appears in output
- Support `error_fallback` for error states from async children
- Enable parallel data fetching **within** a single `Suspense` boundary (its own async children resolve concurrently via `asyncio.gather`). Parallel fetching across **sibling** `Suspense` boundaries is out of scope here (see D7); it is deferred alongside the foundation's deferred sibling parallel rendering.
- Maintain full backward compatibility with existing sync components

**Non-Goals:**
- Streaming SSR (rendering partial HTML progressively)
- Caching or deduplication of async operations
- Client-side transition animations
- Changing `useAsyncResult` behavior
- Nested Suspense with independent loading granularities beyond the natural component tree

## Decisions

### D1: Suspense as a DynamicElement

**Decision**: `Suspense` extends `DynamicElement`, similar to `SwitchElement` and `RepeatElement`.

**Alternatives considered**:
- A `Component` wrapping children: Would require special rendering hooks and doesn't fit the element model well.
- A standalone class outside the element hierarchy: Would duplicate rendering logic.

**Rationale**: `DynamicElement` already represents elements that control their children's rendering lifecycle. `Suspense` needs to decide *when* to render children (after async resolution), which is exactly the `DynamicElement` pattern.

### D2: Children as a lazy generator function

**Decision**: The `children` parameter accepts a `Callable[[], ChildNode]` (zero-argument function) that is only called when the Suspense is ready to render children. The `fallback` parameter also accepts a `Callable[[], ChildNode]` for consistency.

**Alternatives considered**:
- Eager children (rendered immediately, hidden via CSS): Wastes resources on async operations that may fail.
- Children as a plain `ChildNode`: Would be evaluated at Suspense construction time, defeating lazy evaluation.

**Rationale**: A lazy generator allows `Suspense` to defer child evaluation until async setup is ready. This mirrors the `switch()` API where generators are called conditionally.

### D3: Async detection via component tree traversal

**Decision**: `Suspense` detects whether its children subtree has pending async operations by checking a per-component "async pending" flag set during `Component.__setup()`. When a component's setup function is `async`, it sets a flag that `Suspense` can observe.

**Alternatives considered**:
- Using `asyncio` task tracking: Too low-level and fragile.
- Requiring explicit opt-in via `useAsyncResult` integration: Too restrictive; any async operation should be awaited.

**Rationale**: Since `Component.__setup()` already detects `async def` setup functions (via `inspect.iscoroutinefunction()`), we can propagate a "has pending async" flag through the component tree. `Suspense` checks this flag after rendering children to decide whether to show fallback or resolved content.

### D4: Server waits, browser shows fallback then swaps

**Decision**: In the server/SSG environment, `Suspense._render()` awaits the children's async operations (with a configurable timeout) before including them in the output. In the browser, `Suspense._render()` first renders fallback content, then schedules async child resolution and swaps content when ready.

**Alternatives considered**:
- Always show fallback (no waiting): SSR/SSG HTML would never include async data, defeating the purpose.
- Always wait (no fallback in browser): Would show a blank/loading page until all data resolves, no progressive loading.

**Rationale**: Server environments can afford to wait for data (they're generating static files). Browser environments should show immediate feedback (fallback) and progressively enhance.

### D5: Timeout with fallback on expiry

**Decision**: `Suspense` accepts an optional `timeout` parameter (default: 10 seconds).

**Alternatives considered**:
- No timeout (wait forever): Could hang SSG builds indefinitely.
- Hard fail on timeout: Too aggressive; fallback is more graceful.

**Rationale**: SSG builds need a bounded execution time. Timeout + fallback ensures builds always complete.

### D6: Error fallback for async failures

**Decision**: `Suspense` accepts an optional `error_fallback` parameter (also a `Callable[[], ChildNode]`). If children's async setup raises an exception, the error fallback is rendered instead.

**Alternatives considered**:
- Propagate the error: Would crash the entire app for a single failed section.
- Render nothing: Gives no user feedback about the failure.
- Only logging: Invisible to the user.

**Rationale**: Declarative error handling is consistent with the fallback pattern and gives developers control over error UI.

### D7: Sibling Suspense boundaries — scope of "parallel" data fetching

**Decision**: When multiple `Suspense` elements are siblings in the element tree, the **foundation's sequential sibling rendering** (`for child in children: await child._render()`, per the `async-rendering` spec "Sibling children shall render sequentially" requirement) is preserved. Sibling `Suspense` boundaries are therefore rendered one-by-one via `await`, NOT concurrently via a sibling-level `asyncio.gather()`. What "parallel data fetching" means here is only the **within-boundary** concurrency: a single `SuspenseElement._render()` resolves all async setups in its own subtree concurrently via `asyncio.gather(*coroutines)` (see task 3.3).

Concurrent fetching across **sibling** Suspense boundaries is **deferred to future work**, mirroring the foundation's deferred sibling parallel rendering. The `async-rendering` spec's "Future Work → Parallel Sibling Rendering" section enumerates the same prerequisites (DOM ordering guarantees, atomic cleanup, ContextVar isolation, behavioral compatibility, dedicated tests); adopting sibling-level `gather` for Suspense would inherit those same prerequisites.

**Alternatives considered**:
- **Make `SuspenseElement` intercept and gather the parent's sibling loop**: This requires Suspense to reach outside its own `_render()` into the enclosing `ElementWithChildren._render()` loop, or to register sibling-related coordination state on the parent. It conflicts with the foundation's explicit short-circuit sequential semantics and risks re-introducing the very ContextVar isolation / atomic cleanup problems that made the foundation defer sibling gathering. Rejected for this change.
- **Use fire-and-forget render tasks for each sibling**: Loses serial ordering and short-circuit semantics, and makes error capture (D9) much harder because failures are decoupled from the `await` chain. Rejected.

**Rationale**: Keeping sibling Suspense boundaries sequential is consistent with the foundation, while still delivering genuine concurrency within each boundary (multiple async children of the same Suspense resolve together via `asyncio.gather`). This matches the use case — "show fallback for this section until this section's async children resolve" — without re-litigating the sibling parallelism decision at a higher layer.

### D8: SuspenseElement class name and suspense() generator function

**Decision**: The class is named `SuspenseElement` (matching `SwitchElement`, `RepeatElement` pattern) and the public API is `suspense()` generator function (matching `switch()`, `repeat()` pattern). Users import `Suspense` from `webcompy.elements` as a convenience alias for the `suspense()` function return, or use `html.SUSPENSE(...)` if a tag-like API is preferred.

**Rationale**: Consistency with existing element API conventions.

### D9: Exception capture scope — Suspense is the only catching boundary

**Decision**: `SuspenseElement` is the single element class in the async pipeline that may catch exceptions from its children's async setup and translate them into rendered content. Concretely:

1. **`SuspenseElement._render()`** wraps the `await asyncio.gather(*coroutines)` call (its own async-subtree resolution, task 3.3) in a `try/except`:
   - On `Exception` (and `asyncio.TimeoutError` separately for the timeout path): if `error_fallback` is provided, render `error_fallback` via `_patch_children()` (replacing the fallback) and clear pending async state; if not provided, re-raise so the exception propagates per the foundation's sequential short-circuit semantics.
2. **No `try/except` in the foundation's `ElementWithChildren._render()` / `DynamicElement._refresh()` loops**: A failed `await child._render()` propagates immediately and subsequent siblings are NOT rendered, exactly as the `async-rendering` spec scenario "One child raises during sibling rendering" states. Adding a general try/except there would conflict with sequential short-circuit semantics and would steal the exception from its enclosing suspense boundary.
3. **Propagation path**: When a child async setup raises and no enclosing `SuspenseElement` exists, the exception propagates up to the root render. The root render is scheduled via `resolve_async(...)` whose default `on_error=_log_error` hook logs the exception (it is NOT swallowed silently). This means async setup errors outside any `<Suspense>` boundary surface as logged errors rather than user-visible fallback UI; documenting this is part of this change.

**Why not catch earlier (Component._render)**: Wrapping `await self._pending_async_template` inside `Component._render()` would prevent `SuspenseElement` from distinguishing "async setup failed" from "some downstream render raised", and would also keep the failed component's element partially mounted. Letting the exception propagate to the nearest suspense boundary is simpler and matches the developer's mental model: "this section failed to load, show error fallback here".

**Rationale**: Suspense is the explicit async boundary the developer placed; only there does the framework have license to substitute content for a failure. Keeping the foundation's loops free of try/except preserves the short-circuit contract; catching at Suspense preserves developer control and auditability (uncaught errors still log via the root `on_error` hook).

**Compatibility with `async-component-setup` Decision 7**: That decision states the exception propagates via the `await` chain and the closest enclosing `SuspenseElement` catches it. D9 specifies exactly how.

## API Design

```python
from webcompy.elements import Suspense

@define_component
async def DataPage(context):
    return html.DIV(
        {},
        html.H1({}, "Dashboard"),
        Suspense(
            fallback=html.P({}, "Loading data..."),
            children=lambda: DataDisplay(),
        ),
    )

# With error fallback and timeout
Suspense(
    fallback=html.P({}, "Loading data..."),
    error_fallback=lambda: html.P({}, "Failed to load data"),
    children=lambda: DataDisplay(),
    timeout=10.0,  # seconds, server-only
)
```

## Rendering Flow

### Browser Environment

1. `SuspenseElement._render()` is called
2. Children generator is invoked to trigger async component setup
3. If children have pending async operations, fallback is rendered immediately
4. When async operations complete, `SuspenseElement._resolve()` is called
5. Fallback children are replaced with actual children using `_patch_children()`

### Server Environment (SSR/SSG)

1. `SuspenseElement._render()` is called
2. Children generator is invoked, triggering async component setup
3. `SuspenseElement._render()` awaits the async operations (with timeout)
4. If operations complete within timeout, children are rendered directly (no fallback in output)
5. If timeout expires, fallback is rendered instead
6. If an error occurs and `error_fallback` is provided, error fallback is rendered

## File Changes

### New Files

- `webcompy/elements/types/_suspense.py` — `SuspenseElement` class extending `DynamicElement`

### Modified Files

- `webcompy/elements/generators.py` — Add `suspense()` generator function
- `webcompy/elements/__init__.py` — Export `Suspense`
- `webcompy/components/_component.py` — Add async setup tracking integration