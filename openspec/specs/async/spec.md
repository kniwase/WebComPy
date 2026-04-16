# Async Utilities and HTTP Client

## Overview

WebComPy provides async utilities (`AsyncComputed`, `AsyncWrapper`) integrated with the reactive system, and an HTTP client (`HttpClient`) that uses the browser Fetch API.

## Async Module (`webcompy/aio/`)

### resolve_async()

- Takes a coroutine, optional `on_done` callback, optional `on_error` callback
- Runs via `asyncio.run()` (standard Python) or `asyncio.get_event_loop().run_until_complete()` (PyScript/Emscripten)
- Error reporting filters out stack frames from the webcompy package itself using regex matching

### AsyncWrapper[T]

- Decorator factory that wraps an async callable
- When called, runs the coroutine via `resolve_async()` with optional `resolver` and `error` callbacks
- Returns `None` (fire-and-forget pattern)

### AsyncComputed[T]

- Extends `ReactiveBase[T | None]` — integrated with the reactive system
- Constructed with a coroutine
- `_value` is initialized to `None`
- `resolve_async(coroutine, self._resolver, self._error)` is called on construction
- **`_resolver(res: T)`**: Decorated with `_change_event`, sets `_done = True`, `_value = res`
- **`_error(err: Exception)`**: Decorated with `_change_event`, sets `_done = False`, `_exception = err`
- **`value`** property: decorated with `_get_evnet` for dependency tracking
- **`error`** property: decorated with `_get_evnet`, returns `Exception | None`
- **`done`** property: decorated with `_get_evnet`, returns `bool`

### Design Constraints (Async)

- `AsyncComputed.value` is `T | None` — no way to distinguish "not yet resolved" from "resolved to None" without checking `done`
- `_error` sets `_done = False` rather than a separate error state — this means error recovery sets done back to False
- Stack trace filtering removes webcompy-internal frames for cleaner error messages

## HTTP Client (`webcompy/ajax/`)

### HttpClient

- Async HTTP client using `browser.fetch()` (browser-only; raises `WebComPyHttpClientException` otherwise)
- **Static methods**: `get()`, `head()`, `options()`, `post()`, `put()`, `patch()`, `delete()`
- All delegate to `HttpClient.request()` with method-specific parameters

### HttpClient.request()

- Parameters: `method`, `url`, `headers`, `query_params`, `json`, `body_data`, `form_data`, `form_element`
- URL construction: appends query string if `query_params` provided
- Headers are URL-encoded via `urllib.parse.quote`
- Body handling:
  - `json`: Sets `Content-Type: application/json`, serializes via `json_dumps`
  - `body_data`: Used directly as body
  - `form_data`: Creates `browser.FormData.new()` and calls `.set()` for each key-value pair
  - `form_element`: Creates `browser.FormData.new(form_element.node)` from a DomNodeRef
- Headers are proxied via `browser.pyscript.ffi.create_proxy()` and `.destroy()`ed in `finally`
- Returns a `Response` object

### Response

- Properties: `text`, `headers`, `status_code`, `ok`
- Methods: `json()` (parses response text via `json_loads`), `raise_for_status()` (raises `WebComPyHttpClientException` if not ok)

### Design Constraints (Ajax)

- Only works in browser environment — server-side usage raises exception
- `form_element` parameter takes a `DomNodeRef` to access the actual DOM form node
- No request timeout configuration
- No response streaming support