# Proposal: Suspense Component

## Why

WebComPy currently provides `useAsyncResult` for managing async data fetching within components, but it uses a fire-and-forget pattern: `asyncio.ensure_future()` schedules the task in the browser and `loop.create_task()` on the server, but the server-side `_render()` returns before the async operation completes. This means SSR/SSG HTML never contains data from async fetches.

With the `feat/async-rendering-pipeline` change making the rendering pipeline async (async `_render()`, async component setup, async lifecycle hooks), the foundation exists for components to `await` async operations during setup. However, there is still no declarative way to show fallback content while async children are loading and swap to real content when they complete.

Developers need a `Suspense` component that:

1. **Shows fallback while children are loading** — Renders placeholder content (e.g., "Loading...") when children's async setup is in progress.
2. **Swaps to children when complete** — Automatically replaces fallback with actual content once all async operations in the children tree resolve.
3. **Waits for children in SSR/SSG** — On the server, awaits children completion (with a configurable timeout) so the final HTML includes the data.
4. **Enables parallel data fetching within a boundary** — A single `Suspense` boundary resolves its own async children concurrently via `asyncio.gather(*coroutines)`. Parallel fetching across **sibling** `Suspense` boundaries is **not** provided by this change: sibling boundaries remain sequential per the foundational `async-rendering` spec, and sibling-level `gather` is deferred to the same future work that lifts the foundation's sibling-render parallelism restriction (see design D7).

## What Changes

- **NEW** `Suspense` element class in `webcompy/elements/types/_suspense.py` — A `DynamicElement` that controls when children generators are evaluated, showing fallback during async loading and children after completion.
- **NEW** `suspense()` generator function in `webcompy/elements/generators.py` — Factory function accepting `fallback`, `children`, `error_fallback`, and `timeout` parameters.
- **MODIFIED** `webcompy/elements/__init__.py` — Export `Suspense`.
- **MODIFIED** `webcompy/components/_component.py` — Integration with async setup detection so `Suspense` knows when its children subtree has pending async operations.

## Capabilities

### New Capabilities

- `suspense`: Declarative component for showing fallback content while async children are loading, swapping to real content when complete. In SSR/SSG, awaits children completion (with timeout) so data is included in output. Supports `error_fallback` for error states and configurable `timeout`.

### Modified Capabilities

- `elements`: The element system gains a `Suspense` dynamic element that orchestrates async child rendering with fallback/error states.

## Known Issues Addressed

- **SSR/SSG never contains async data** — Currently `_render()` returns before async operations complete, so SSG HTML lacks fetched data. `Suspense` awaits children in the server environment so data can be included in the final HTML.

## Non-goals

- Data fetching primitives (use `useAsyncResult` or direct `HttpClient` calls inside components).
- Nested `Suspense` boundaries with independent loading states (supported by design but not a primary focus).
- **Parallel fetching across sibling `Suspense` boundaries** — Sibling `Suspense` elements render sequentially per the foundational `async-rendering` spec. Sibling-level `asyncio.gather` is deferred to the same future work that lifts the foundation's sequential sibling rendering restriction (prerequisites: DOM ordering guarantees, atomic cleanup, ContextVar isolation — see foundation `async-rendering` spec "Future Work → Parallel Sibling Rendering"). This change delivers concurrency only **within** a single boundary (its own async children via `gather`).
- Streaming SSR (rendering partial HTML as sections resolve).
- Changing `useAsyncResult` behavior (it remains fire-and-forget; `Suspense` is complementary).
- Caching or deduplication of async operations (separate concern).
- Client-side transition animations between fallback and children.
- A built-in root-level error boundary. Uncaught async setup exceptions (no enclosing `Suspense`) are logged via the root render's `resolve_async` `on_error` hook; making them user-visible without an explicit `Suspense` boundary is out of scope here.

## Dependency

- **Requires** `feat/async-rendering-pipeline` — async `_render()` and async component setup are prerequisites for `Suspense` to await async operations.
- **Requires** `feat/async-component-setup` — `_pending_async_template` tree traversal is used for async detection.
- **Requires** `feat/hydration-data-transfer` — Suspense hydration checks the transfer payload to determine whether children async data was resolved during SSR. The Suspense-specific hydration logic is owned by Suspense (per `feat-suspense-component` tasks); the `feat-hydration-data-transfer` change provides the `HYDRATION_DATA_KEY` DI key and `has_resolved_data()` helper that Suspense uses.

## Impact

- **Affected modules**: `webcompy/elements/types/` (new `_suspense.py`), `webcompy/elements/generators.py` (new `suspense()` function), `webcompy/elements/__init__.py` (export), `webcompy/components/_component.py` (async setup detection integration)
- **Breaking**: None — `Suspense` is a new addition, not a modification of existing APIs.
- **Testing**: Unit tests for `Suspense` rendering in both environments, E2E tests for async data loading with fallback display.