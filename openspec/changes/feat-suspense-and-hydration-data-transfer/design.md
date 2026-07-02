# Design: Suspense and Hydration Data Transfer

## Context

WebComPy's async rendering pipeline (`feat/async-rendering-pipeline`) makes the
rendering pipeline fully async, and `feat/async-component-setup` extends it so
component definitions can themselves be `async def`. These foundations enable two
interrelated features that together unlock production-quality SSR/SSG with async data:

1. **Suspense** — A `DynamicElement` that controls when children generators are
   evaluated. Shows fallback while children are loading, swaps to real content when
   complete. In SSR/SSG, `await`s children (with a configurable timeout) so resolved
   data appears in the output HTML. Supports `error_fallback` for the failure case.

2. **Hydration Data Transfer** — A server-to-browser data transfer mechanism.
   `ServerFetchPort` caches self-site responses during SSR, and resolved
   `AsyncResult` states are collected into a `TransferPayload` that is serialized as
   a `<script type="application/json" id="__webcompy_data__">` tag in the HTML.
   During browser hydration, `app.run()` reads the payload, restores
   `AsyncResult` states (so they skip `LOADING`), and populates `BrowserFetchPort`'s
   response cache (so duplicate requests are avoided).

The two features share an **API surface**: `HYDRATION_DATA_KEY` (DI key) and
`has_resolved_data(component_id)` (helper). This design defines that surface
explicitly so Suspense can be implemented on top of the data transfer mechanism
without a circular dependency.

## Goals / Non-Goals

**Goals:**

- Define the shared API surface (`HYDRATION_DATA_KEY`, `has_resolved_data()`,
  `TransferPayload` schema) that both Suspense and Hydration Data Transfer depend on.
- Implement the transfer mechanism: server-side collection, HTML injection, browser
  deserialization, `AsyncResult` and `FetchPort` cache restoration.
- Implement `SuspenseElement` that:
  - Renders `fallback` while children have unresolved async setup.
  - On the server, `await`s the children (with timeout) so resolved data is in the
    SSR output.
  - In the browser, schedules async resolution and swaps fallback for children on
    completion.
  - Renders `error_fallback` if children's async setup raises.
  - Coordinates with `SUSPENSE_RESOLVING_KEY` so child components do not resolve
    their own `_pending_async_template` (Suspense owns it).
- Provide declarative `suspense()` generator function in
  `webcompy/elements/generators.py` matching the `switch()`/`repeat()` API pattern.

**Non-Goals:**

- Streaming SSR (data transfer is a single payload).
- Client-to-server data transfer.
- Signal value restoration (only `AsyncResult` and `FetchPort` cache are
  transferred).
- Payload compression.
- Custom transfer keys (URLs and component IDs only).
- Parallel sibling Suspense gathering (sibling Suspense renders sequentially per
  the `async-rendering` spec).
- Changing `useAsyncResult` API.
- A built-in root-level error boundary.

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Server (SSR / SSG)                                │
│                                                                        │
│  generate_html()                                                       │
│      │                                                                 │
│      ▼                                                                 │
│  AppDocumentRoot._render()                                             │
│      │                                                                 │
│      ▼                                                                 │
│  SuspenseElement._render()                                             │
│      │  provides SUSPENSE_RESOLVING_KEY=True                           │
│      │  collects _pending_async_template coroutines from children      │
│      │  await asyncio.wait_for(gather(*coroutines), timeout=10.0)      │
│      │                                                                 │
│      ▼                                                                 │
│  Component._render()  (skips _pending_async_template resolution)       │
│      │                                                                 │
│      ▼                                                                 │
│  ServerFetchPort.fetch() ─── caches self-site responses                │
│  AsyncResult._execute()  ─── resolves data, transitions to SUCCESS     │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ After render:                                                    │ │
│  │   collect_transfer_data() → TransferPayload                      │ │
│  │   serialize_payload() → HTML-escaped JSON                        │ │
│  │   <script id="__webcompy_data__">{...}</script> appended to body │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
                                │
                                │   HTML response
                                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Browser (PyScript)                                │
│                                                                        │
│  app.run()                                                             │
│      │                                                                 │
│      ▼                                                                 │
│  1. Read <script id="__webcompy_data__"> from DOM                      │
│  2. deserialize_payload() → TransferPayload | None                     │
│  3. browser_fetch_port.populate_from_transfer(payload.fetches)         │
│  4. provide HYDRATION_DATA_KEY → payload.async_results                 │
│  5. Render tree:                                                       │
│       Component._render() reads _pending_async_template                │
│       useAsyncResult checks HYDRATION_DATA_KEY first:                  │
│           if found → AsyncResult._restore_from_transfer() (no fetch)   │
│           if not   → normal PENDING → LOADING → SUCCESS lifecycle      │
│                                                                        │
│  SuspenseElement._hydrate_node()                                       │
│      │  uses has_resolved_data() to decide:                            │
│      │    if True  → immediately render children (data is ready)       │
│      │    if False → keep fallback, schedule async resolution          │
└────────────────────────────────────────────────────────────────────────┘
```

## API Surface (Section 1 — must be implemented first)

This section defines the shared types, keys, and helpers. Both the transfer
mechanism and Suspense depend on these.

### `HYDRATION_DATA_KEY: InjectKey[dict]`

A DI key used to provide the `async_results` section of the transfer payload
during browser initialization. The value is a `dict[str, TransferAsyncResultEntry]`
mapping component ID to its resolved data.

```python
# packages/webcompy/src/webcompy/di/_keys.py
HYDRATION_DATA_KEY: InjectKey[dict[str, Any]] = InjectKey("webcompy-hydration-data")
```

Provisioned in `app.run()` before the first render:
```python
ctx.di_scope.provide(HYDRATION_DATA_KEY, payload.async_results)
```

### `TransferPayload` and friends

```python
# packages/webcompy/src/webcompy/hydration/_payload.py
@dataclass
class TransferFetchEntry:
    status_code: int
    headers: dict[str, str]
    body: str

@dataclass
class TransferAsyncResultEntry:
    state: str  # always "success" in v1
    data: Any

@dataclass
class TransferPayload:
    __webcompy_transfer_version__: int = 1
    fetches: dict[str, TransferFetchEntry]
    async_results: dict[str, TransferAsyncResultEntry]
```

`serialize_payload(payload: TransferPayload) -> str` produces HTML-escaped JSON.
`deserialize_payload(text: str) -> TransferPayload | None` returns `None` on
parse error or version mismatch (forward compatibility).

### `has_resolved_data(component_id: str) -> bool`

```python
# packages/webcompy/src/webcompy/hydration/__init__.py
def has_resolved_data(component_id: str) -> bool:
    """Return True if the transfer payload contains a resolved AsyncResult
    entry for the given component ID, False if not present or payload missing.
    """
    payload = inject(HYDRATION_DATA_KEY, default=None)
    if payload is None:
        return False
    return component_id in payload
```

This is the helper `SuspenseElement._hydrate_node()` calls to decide whether to
immediately render children (data ready) or keep fallback and schedule async
resolution (data not ready).

## Decisions

### D1: JSON in a `<script type="application/json">` tag

The transfer payload is a JSON object embedded in a `<script type="application/json"
id="__webcompy_data__">` tag at the end of `<body>`, before the PyScript bootstrap
`<script>`. The `<script type="application/json">` MIME type is not executed by
browsers; `app.run()` reads it via `DOMPort.query_selector()` and removes it after
parsing. JSON is the universal data format for server-to-client transport; the
payload is HTML-escaped before embedding to prevent XSS.

**Alternatives considered:**
- Inline `<script>` with a JS variable assignment — works but requires careful
  escaping and is less idiomatic.
- Custom element with JSON attribute — harder to parse, not standard.
- Separate JSON file fetched at runtime — adds a network round-trip, defeating
  the purpose.

### D2: Component IDs as keys for `async_results`

Each `AsyncResult` is keyed by `component._tree_path_id`, a per-instance
tree-position identifier. This is stable across SSR and hydration as long as
the component tree is identical (which hydration guarantees).

**Alternatives considered:**
- Async function's qualified name — not unique if the same function is used in
  multiple components.
- Array indices — fragile if the component tree changes between SSR and hydration.
- Hash of the component path — more complex and not obviously better.

### D3: `ServerFetchPort` caches self-site responses for transfer

`ServerFetchPort` maintains an internal response cache keyed by URL (or
`f"{method}:{url}:{body}"` for non-GET). After SSR rendering, the cache contents
are exposed via `get_transfer_data() -> dict[str, TransferFetchEntry]` for
inclusion in the payload. `BrowserFetchPort.populate_from_transfer()` reads the
payload and populates its own cache so matching URLs return without a network
request.

**Rationale:** Caching at the `FetchPort` layer is the most natural
deduplication point. All consumers (`HttpClient`, `useAsyncResult`, direct
`fetch()` calls) benefit automatically.

### D4: `AsyncResult._restore_from_transfer()` bypasses async execution

When a transfer entry matches an `AsyncResult`'s component ID, the
`_restore_from_transfer(data)` method sets `_state` to `SUCCESS`, sets `_data`,
and skips `_execute()`. The `LOADING` state is never entered.

**Rationale:** The data was already resolved on the server. Re-executing the
async function would be wasteful and would show a loading flash. Direct state
restoration is the most efficient path.

### D5: Version field for forward compatibility

The payload includes `__webcompy_transfer_version__: 1`. If the payload format
changes, the version is incremented and the browser deserializer can handle
multiple versions.

### D6: Only include resolved `AsyncResult` states (not PENDING/LOADING/ERROR)

The `async_results` section only includes entries where `_state` is `SUCCESS`.
`PENDING`, `LOADING`, and `ERROR` states are not transferred. `ERROR` could be
transferred in a future change but adds complexity (error types, messages, stack
traces) deferred to a follow-up.

### D7: Suspense as a `DynamicElement`

`SuspenseElement` extends `DynamicElement` (like `SwitchElement` and
`RepeatElement`). A `DynamicElement` has no DOM node of its own — it renders its
children directly into the parent. Suspense needs direct control over when
children generators are evaluated, which is exactly the `DynamicElement`
pattern.

**Alternatives considered:**
- A `Component` wrapping children — would require special rendering hooks and
  doesn't fit the element model well.
- A standalone class outside the element hierarchy — would duplicate rendering
  logic.

### D8: Children as a lazy generator function

The `children` parameter accepts `Callable[[], ChildNode]` (zero-argument
function) that is only called when Suspense is ready to render children. The
`fallback` parameter also accepts `Callable[[], ChildNode]`.

**Rationale:** Lazy evaluation allows Suspense to defer child evaluation until
async setup is ready. This mirrors the `switch()` API where generators are
called conditionally.

### D9: Suspense owns async child resolution via `SUSPENSE_RESOLVING_KEY`

The `feat-async-component-setup` change introduces
`SUSPENSE_RESOLVING_KEY: InjectKey[bool]`. When `True` (provided by
`SuspenseElement._render()`), child `Component._render()` SHALL skip its
`_pending_async_template` resolution block. Suspense collects the coroutines
itself, awaits them via `asyncio.wait_for(..., timeout=...)`, and then resolves
each component's template by calling `__init_component()` directly.

**Rationale:** Suspense is the explicit async boundary; only there does the
framework have license to substitute content for an unresolved async
subtree. The DI key provides this handoff without coupling the components to
Suspense.

### D10: Server waits, browser shows fallback then swaps

- **Server (SSR/SSG)**: `SuspenseElement._render()` `await`s children's async
  operations (with `timeout`, default 10s) before including them in the
  output. If timeout expires, renders `fallback` and logs a warning.
- **Browser**: `SuspenseElement._render()` first renders `fallback`, then
  schedules async child resolution and calls `_resolve()` to swap fallback for
  children using `_patch_children()`.

**Rationale:** Server environments can afford to wait (they generate static
files). Browser environments should show immediate feedback (fallback) and
progressively enhance.

### D11: Sibling Suspense boundaries render sequentially

Multiple `Suspense` siblings render one-by-one via `await`, NOT concurrently.
Within a single `Suspense`, async children resolve concurrently via
`asyncio.gather()`. This matches the `async-rendering` spec's foundational
sibling-rendering rule and avoids the ContextVar isolation / DOM ordering
problems that motivated that decision.

**Alternatives considered:**
- Make `SuspenseElement` intercept and gather the parent's sibling loop —
  requires Suspense to reach outside its own `_render()` into the enclosing
  `ElementWithChildren._render()` loop, or to register sibling-related
  coordination state on the parent. Conflicts with the foundation's explicit
  short-circuit sequential semantics. Rejected.
- Use fire-and-forget render tasks for each sibling — loses serial ordering
  and short-circuit semantics, and makes error capture much harder. Rejected.

### D12: Exception capture scope — Suspense is the only catching boundary

`SuspenseElement._render()` wraps the `await asyncio.gather(*coroutines)` call
in a `try/except`:
- On `Exception`: if `error_fallback` is provided, render `error_fallback` via
  `_patch_children()`; if not, re-raise so the exception propagates per the
  foundation's sequential short-circuit semantics.
- On `asyncio.TimeoutError` separately: render `fallback` and log a warning.

No `try/except` in the foundation's `ElementWithChildren._render()` /
`DynamicElement._refresh()` loops. A failed `await child._render()` propagates
immediately. When a child async setup raises and no enclosing
`SuspenseElement` exists, the exception propagates to the root and is logged
via the `resolve_async` `on_error` hook (default `_log_error`).

**Rationale:** Suspense is the explicit async boundary; only there does the
framework have license to substitute content. Keeping the foundation's loops
free of `try/except` preserves the short-circuit contract.

## API Design

```python
from webcompy.elements import html, Suspense
from webcompy.aio import use_async_result

@define_component
def DataDisplay(context):
    data = use_async_result(lambda: fetch("/api/data"))
    return html.DIV({}, f"Data: {data.value}")

@define_component
def DataPage(context):
    return html.DIV(
        {},
        html.H1({}, "Dashboard"),
        Suspense(
            fallback=html.P({}, "Loading data..."),
            children=lambda: DataDisplay(),
            error_fallback=lambda: html.P({}, "Failed to load data"),
            timeout=10.0,  # server-only
        ),
    )
```

The `Suspense` class is also exported for direct use (matching
`SwitchElement`/`switch` pattern). A user can either write
`Suspense(fallback=..., children=lambda: ...)` or
`suspense(fallback=..., children=lambda: ...)`.

## Rendering Flow

### Server (SSR/SSG)

1. `SuspenseElement._render()` is called.
2. Children generator is invoked. The child `Component.__init__` runs
   synchronously; if the component definition is `async def`, the coroutine
   is stored in `_pending_async_template` (per
   `feat-async-component-setup`).
3. `SuspenseElement._render()` provides `SUSPENSE_RESOLVING_KEY=True` and
   traverses the children subtree, collecting unresolved
   `_pending_async_template` coroutines.
4. `asyncio.wait_for(asyncio.gather(*coroutines), timeout=10.0)` is awaited.
5. On success: each component's template is set and `__init_component()`
   called directly, clearing `_pending_async_template`.
6. On timeout: `fallback` is rendered and a warning is logged.
7. On exception: `error_fallback` is rendered if provided, else the
   exception propagates.

### Browser

1. `SuspenseElement._render()` is called.
2. Children generator is invoked. `useAsyncResult` checks
   `HYDRATION_DATA_KEY` first: if the component ID is in the transfer payload,
   `AsyncResult._restore_from_transfer()` sets state to `SUCCESS` and
   `Component._render()` proceeds normally. Otherwise the coroutine is
   scheduled.
3. If no children are unresolved, children are rendered directly.
4. If children have unresolved async: `fallback` is rendered.
   `SuspenseElement._resolve()` is scheduled as a callback after each
   coroutine completes, calling `_patch_children()` to swap fallback for
   children.

### Browser hydration (`_hydrate_node`)

1. `SuspenseElement._hydrate_node()` checks `has_resolved_data()` for each
   child's component ID.
2. If all children have resolved data: render children directly,
   no fallback in the DOM.
3. If any child lacks resolved data: hydrate as fallback, then schedule
   `_render()` to swap in resolved children once the data arrives.

## File Changes

### New Files

- `packages/webcompy/src/webcompy/elements/types/_suspense.py` —
  `SuspenseElement` class extending `DynamicElement`.
- `packages/webcompy/src/webcompy/hydration/__init__.py` — Public API
  exports, `has_resolved_data()`.
- `packages/webcompy/src/webcompy/hydration/_payload.py` —
  `TransferPayload`, `TransferFetchEntry`, `TransferAsyncResultEntry`,
  `serialize_payload()`, `deserialize_payload()`.
- `packages/webcompy/src/webcompy/hydration/_collect.py` —
  `collect_transfer_data()`.
- `tests/test_hydration_payload.py` — Payload serialization tests.
- `tests/test_server_fetch_cache.py` — `ServerFetchPort` response cache.
- `tests/test_async_result_restore.py` — `AsyncResult` restoration.
- `tests/test_browser_fetch_cache.py` — `BrowserFetchPort` cache from
  payload.
- `tests/test_suspense_element.py` — `SuspenseElement` rendering paths.

### Modified Files

- `packages/webcompy/src/webcompy/elements/generators.py` — Add
  `suspense()` function.
- `packages/webcompy/src/webcompy/elements/__init__.py` — Export
  `Suspense`.
- `packages/webcompy/src/webcompy/components/_component.py` — Add
  async setup tracking integration.
- `packages/webcompy/src/webcompy/aio/_async_result.py` — Add
  `_restore_from_transfer()`.
- `packages/webcompy/src/webcompy/di/_keys.py` — Add
  `HYDRATION_DATA_KEY`.
- `packages/webcompy/src/webcompy/ports/_browser/_fetch.py` — Add
  response cache, `populate_from_transfer()`.
- `packages/webcompy-server/src/webcompy_server/ports/_fetch.py` — Add
  response cache, `get_transfer_data()`, `clear_cache()`.
- `packages/webcompy-server/src/webcompy_server/_html.py` — Inject
  payload `<script>` tag.
- `packages/webcompy/src/webcompy/app/_app.py` — Read payload during
  `app.run()`, provide via DI, populate `BrowserFetchPort`.
- `packages/webcompy/src/webcompy/app/_root_component.py` — Collect
  transfer data after SSR.

## Risks / Trade-offs

- **Payload size** — For applications that fetch large amounts of data, the
  payload could significantly increase HTML size. → Mitigation: only
  resolved data is included. Compression is a future change.
- **Stale data** — If the server caches are warmed from a previous request,
  transferred data may be stale. → Mitigation: This is acceptable for SSG.
  For dynamic SSR, data is always fresh from the current render. No caching
  across requests is involved.
- **XSS via payload injection** — A malicious actor could inject content.
  → Mitigation: payload is JSON-serialized and HTML-escaped before embedding.
- **Component ID stability** — IDs must match between SSR and hydration.
  → Mitigation: IDs are derived from the component tree structure. As long
  as the same tree is rendered, IDs match.
- **Suspense exception path** — If a child setup raises and there's no
  `error_fallback` and no enclosing Suspense, the exception propagates to
  the root and is logged via the root's `on_error` hook. Users see a logged
  error, not user-visible fallback. This is by design: a developer must
  explicitly choose `error_fallback` or wrap the failure in another
  Suspense.
- **Payload deserialization failure** — If JSON parse fails or version
  mismatch, the browser falls back to the normal `PENDING → LOADING →
  SUCCESS` lifecycle. The transfer is best-effort.
- **Concurrent async gather in nested Suspense** — A nested `Suspense` may
  contain its own `gather` of async children. The awaits compose naturally;
  no deadlock risk because each `gather` runs in the same event loop with
  independent coroutines.

## Open Questions

1. Should `ERROR` state `AsyncResult` entries be transferred? (Current
   decision: no, only `SUCCESS`. Can be added later.)
2. Should the payload be placed in `<head>` or at the end of `<body>`?
   (Current decision: end of `<body>`, before the PyScript bootstrap
   `<script>`, so it doesn't block initial HTML parsing.)
3. Should `timeout` also apply to the browser-side async resolution? (Current
   decision: no — the browser does not wait, it shows fallback and resolves
   in the background. `timeout` is server-only.)
4. Future: Signal value restoration — Signal values (non-AsyncResult) are
   NOT transferred. Only `AsyncResult` and `FetchPort` responses. Signal
   value restoration can be added as a follow-up.
