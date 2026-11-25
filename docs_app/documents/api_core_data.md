---
title: Data, Forms & i18n API
description: API reference for webcompy.ajax, webcompy.aio, webcompy.forms, webcompy.storage, webcompy.events, webcompy.resources, webcompy.realtime, and webcompy.i18n.
---

# Data, Forms & i18n API

<!-- author:start:intro -->
API reference for data-layer modules: HTTP fetching (`webcompy.ajax`), async helpers and streams (`webcompy.aio`), embedded resources (`webcompy.resources`), forms and validators (`webcompy.forms`), browser storage (`webcompy.storage`), document events (`webcompy.events`), typed realtime (`webcompy.realtime`), and internationalization (`webcompy.i18n`).
<!-- author:end:intro -->

<!-- generated:start -->

## HTTP, Async & Resources

### AsyncResult

```python
class AsyncResult(Generic[T]):
    def __init__(
        self,
        func: Callable[[], Coroutine[Any, Any, T]],
        default: T | None = _MISSING,
    ) -> None
```

Key: `webcompy.aio._async_result:AsyncResult` · Exports: `from webcompy.aio import AsyncResult`

Reactive holder exposing the state and outcome of an async operation.

The operation function is not launched automatically: call `refetch` to run it. `state`, `data`, and `error` are signals tracking the outcome, and `is_pending`, `is_loading`, `is_success`, and `is_error` are `Computed[bool]` conveniences derived from `state`.

**Args:**

- `func`: Zero-argument coroutine factory producing the value.
- `default`: Initial value of `data` before the first successful run.

**Attributes:**

- `state`: `Signal[AsyncState]` holding the current lifecycle state.
- `data`: `Signal[T | None]` holding the latest successfully produced value, or `None` before the first success.
- `error`: `Signal[Exception | None]` holding the exception from the last failed run, or `None` after a success.
- `is_pending`: `Computed[bool]` — true while no run has started.
- `is_loading`: `Computed[bool]` — true while a run is in flight.
- `is_success`: `Computed[bool]` — true when the last run succeeded.
- `is_error`: `Computed[bool]` — true when the last run failed.

#### Members

**`data`** (property)

```python
@property
def data(self) -> Signal[T | None]
```

The latest successfully produced value.

**Returns:** A signal holding the value, or `None` before the first success.

**`error`** (property)

```python
@property
def error(self) -> Signal[Exception | None]
```

The exception from the last failed run.

**Returns:** A signal holding the exception, or `None` when the last run succeeded.

**`refetch`** (method)

```python
def refetch(self, *_: Any) -> None
```

Run the operation function and move `state` to `LOADING`.

**Args:**

- `*_`: Any positional arguments are ignored; the signature accepts them so this method can be wired directly to signal-driven callback sites.

**`state`** (property)

```python
@property
def state(self) -> Signal[AsyncState]
```

The current `AsyncState`.

**Returns:** A signal holding the current lifecycle state.

### AsyncState

```python
class AsyncState(Enum)
```

Key: `webcompy.aio._async_result:AsyncState` · Exports: `from webcompy.aio import AsyncState`

Lifecycle stages of an `AsyncResult`.

`PENDING` before the first run, `LOADING` while running, and `SUCCESS` or `ERROR` after the operation settles.

### AsyncWrapper

```python
class AsyncWrapper(Generic[T]):
    def __init__(
        self,
        resolver: Callable[[T], Any] | None = None,
        error: Callable[[Exception], Any] | None = _log_error,
    ) -> None
```

Key: `webcompy.aio._aio:AsyncWrapper` · Exports: `from webcompy.aio import AsyncWrapper`

Wrap an async callable to run fire-and-forget when invoked.

Calling the wrapped callable schedules the produced coroutine through `aio_run` and resolves it through the configured callbacks.

**Args:**

- `resolver`: Called with the resolved value on success.
- `error`: Called with the exception on failure. Defaults to logging the error.

**Attributes:**

- `resolver`: Success callback invoked with the resolved value, or `None` when no callback was supplied.
- `error`: Failure callback invoked with the raised exception.

### from_json

```python
def from_json(
    cls: type[T],
    data: Any,
    *,
    strict: bool = False,
    meta: Mapping[str, str] | None = None,
) -> T
```

Key: `webcompy.ajax._serde:from_json` · Exports: `from webcompy.ajax import from_json`

Deserialize `data` into an instance of the annotated type `cls`.

Converts plain JSON values into dataclass, enum, container, and scalar types declared by the target's annotations. `meta` carries transfer metadata (e.g. custom type tags) applied to `data` before conversion.

**Args:**

- `cls`: Target type, typically a dataclass.
- `data`: JSON-parsed value to convert.
- `strict`: When `True`, reject unknown fields instead of ignoring them.
- `meta`: Optional transfer metadata mapping applied to `data` beforehand.

**Returns:** An instance of `cls` produced from `data`.

### HttpClient

```python
class HttpClient
```

Key: `webcompy.ajax._fetch:HttpClient` · Exports: `from webcompy.ajax import HttpClient`

Static HTTP client whose requests are routed through the `FetchPort`.

All operations are classmethods returning a `Response`, or a typed value when `response_type` is given.

#### Members

**`delete`** (async_method)

```python
@classmethod
async def delete(
    cls,
    url: str,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    body_data: str | bytes | None = None,
    form_data: dict[str, str | bytes] | None = None,
    form_element: DomNodeRef | None = None,
    *,
    response_type: type[T] | None = None,
) -> Response | T
```

Send a DELETE request.

**Args:**

- `url`: Request URL.
- `headers`: Request headers as a `{name: value}` mapping.
- `query_params`: Query parameters appended to the URL.
- `json`: JSON object serialized as the request body.
- `body_data`: Raw `str` or `bytes` request body.
- `form_data`: Multipart form fields encoded and sent through the fetch port.
- `form_element`: A form DOM node whose fields are submitted (browser only).
- `response_type`: When given, deserialize the JSON response body as this type instead of returning a `Response`.

**Returns:** The `Response`, or the typed value when `response_type` is given.

**`get`** (async_method)

```python
@classmethod
async def get(
    cls,
    url: str,
    query_params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    *,
    response_type: type[T] | None = None,
) -> Response | T
```

Send a GET request.

**Args:**

- `url`: Request URL.
- `query_params`: Query parameters appended to the URL.
- `headers`: Request headers as a `{name: value}` mapping.
- `response_type`: When given, deserialize the JSON response body as this type instead of returning a `Response`.

**Returns:** The `Response`, or the typed value when `response_type` is given.

**`head`** (async_method)

```python
@classmethod
async def head(
    cls,
    url: str,
    query_params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    *,
    response_type: type[T] | None = None,
) -> Response | T
```

Send a HEAD request.

**Args:**

- `url`: Request URL.
- `query_params`: Query parameters appended to the URL.
- `headers`: Request headers as a `{name: value}` mapping.
- `response_type`: When given, deserialize the JSON response body as this type instead of returning a `Response`.

**Returns:** The `Response`, or the typed value when `response_type` is given.

**`options`** (async_method)

```python
@classmethod
async def options(
    cls,
    url: str,
    query_params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    *,
    response_type: type[T] | None = None,
) -> Response | T
```

Send an OPTIONS request.

**Args:**

- `url`: Request URL.
- `query_params`: Query parameters appended to the URL.
- `headers`: Request headers as a `{name: value}` mapping.
- `response_type`: When given, deserialize the JSON response body as this type instead of returning a `Response`.

**Returns:** The `Response`, or the typed value when `response_type` is given.

**`patch`** (async_method)

```python
@classmethod
async def patch(
    cls,
    url: str,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    body_data: str | bytes | None = None,
    form_data: dict[str, str | bytes] | None = None,
    form_element: DomNodeRef | None = None,
    *,
    response_type: type[T] | None = None,
) -> Response | T
```

Send a PATCH request.

**Args:**

- `url`: Request URL.
- `headers`: Request headers as a `{name: value}` mapping.
- `query_params`: Query parameters appended to the URL.
- `json`: JSON object serialized as the request body.
- `body_data`: Raw `str` or `bytes` request body.
- `form_data`: Multipart form fields encoded and sent through the fetch port.
- `form_element`: A form DOM node whose fields are submitted (browser only).
- `response_type`: When given, deserialize the JSON response body as this type instead of returning a `Response`.

**Returns:** The `Response`, or the typed value when `response_type` is given.

**`post`** (async_method)

```python
@classmethod
async def post(
    cls,
    url: str,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    body_data: str | bytes | None = None,
    form_data: dict[str, str | bytes] | None = None,
    form_element: DomNodeRef | None = None,
    *,
    response_type: type[T] | None = None,
) -> Response | T
```

Send a POST request.

**Args:**

- `url`: Request URL.
- `headers`: Request headers as a `{name: value}` mapping.
- `query_params`: Query parameters appended to the URL.
- `json`: JSON object serialized as the request body.
- `body_data`: Raw `str` or `bytes` request body.
- `form_data`: Multipart form fields encoded and sent through the fetch port.
- `form_element`: A form DOM node whose fields are submitted (browser only).
- `response_type`: When given, deserialize the JSON response body as this type instead of returning a `Response`.

**Returns:** The `Response`, or the typed value when `response_type` is given.

**`put`** (async_method)

```python
@classmethod
async def put(
    cls,
    url: str,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    body_data: str | bytes | None = None,
    form_data: dict[str, str | bytes] | None = None,
    form_element: DomNodeRef | None = None,
    *,
    response_type: type[T] | None = None,
) -> Response | T
```

Send a PUT request.

**Args:**

- `url`: Request URL.
- `headers`: Request headers as a `{name: value}` mapping.
- `query_params`: Query parameters appended to the URL.
- `json`: JSON object serialized as the request body.
- `body_data`: Raw `str` or `bytes` request body.
- `form_data`: Multipart form fields encoded and sent through the fetch port.
- `form_element`: A form DOM node whose fields are submitted (browser only).
- `response_type`: When given, deserialize the JSON response body as this type instead of returning a `Response`.

**Returns:** The `Response`, or the typed value when `response_type` is given.

**`request`** (async_method)

```python
@classmethod
async def request(
    cls,
    method: Literal['GET', 'OPTIONS', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'],
    url: str,
    headers: dict[str, str] | None = None,
    query_params: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    body_data: str | bytes | None = None,
    form_data: dict[str, str | bytes] | None = None,
    form_element: DomNodeRef | None = None,
) -> Response
```

Send a raw HTTP request and return the response.

**Args:**

- `method`: HTTP method to use.
- `url`: Request URL.
- `headers`: Request headers as a `{name: value}` mapping. An explicit `Content-Type` always wins over the auto-generated value.
- `query_params`: Query parameters appended to the URL.
- `json`: JSON object serialized as the request body.
- `body_data`: Raw `str` or `bytes` request body.
- `form_data`: Multipart form fields encoded and sent through the fetch port. The body is always encoded with an auto-generated boundary; an explicit `multipart/form-data; boundary=...` header is passed through unchanged and therefore does not match the encoded body. Callers that need a custom boundary must build the body themselves and send it via `body_data`.
- `form_element`: A form DOM node whose fields are submitted (browser only).

**Returns:** The parsed `Response`.

**Raises:**

- `WebComPyHttpClientException`: If the request cannot be dispatched.

### load_bytes

```python
async def load_bytes(source: str | Path) -> bytes
```

Key: `webcompy.resources:load_bytes` · Exports: `from webcompy import load_bytes`

Load a binary resource from the app package.

Resolves `source` relative to the application package root and delegates to the active `ResourcePort`.

**Args:**

- `source`: Resource path as a string or relative `Path`; absolute paths and `..` segments are rejected.

**Returns:** The raw bytes of the resource.

**Raises:**

- `WebComPyException`: If `source` is absolute, contains `..`, has an unsupported type, or no `ResourcePort` is available in the current DI scope.

### load_text

```python
async def load_text(source: str | Path) -> str
```

Key: `webcompy.resources:load_text` · Exports: `from webcompy import load_text`

Load a text resource from the app package.

Resolves `source` relative to the application package root and delegates to the active `ResourcePort`.

**Args:**

- `source`: Resource path as a string or relative `Path`; absolute paths and `..` segments are rejected.

**Returns:** The decoded text content of the resource.

**Raises:**

- `WebComPyException`: If `source` is absolute, contains `..`, has an unsupported type, or no `ResourcePort` is available in the current DI scope.

### resolve_async

```python
def resolve_async(
    coroutine: Coroutine[Any, Any, T],
    on_done: Callable[[T], Any] | None = None,
    on_error: Callable[[Exception], Any] | None = _log_error,
)
```

Key: `webcompy.aio._aio:resolve_async` · Exports: `from webcompy.aio import resolve_async`

Schedule a coroutine and invoke callbacks when it settles.

**Args:**

- `coroutine`: Coroutine to run.
- `on_done`: Called with the resolved value when the coroutine succeeds.
- `on_error`: Called with the exception when the coroutine fails. Defaults to logging the error.

### Response

```python
class Response:
    def __init__(
        self,
        text: str,
        headers: dict[str, str],
        status_code: int,
        reason: str,
        ok: bool,
    ) -> None
```

Key: `webcompy.ajax._fetch:Response` · Exports: `from webcompy.ajax import Response`

An HTTP response returned by `HttpClient`.

**Args:**

- `text`: Response body as decoded text.
- `headers`: Response headers as a `{name: value}` mapping.
- `status_code`: HTTP status code.
- `reason`: Human-readable HTTP status text.
- `ok`: Whether the status code is in the success range.

**Attributes:**

- `text`: Response body as decoded text.
- `headers`: Response headers as a `{name: value}` mapping.
- `status_code`: HTTP status code.
- `ok`: Whether the status code is in the success range.

#### Members

**`headers`** (property)

```python
@property
def headers(self)
```

The response headers.

**Returns:** A `{name: value}` mapping of the response headers.

**`json`** (method)

```python
def json(self, **kwargs: Any) -> dict[str, Any]
```

Parse the response body as a JSON object.

**Args:**

- `**kwargs`: Keyword arguments forwarded to `json.loads`.

**Returns:** The parsed JSON value.

**`ok`** (property)

```python
@property
def ok(self)
```

Whether the status code is in the success range.

**Returns:** `True` when the HTTP status code is in the success range.

**`raise_for_status`** (method)

```python
def raise_for_status(self)
```

Raise an error when the response has a non-success status.

**Raises:**

- `WebComPyHttpClientException`: When `ok` is `False`.

**`status_code`** (property)

```python
@property
def status_code(self)
```

The HTTP status code.

**Returns:** The integer HTTP status code.

**`text`** (property)

```python
@property
def text(self)
```

The response body text.

**Returns:** The response body as decoded text.

### sleep

```python
async def sleep(delay: float) -> None
```

Key: `webcompy.aio._utils:sleep` · Exports: `from webcompy.aio import sleep`

Coroutine that completes after a given time (in seconds).

**Args:**

- `delay`: seconds to wait.

### StreamAsyncIterator

```python
class StreamAsyncIterator(Generic[T]):
    def __init__(self, generator: AsyncGenerator[T, None], dispose: Callable[[], None]) -> None
```

Key: `webcompy.aio._stream:StreamAsyncIterator` · Exports: `from webcompy.aio import StreamAsyncIterator`

An async iterator that disposes its generator source on close.

**Args:**

- `generator`: Async generator yielding the iterator's items.
- `dispose`: Cleanup callback invoked exactly once, when the iterator is closed or garbage collected.

#### Members

**`aclose`** (async_method)

```python
async def aclose(self) -> None
```

Dispose the source generator and close the iterator.

### StreamListResult

```python
class StreamListResult(Generic[T]):
    def __init__(self) -> None
```

Key: `webcompy.aio._stream:StreamListResult` · Exports: `from webcompy.aio import StreamListResult`

Signals tracking the accumulated items of a consumed source.

**Attributes:**

- `items`: Reactive list that grows as items arrive from the source.
- `error`: Signal holding the exception that terminated the source, or `None`.
- `finished`: Signal that becomes `True` when the source is exhausted (or failed).

#### Members

**`aclose`** (async_method)

```python
async def aclose(self) -> None
```

Cancel consumption of the source and detach the stream handle.

**`error`** (property)

```python
@property
def error(self) -> Signal[Exception | None]
```

The exception that terminated the source, if any.

**Returns:** A signal holding the exception, or `None`.

**`finished`** (property)

```python
@property
def finished(self) -> Signal[bool]
```

Whether the source finished successfully.

**Returns:** A signal that becomes `True` when the source is exhausted.

**`items`** (property)

```python
@property
def items(self) -> ReactiveList[T]
```

The items accumulated from the source so far.

**Returns:** A reactive list that grows as items arrive.

### StreamResult

```python
class StreamResult(Generic[T]):
    def __init__(self, initial: T) -> None
```

Key: `webcompy.aio._stream:StreamResult` · Exports: `from webcompy.aio import StreamResult`

Signals tracking the latest item of a consumed source.

**Args:**

- `initial`: Initial value of the `value` signal.

**Attributes:**

- `value`: Signal holding the latest item emitted by the source.
- `error`: Signal holding the exception that terminated the source, or `None`.
- `finished`: Signal that becomes `True` when the source is exhausted (or failed).

#### Members

**`aclose`** (async_method)

```python
async def aclose(self) -> None
```

Cancel consumption of the source and detach the stream handle.

**`error`** (property)

```python
@property
def error(self) -> Signal[Exception | None]
```

The exception that terminated the source, if any.

**Returns:** A signal holding the exception, or `None`.

**`finished`** (property)

```python
@property
def finished(self) -> Signal[bool]
```

Whether the source finished successfully.

**Returns:** A signal that becomes `True` when the source is exhausted.

**`value`** (property)

```python
@property
def value(self) -> Signal[T]
```

The latest item emitted by the source.

**Returns:** A signal holding the latest item.

### to_async_iter

```python
def to_async_iter(
    sig: Signal[T],
    *,
    emit_initial: bool = False,
    maxlen: int | None = None,
) -> StreamAsyncIterator[T]
```

Key: `webcompy.aio._stream:to_async_iter` · Exports: `from webcompy.aio import to_async_iter`

Convert the updates of a signal into an async iterator.

Yields each new value of `sig` as an occurrence. Queueing is drop-oldest: while the consumer falls behind, older values are dropped so the next yield is always the newest available value. The iterator stops when closed or when the surrounding component is destroyed.

**Args:**

- `sig`: The signal whose updated values are yielded.
- `emit_initial`: When `True`, yield the current value first.
- `maxlen`: Optional bound on the queue of pending values.

**Returns:** A `StreamAsyncIterator` yielding the signal's updated values.

### to_reactive_list

```python
def to_reactive_list(
    source: AsyncIterable[T] | Iterable[T],
    *,
    maxlen: int | None = None,
) -> StreamListResult[T]
```

Key: `webcompy.aio._stream:to_reactive_list` · Exports: `from webcompy.aio import to_reactive_list`

Append the items of an async or sync iterable to a reactive list.

Consumption starts immediately. Items are appended to `items` in arrival order until the source finishes; call `aclose()` to stop consuming.

**Args:**

- `source`: Async or sync iterable whose items are collected.
- `maxlen`: When given, drop the oldest items so the list never grows beyond this length.

**Returns:** A `StreamListResult` exposing the accumulated items.

### to_signal

```python
def to_signal(source: AsyncIterable[T] | Iterable[T], initial: T) -> StreamResult[T]
```

Key: `webcompy.aio._stream:to_signal` · Exports: `from webcompy.aio import to_signal`

Track the latest item of an async or sync iterable in a signal.

Consumption starts immediately. Update the returned `StreamResult`: `value` follows each emitted item, `error` records the terminating exception, and `finished` marks exhaustion. Call `aclose()` to stop consuming.

**Args:**

- `source`: Async or sync iterable whose items are tracked.
- `initial`: Initial value of the `value` signal.

**Returns:** A `StreamResult` exposing the tracked signals.

### TypedResponseError

```python
class TypedResponseError(Exception)
```

Key: `webcompy.ajax._serde:TypedResponseError` · Exports: `from webcompy.ajax import TypedResponseError`

Raised when a response body cannot be converted to the requested schema.

### WebComPyHttpClientException

```python
class WebComPyHttpClientException(WebComPyException)
```

Key: `webcompy.ajax._fetch:WebComPyHttpClientException` · Exports: `from webcompy.ajax import WebComPyHttpClientException`

Raised when an HTTP request fails or a response status is not OK.

## Forms & Validation

### email

```python
def email(message: str = 'Invalid email address') -> Validator[Any]
```

Key: `webcompy.forms._validators:email` · Exports: `from webcompy.forms import email`

Build a validator for email addresses.

Uses a simple pattern that requires a `user@domain.tld` shape.

**Args:**

- `message`: Error message returned for non-matching values.

**Returns:** A `Validator` rejecting values that do not look like email addresses.

### Field

```python
class Field(Generic[T]):
    def __init__(
        self,
        signal: Signal[T],
        validators: Iterable[Validator[T]] = (),
        name: str | None = None,
    ) -> None
```

Key: `webcompy.forms._field:Field` · Exports: `from webcompy.forms import Field`

Reactive form state bound to a single `Signal` value.

Tracks the value, touched/dirty flags, and validation errors as signals so form UI reacts to changes. `errors` is a `Computed` list produced by running the validators on each read, and `valid` and `invalid` are computed booleans derived from it.

**Args:**

- `signal`: Reactive value the field wraps.
- `validators`: Iterable of `Validator` callables run on read.
- `name`: Optional field name, exposed for form aggregation.

**Attributes:**

- `name`: Field name used for form aggregation, or `None`.
- `value`: The wrapped `Signal[T]` holding the current value.
- `touched`: `Signal[bool]` — set to true on the field's `blur` event when bound through `:bind`.
- `dirty`: `Signal[bool]` — set to true when user input is written back to `value` through `:bind`.
- `errors`: `Computed[list[str]]` — validation messages produced by running the validators on the current value.
- `valid`: `Computed[bool]` — true when `errors` is empty.
- `invalid`: `Computed[bool]` — negation of `valid`.

#### Members

**`reset`** (method)

```python
def reset(self) -> None
```

Reset the value to the initial value and clear the touched/dirty flags.

### Form

```python
class Form:
    def __init__(self, fields: dict[str, Field[Any]]) -> None
```

Key: `webcompy.forms._form:Form` · Exports: `from webcompy.forms import Form`

Reactive aggregation of named `Field` instances.

Derives computed `valid`/`invalid`/`touched`/`dirty` state from the member fields. `submit()` builds an event handler that validates the form, runs an async-capable handler with the current values, and records submission state in `submitting` and `submit_error`.

**Args:**

- `fields`: `Field` instances keyed by name.

**Attributes:**

- `fields`: Member `Field` instances keyed by name.
- `valid`: `Computed[bool]` — true when every member field is valid.
- `invalid`: `Computed[bool]` — negation of `valid`.
- `touched`: `Computed[bool]` — true when any member field is touched.
- `dirty`: `Computed[bool]` — true when any member field is dirty.
- `submitting`: `Signal[bool]` — true while an async submit handler is running.
- `submit_error`: `Signal` holding the exception raised by the last failed submission, or `None`.

#### Members

**`reset`** (method)

```python
def reset(self) -> None
```

Reset every member field to its initial state.

**`submit`** (method)

```python
def submit(self, handler: Callable[[dict[str, Any]], Any]) -> Callable[[DOMEvent], None]
```

Build a submit event handler that validates and runs `handler`.

**Args:**

- `handler`: Callable receiving the field values dict. May be synchronous or async.

**Returns:** A `DOMEvent` handler suitable for a form `submit` event.

**`touch_all`** (method)

```python
def touch_all(self) -> None
```

Mark every member field as touched.

**`values`** (method)

```python
def values(self) -> dict[str, Any]
```

Return a snapshot of the values of all member fields.

**Returns:** Dict mapping field names to their current values.

### max_length

```python
def max_length(n: int, message: str | None = None) -> Validator[Any]
```

Key: `webcompy.forms._validators:max_length` · Exports: `from webcompy.forms import max_length`

Build a validator requiring values of length at most `n`.

**Args:**

- `n`: Maximum acceptable length.
- `message`: Error message returned for longer values. Defaults to a message derived from `n`.

**Returns:** A `Validator` returning the message when `len(value) > n`.

### max_value

```python
def max_value(n: float, message: str | None = None) -> Validator[Any]
```

Key: `webcompy.forms._validators:max_value` · Exports: `from webcompy.forms import max_value`

Build a validator requiring values of at most `n`.

**Args:**

- `n`: Maximum acceptable value.
- `message`: Error message returned for larger values. Defaults to a message derived from `n`.

**Returns:** A `Validator` returning the message when `value > n`.

### min_length

```python
def min_length(n: int, message: str | None = None) -> Validator[Any]
```

Key: `webcompy.forms._validators:min_length` · Exports: `from webcompy.forms import min_length`

Build a validator requiring values of length at least `n`.

**Args:**

- `n`: Minimum acceptable length.
- `message`: Error message returned for shorter values. Defaults to a message derived from `n`.

**Returns:** A `Validator` returning the message when `len(value) < n`.

### min_value

```python
def min_value(n: float, message: str | None = None) -> Validator[Any]
```

Key: `webcompy.forms._validators:min_value` · Exports: `from webcompy.forms import min_value`

Build a validator requiring values of at least `n`.

**Args:**

- `n`: Minimum acceptable value.
- `message`: Error message returned for smaller values. Defaults to a message derived from `n`.

**Returns:** A `Validator` returning the message when `value < n`.

### pattern

```python
def pattern(regex: str, message: str = 'Invalid format') -> Validator[Any]
```

Key: `webcompy.forms._validators:pattern` · Exports: `from webcompy.forms import pattern`

Build a validator requiring string values to match a regex.

**Args:**

- `regex`: Regular expression searched against the value.
- `message`: Error message returned when the value does not match.

**Returns:** A `Validator` returning the message when `regex` does not match the value.

### required

```python
def required(message: str = 'This field is required') -> Validator[Any]
```

Key: `webcompy.forms._validators:required` · Exports: `from webcompy.forms import required`

Build a validator rejecting `None`, `False`, and blank strings.

Falsy but listed values such as `0` or `[]` pass validation; only `None`, `False`, and strings that are empty or whitespace fail.

**Args:**

- `message`: Error message returned for failing values.

**Returns:** A `Validator` applying the rejection rule.

### use_field

```python
def use_field(
    signal: Signal[T],
    *,
    validators: Iterable[Validator[T]] = (),
    name: str | None = None,
) -> Field[T]
```

Key: `webcompy.forms._field:use_field` · Exports: `from webcompy.forms import use_field`

Create a `Field` bound to a reactive value.

**Args:**

- `signal`: Reactive value the field wraps.
- `validators`: Iterable of `Validator` callables run on read.
- `name`: Optional field name, exposed for form aggregation.

**Returns:** A `Field` wrapping `signal`.

### use_form

```python
def use_form(**fields: Field[Any]) -> Form
```

Key: `webcompy.forms._form:use_form` · Exports: `from webcompy.forms import use_form`

Create a `Form` aggregating the given keyword fields.

**Args:**

- `**fields`: `Field` instances keyed by name.

**Returns:** A `Form` over the given fields.

### Validator

```python
Validator: TypeAlias = Callable[[T], str | None]
```

Key: `webcompy.forms._validators:Validator` · Exports: `from webcompy.forms import Validator`

Callable that validates a value and returns an error message, or `None` when the value is valid.

## Storage & Browser Events

### use_document_event

```python
def use_document_event(
    event_type: str,
    initial: T,
    *,
    transform: Callable[[Any], T] | None = None,
) -> tuple[ReadonlySignal[T], Callable[[T], T]]
```

Key: `webcompy.events._composable:use_document_event` · Exports: `from webcompy import use_document_event`, `from webcompy.events import use_document_event`

Bridge a document state event into a read-only signal.

Same semantics as `use_window_event` but the listener is attached via `DOMPort.add_document_event_listener`.

**Args:**

- `event_type`: DOM event type name to listen for (e.g. `"visibilitychange"`).
- `initial`: Signal value used before any event fires (and whenever no listener could be attached).
- `transform`: Optional callable converting each raw event object into the stored value. When `None`, the raw event object itself is stored.

**Returns:** A `(view, update)` pair where `view` is a `ReadonlySignal[T]` fed by the event listener and `update` is the internal setter.

### use_local_storage

```python
def use_local_storage(
    key: str,
    default: T | Callable[[], T],
    *,
    sync_tabs: bool = False,
) -> Signal[T]
```

Key: `webcompy.storage._composable:use_local_storage` · Exports: `from webcompy import use_local_storage`, `from webcompy.storage import use_local_storage`

Create a `Signal` persisted to `localStorage`.

In the browser the current stored value for `key` is read at creation time (JSON-decoded) and used as the initial value; when the key is absent, `default` is used. Every subsequent update of the returned signal is written back to `localStorage` (JSON-encoded).

In any non-PyScript environment (SSR, SSG, server-side tests) no storage API is accessed and `Signal(default)` is returned.

When `sync_tabs=True` (browser only) the signal additionally reacts to `storage` events fired by other tabs of the same origin: a write of `key` updates the signal to the incoming JSON-decoded value, and a removal (`removeItem` or `clear()` covering it) resets it to `default`. Concurrent writes follow last-writer-wins; applying a remote value never re-broadcasts to other tabs. `sync_tabs=True` is a no-op outside PyScript (no listener is created).

The value type is inferred from `default`. To declare a wider type (for example an optional value), annotate the variable:

```python
theme: Signal[str | None] = use_local_storage("theme", None)
```

**Args:**

- `key`: Storage key read at creation time and written back on every subsequent signal update.
- `default`: Initial value used when `key` is absent, or a zero-argument factory producing it.
- `sync_tabs`: When `True` (browser only), the signal also reacts to `storage` events fired by other tabs of the same origin.

**Returns:** A `Signal[T]` persisted to `localStorage` in the browser; a plain signal seeded with `default` in any non-PyScript environment.

### use_session_storage

```python
def use_session_storage(key: str, default: T | Callable[[], T]) -> Signal[T]
```

Key: `webcompy.storage._composable:use_session_storage` · Exports: `from webcompy import use_session_storage`, `from webcompy.storage import use_session_storage`

Create a `Signal` persisted to `sessionStorage`.

Same semantics as `use_local_storage` but backed by `sessionStorage` (per-tab lifetime).

**Args:**

- `key`: Storage key read at creation time and written back on every subsequent signal update.
- `default`: Initial value used when `key` is absent, or a zero-argument factory producing it.

**Returns:** A `Signal[T]` persisted to `sessionStorage` in the browser; a plain signal seeded with `default` in any non-PyScript environment.

### use_window_event

```python
def use_window_event(
    event_type: str,
    initial: T,
    *,
    transform: Callable[[Any], T] | None = None,
) -> tuple[ReadonlySignal[T], Callable[[T], T]]
```

Key: `webcompy.events._composable:use_window_event` · Exports: `from webcompy import use_window_event`, `from webcompy.events import use_window_event`

Bridge a window state event into a read-only signal.

Inside component setup with a resolvable `HostPort`, a listener is attached via `HostPort.add_window_event_listener` and removed on component destroy. Outside component setup a `UserWarning` is emitted and nothing is attached; a missing port (or the server `ServerHostPort` no-op) keeps the signal at `initial`.

**Args:**

- `event_type`: DOM event type name to listen for (e.g. `"resize"`).
- `initial`: Signal value used before any event fires (and whenever no listener could be attached).
- `transform`: Optional callable converting each raw event object into the stored value. When `None`, the raw event object itself is stored.

**Returns:** A `(view, update)` pair where `view` is a `ReadonlySignal[T]` fed by the event listener and `update` is the internal setter.

## Realtime (SSE & WebSocket)

### CloseInfo

```python
class CloseInfo:
    code: int
    reason: str
    was_clean: bool
```

Key: `webcompy.realtime._registry:CloseInfo` · Exports: `from webcompy import CloseInfo`, `from webcompy.realtime import CloseInfo`

Information about a WebSocket close event.

**Args:**

- `code`: The close code reported by the browser.
- `reason`: The close reason text.
- `was_clean`: Whether the close was a clean, protocol-level close.

**Attributes:**

- `code`: The close code reported by the browser.
- `reason`: The close reason text.
- `was_clean`: Whether the close was a clean, protocol-level close.

### ConnectionState

```python
class ConnectionState(Enum)
```

Key: `webcompy.realtime._registry:ConnectionState` · Exports: `from webcompy import ConnectionState`, `from webcompy.realtime import ConnectionState`

Lifecycle stages of a realtime connection.

`CONNECTING` while establishing, `OPEN` while active, `RECONNECTING` while re-establishing after a drop, and `CLOSED` after termination.

### EventSourceHandle

```python
class EventSourceHandle:
    def __init__(
        self,
        state: Signal[ConnectionState],
        queue: _StreamQueue[Any],
        detach: Callable[[], None],
    ) -> None
```

Key: `webcompy.realtime._sse:EventSourceHandle` · Exports: `from webcompy.realtime import EventSourceHandle`

Async iterator and connection handle for a Server-Sent Events subscription.

Iterating yields `SSEvent` occurrences in arrival order. `close()` detaches only this handle's subscription.

**Args:**

- `state`: Signal exposing the shared connection state.
- `queue`: Per-subscription queue of parsed events.
- `detach`: Callback releasing this handle's subscription.

**Attributes:**

- `state`: Signal exposing the `ConnectionState` of the shared connection.

#### Members

**`close`** (method)

```python
def close(self) -> None
```

Detach this subscription and stop iteration.

**`state`** (property)

```python
@property
def state(self) -> Signal[ConnectionState]
```

The state of the underlying connection.

**Returns:** A signal exposing `ConnectionState`.

### register_realtime_type_handler

```python
def register_realtime_type_handler(
    cls: type,
    encoder: Callable[[Any], Any],
    decoder: Callable[[Any], Any],
) -> None
```

Key: `webcompy.realtime._typed:register_realtime_type_handler` · Exports: `from webcompy import register_realtime_type_handler`, `from webcompy.realtime import register_realtime_type_handler`

Register a custom type for typed realtime messages in the app DI scope.

The encoder converts an instance to a JSON-serializable value and the decoder restores it. Tags use the qualified type name; only builtin tags and registered tags are accepted on receive. Outside an app DI scope the registration is a no-op and a `UserWarning` is emitted.

**Args:**

- `cls`: Custom type handled by this codec.
- `encoder`: Converts an instance of `cls` to a JSON-serializable value.
- `decoder`: Restores an instance of `cls` from the encoded value.

### SSEvent

```python
class SSEvent:
    event: str
    data: str
    last_event_id: str
```

Key: `webcompy.realtime._sse:SSEvent` · Exports: `from webcompy import SSEvent`, `from webcompy.realtime import SSEvent`

A parsed Server-Sent Event.

**Args:**

- `event`: The event type (defaults to `"message"`).
- `data`: The event payload.
- `last_event_id`: The `id` value persisted by the stream.

**Attributes:**

- `event`: The event type (defaults to `"message"`).
- `data`: The event payload.
- `last_event_id`: The `id` value persisted by the stream.

### TypedWebSocketHandle

```python
class TypedWebSocketHandle(Generic[T]):
    def __init__(
        self,
        raw: WebSocketHandle,
        message_type: type[T],
        *,
        strict: bool,
        registry: _RealtimeTypeRegistry | None,
    ) -> None
```

Key: `webcompy.realtime._typed:TypedWebSocketHandle` · Exports: `from webcompy import TypedWebSocketHandle`, `from webcompy.realtime import TypedWebSocketHandle`

Async iterator and typed messaging facade over a `WebSocketHandle`.

Iterating yields received messages decoded into instances of `T`; frames that fail decoding are skipped and surfaced on `last_error`. `send()` encodes `T` instances with attached transfer metadata.

**Args:**

- `raw`: The underlying text-message handle.
- `message_type`: Dataclass type messages are decoded as.
- `strict`: When `True`, reject unknown or missing fields on decode.
- `registry`: Optional app-scoped registry of custom type handlers.

**Attributes:**

- `state`: Signal exposing the `ConnectionState` of the underlying connection.
- `last_close`: Signal with the most recent close information, or `None` before the first close.
- `last_error`: Signal holding the most recent decode error, or `None` when every received frame decoded successfully.

#### Members

**`close`** (method)

```python
def close(self) -> None
```

Close the underlying connection for this subscription.

**`force_close`** (method)

```python
def force_close(self, code: int = 4000, reason: str = '') -> None
```

Force an abnormal close of the underlying connection.

**Args:**

- `code`: Close code to report. Defaults to `4000`.
- `reason`: Close reason text.

**`last_close`** (property)

```python
@property
def last_close(self) -> Signal[CloseInfo | None]
```

Information about the most recent close event.

**Returns:** The underlying handle's close information signal.

**`last_error`** (property)

```python
@property
def last_error(self) -> Signal[Exception | None]
```

The most recent decode error, if any.

**Returns:** A signal holding the last error, or `None`.

**`send`** (method)

```python
def send(self, message: T) -> None
```

Encode and send a typed message.

**Args:**

- `message`: An instance of the configured `message_type`.

**`state`** (property)

```python
@property
def state(self) -> Signal[ConnectionState]
```

The state of the underlying connection.

**Returns:** A signal exposing `ConnectionState`.

### use_event_source

```python
def use_event_source(
    url: str,
    *,
    events: tuple[str, ...] = ('message',),
    max_queue: int | None = None,
    method: str = 'GET',
    body: str | None = None,
    headers: dict[str, str] | None = None,
) -> EventSourceHandle
```

Key: `webcompy.realtime._sse:use_event_source` · Exports: `from webcompy import use_event_source`, `from webcompy.realtime import use_event_source`

Open a Server-Sent Events connection and return its connection handle.

The handle is an `AsyncIterator[SSEvent]` yielding every received event in arrival order (occurrence semantics). `.state` is a signal exposing `ConnectionState`; `.close()` detaches only the caller's own subscription. Subscriptions with the same URL inside one app DI scope share a single underlying connection; a later subscriber requesting event types not yet registered reopens the shared connection with the union of types.

With the default `method="GET"` the connection is opened through the browser-native `EventSource` API. Any other non-empty `method` opens a fetch-based connection through the framework's streaming fetch capability, sending `body` as the request body and `headers` as request headers. Fetch-based connections are keyed by `(url, method, body, normalized headers)` and filter event types per subscriber without reopening.

Outside the browser, a connection is opened only when the resolved `EventSourcePort` (GET) or `FetchPort` (non-GET) is a real implementation (e.g., a testing fake); with the server no-op port (or no port at all) an immediately-finished empty handle with `state == CLOSED` is returned and a warning is emitted.

**Args:**

- `url`: Endpoint URL of the event stream.
- `events`: Event types to subscribe to. Defaults to `("message",)`.
- `max_queue`: Optional bound on the per-subscription event queue.
- `method`: HTTP method used to open the connection; anything other than `"GET"` selects the fetch-based transport.
- `body`: Request body for fetch-based connections.
- `headers`: Request headers for fetch-based connections.

**Returns:** An `EventSourceHandle` yielding received events.

**Raises:**

- `TypeError`: If `events`, `max_queue`, or `method` has an invalid type, or if an event type is empty.
- `ValueError`: If `events` is empty, `max_queue` is less than 1, or `body`/`headers` are supplied with `method="GET"`.

### use_websocket

```python
def use_websocket(
    url: str,
    *,
    protocols: tuple[str, ...] | None = None,
    max_queue: int | None = None,
    reconnect: bool = True,
    reconnect_base_delay: float = 1.0,
    reconnect_max_delay: float = 30.0,
    reconnect_max_attempts: int | None = None,
    buffer_while_disconnected: bool = False,
    message_type: type[T] | None = None,
    strict: bool = True,
) -> WebSocketHandle | TypedWebSocketHandle[T]
```

Key: `webcompy.realtime._ws:use_websocket` · Exports: `from webcompy import use_websocket`, `from webcompy.realtime import use_websocket`

Open a WebSocket connection and return its connection handle.

The handle is an `AsyncIterator[str]` yielding every received text message in arrival order (occurrence semantics). `.state` is a signal exposing `ConnectionState` (including `RECONNECTING` while a dropped connection is being re-established); `.last_close` is a signal holding a `CloseInfo` for the most recent close event. `.send(data)` sends one text frame; while disconnected it warns and discards by default, or buffers FIFO (flushed on reopen) when `buffer_while_disconnected=True`. `.close()` detaches only the caller's own subscription.

Subscriptions with the same URL and subprotocols inside one app DI scope share a single underlying connection. The first subscriber's reconnection parameters apply to the shared connection.

Outside the browser, a connection is opened only when the resolved `WebSocketPort` is a real implementation (e.g., a testing fake); with the server no-op port (or no port at all) an immediately-finished empty handle with `state == CLOSED` is returned and a warning is emitted.

When `message_type` is a dataclass type, the handle becomes an `AsyncIterator[T]` and `.send()` accepts instances of `T`: each text frame is a JSON object carrying the payload fields plus the `__webcompy_transfer_meta__` member (typed-response body wire mode), and metadata-typed fields are restored on receive. Frames that fail JSON parsing, type-tag validation, or schema reconstruction are skipped and surfaced on `.last_error` (a `Signal[Exception | None]`) with a warning; the subscription and connection survive. Reconstruction uses `strict=True` by default (rejecting unknown or missing fields), or `strict=False` for lenient coercion. Custom types can be registered via `register_realtime_type_handler` within the app DI scope.

**Args:**

- `url`: Endpoint URL of the WebSocket.
- `protocols`: Optional subprotocols offered during the handshake.
- `max_queue`: Optional bound on the per-subscription message queue.
- `reconnect`: When `True` (default), reconnect after a drop.
- `reconnect_base_delay`: Base delay in seconds before reconnecting. Defaults to 1.
- `reconnect_max_delay`: Maximum delay in seconds before reconnecting. Defaults to 30.
- `reconnect_max_attempts`: Optional bound on reconnection attempts.
- `buffer_while_disconnected`: When `True`, buffer sends while disconnected and flush them on reopening.
- `message_type`: When a dataclass type is given, exchange typed messages of that type instead of raw text.
- `strict`: For typed messaging, reject unknown or missing fields when `True` (default).

**Returns:** A `WebSocketHandle`, or a typed `TypedWebSocketHandle[T]` when `message_type` is given.

**Raises:**

- `TypeError`: If `message_type` is not a dataclass type, or another parameter has an invalid type.
- `ValueError`: If a numeric reconnection parameter is not positive.

### WebSocketHandle

```python
class WebSocketHandle:
    def __init__(
        self,
        state: Signal[ConnectionState],
        last_close: Signal[CloseInfo | None],
        queue: _StreamQueue[Any],
        detach: Callable[[], None],
        send: Callable[[str], None],
        force_close: Callable[[int, str], None] | None = None,
    ) -> None
```

Key: `webcompy.realtime._ws:WebSocketHandle` · Exports: `from webcompy.realtime import WebSocketHandle`

Async iterator and connection handle for a WebSocket subscription.

Iterating yields received text messages in arrival order. `close()` detaches only this handle's subscription.

**Args:**

- `state`: Signal exposing the shared connection state.
- `last_close`: Signal exposing the most recent close information.
- `queue`: Per-subscription queue of received messages.
- `detach`: Callback releasing this handle's subscription.
- `send`: Callback forwarding text messages to the shared connection.
- `force_close`: Optional callback forcing an abnormal close.

**Attributes:**

- `state`: Signal exposing the `ConnectionState` of the shared connection.
- `last_close`: Signal exposing the most recent close information, or `None` before the first close.

#### Members

**`close`** (method)

```python
def close(self) -> None
```

Detach this subscription and stop iteration.

**`force_close`** (method)

```python
def force_close(self, code: int = 4000, reason: str = '') -> None
```

Force an abnormal close so the reconnect loop engages.

**Args:**

- `code`: Close code to report. Defaults to `4000`.
- `reason`: Close reason text.

**`last_close`** (property)

```python
@property
def last_close(self) -> Signal[CloseInfo | None]
```

Information about the most recent close event.

**Returns:** A signal holding a `CloseInfo`, or `None` before the first close.

**`send`** (method)

```python
def send(self, data: str) -> None
```

Send a text message over the shared connection.

**Args:**

- `data`: The message to send.

**`state`** (property)

```python
@property
def state(self) -> Signal[ConnectionState]
```

The state of the underlying connection.

**Returns:** A signal exposing `ConnectionState`.

## Internationalization (i18n)

### I18N_KEY

```python
I18N_KEY: InjectKey[object] = InjectKey[object]('webcompy-i18n')
```

Key: `webcompy.i18n._types:I18N_KEY` · Exports: `from webcompy.i18n import I18N_KEY`

DI key under which an application provides its `I18nManager`.

### I18nController

```python
class I18nController:
    def __init__(self, manager: I18nManager) -> None
```

Key: `webcompy.i18n._controller:I18nController` · Exports: `from webcompy.i18n import I18nController`

User-facing controls over the active locale returned by `use_i18n`.

**Args:**

- `manager`: I18n manager the controller operates on.

#### Members

**`locale`** (property)

```python
@property
def locale(self) -> str
```

Currently active locale.

**`set`** (method)

```python
def set(self, locale: str) -> None
```

Set the active locale.

**Args:**

- `locale`: Locale to activate.

### I18nManager

```python
class I18nManager:
    def __init__(
        self,
        catalogs: Mapping[str, Mapping[str, object]],
        *,
        default_locale: str,
        fallback_locale: str | None = None,
        supported_locales: Iterable[str] | None = None,
        initial_locale: str | None = None,
        persist: bool = True,
    ) -> None
```

Key: `webcompy.i18n._manager:I18nManager` · Exports: `from webcompy.i18n import I18nManager`

Reactive locale state holding a `Signal[str]` and message catalogs.

The manager resolves the active locale at construction (an explicit `initial_locale`, then the locale cookie, then `default_locale`) and exposes the translation function `t`, whose reads of the locale signal make template interpolations reactive. `set_locale` updates the signal and persists the choice to the locale cookie.

**Args:**

- `catalogs`: Locale-to-catalog mapping; keys resolve by dot path through nested dictionaries.
- `default_locale`: Locale used when nothing else determines the active locale.
- `fallback_locale`: Locale consulted after the exact locale and its language during message lookup; defaults to `default_locale`.
- `supported_locales`: Locales the application can render; defaults to the catalog keys. Governs normalization and resolution.
- `initial_locale`: Externally seeded locale that takes priority over the cookie/default resolution.
- `persist`: Whether `set_locale` writes the locale cookie.

**Attributes:**

- `locale`: Reactive signal holding the current locale.

#### Members

**`default_locale`** (property)

```python
@property
def default_locale(self) -> str
```

Locale used when nothing else determines the active locale.

**`fallback_locale`** (property)

```python
@property
def fallback_locale(self) -> str
```

Locale consulted after the exact locale and its language.

**`locale`** (property)

```python
@property
def locale(self) -> Signal[str]
```

Reactive signal holding the current locale.

**`set_locale`** (method)

```python
def set_locale(self, locale: str) -> None
```

Set the active locale, persisting it when persistence is enabled.

**Args:**

- `locale`: Locale to activate.

**`t`** (method)

```python
def t(self, key: str, *, count: int | float | None = None, **params: Any) -> str
```

Translate `key` against the current locale.

**Args:**

- `key`: Dot-path message key.
- `count`: Count driving plural selection; interpolated as `{count}` when provided.
- `**params`: Interpolation parameters.

**Returns:** The translated string, or the key when it is missing along the fallback chain.

**`value`** (property)

```python
@property
def value(self) -> str
```

Current locale.

### read_locale_from_cookie

```python
def read_locale_from_cookie(
    headers: Mapping[str, str] | Sequence[tuple[str, str]] | None,
) -> str | None
```

Key: `webcompy.i18n._server:read_locale_from_cookie` · Exports: `from webcompy.i18n import read_locale_from_cookie`

Extract the locale from the Cookie header.

**Args:**

- `headers`: Request headers as a mapping or a sequence of `(name, value)` pairs.

**Returns:** The requested locale, or `None` when the cookie is absent or empty.

### register_plural_rule

```python
def register_plural_rule(locale: str, rule: PluralRule, *, override: bool = False) -> None
```

Key: `webcompy.i18n._plural:register_plural_rule` · Exports: `from webcompy.i18n import register_plural_rule`

Register a plural-rule selector for a locale.

Locales are matched by their language part (`"de-AT"` falls back to `"de"`). The built-in table registers at registration time, so the Babel adapter or application code can replace or extend entries.

**Args:**

- `locale`: Locale tag the rule applies to.
- `rule`: Selector mapping a count to a CLDR category name.
- `override`: Replace an existing registration under the same locale.

**Raises:**

- `ValueError`: If the locale is already registered while `override` is `False`.

### resolve_locale

```python
def resolve_locale(
    headers: Mapping[str, str] | Sequence[tuple[str, str]] | None,
    supported_locales: Iterable[str],
    default_locale: str,
) -> str
```

Key: `webcompy.i18n._server:resolve_locale` · Exports: `from webcompy.i18n import resolve_locale`

Resolve the locale for a request from its headers.

Resolution order: the locale cookie if it matches a supported locale (exact tag or language part, selected deterministically in sorted candidate order), otherwise `default_locale`. The `Accept-Language` header is deliberately not consulted: server-side negotiation without an app-scoped transfer of the resolved value breaks first-render/ hydration agreement with the browser.

**Args:**

- `headers`: Request headers as a mapping or a sequence of `(name, value)` pairs.
- `supported_locales`: Locales the application can render.
- `default_locale`: Fallback locale when no supported cookie exists.

**Returns:** The resolved locale, always one of `supported_locales` or `default_locale`.

### use_i18n

```python
def use_i18n() -> tuple[Signal[str], Callable[..., str], I18nController]
```

Key: `webcompy.i18n._composable:use_i18n` · Exports: `from webcompy.i18n import use_i18n`

Resolve the reactive locale signal, translator, and controller from DI.

Requires an `I18nManager` to have been provided under `I18N_KEY` in the active DI scope.

**Returns:** A `(locale, t, controller)` triple: the reactive `Signal[str]` holding the locale, the translation function, and an `I18nController` bound to the same manager.

**Raises:**

- `LookupError`: If no i18n manager is registered in the active DI scope.
- `TypeError`: If the injected value is not an `I18nManager`.

<!-- generated:end -->

## Next steps

<!-- author:start:see-also -->
- Core guides: [HTTP & Async](/documents/basic/http-and-async), [Forms](/documents/basic/forms), and [Storage](/documents/basic/storage).
- Advanced guides: [Typed API Deep Dive](/documents/advanced/typed-api-deep-dive), [Persistence Patterns](/documents/advanced/persistence-patterns), [Typed Realtime](/documents/advanced/typed-realtime), [Signals and Streams](/documents/advanced/signal-stream), and [Internationalization](/documents/advanced/i18n).
<!-- author:end:see-also -->
