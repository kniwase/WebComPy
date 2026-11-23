---
title: HTTP & Async
description: Fetch HTTP endpoints with HttpClient, decode responses into Python types with response_type, and render loading/success/error UI with use_async_result().
---

# HTTP & Async

WebComPy runs data fetching through `HttpClient` (`webcompy.ajax`) — routed over browser `fetch()` on the client and the ASGI/resource transport during pre-rendering. Pair `HttpClient` with `use_async_result()` (`webcompy.components`) to expose loading, success, and error states directly as reactive signals.

## At a glance

```python
from dataclasses import dataclass

from webcompy import use_computed
from webcompy.ajax import HttpClient
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.elements import html, switch


@dataclass
class Profile:
    name: str
    role: str


@define_component()
def ProfilePanel(context: ComponentContext[None]):
    profile = use_async_result(
        lambda: HttpClient.get("/api/profile.json", response_type=Profile)
    )

    return html.DIV(
        {},
        switch(
            {"case": profile.is_loading, "generator": lambda: html.P({}, "Loading profile...")},
            {"case": profile.is_error, "generator": lambda: html.P({}, f"Failed: {profile.error.value}")},
            {
                "case": profile.is_success,
                "generator": lambda: html.P(
                    {},
                    use_computed(
                        lambda: f"{profile.data.value.name} ({profile.data.value.role})"
                        if profile.data.value
                        else ""
                    ),
                ),
            },
        ),
        html.BUTTON({"@click": lambda _ev: profile.refetch()}, "Refresh"),
    )
```

## Making requests with `HttpClient`

All `HttpClient` methods are `async` classmethods on `HttpClient`:

```python
from webcompy.ajax import HttpClient

resp = await HttpClient.get("/api/items", query_params={"limit": "10"})
resp.raise_for_status()
items = resp.json()

created = await HttpClient.post(
    "/api/items",
    json={"title": "Write tests"},
    headers={"Accept": "application/json"},
)
```

Available helpers on `HttpClient`:

- `HttpClient.get(url, query_params=None, headers=None, *, response_type=None)`
- `HttpClient.post(url, headers=None, query_params=None, json=None, body_data=None, form_data=None, form_element=None, *, response_type=None)`
- `HttpClient.put(...)`, `HttpClient.patch(...)`, `HttpClient.delete(...)`
- `HttpClient.head(...)`, `HttpClient.options(...)`, `HttpClient.request(method, url, ...)`

Without `response_type`, each method returns a `Response` carrying:

- `.status_code` (`int`), `.reason` (`str`), `.ok` (`bool`: `200 <= status_code < 400`)
- `.headers` (`dict[str, str]`), `.text` (`str`)
- `.json()` (parses JSON body)
- `.raise_for_status()` (raises `WebComPyHttpClientException` when `not ok`)

## Typed decoding with `response_type`

Pass `response_type=` (such as a `dataclass`, `TypedDict`, or `list[User]`) to decode and validate the JSON response automatically:

```python
from dataclasses import dataclass

from webcompy.ajax import HttpClient, TypedResponseError


@dataclass
class Task:
    id: int
    title: str
    done: bool


try:
    tasks = await HttpClient.get("/api/tasks", response_type=list[Task])
except TypedResponseError as err:
    print("Invalid server payload:", err)
```

When `response_type=` is set, `HttpClient` checks HTTP status and parses the JSON body into your target type, raising `TypedResponseError` if the status is not `ok` or the JSON structure does not match.

## Managing UI states with `use_async_result()`

`use_async_result(func, *, default=None, immediate=True)` takes a zero-argument coroutine factory (`lambda: ...`) and returns an `AsyncResult[T]` whose lifecycle fields are reactive signals:

| Property / Method | Type | Description |
|---|---|---|
| `result.state` | `Signal[AsyncState]` | `AsyncState.PENDING`, `LOADING`, `SUCCESS`, or `ERROR` |
| `result.is_pending` | `Computed[bool]` | `True` before the first fetch starts |
| `result.is_loading` | `Computed[bool]` | `True` while a request is in flight |
| `result.is_success` | `Computed[bool]` | `True` after the latest run succeeded |
| `result.is_error` | `Computed[bool]` | `True` if the latest run raised |
| `result.data` | `Signal[T \| None]` | Latest decoded result (or `default` before first success) |
| `result.error` | `Signal[Exception \| None]` | Exception from last failed run |
| `result.refetch()` | `() -> None` | Re-runs the async operation (also starts manual `immediate=False` requests) |

With `immediate=True` (the default), WebComPy launches the operation right after the first render inside component setup and cancels pending updates if the component destroys first.

## Notes & caveats

- Call `HttpClient.get(...)`, `HttpClient.post(...)`, etc. as classmethods — do not instantiate `HttpClient()`.
- Inside `use_async_result(lambda: ...)`, pass a callable returning a new coroutine object each time rather than passing an already-created coroutine, so `.refetch()` can run multiple times.

## Next steps

- Wrap async views with fallback recovery in [Error Handling](/documents/basic/error-handling).
- For server-pushed streams or typed RPC calls, explore [Server-Sent Events](/documents/advanced/event-source) and [RPC](/documents/advanced/rpc).
- Advanced topics coming in Advanced Usage: `watch` signal dependencies, opting out of SSR transfer (`transfer=False`), and scheduler scoping.
