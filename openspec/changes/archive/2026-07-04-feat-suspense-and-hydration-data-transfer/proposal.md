# Proposal: Suspense and Hydration Data Transfer

## Why

WebComPy's async rendering pipeline (`feat/async-rendering-pipeline`) makes the rendering
pipeline fully async, and `feat/async-component-setup` extends it so component definitions can
themselves be `async def`. These foundations enable two interrelated features that together
unlock production-quality SSR/SSG with async data:

1. **Suspense** — Declarative async boundaries that show fallback content while children
   are loading and swap to real content when complete. In SSR/SSG, Suspense awaits children
   (with a configurable timeout) so resolved data appears in the output HTML.

2. **Hydration Data Transfer** — Server-to-browser data transfer mechanism that serializes
   resolved `AsyncResult` states and `FetchPort` response caches into a `<script>` tag in
   the HTML. During browser hydration, the data is restored so components skip the
   `LOADING` phase entirely — eliminating duplicate network requests and the flash of
   loading states for data that was already available on the server.

### Why combine these two changes

These features have a **mutual dependency** at the spec level:

- `SuspenseElement._hydrate_node()` needs `has_resolved_data(component_id)` to decide
  whether to immediately render children (data is in the transfer payload) or keep the
  fallback (data not available, must re-resolve). This requires a hydration-data API.
- The hydration data transfer infrastructure is most useful when components are wrapped
  in `Suspense` boundaries, because Suspense is the natural place to ensure all async
  children complete on the server before the data is collected.

The original two-change design (`feat-suspense-component` + `feat-hydration-data-transfer`)
created a circular dependency. The merged change resolves this by defining the shared
**API surface** (HYDRATION_DATA_KEY, `has_resolved_data()`, payload schema) as the first
section, then building the transfer mechanism, then Suspense on top.

### What this delivers

```python
from webcompy.elements import html, Suspense, DataComponent
from webcompy.aio import use_async_result

@define_component
async def DataPage(context):
    # Async setup: data fetched during SSR, included in HTML
    data = await fetch("/api/data")  # server-rendered into transfer payload
    return html.DIV(
        {},
        html.H1({}, "Dashboard"),
        Suspense(
            fallback=html.P({}, "Loading..."),
            children=lambda: DataComponent(data=data),
        ),
    )
```

During SSR, `Suspense` awaits `DataComponent`'s async setup. The fetched data lands in
the transfer payload. The browser hydration sees the resolved state, skips the network
request, and renders the content directly — no loading flash.

## What Changes

- **NEW** `Suspense` element class in
  `packages/webcompy/src/webcompy/elements/types/_suspense.py` — A `DynamicElement` that
  controls when children generators are evaluated, showing fallback during async loading
  and children after completion. Supports `error_fallback` and a server-side `timeout`.
- **NEW** `suspense()` generator function in
  `packages/webcompy/src/webcompy/elements/generators.py`.
- **MODIFIED** `packages/webcompy/src/webcompy/elements/__init__.py` — Export `Suspense`.
- **NEW** `webcompy/hydration/` module in the `webcompy` core package:
  - `_payload.py` — `TransferPayload`, `TransferFetchEntry`, `TransferAsyncResultEntry`,
    `serialize_payload()`, `deserialize_payload()`.
  - `_collect.py` — `collect_transfer_data()` that gathers `AsyncResult` states and
    `FetchPort` cache from the component tree.
  - `__init__.py` — Public API exports, including `has_resolved_data(component_id)`.
- **NEW** `HYDRATION_DATA_KEY: InjectKey[dict]` in
  `packages/webcompy/src/webcompy/di/_keys.py` — The DI key used to provide the
  `async_results` section of the transfer payload during browser initialization.
- **MODIFIED** `packages/webcompy/src/webcompy/aio/_async_result.py` — `AsyncResult`
  gains `_restore_from_transfer(data)`; `useAsyncResult` checks the transfer payload
  before scheduling execution.
- **MODIFIED** `packages/webcompy/src/webcompy/ports/_browser/_fetch.py` —
  `BrowserFetchPort` gains a response cache populated from the transfer payload.
- **MODIFIED** `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` —
  `ServerFetchPort` caches self-site responses during SSR for inclusion in the payload.
- **MODIFIED** `packages/webcompy-server/src/webcompy_server/_html.py` — Inject the
  serialized transfer payload as a `<script type="application/json"
  id="__webcompy_data__">` tag in the SSR/SSG output.
- **MODIFIED** `packages/webcompy/src/webcompy/app/_app.py` — On `app.run()`, read the
  payload from the DOM and provide it via `HYDRATION_DATA_KEY`; call
  `BrowserFetchPort.populate_from_transfer()`.
- **MODIFIED** `packages/webcompy/src/webcompy/app/_root_component.py` — Collect
  transfer data from `AsyncResult` instances and `ServerFetchPort` cache after SSR
  rendering.

## Capabilities

### New Capabilities

- `suspense`: Declarative async boundary that shows fallback while children load and
  swaps to real content on completion. In SSR/SSG, awaits children (with timeout) so
  data appears in the output. Supports `error_fallback`.
- `hydration-data-transfer`: Server-to-browser data transfer that serializes resolved
  `AsyncResult` states and `FetchPort` response caches into the HTML payload, and
  restores them during hydration.

### Modified Capabilities

- `elements`: New `SuspenseElement` `DynamicElement` subclass alongside `SwitchElement`
  and `RepeatElement`.
- `async`: `AsyncResult` supports state restoration from transfer payload, bypassing
  async re-execution.
- `port-abstraction`: `BrowserFetchPort` and `ServerFetchPort` support response
  caching and transfer payload integration.
- `app-lifecycle`: `AppDocumentRoot` collects transfer data after SSR rendering and
  restores it during browser hydration.
- `architecture`: HTML output includes a data transfer payload `<script>` tag; the
  hydration process reads and restores this payload.

## Dependencies

- **Requires** `feat/async-rendering-pipeline` (#177) — `Component._render()` and
  `ElementWithChildren._render()` are already `async def`; `generate_html()` is async.
- **Requires** `feat/async-component-setup` — `_pending_async_template` tree traversal
  and `SUSPENSE_RESOLVING_KEY` are the primitives Suspense uses to detect and own
  async child resolution.
- **Requires** `feat/server-fetch-port-asgi` — `ServerFetchPort` must support
  self-site fetching via ASGI transport so async components can fetch data during
  SSR/SSG; the response cache is the source of the `fetches` section of the
  transfer payload.
- **Requires** `feat/ssg-via-ssr` (or equivalent) — `generate_html()` must be async
  and `generate_static_site()` must drive the async pipeline so the payload collection
  step (`_collect_transfer_data()`) runs after the entire SSR tree has resolved.

## Known Issues Addressed

- **No declarative async boundary** — Developers currently use fire-and-forget
  `useAsyncResult` for data fetching during SSR, which means SSG output never
  contains fetched data.
- **Flash of loading states during hydration** — After SSR resolves data, the browser
  re-fetches and shows a `LOADING` state until the duplicate request completes.
- **Duplicate fetches during hydration** — Browser-side `FetchPort` makes the same
  requests the server already made, wasting bandwidth and time.
- **Suspense ↔ Hydration Data Transfer circular dependency** — The original
  two-change design required both changes to be implemented before either could
  complete. The merged change defines the shared API surface first, breaking the
  cycle.

## Non-goals

- **Streaming SSR** — Data transfer happens in a single payload embedded in the HTML.
  No incremental streaming.
- **Client-to-server data transfer** — The payload is unidirectional
  (server → browser).
- **Signal value restoration** — Only `AsyncResult` and `FetchPort` cache are
  transferred. Application-level `Signal` values are not serialized. Developers SHOULD
  use `Suspense` or `ClientOnly` to manage the transition for Signal-derived state.
- **Payload compression** — JSON without compression. Can be added later.
- **Custom transfer keys** — URLs (for fetches) and component IDs (for async results)
  are the only keys.
- **Parallel sibling Suspense gathering** — Sibling `Suspense` boundaries render
  sequentially (per the `async-rendering` spec). Within a single boundary, async
  children resolve concurrently via `asyncio.gather`.
- **Changing `useAsyncResult` API** — `useAsyncResult` is unchanged; it transparently
  benefits from transfer data.
- **Server-only rendering primitive (`ServerOnly`)** — A `ServerOnly` element is not in
  scope. `ClientOnly` is the bidirectional counterpart in a separate change.

## Impact

- **Affected modules**:
  - `packages/webcompy/src/webcompy/elements/types/_suspense.py` (new)
  - `packages/webcompy/src/webcompy/elements/generators.py` (new `suspense()` function)
  - `packages/webcompy/src/webcompy/elements/__init__.py` (export)
  - `packages/webcompy/src/webcompy/components/_component.py` (async setup detection)
  - `packages/webcompy/src/webcompy/aio/_async_result.py` (state restoration)
  - `packages/webcompy/src/webcompy/di/_keys.py` (new `HYDRATION_DATA_KEY`)
  - `packages/webcompy/src/webcompy/hydration/` (new module)
  - `packages/webcompy/src/webcompy/ports/_browser/_fetch.py` (cache from payload)
  - `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` (response caching)
  - `packages/webcompy-server/src/webcompy_server/_html.py` (payload injection)
  - `packages/webcompy/src/webcompy/app/_app.py` (payload provision via DI)
  - `packages/webcompy/src/webcompy/app/_root_component.py` (data collection)
- **Backward compatibility**: Existing components without `async` setup and without
  `Suspense` work unchanged. `AsyncResult` without a matching transfer entry falls
  through to the normal `PENDING → LOADING → SUCCESS` lifecycle.
- **Testing**: Unit tests for payload serialization, `AsyncResult` restoration,
  `BrowserFetchPort` cache hits, `ServerFetchPort` cache population, and Suspense
  fallback/error paths. E2E tests for the full SSR → browser data transfer flow.
