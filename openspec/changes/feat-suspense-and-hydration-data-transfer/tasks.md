# Tasks: Suspense and Hydration Data Transfer

> This change merges `feat-suspense-component` and `feat-hydration-data-transfer` into a
> single integrated change to resolve the circular dependency between them. The work is
> organized into nine sections: **API surface first**, then the transfer mechanism, then
> Suspense on top of the API.

## Section 1: API Surface (HYDRATION_DATA_KEY, has_resolved_data, TransferPayload)

> **Critical: must be implemented first.** Both the transfer mechanism (Sections 2–6) and
> Suspense (Section 7) depend on this API. Implementing the API first breaks the circular
> dependency between the original two changes.

- [ ] 1.1 Create `packages/webcompy/src/webcompy/hydration/__init__.py` with public API
      exports and the `has_resolved_data()` helper.
- [ ] 1.2 Create `packages/webcompy/src/webcompy/hydration/_payload.py` with
      `TransferPayload`, `TransferFetchEntry`, `TransferAsyncResultEntry`,
      `serialize_payload()` and `deserialize_payload()`.
- [ ] 1.3 Create `packages/webcompy/src/webcompy/hydration/_collect.py` with
      `collect_transfer_data()` — gathers `AsyncResult` states and `FetchPort` cache.
- [ ] 1.4 Add `HYDRATION_DATA_KEY: InjectKey[dict[str, Any]]` to
      `packages/webcompy/src/webcompy/di/_keys.py` and export from
      `packages/webcompy/src/webcompy/di/__init__.py`.
- [ ] 1.5 Define the payload schema as a JSON object:
      `{"__webcompy_transfer_version__": 1, "fetches": {...}, "async_results": {...}}`.
- [ ] 1.6 `serialize_payload()` produces HTML-escaped JSON.
- [ ] 1.7 `deserialize_payload()` returns `TransferPayload | None` — `None` on parse
      error or unknown version.

## Section 2: ServerFetchPort Response Cache

- [ ] 2.1 Add `_response_cache: dict[str, Response]` to
      `packages/webcompy-server/src/webcompy_server/ports/_fetch.py:ServerFetchPort.__init__()`.
- [ ] 2.2 In `ServerFetchPort.fetch()`, after a successful self-site request, cache the
      response keyed by URL (GET) or `f"{method}:{url}:{body}"` (non-GET).
- [ ] 2.3 On cache hit, return the cached response without making a network request.
- [ ] 2.4 Add `get_transfer_data() -> dict[str, TransferFetchEntry]` that returns
      cache contents in transfer payload format (excluding external URL responses).
- [ ] 2.5 Add `clear_cache()` for cleanup between SSR renders.
- [ ] 2.6 Add `is_self_site_url()` to `FetchPort` ABC in
      `packages/webcompy/src/webcompy/ports/_fetch.py` (this may already exist from
      `feat/server-fetch-port-asgi`).

## Section 3: AsyncResult State Restoration

- [ ] 3.1 In `packages/webcompy/src/webcompy/aio/_async_result.py`, add
      `_restore_from_transfer(data: Any)` method to `AsyncResult`:
      - Sets `_state.value` to `SUCCESS`
      - Sets `_data.value` to `data`
      - Sets `_error.value` to `None`
      - Skips `_execute()` — the async function is never called.
- [ ] 3.2 Modify `use_async_result` (in `packages/webcompy/src/webcompy/aio/`) to check
      the transfer payload via `HYDRATION_DATA_KEY` before scheduling async execution:
      - If the component ID is found in `async_results` with `state == "success"`, call
        `_restore_from_transfer(data)`.
      - If not found, proceed with normal `PENDING → LOADING → SUCCESS/ERROR` lifecycle.
- [ ] 3.3 Ensure the transfer payload lookup uses `inject(HYDRATION_DATA_KEY, default={})`
      so absence of the key is handled gracefully (no transfer = normal lifecycle).

## Section 4: BrowserFetchPort Cache Population

- [ ] 4.1 Add `_response_cache: dict[str, Response]` to
      `packages/webcompy/src/webcompy/ports/_browser/_fetch.py:BrowserFetchPort.__init__()`.
- [ ] 4.2 Add `populate_from_transfer(data: dict[str, TransferFetchEntry])` method that
      converts transfer entries into `Response` objects and stores them.
- [ ] 4.3 In `BrowserFetchPort.fetch()`, check `_response_cache` for matching URL before
      making a network request. On hit, return the cached `Response` without calling
      `browser.fetch()`.
- [ ] 4.4 Add a key generation helper that matches `ServerFetchPort`'s format for
      non-GET requests (method + URL + body).

## Section 5: HTML Payload Injection

- [ ] 5.1 In `packages/webcompy/src/webcompy/app/_root_component.py` (or
      `WebComPyApp`), add `_collect_transfer_data() -> TransferPayload`:
      - Retrieve `ServerFetchPort` from DI scope.
      - Call `server_fetch_port.get_transfer_data()`.
      - Iterate over `ComponentStore.components` to find `AsyncResult` instances in
        `SUCCESS` state with a `component_id` matching the instance's
        `_tree_path_id`.
      - Return the combined `TransferPayload`.
- [ ] 5.2 In `packages/webcompy-server/src/webcompy_server/_html.py:generate_html()`,
      after rendering the app root:
      - Call `app._collect_transfer_data()` (or accept it as a parameter).
      - Serialize using `serialize_payload()`.
      - Create `<script type="application/json" id="__webcompy_data__">{escaped}</script>`.
      - Insert it before the PyScript bootstrap `<script>` tag.
- [ ] 5.3 If `generate_html()` is called without an app (e.g., `prerender=False`),
      inject an empty payload (or omit the script tag entirely).

## Section 6: Browser Initialization Restore

- [ ] 6.1 In `packages/webcompy/src/webcompy/app/_app.py:app.run()`, before the first
      render:
      - Locate the `<script type="application/json" id="__webcompy_data__">` element in
        the DOM.
      - Parse its content using `deserialize_payload()`.
      - If the payload is valid:
        - Call `browser_fetch_port.populate_from_transfer(payload.fetches)`.
        - Provide `payload.async_results` via DI using `HYDRATION_DATA_KEY` in the root
          DI scope.
      - If the payload is missing or invalid, proceed with an empty payload.
- [ ] 6.2 Remove the `<script>` element from the DOM after reading to free memory.
- [ ] 6.3 After all component restorations, clear the `async_results` reference to
      allow garbage collection of the payload.

## Section 7: SuspenseElement Implementation

> Depends on `feat-async-component-setup` (`_pending_async_template`, `SUSPENSE_RESOLVING_KEY`).

- [ ] 7.1 Create `packages/webcompy/src/webcompy/elements/types/_suspense.py` with
      `SuspenseElement` class extending `DynamicElement`.
- [ ] 7.2 Implement `__init__` accepting `fallback`, `children`, `error_fallback`, and
      `timeout` parameters.
- [ ] 7.3 Implement `_on_set_parent()` — no signal subscriptions needed.
- [ ] 7.4 Implement `_render()`:
      - Provide `SUSPENSE_RESOLVING_KEY=True` via the DI scope.
      - Invoke children generator; collect unresolved
        `_pending_async_template` coroutines from the children subtree.
      - **Server (SSR/SSG)**: `await asyncio.wait_for(asyncio.gather(*coroutines),
        timeout=timeout)`. On success, set each component's template and call
        `__init_component()`. On timeout, render `fallback` and log a warning. On
        exception, render `error_fallback` if provided, else re-raise.
      - **Browser (PyScript)**: render `fallback` first, then schedule async child
        resolution. On completion, call `_resolve()` to swap fallback for children.
- [ ] 7.5 Implement `_resolve()` — replaces fallback with children using
      `_patch_children()`.
- [ ] 7.6 Implement `_handle_error()` — renders `error_fallback` if provided, otherwise
      keeps fallback and logs a warning.
- [ ] 7.7 Implement `_remove_element()` with proper cleanup of pending async tasks and
      any registered callbacks.
- [ ] 7.8 Implement `_hydrate_node()`:
      - If `has_resolved_data(component_id)` is True for all children: render children
        directly (no fallback in DOM).
      - If any child lacks resolved data: hydrate as fallback, then schedule
        `_render()` to swap in resolved children.
- [ ] 7.9 Add `suspense()` function to
      `packages/webcompy/src/webcompy/elements/generators.py` with parameters
      `fallback`, `children`, `error_fallback=None`, `timeout=10.0`.
- [ ] 7.10 Export `Suspense` from `packages/webcompy/src/webcompy/elements/__init__.py`.

## Section 8: Tests

### Unit Tests

- [ ] 8.1 `tests/test_hydration_payload.py` — `TransferPayload` serialization:
      - Valid payload with fetches and async_results
      - Empty payload (no data)
      - Payload with non-serializable data (excluded with warning)
      - HTML escaping of special characters
      - Unknown version rejection
      - Malformed JSON handling
- [ ] 8.2 `tests/test_server_fetch_cache.py` — `ServerFetchPort` response caching:
      - Cache population on self-site GET request
      - Cache hit returns cached response
      - Cache miss makes network request
      - Non-GET request cache key includes method and body
      - External URLs are not cached
      - `get_transfer_data()` returns correct format
      - `clear_cache()` empties the cache
- [ ] 8.3 `tests/test_async_result_restore.py` — `AsyncResult._restore_from_transfer()`:
      - Restoration sets state to SUCCESS with correct data
      - `is_success` and `is_loading` computed values are correct
      - Async function is NOT called after restoration
      - Missing component ID falls through to normal lifecycle
- [ ] 8.4 `tests/test_browser_fetch_cache.py` — `BrowserFetchPort` cache population:
      - `populate_from_transfer()` creates `Response` objects from payload data
      - `fetch()` returns cached response without network request
      - `fetch()` makes network request for non-cached URLs
      - Cache persists across multiple fetches
- [ ] 8.5 `tests/test_suspense_element.py` — `SuspenseElement`:
      - Sync children render immediately without fallback
      - Fallback is shown when async children are pending
      - Children replace fallback when async completes (browser path)
      - Server-side awaiting with successful resolution
      - Server-side timeout falls back to fallback content
      - Error fallback rendering on async failure
      - When an async child setup raises and `error_fallback` is provided, the error
        fallback is rendered in place; pending async state is cleared and no other
        async tasks leak.
      - When an async child setup raises and NO `error_fallback` is provided, the
        exception propagates out of `SuspenseElement._render()` and is NOT swallowed
        (logged by the root render `on_error` hook in tests via a captured logger).
      - When a sibling Suspense raises, a non-enclosing sibling element's render is
        unaffected — short-circuit semantics (the exception propagates per foundation
        "One child raises during sibling rendering" without
        `ElementWithChildren._render()` wrapping it in `try/except`).
      - Cleanup on element removal (pending tasks cancelled)
      - `suspense()` generator function creates correct `SuspenseElement`

### E2E Tests

- [ ] 8.6 E2E test: SSG output contains the `__webcompy_data__` script tag with
      resolved data.
- [ ] 8.7 E2E test: browser hydration reads the payload and restores `AsyncResult`
      states.
- [ ] 8.8 E2E test: browser-side `FetchPort.fetch()` returns cached responses from the
      payload.
- [ ] 8.9 E2E test: components with transferred `AsyncResult` data skip the loading
      phase.
- [ ] 8.10 E2E test: components not in the payload follow the normal async lifecycle.
- [ ] 8.11 E2E test: the payload is removed from the DOM after reading.
- [ ] 8.12 E2E test: full SSR with async data → SSG output with payload → browser
      hydration with restored state.

## Section 9: Spec Updates and Documentation

- [ ] 9.1 Create `openspec/changes/feat-suspense-and-hydration-data-transfer/specs/suspense/spec.md`
      (delta spec) — document the `suspense` capability, `SuspenseElement`, `suspense()`
      generator function, `SUSPENSE_RESOLVING_KEY` (owned by
      `feat-async-component-setup`, referenced here), exception semantics, and
      sequential sibling rendering.
- [ ] 9.2 Create `openspec/changes/feat-suspense-and-hydration-data-transfer/specs/hydration-data-transfer/spec.md`
      (delta spec) — document the `hydration-data-transfer` capability, payload
      schema, `HYDRATION_DATA_KEY`, `has_resolved_data()`, `TransferPayload`, and the
      server/browser integration flow.
- [ ] 9.3 Update `openspec/specs/async/spec.md` to mention `Suspense` as a
      complementary approach to `use_async_result`.
- [ ] 9.4 Update `openspec/specs/elements/spec.md` to reference the `Suspense` element
      type.
- [ ] 9.5 Update `openspec/specs/async-rendering/spec.md` to note the
      `SUSPENSE_RESOLVING_KEY` contract and sequential sibling Suspense rendering.
- [ ] 9.6 Update `.opencode/agents/ci-review.md` file→spec mapping to include
      `packages/webcompy/src/webcompy/elements/types/_suspense.py` → `suspense` spec
      and `packages/webcompy/src/webcompy/hydration/` → `hydration-data-transfer`
      spec.
- [ ] 9.7 Update `docs_app/` to add a Suspense demo page (stretch goal — can be
      deferred if the docs_app sample is too large).

## Section 10: Verification

- [ ] 10.1 `npx @fission-ai/openspec@latest validate --specs` — all specs pass.
- [ ] 10.2 `npx @fission-ai/openspec@latest validate --changes` — this change passes.
- [ ] 10.3 `uv run ruff check .` — no errors.
- [ ] 10.4 `uv run ruff format .` — no changes.
- [ ] 10.5 `uv run pyright` — 0 errors.
- [ ] 10.6 `uv run python -m pytest tests/ --tb=short --ignore=tests/e2e --ignore=tests/e2e_docs`
      — all unit tests pass.
- [ ] 10.7 `uv run python -m webcompy generate --app docs_app.bootstrap:app` — SSG
      completes; generated HTML contains the `__webcompy_data__` script tag.
- [ ] 10.8 `scripts/run-e2e-tests.sh --serving-mode=static` — all 14 E2E groups
      pass.
