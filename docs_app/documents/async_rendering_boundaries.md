---
title: Async Rendering & Boundaries
description: Author async components cleanly, coordinate Suspense and ClientOnly across SSR and hydration, and understand how AsyncSchedulerPort gates the initial page reveal.
---

# Async Rendering & Boundaries

WebComPy's rendering pipeline is asynchronous end to end (`async def _render()`): components, lifecycle hooks, `Suspense` fallbacks, and dynamic child refreshes all integrate natively with `async`/`await` while preserving deterministic DOM order.

Choose your async pattern based on what needs to happen on the server vs the browser:

| Tool | When to use it | Server behavior (SSR/SSG) | Browser behavior |
|---|---|---|---|
| `async def` component setup | A component needs data/resources *before* building its template | Awaited inline before HTML serialization | Awaited during initial render or under enclosing `Suspense` |
| `Suspense` / `suspense()` | Show a loading placeholder while one or more async children settle | Awaits children up to `timeout` (10s default); emits resolved HTML | Shows `fallback`, resolves children via `asyncio.gather()`, swaps cleanly |
| `ClientOnly` / `client_only()` | Subtree depends on browser-only modules, DOM/canvas APIs, or shouldn't pre-render | Never calls `children()`; emits `fallback` or empty placeholder | Hydrates by replacing fallback with `children()` once live |
| `use_async_result()` | Reactive data fetching with loading/error states and `.refetch()` | Runs after initial render; drained via scheduler for transfer | Restores from transfer payload on initial boot, else runs `LOADING` → `SUCCESS`/`ERROR` |
| `ErrorBoundary` | Catch synchronous, async-setup, or re-render failures in a subtree | Renders `fallback` on SSR; fails fast on SSG | Captures exceptions, runs `fallback(error, reset)` |

## Async component setup and lifecycle hooks

Decorate an `async def` function directly with `@define_component()`:

```python
from webcompy import load_text
from webcompy.components import (
    ComponentContext,
    define_component,
    on_before_rendering,
)
from webcompy.elements import html
from webcompy.template import render_markdown


@define_component()
async def ReleaseNotesPanel(context: ComponentContext[dict[str, str]]):
    source = await load_text(context.props["resource"])

    @on_before_rendering
    async def log_visit():
        print("Rendering release notes")

    return html.SECTION({"class": "notes"}, render_markdown(source))
```

Key execution contracts:

- **Two-phase initialization**: Calling `ReleaseNotesPanel(props)` stores the unresolved coroutine on the component without touching its template yet, making pending async components discoverable by ancestor `Suspense` boundaries before rendering starts. Once awaited, WebComPy extracts any hooks, `use_*` signals, and `use_async_result` entries registered inside the `async def` body cleanly via `ComponentRenderState`.
- **Sequential sibling rendering**: Parent elements render their children sequentially (`for child in children: await child._render()`). DOM order is deterministic, `ContextVar` state flows cleanly along the `await` chain, and an unhandled exception short-circuits subsequent siblings without partial trailing nodes.
- **Async lifecycle hooks**: Both `@on_before_rendering` and `@on_after_rendering` (and their `context.*` methods) accept either synchronous functions or `async def` coroutines.

## Coordinating async trees with `Suspense`

Wrap one or more `async def` components in `Suspense` (or its helper `suspense()`) from `webcompy.elements` to display a shared loading state while unresolved async descendant setups finish:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import Suspense, html


@define_component()
def DashboardSection(context: ComponentContext[None]):
    return Suspense(
        fallback=lambda: html.P({"class": "skeleton"}, "Loading dashboard metrics…"),
        children=lambda: MetricsGrid(None),
        error_fallback=lambda: html.P({"class": "error"}, "Failed to load dashboard."),
        timeout=8.0,
    )
```

`Suspense` (alias for `SuspenseElement`) and `suspense(*, fallback=..., children=..., error_fallback=None, timeout=10.0)` share four parameters, all lazy zero-argument callables (`lambda: ...`):

- `fallback`: displayed while child async setups are unresolved (`timeout` defaults to `10.0` seconds).
- `children`: evaluated lazily when `Suspense` prepares resolution; all pending `async def` descendant coroutines within this boundary are gathered **concurrently** via `asyncio.gather()` (each isolated with its own component context), whereas sibling `Suspense` boundaries render sequentially one after another.
- `error_fallback`: optional fallback rendered if a child raises during resolution. When omitted, the exception propagates outward to the nearest `ErrorBoundary` (or parent caller).
- `timeout`: maximum seconds to await async child resolution on both server and browser.

### SSR and hydration behavior

- **On the server (SSR/SSG)**: `Suspense` blocks rendering via `asyncio.wait_for(..., timeout=timeout)` and emits the resolved children straight into HTML. If `timeout` expires, it logs a warning, destroys the discarded probe subtree, and renders `fallback`.
- **On browser hydration**: `Suspense` checks `has_resolved_data(transfer_id)` for its async children. When all are already present in `#__webcompy_data__` (from SSR/SSG), it takes the **fast path**—adopting the pre-rendered DOM nodes and wiring reactivity with zero fallback flash. Otherwise it hydrates `fallback` and schedules resolution inside a render-scoped task reusing the probed children so per-instance transfer IDs and parent DI scopes remain aligned.
- **Provisional transfer IDs**: Fallbacks rendered for timeout, error, or unresolved hydration receive non-consuming provisional transfer IDs so they never shift ordinal `#0`/`#1` counters for sibling components outside the boundary.

## Skipping SSR with `ClientOnly`

Wrap browser-only widgets (charts, canvas tools, WebGL/audio wrappers, components importing browser packages) inside `ClientOnly` or `client_only` from `webcompy.elements`:

```python
from webcompy.elements import ClientOnly, client_only, html

chart = ClientOnly(
    children=lambda: InteractiveChart(None),
    fallback=lambda: html.DIV({"class": "chart-placeholder"}, "Loading chart…"),
)

# Functional helper with identical behavior:
analytics = client_only(
    children=lambda: AnalyticsTracker(None),
    fallback=None,  # renders an empty placeholder text node on the server
)
```

- **Server guarantee**: During SSR and SSG, the `children` callable is **never invoked**—components inside it do not even run `__init__`, preventing `ImportError` or DOM crashes from browser-only code.
- **No wrapper DOM node**: `ClientOnly` extends `DynamicElement`, mounting its children directly under the parent element without introducing an extra container tag.
- **Hydration swap**: In the browser, hydration cleanly removes the SSR `fallback` (or empty placeholder) and mounts the live `children` tree without mismatch warnings.

## How `AsyncSchedulerPort` gates the reveal

Framework background work (hydrating dynamic containers, `Teleport` post-hydration mounts, `ErrorBoundary` resets, `use_async_result` initial fetches, `aio_run` tasks) routes through `AsyncSchedulerPort` (`ASYNC_SCHEDULER_PORT_KEY`) rather than bare `asyncio.ensure_future()`:

```text
schedule(coro, *, render=True | False)
  │
  ├─ Server (SSR/SSG)
  │    Drains ALL tasks recursively (up to 20 passes) on `await scheduler.await_pending()`
  │    before `collect_transfer_data()` and `ctx.dispose()` run.
  │
  └─ Browser (Hydration)
       Initial render awaits `await scheduler.await_pending(only_render=True)`
       before closing the hydration window and tearing down `#webcompy-loading`.
       └─ Tasks with render=True finish before page reveal (routed views are present).
       └─ Tasks with render=False (e.g. generic user `aio_run` calls) never delay reveal.
```

Async signal callbacks (`@signal.on_after_updating async def ...`) follow intentional environment-specific semantics via the framework scheduler: on the **server/test**, async callbacks execute to completion before returning so HTML snapshots are deterministic; in the **browser**, they dispatch asynchronously via `aio_run()` to keep user interaction responsive while synchronous `Computed` and text bindings still settle first.

## Behavior notes & pitfalls

- **Always wrap `children` and `fallback` in lambdas**: `ClientOnly(InteractiveChart(None))` would evaluate `InteractiveChart(None)` immediately during SSR before `ClientOnly` runs! Always pass `children=lambda: InteractiveChart(None)` and `fallback=lambda: ...`.
- **Keep `provide()` scoped cleanly inside `Suspense`**: `Suspense` snapshots and restores the active DI scope after probing children, so a `provide()` inside a child does not leak into sibling components.
- **`ErrorBoundary` vs `Suspense(error_fallback=...)`**: Use `error_fallback` when an async fetch/setup failure should stay local to that `Suspense`; omit it when errors should escalate to an enclosing `ErrorBoundary` (which provides `reset()` to retry and obeys SSG fail-fast rules).

## Next steps

- Learn how `use_*` composables transfer resolved `Suspense` and async state across SSR in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
- Understand the full SSR/SSG lifecycle behind `await_pending()` in [SSR & SSG](/documents/advanced/ssr-and-ssg).
- Configure grace periods and removal fades triggered after `await_pending(only_render=True)` in [Loading Screen](/documents/advanced/loading-screen).
- Revisit `ErrorBoundary` parameters in [Error Handling](/documents/basic/error-handling) and typed RPC calls in [RPC Contracts](/documents/advanced/rpc-contracts).
- Full API: [Elements, Routing & DI API](/documents/api/elements-and-routing) and [Data, Forms & i18n API](/documents/api/data).
