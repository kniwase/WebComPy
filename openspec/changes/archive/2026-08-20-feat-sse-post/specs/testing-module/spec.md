# Testing Module (delta)

## ADDED Requirements

### Requirement: FakeFetchPort shall implement stream with scripted chunks

`FakeFetchPort` SHALL implement `stream(url, *, method="GET", headers=None, body=None)` returning a `FetchStream` whose `status_code`, `headers`, and `ok` are those of the canned response matched by the existing `(method, url)` response key, and whose iteration yields a scripted sequence of chunks in order. The constructor SHALL accept an optional `streams` parameter — a `dict` mapping `(method, url)` tuples to `list[str]` chunks. When a scripted stream is registered for the key, `stream()` SHALL yield exactly those chunks in order and then finish. When no scripted stream is registered but a canned `Response` is registered for the key, `stream()` SHALL yield the canned response body text as a single chunk. When neither is registered, `stream()` SHALL raise `KeyError` listing available keys, matching the existing `fetch()` behavior. `close()` SHALL be idempotent and SHALL record that the stream was aborted, and subsequent iteration SHALL finish.

#### Scenario: Scripted chunks are yielded in order

- **WHEN** `FakeFetchPort(streams={("GET", "/s"): ["a", "b"]}).stream("/s")` is iterated
- **THEN** the iterator SHALL yield `"a"` then `"b"` and then finish

#### Scenario: Canned response degrades to a single chunk

- **WHEN** `FakeFetchPort(responses={("GET", "/s"): Response(text="xyz", ...)}).stream("/s")` is iterated
- **THEN** the iterator SHALL yield exactly one chunk equal to `"xyz"`

#### Scenario: Unregistered stream raises KeyError

- **WHEN** `FakeFetchPort().stream("/unknown")` is called
- **THEN** a `KeyError` SHALL be raised

#### Scenario: close records the abort

- **WHEN** `close()` is called on a `FakeFetchPort` `FetchStream`
- **THEN** the abort SHALL be recorded for later assertion
- **AND** subsequent iteration SHALL finish without yielding further chunks

## Notes

### Note: Fetch-based realtime connections never finish their scheduled pump

The fetch-based SSE transport (`use_event_source` with a non-GET method) schedules a pump coroutine that only ends when the connection is closed. When such a composable is used in a test whose DI scope provides `FakeAsyncSchedulerPort`, `drain()` / `await_pending()` execute collected coroutines and await their completion — the never-ending pump SHALL therefore keep the drain blocked until the connection is closed. Tests exercising the fetch-based SSE path SHALL either run the pump on a real event loop (e.g. an `asyncio`-based test without the fake scheduler, or the fallback path) or close the connection before draining. This mirrors the existing WebSocket reconnection coroutine behavior.
