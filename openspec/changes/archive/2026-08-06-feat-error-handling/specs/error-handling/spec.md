# Delta: error-handling

## ADDED Requirements

### Requirement: ErrorBoundary element shall catch descendant render errors

The framework SHALL provide an `ErrorBoundary` element (exported from `webcompy.elements`) accepting `children: Callable[[], ElementChildren]`, `fallback: Callable[[Exception, Callable[[], None]], ElementChildren]`, optional `on_error: Callable[[Exception], Any]`, and optional `catch_events: bool` (default `False`). When a descendant raises during setup (sync or async), initial render, or a signal-driven re-render, the boundary SHALL destroy the failed subtree, render the fallback in its place, and invoke `on_error` with the exception. The fallback SHALL receive the caught exception and a `reset` callable.

#### Scenario: Sync setup error renders fallback
- **WHEN** a descendant component raises synchronously in its setup/template during the boundary's render
- **THEN** the boundary SHALL render `fallback(error, reset)` at the same tree position
- **AND** `on_error` SHALL be called with the exception
- **AND** siblings outside the boundary SHALL render and remain interactive

#### Scenario: Async setup error renders fallback
- **WHEN** a descendant with async setup raises while the boundary is resolving
- **THEN** the boundary SHALL engage the fallback exactly as for sync errors (including descendants rendered via `Suspense` without its own `error_fallback`)

#### Scenario: Reactive re-render error renders fallback
- **WHEN** a signal update triggers a re-render inside a descendant `repeat`/`switch`/dynamic element and that re-render raises
- **THEN** the boundary SHALL engage the fallback
- **AND** the application outside the boundary SHALL continue to process signal updates

### Requirement: reset() shall rebuild the children subtree from scratch

The `reset` callable passed to `fallback` SHALL destroy the boundary's entire children subtree (including component destruction and DI-scope disposal) and re-invoke the `children` generator, re-running all descendant setup functions. State is NOT preserved. If `reset` is never called, the boundary SHALL keep showing the fallback. If the error cause persists, the boundary SHALL re-engage the fallback; reset SHALL only be triggerable from external events, never from the error path itself.

#### Scenario: Retry after transient failure
- **WHEN** the fallback's retry button calls `reset()` and the error cause is gone
- **THEN** the children SHALL re-render successfully with freshly initialized state

#### Scenario: Error cause persists
- **WHEN** `reset()` is called but the descendant raises again
- **THEN** the boundary SHALL render the fallback again without an infinite loop

### Requirement: Errors shall propagate bottom-up through hooks then boundaries

On error, the framework SHALL walk the element parent chain upward from the error source. `on_error_captured` hooks on ancestor components SHALL be invoked nearest-first. A hook returning `False` SHALL mark the error handled and stop all further propagation (no boundary engages). Otherwise the nearest ancestor `ErrorBoundary` SHALL engage; hooks and boundaries above it SHALL NOT be invoked. An error raised inside a fallback SHALL propagate as if the engaging boundary were transparent (it SHALL NOT catch its own fallback). With no engaging boundary, the error SHALL be reported to `WebComPyAppConfig.on_error` if set, else logged.

#### Scenario: Hook veto
- **WHEN** an `on_error_captured` hook between the error source and the nearest boundary returns `False`
- **THEN** the boundary SHALL NOT engage and no fallback swap SHALL occur

#### Scenario: Nearest boundary wins
- **WHEN** nested boundaries exist and an inner boundary's descendant raises
- **THEN** only the inner boundary SHALL engage

#### Scenario: Error inside fallback escalates
- **WHEN** a boundary's fallback render itself raises
- **THEN** the next boundary above SHALL engage (or the global handler SHALL be invoked if none)

### Requirement: Event-handler errors shall route to the global handler by default

Exceptions raised by event handlers (sync or async) SHALL be caught by the framework's handler wrapper. By default they SHALL be reported via the D2 propagation walk (hooks, then `AppConfig.on_error`, else log) WITHOUT swapping any boundary fallback. A boundary with `catch_events=True` SHALL additionally engage its fallback for event-handler errors from descendants.

#### Scenario: Default event error reporting
- **WHEN** a button's `on_click` handler raises and no ancestor boundary has `catch_events=True`
- **THEN** the error SHALL reach `AppConfig.on_error` (or be logged)
- **AND** no boundary fallback SHALL render and the DOM SHALL remain unchanged

#### Scenario: Opt-in boundary catch
- **WHEN** a descendant event handler raises inside a boundary with `catch_events=True`
- **THEN** that boundary SHALL engage its fallback

### Requirement: SSR shall survive contained errors; SSG shall fail fast

During per-request SSR, an engaged boundary SHALL render its fallback HTML and the rest of the page SHALL render normally; uncontained errors keep failing the request (500). During SSG (build time), any error reaching a boundary SHALL fail the build. The policy SHALL be selected via an injectable key (default SSR-tolerant) provided as `"ssg"` by the static-generation entry point.

#### Scenario: SSR page survives
- **WHEN** a descendant raises during SSR inside a boundary
- **THEN** the response SHALL be 200 with the fallback HTML in place and the rest of the page fully rendered

#### Scenario: SSG build fails
- **WHEN** a descendant raises during `webcompy generate` inside a boundary
- **THEN** the generation SHALL fail with the original error surfaced

### Requirement: RouterView shall isolate each route level in an implicit boundary

Each chain level rendered by a `RouterView` SHALL be wrapped in an implicit `ErrorBoundary` whose fallback renders nothing. A failing level SHALL NOT destroy ancestor levels (layouts). On navigation, if the implicit boundary is in error state, it SHALL be reset (the level retries); levels destroyed by the reuse rule carry no error state into their re-creation. App-declared boundaries inside page components nest within the implicit one and SHALL engage first.

#### Scenario: Page crash preserves layout
- **WHEN** the leaf page of `/docs/guide` raises during render
- **THEN** the depth-0 layout (sidebar) SHALL remain mounted and interactive
- **AND** the leaf level SHALL render empty

#### Scenario: Re-navigation retries
- **WHEN** a page level is in implicit-boundary error state and the user navigates (including re-clicking the same link)
- **THEN** the level SHALL attempt to render again

### Requirement: Boundary fallback from SSR should auto-retry on hydration (stretch)

When SSR output contains a boundary fallback (marked with `data-webcompy-error-fallback`), the hydrating client boundary SHOULD adopt the fallback DOM and schedule exactly one automatic `reset()` after initial hydration. If the retry fails, the boundary SHALL settle into the fallback normally. The hydration guard structure of `AppDocumentRoot._render()` SHALL NOT be modified.

#### Scenario: Server-specific failure recovered on client
- **WHEN** SSR rendered a boundary fallback (e.g., SSR-time fetch failed) and the client hydrate succeeds for the rest of the page
- **THEN** the boundary SHOULD attempt children rendering once on the client
- **AND** on success the children SHALL replace the fallback
