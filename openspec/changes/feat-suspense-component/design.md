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
- Enable parallel data fetching across sibling `Suspense` boundaries
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

**Decision**: `Suspense` accepts an optional `timeout` parameter (default: 30 seconds). If children's async operations don't complete within the timeout, fallback content is rendered instead. This applies primarily to the server environment.

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

### D7: Parallel data fetching across sibling Suspense boundaries

**Decision**: When multiple `Suspense` elements are siblings in the element tree, their async operations are run concurrently via `asyncio.gather()`. Each Suspense boundary independently resolves and swaps content.

**Rationale**: This is the natural behavior of `asyncio.gather()` when each Suspense awaits its own async subtree. No special coordination is needed beyond the existing async rendering pipeline.

### D8: SuspenseElement class name and suspense() generator function

**Decision**: The class is named `SuspenseElement` (matching `SwitchElement`, `RepeatElement` pattern) and the public API is `suspense()` generator function (matching `switch()`, `repeat()` pattern). Users import `Suspense` from `webcompy.elements` as a convenience alias for the `suspense()` function return, or use `html.SUSPENSE(...)` if a tag-like API is preferred.

**Rationale**: Consistency with existing element API conventions.

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