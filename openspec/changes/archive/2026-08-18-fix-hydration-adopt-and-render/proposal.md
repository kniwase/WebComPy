# Proposal: Fix Hydration "Adopt & Render"

## Why

SSR/SSG HTML already ships the fully rendered page, but browser hydration discards most of it: browser measurements on the docs app show ~90% of prerendered DOM nodes are removed and rebuilt (the entire `RouterView` route subtree — 197 of 218 nodes on a markdown document page — plus all `RepeatElement` content), and the loading overlay is removed before the scheduled hydration render tasks complete. On Markdown/HTML-template pages with large async-rendered content this produces a visible flicker after first paint, and node identity loss re-triggers images, iframes, scroll state and transitions.

Hydration currently fulfills only one of two required phases per element type: it either adopts prerendered nodes without ever completing their render (dead reactive wiring — the failure mode `feat-nested-routes` patched by dropping adoption), or renders without adopting (wholesale node removal). This change establishes a single unified contract that does both.

## What Changes

- **Unified "adopt & render" hydration contract** across all element types: `_hydrate_node()` adopts prerendered DOM nodes, and a hydration render pass runs for every hydrated element — including mounted/adopted ones — so reactive machinery (signal subscriptions, key maps, switch branch state, lifecycle completion) initializes. Writes remain diff-only, so the render pass is visually neutral when server and client content match.
- **`DynamicElement._hydrate_node()`** schedules hydration render tasks for ALL children (not only unmounted ones); the hydration render pass disables the mounted/`_hydrated` render skip so adopted subtrees are wired.
- **`RouterView._hydrate_node()`** converges to the standard `DynamicElement` path: it generates the route component, hydrates (adopts) it, and schedules its hydration render — instead of the custom schedule-only implementation that causes SSR route content to be removed.
- **`RepeatElement._refresh()`** becomes adopt-aware: the first refresh after hydration repositions adopted SSR children and rebuilds the key map without destroying them (currently the full-rebuild path discards all adopted children).
- **`SwitchElement`** initializes its rendered branch at hydration time from the SSR branch, so the first refresh does not regenerate adopted children.
- **`SuspenseElement`** resolved-children path completes a hydration render (today the adopted children are never rendered).
- **Completion synchronization**: `BrowserAsyncSchedulerPort.await_pending()` drains scheduled tasks, and `AppDocumentRoot._render()` awaits the drain before removing the loading overlay, closing the race where the page is visible without its routed content.
- **Hydration mismatch diagnostics**: structural (tag/node-count) and recoverable (text/attr) mismatches are recorded with expected/actual values and owning component ID, aggregated into a single console warning, and exposed via a `RenderContext.hydration_report` API for tests and tooling. Existing silent `existing.remove()` repairs become reported repairs.

## Capabilities

### New Capabilities

(none — all requirements belong to existing capabilities)

### Modified Capabilities

- `elements`: hydration contract extension (adopt + render, diff-only writes), Repeat/Switch adopt-aware first refresh, element-level mismatch detection hooks, RawHTML adoption content preservation (compare-then-apply with canonical comparison)
- `async-rendering`: hydration render task scheduling rules, scheduler drain before loading-removal, aggregated mismatch reporting and `hydration_report` API
- `async-scheduler`: `AsyncSchedulerPort.schedule(coro, *, render=False)` and `await_pending(*, only_render=False)` port API; the browser drain is scoped to render-marked tasks so unrelated user tasks do not delay the reveal
- `router`: RouterView hydration behavior — route component SSR nodes are adopted and rendered, not removed
- `suspense`: resolved-path Suspense children receive a hydration render
- `signal-value-transfer`: auto transfer keys are derived from the call-site module identity instead of the absolute filesystem path, so SSR and browser environments agree on the same keys

## Known Issues Addressed

- **Visible flicker on SSR/SSG pages using Markdown or HTML templates**: prerendered route content is removed during the hydration pass and rebuilt later by scheduled tasks; the loading overlay removal races the rebuild. Established by browser instrumentation (MutationObserver timelines, node-survival counts).
- **Silently broken interactive updates on eagerly hydrated routed components** (the trade-off that led `feat-nested-routes` to drop adoption): resolved by executing the render phase while preserving adopted nodes.
- **Event-handler/identity loss in repeated content**: `RepeatElement` destroys adopted SSR children on its first refresh, re-triggering images/iframes inside repeated items.
- **Silent loss of prerendered code-block content on demo pages**: auto transfer keys embed the absolute filesystem path of the call site, which differs between the SSR checkout and the browser wheel bundle, so `use_state()` values (e.g., `DemoDisplay.source_code`) are never restored and the prerendered highlighted content is wiped and refetched. Exposed by the new `raw_html` mismatch diagnostics; fixed by deriving auto keys from the call-site module identity.

## Non-goals

- **No final sweep phase** that removes remaining unadopted SSR nodes in bulk after hydration. Genuine mismatches keep the existing in-place removal path (now reported). If measurement shows residual unadopted nodes, a follow-up change will add the sweep.
- **No inspect CLI extension** (e.g., `hydration:no-mismatch` verify rule).
- **No changes to hydration data transfer serialization**: payload version, codec, and `__webcompy_data__` format stay unchanged.
- **No changes to `_hydrate_node()` being synchronous**: the hydration pass phase ordering follows the existing contract.
- **No changes to non-hydrate mode or the server render path**: the `_hydrate` guard and the synchronous await-chain render remain as specified.

## Impact

- **Code**: `webcompy/elements/types/_dynamic.py`, `_repeat.py`, `_switch.py`, `_suspense.py`, `_error_boundary.py`, `_teleport.py`; `webcompy/router/_view.py`; `webcompy/app/_root_component.py`, `app/_render_context.py`; `webcompy/ports/_async_scheduler.py`, `ports/_browser/_async_scheduler.py`, `webcompy-server/ports/_async_scheduler.py`
- **Public API**: new `RenderContext.hydration_report` attribute (read-only diagnostics); `AsyncSchedulerPort.schedule(coro, *, render=False)` / `await_pending(*, only_render=False)` keyword flags; `webcompy.hydration` exports `record_mismatch` and `HydrationMismatchRecord`
- **Tests**: unit tests for hydration adopt/render per dynamic element type (`tests/test_full_hydration.py`, `test_dynamic_child_node_index.py`, `test_repeat.py`, `test_switch.py`, `test_suspense.py`, `test_router_view*.py`, `test_custom_element_components.py` expectations updated/added); new E2E regression asserting SSR node survival on docs pages plus warning-free console
- **Specs**: deltas for `elements`, `async-rendering`, `async-scheduler`, `router`, `suspense`