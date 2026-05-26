# Suspense

## Purpose

Web applications frequently need to load data asynchronously before displaying content. Without a declarative boundary, developers must manually manage loading states, error states, and data resolution — often with verbose `useAsyncResult` + `switch()` patterns repeated across components.

Suspense provides a declarative way to show fallback content while async children are loading and automatically swap to real content when async operations complete. In SSR/SSG, Suspense awaits children completion so that data is included in the final HTML output, solving the problem of static sites that lack async data.

Suspense is complementary to `useAsyncResult`: `useAsyncResult` gives fine-grained control over loading/error/success states within a component, while `Suspense` gives declarative control at the element tree level, wrapping entire sections.

## ADDED Requirements

### Requirement: Suspense shall show fallback content while children are loading
`Suspense` SHALL accept a `fallback` parameter (a `Callable[[], ChildNode]` generator) and a `children` parameter (a `Callable[[], ChildNode]` generator). When the children subtree has pending async operations, the fallback content SHALL be rendered in place of the children.

#### Scenario: Showing fallback during async loading
- **WHEN** a developer wraps an async component in `Suspense(fallback=lambda: html.P({}, "Loading..."), children=lambda: AsyncDataComponent())`
- **AND** the async component's setup is still in progress
- **THEN** the fallback content `<p>Loading...</p>` SHALL be rendered

#### Scenario: Swapping to children when async completes
- **WHEN** the async component's setup completes successfully
- **THEN** the fallback content SHALL be removed
- **AND** the actual children content SHALL be rendered in its place

### Requirement: Suspense shall render children directly when no async operations are pending
If the children subtree does not contain any async component setups, `Suspense` SHALL skip the fallback phase and render children content directly. This ensures that `Suspense` has zero overhead for synchronous content.

#### Scenario: Wrapping a sync component in Suspense
- **WHEN** a developer wraps a synchronous component in `Suspense(fallback=lambda: html.P({}, "Loading..."), children=lambda: SyncComponent())`
- **THEN** the children SHALL be rendered immediately without showing fallback
- **AND** no flash of fallback content SHALL occur

### Requirement: Suspense shall await children in SSR/SSG environment
In the server environment (during static site generation or server-side rendering), `Suspense._render()` SHALL await the completion of async operations in the children subtree before rendering. If the async operations complete within the timeout, the final HTML SHALL include the children content (no fallback). If the timeout is exceeded, fallback content SHALL be rendered instead.

#### Scenario: SSR with async data that resolves within timeout
- **WHEN** `Suspense` is rendered during SSG with `timeout=10` (default)
- **AND** the children's async operations complete within 10 seconds
- **THEN** the generated HTML SHALL contain the children content
- **AND** no fallback content SHALL appear in the HTML

#### Scenario: SSR with async data that exceeds timeout
- **WHEN** `Suspense` is rendered during SSG with `timeout=10`
- **AND** the children's async operations do not complete within 10 seconds
- **THEN** the generated HTML SHALL contain the fallback content
- **AND** a warning SHALL be logged indicating the timeout was exceeded

### Requirement: Suspense shall show fallback then swap in browser environment
In the browser environment, `Suspense._render()` SHALL first render fallback content for immediate display, then schedule the async children resolution. When the async operations complete, `Suspense` SHALL replace the fallback with the actual children by removing the fallback DOM nodes via the existing `_remove_element()` mechanism and rendering the children content in their place, following the same pattern as `SwitchElement._refresh()`.

#### Scenario: Browser Suspense with async data
- **WHEN** `Suspense` is rendered in the browser
- **AND** the children's async operations are in progress
- **THEN** fallback content SHALL be displayed immediately
- **WHEN** the async operations complete
- **THEN** the fallback SHALL be replaced with children content
- **AND** the DOM transition SHALL not cause a visible layout shift (patching is used when possible)

### Requirement: Suspense shall support error fallback for async failures
`Suspense` SHALL accept an optional `error_fallback` parameter (a `Callable[[], ChildNode]` generator). If children's async setup raises an exception, the `error_fallback` SHALL be rendered instead of the children. If `error_fallback` is not provided, the exception SHALL propagate and the fallback SHALL remain displayed.

#### Scenario: Async operation fails with error_fallback provided
- **WHEN** a developer provides `Suspense(fallback=..., error_fallback=lambda: html.P({}, "Error!"), children=lambda: FailingComponent())`
- **AND** `FailingComponent`'s async setup raises an exception
- **THEN** the error fallback `<p>Error!</p>` SHALL be rendered

#### Scenario: Async operation fails without error_fallback
- **WHEN** a developer provides `Suspense(fallback=..., children=lambda: FailingComponent())` without `error_fallback`
- **AND** `FailingComponent`'s async setup raises an exception
- **THEN** the fallback content SHALL remain displayed
- **AND** the exception SHALL be logged as a warning
### Requirement: Suspense shall accept a configurable timeout

`Suspense` SHALL accept an optional `timeout` parameter (a `float` in seconds, default 10.0). This timeout applies to the server environment only — it determines how long `_render()` waits for async children before falling back. In the browser, the timeout has no effect (the fallback is shown indefinitely until children resolve or fail).

#### Scenario: Custom timeout for slow data sources
- **WHEN** a developer provides `Suspense(fallback=..., children=lambda: SlowComponent(), timeout=60.0)`
- **AND** `Suspense` is rendered in SSR/SSG
- **THEN** `_render()` SHALL wait up to 60 seconds for the children to resolve
- **AND** if they resolve within 60 seconds, children content SHALL be in the output

#### Scenario: Timeout only applies to server environment
- **WHEN** a developer provides `Suspense(fallback=..., children=lambda: AsyncComponent(), timeout=10.0)`
- **AND** `Suspense` is rendered in the browser
- **THEN** the timeout SHALL be ignored
- **AND** fallback SHALL be shown until children resolve, regardless of duration

### Requirement: Sibling Suspense boundaries shall resolve independently and in parallel
When multiple `Suspense` elements are siblings in the element tree, each SHALL independently manage its own loading state. Their async operations SHALL run concurrently via `asyncio.gather()`. Each Suspense boundary SHALL swap from fallback to children as its own async operations complete, without waiting for sibling Suspense boundaries.

#### Scenario: Two sibling Suspense elements loading different data
- **WHEN** a developer renders two `Suspense` elements side by side:
  ```python
  html.DIV(
      {},
      Suspense(fallback=lambda: html.P({}, "Loading users..."), children=lambda: UsersList()),
      Suspense(fallback=lambda: html.P({}, "Loading posts..."), children=lambda: PostsList()),
  )
  ```
- **AND** `UsersList` resolves in 1 second and `PostsList` resolves in 3 seconds
- **THEN** `UsersList` content SHALL appear after 1 second
- **AND** `PostsList` fallback SHALL remain for 3 seconds, then swap to content

### Requirement: Suspense shall detect and resolve async pending state via _pending_async_template tree traversal

`SuspenseElement` SHALL detect whether its children subtree has pending async operations by traversing the element tree and checking for unresolved `Component._pending_async_template` instances (as defined by `feat-async-component-setup`). When such instances are found, the subtree is considered "loading." When all `_pending_async_template` instances in the subtree have been resolved (`None`), the subtree is considered "ready."

Suspense SHALL own the resolution: when it detects pending `_pending_async_template` coroutines, it SHALL collect them via tree traversal, `await asyncio.gather(*coroutines)` to resolve them in parallel, then call `Component._render()` on each resolved component. `Component._render()` SHALL detect that `_pending_async_template` is already `None` (because Suspense already resolved it) and skip the await step. This ownership model ensures Suspense shows fallback while the coroutines are pending and observable, and swaps to children after resolution.

#### Scenario: Detecting an async child component
- **WHEN** a `Suspense` wraps a component whose `_pending_async_template` is set (not yet resolved)
- **THEN** `Suspense._render()` SHALL detect the pending state and render fallback
- **AND** when `_pending_async_template` is resolved to `None` after `await` completes
- **THEN** `Suspense` SHALL transition from fallback to children

#### Scenario: Detecting nested async children
- **WHEN** a `Suspense` wraps a sync component that contains an async child component
- **THEN** `Suspense._render()` SHALL traverse into nested children to detect the async grandchild
- **AND** fallback SHALL be shown until the grandchild's async setup completes

### Requirement: Suspense shall replace fallback with children during hydration

When `SuspenseElement._hydrate_node()` is called in the browser, the server-rendered fallback DOM nodes SHALL be replaced with the actual children content. The Suspense SHALL check the hydration data transfer payload to determine whether children async data was resolved during SSR: if the transfer payload contains resolved data for the Suspense's children, `_hydrate_node()` SHALL immediately render children; if no transfer data is present or the children's async setup is still unresolved, `_hydrate_node()` SHALL keep the fallback displayed, schedule async children resolution, and swap to children content when the async operations complete.

#### Scenario: Hydrating a Suspense element with already-resolved data
- **WHEN** a page containing `Suspense(fallback=..., children=lambda: DataComponent())` is hydrated in the browser
- **AND** the data was pre-resolved during SSR and included in the Hydration Data Transfer payload
- **THEN** the children's async setup SHALL be resolved immediately from the transfer payload
- **AND** fallback SHALL be replaced with children content immediately

#### Scenario: Hydrating a Suspense element without transfer data
- **WHEN** a page containing `Suspense(fallback=..., children=lambda: DataComponent())` is hydrated in the browser
- **AND** no transfer payload is present
- **THEN** the children's async setup SHALL begin executing
- **AND** fallback SHALL remain displayed until children resolve
- **AND** fallback SHALL be replaced with children content when ready

### Requirement: Suspense shall be usable with useAsyncResult
`Suspense` and `useAsyncResult` SHALL be compatible and complementary. A component using `useAsyncResult` can be wrapped in `Suspense` for declarative fallback. In this case, `Suspense` detects the async operation started by `useAsyncResult` and shows fallback until it completes.

#### Scenario: Suspense wrapping a useAsyncResult component
- **WHEN** a developer wraps a component that uses `useAsyncResult` in `Suspense`
- **THEN** `Suspense` SHALL show fallback while `useAsyncResult` is in `LOADING` state
- **AND** `Suspense` SHALL swap to children when `useAsyncResult` transitions to `SUCCESS` or `ERROR`

### Requirement: Suspense shall properly clean up on removal
When a `Suspense` element is removed from the DOM (e.g., due to a route change or conditional rendering), any pending async operations in its children subtree SHALL be cancelled. Signal callbacks registered by `Suspense` SHALL be cleaned up via `consumer_destroy()`.

#### Scenario: Navigating away from a Suspense boundary
- **WHEN** a `Suspense` element is inside a `switch()` conditional
- **AND** the condition changes, causing the `Suspense` to be removed
- **THEN** any pending async operations for that Suspense's children SHALL be cancelled
- **AND** signal callbacks SHALL be cleaned up

### Requirement: Suspense shall be a DynamicElement
`SuspenseElement` SHALL extend `DynamicElement`, meaning it has no DOM node of its own and renders its children directly into the parent element. This is consistent with `SwitchElement` and `RepeatElement`.

#### Scenario: Suspense renders children without wrapper element
- **WHEN** `Suspense` is used inside a `div`
- **THEN** the fallback or children content SHALL be direct children of the `div`
- **AND** no wrapper element SHALL be inserted around the Suspense content