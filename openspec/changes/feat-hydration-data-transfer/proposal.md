# Proposal: Hydration Data Transfer

## Why

WebComPy currently has NO mechanism for transferring server-side data to the browser. During hydration, the browser re-executes all component setups from scratch, re-fetching all data that was already resolved on the server. This causes:

1. **Duplicate fetches** — Every `AsyncResult` that completed during SSR/SSG triggers a new network request in the browser, wasting bandwidth and increasing time-to-interactive.
2. **Flash of loading states** — Users see Suspense fallback or `useAsyncResult` loading indicators for data that was already available in the server-rendered HTML.
3. **Signal flash-of-default-content** — Signal values computed during SSR reset to their defaults on the browser side, causing visible content flicker before reactive updates propagate.

Other frameworks solve this with server-to-client data transfer: Next.js serializes RSC payloads, Nuxt 3 uses `__NUXT_DATA__`, and SvelteKit serializes `load()` data into the page HTML. WebComPy needs an equivalent mechanism.

With the `feat/async-rendering-pipeline` change making the rendering pipeline async, and `feat/suspense-component` providing async boundary management, the server can now fully resolve async data during SSR. The `feat/server-fetch-port-asgi` change enables `ServerFetchPort` to route self-site requests through the ASGI app. This change builds on all three to serialize resolved server-side data into the HTML and restore it during browser-side hydration.

## What Changes

- **NEW** `webcompy/hydration/` module — Transfer payload serialization/deserialization, payload schema definition, and hydration data restoration logic.
- **NEW** Transfer payload injection in `packages/webcompy-server/src/webcompy_server/_html.py` — After async SSR rendering, collect all resolved `AsyncResult` states and `FetchPort` response caches, serialize them into a `<script type="application/json" id="__webcompy_data__">` tag appended to the HTML output.
- **MODIFIED** `packages/webcompy/src/webcompy/aio/_async_result.py` — `AsyncResult` gains a `_restore_from_transfer()` method that accepts pre-resolved data and transitions directly to `SUCCESS` state without re-executing the async function. `useAsyncResult` checks the transfer payload before scheduling execution.
- **MODIFIED** `packages/webcompy/src/webcompy/ports/_browser/_fetch.py` — `BrowserFetchPort` reads the transfer payload during initialization and returns cached responses for URLs present in the payload, avoiding duplicate network requests.
- **MODIFIED** `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` — `ServerFetchPort` caches response data during SSR for inclusion in the transfer payload.
- **MODIFIED** `packages/webcompy/src/webcompy/app/_root_component.py` — After SSR rendering, collect transfer data from `AsyncResult` instances and `FetchPort` response cache. During browser hydration, restore `AsyncResult` states and populate `BrowserFetchPort` cache from the transfer payload.

## Capabilities

### New Capabilities

- `hydration-data-transfer`: Server-to-browser data transfer that serializes resolved `AsyncResult` states and `FetchPort` response caches into the HTML payload, and restores them during hydration to prevent duplicate fetches and flash-of-loading-content.

### Modified Capabilities

- `app-lifecycle`: `AppDocumentRoot` collects transfer data after SSR rendering and restores it during browser hydration.
- `async`: `AsyncResult` supports state restoration from transfer payload, bypassing async re-execution.
- `port-abstraction`: `BrowserFetchPort` and `ServerFetchPort` support response caching and transfer payload integration.
- `architecture`: The HTML output includes a data transfer payload `<script>` tag; the hydration process reads and restores this payload.

## Known Issues Addressed

- **Duplicate fetches during hydration** — Browser re-fetches data that was already resolved during SSR. This change eliminates duplicate fetches by transferring server-side data to the browser.
- **Flash of loading states** — Users see loading indicators for data that was already resolved on the server. `AsyncResult` state restoration prevents the `LOADING` phase for transferred data.

## Limitations

- **Signal values are NOT transferred** — This change transfers `AsyncResult` states and `FetchPort` response caches only. Application-level `Signal` values computed during SSR are not serialized. Components that derive UI state directly from `Signal` values (rather than from `AsyncResult.data` or fetch responses) may still experience a flash of default values during hydration. Developers SHOULD use `Suspense` or `ClientOnly` boundaries to manage the transition from SSR-rendered content to browser-reactive content for Signal-derived state. Full `Signal` value transfer is deferred to a future change.

## Non-goals

- **Streaming SSR** — Data transfer happens in a single payload embedded in the HTML. Streaming incremental data is not in scope.
- **Client-to-server data transfer** — This change only transfers data from server to browser. There is no mechanism for the browser to send data back to the server via the payload.
- **Signal persistence across sessions** — The transfer payload is per-page-load; it is not a persistence mechanism like localStorage.
- **Changing `useAsyncResult` API** — `useAsyncResult` remains the same composable API; it transparently benefits from transfer data.
- **Partial hydration** — All transferred data is restored at once during initial hydration. There is no lazy or incremental restoration.
- **Payload compression** — The payload is stored as JSON without compression. Compression can be added in a future change if payload size becomes a concern.
- **Custom transfer keys** — This change uses fetch URLs as keys for `fetches` and component IDs for `async_results`. Custom key strategies are not supported.

## Dependencies

- **Requires** `feat/async-rendering-pipeline` — Async `_render()` is required so the server can fully resolve `AsyncResult` operations before collecting transfer data.
- **Requires** `feat/server-fetch-port-asgi` — `ServerFetchPort` must support self-site fetching via ASGI transport so async components can fetch data during SSR.
- **Requires** `feat/suspense-component` — `Suspense` boundaries enable the server to await async children and include their resolved data in the HTML output and transfer payload.

## Impact

- **Affected modules**: `packages/webcompy/src/webcompy/hydration/` (new), `packages/webcompy-server/src/webcompy_server/_html.py` (payload injection), `packages/webcompy/src/webcompy/aio/_async_result.py` (state restoration), `packages/webcompy/src/webcompy/ports/_browser/_fetch.py` (cache from payload), `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` (response caching), `packages/webcompy/src/webcompy/app/_root_component.py` (data collection and restoration)
- **Breaking**: None — the transfer payload is additive; existing apps without async data fetching work unchanged.
- **Testing**: Unit tests for payload serialization/deserialization, `AsyncResult` state restoration, `BrowserFetchPort` cache hit, and `ServerFetchPort` response caching. E2E tests for full SSR→browser data transfer flow.