---
title: Step 5 — Remote Data
description: Load and mutate tasks over HTTP using HttpClient, dataclass decoding, and use_async_result(), backed by a client-side FetchMiddleware mock.
---

# Step 5 — Remote Data

In Step 5 (~15 minutes), your ToDo app loads its task list from `/api/tasks` and persists new tasks and checkbox toggles via `HttpClient` and `use_async_result`. Because the docs site runs on static hosting without a backend database, this demo also registers an in-app `FetchMiddleware` mock so every API call works completely in memory with zero network errors.

The live interactive demo and complete source for this step appear at the bottom of the page.

## Typed API payloads with `@dataclass` and `HttpClient`

Define a `@dataclass` matching your API JSON shape so `HttpClient` decodes and validates responses automatically via `response_type=`:

```python
from dataclasses import dataclass

from webcompy.ajax import HttpClient


@dataclass
class Task:
    id: int
    title: str
    done: bool
```

Inside `TodoApp`, fetch initial tasks with `HttpClient.get("/api/tasks", response_type=list[Task])` and populate the reactive store inside `use_async_result`:

```python
from webcompy.components import use_async_result

async def load_tasks() -> list[Task]:
    loaded = await HttpClient.get("/api/tasks", response_type=list[Task])
    tasks.value = [_to_item(t) for t in loaded]
    return loaded

load_result = use_async_result(load_tasks)
```

Use `async def` handlers for both creating tasks (`HttpClient.post("/api/tasks", json={"title": ...}, response_type=Task)`) and persisting checkbox changes (`HttpClient.patch(f"/api/tasks/{task['id']}", json={"done": checked}, response_type=Task)` triggered through `@AsyncWrapper()`).

## Rendering loading and error UI with `switch()`

Bind `load_result.is_loading`, `load_result.is_error`, and `load_result.is_success` with `switch()` so users see feedback while waiting or a retry button if loading fails:

```python
from webcompy.elements import html, switch
from webcompy.router import RouterView

switch(
    {
        "case": load_result.is_error,
        "generator": lambda: html.DIV(
            {"class": "status error"},
            html.P({}, f"Failed to load tasks: {load_result.error.value}"),
            html.BUTTON({"type": "button", "@click": lambda _ev: load_result.refetch()}, "Retry"),
        ),
    },
    {"case": load_result.is_success, "generator": lambda: html.MAIN({}, RouterView())},
    default=lambda: html.P({"class": "status"}, "Loading tasks..."),
)
```

## Client-side API mocking with `FetchMiddleware`

To run this step cleanly on both dev servers and static hosting, `TodoApp` calls `add_fetch_middleware(create_tasks_api())` at the start of component setup (never at module level, because the middleware registry lives in the active render DI scope):

```python
from webcompy.ports import (
    FetchMiddleware,
    FetchNext,
    FetchRequest,
    FetchStream,
    Response,
    add_fetch_middleware,
)
```

Requests to `GET /api/tasks`, `POST /api/tasks`, and `PATCH /api/tasks/<id>` return a `Response(...)` built from the middleware's in-memory list without touching the network, while any other URL falls through with `return await next(request)`. See Advanced middleware documentation once available — or explore typed server APIs in [RPC](/documents/advanced/rpc) and [Server-Sent Events](/documents/advanced/event-source) — when you are ready to connect a real backend.

## Next steps

- Add an error boundary and prepare your production build in [Step 6: Deploy](/documents/guides/todo-deploy).
- Review `use_async_result()` and `TypedResponseError` in [HTTP & Async](/documents/basic/http-and-async).
