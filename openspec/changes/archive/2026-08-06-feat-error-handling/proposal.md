# Proposal: Error Handling (`ErrorBoundary`, `on_error_captured`, global handler)

## Why

WebComPy currently has no error containment. An exception raised in a component's setup, template, or signal-driven re-render propagates uncaught and aborts the entire render pass: in the browser the whole application stops rendering, and during SSR the whole page fails with a 500. This is the framework's largest robustness gap, and it is especially damaging in the PyScript environment where debugging is inherently difficult (console access is indirect, stack traces cross the Wasm boundary). Every major frontend framework ships an answer to this — React error boundaries, Vue `errorCaptured` / `app.config.errorHandler`, Svelte 5 `<svelte:boundary>` — and WebComPy needs one before an official release.

The machinery already half-exists: `SuspenseElement._handle_error()` swaps children for a fallback with correct node positioning and re-indexing, but it only engages for async-setup failures inside `Suspense`. This change generalizes that pattern into a first-class error-handling capability.

## What Changes

- **`ErrorBoundary` element** (Suspense-style, core API): wraps children, catches errors from descendant setup/render/reactive re-renders, swaps the subtree to a `fallback(error, reset)` UI, and calls an optional `on_error` side channel. `reset()` destroys the subtree and re-runs the children generator from scratch (fresh setup, state is re-initialized); if never called, the fallback stays. `catch_events=True` opts the boundary into also catching errors from descendant event handlers (default off — event errors route to the global handler only).
- **Error discovery via parent-chain walk**: when an error surfaces, the framework walks `element._parent` upward, invoking `on_error_captured` hooks on component ancestors (nearest-first; returning `False` marks the error handled and stops propagation), then engaging the nearest `ErrorBoundary`. A boundary's fallback swap stops propagation (hooks above the boundary are not called), matching React semantics. Errors inside a fallback propagate to the next boundary up.
- **`on_error_captured` hook**: registered inside component setup via `context.on_error_captured(fn)` (same `_active_component_context` pattern as `on_before_destroy`), released on component destruction. Logic-only counterpart to the boundary element (logging, filtering, swallowing).
- **Global handler**: `WebComPyAppConfig.on_error` receives any error that reaches the top unhandled (including event-handler errors that no `catch_events` boundary claimed). Final fallback remains logging, as today.
- **Event-handler error routing**: `_generate_event_handler` wraps invocation; sync and async handler errors are reported to the global handler by default, and to the nearest `catch_events=True` boundary when present.
- **Environment policy**: during per-request SSR, an engaged boundary renders its fallback and the rest of the page survives (uncontained errors still 500). During SSG (build time), component errors are developer bugs — the build fails fast.
- **RouterView implicit boundary**: each chain level rendered by a `RouterView` is wrapped in an implicit boundary, so one page's failure cannot take down a shared layout. The implicit boundary resets automatically on navigation ("clicking the same link retries"), integrating with the level-reuse rule.
- **Signal notification isolation** (reactive capability): an exception in one signal consumer callback no longer blocks notification of the remaining consumers; the failing consumer's error is routed through the error-handling pipeline.
- **Hydration stretch goal**: when SSR rendered a boundary's fallback, the client boundary adopts the fallback DOM and performs one automatic `reset()` attempt, rescuing server-specific failures (e.g., SSR-time fetch errors that succeed in the browser).

## Capabilities

### New Capabilities

- `error-handling`: the `ErrorBoundary` element, error discovery and propagation order, environment policy (SSR fallback / SSG fail-fast), RouterView implicit boundary, hydration retry (stretch).

### Modified Capabilities

- `components`: adds the `on_error_captured` setup hook (registration, bottom-up invocation, veto semantics, release on destroy).
- `app-config`: adds `WebComPyAppConfig.on_error`.
- `elements`: adds event-handler error routing (default report-to-global, opt-in boundary catch).
- `router`: adds the RouterView implicit per-level boundary with navigation-triggered reset.
- `reactive`: adds consumer-notification isolation (one failing consumer must not block other consumers; failing consumer errors enter the error-handling pipeline).

## Impact

- **Code**: new `packages/webcompy/src/webcompy/elements/types/_error_boundary.py`; `elements/__init__.py` export; `components/_hooks.py` + component instance hook storage; `app/_config.py` (`on_error` field); `elements/types/_element.py` (`_generate_event_handler` wrap); dynamic-element refresh paths wrapped to route reactive-update errors; `router/_view.py` (implicit boundary + reset-on-navigate); `signal/_graph.py` / `_base.py` (consumer isolation); SSG strictness flag plumbed from `webcompy_cli._generate` through render context / DI.
- **Specs**: new `openspec/specs/error-handling/spec.md`; deltas to `components`, `app-config`, `elements`, `router`, `reactive`.
- **Tests**: unit coverage per error source × propagation order; SSR-survives / SSG-fails; e2e crashing-component-with-retry scenario and layout-survives-page-crash scenario.
- No breaking changes: apps without boundaries/hooks behave as today except that signal consumer failures no longer abort sibling notifications (a robustness fix, previously undefined behavior).

## Known Issues Addressed

- Uncaught component errors abort the entire browser render / SSR page (no containment mechanism exists).
- A raising signal consumer callback can block notification of subsequent consumers (undefined robustness gap in the notification chain).
- Event-handler exceptions vanish into the PyScript console with no framework-level reporting hook.

## Non-goals

- A dev-server error overlay (CLI-side DX feature, separate change).
- `reset_on` / declarative auto-reset triggers beyond RouterView navigation (future extension).
- Retry with backoff, error telemetry integrations, or source-mapped stack traces.
- Changing `AsyncResult` semantics — data-fetching errors are already self-contained via its `error` state and intentionally stay out of the boundary path.
- Full Jinja2-style template error recovery; template compile-time errors remain hard failures.
