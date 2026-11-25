---
title: Fetch Middleware
description: Stackable FetchMiddleware chains adding trace headers and mocking a /api/notes REST endpoint inside a serverless static app.
---

# Fetch Middleware

This example stacks two `FetchMiddleware` functions inside component setup: an outer tracing middleware that injects `X-Demo-Trace` headers and logs every status code, and an inner mock responder that answers `GET`, `POST`, and `DELETE` requests to `/api/notes` completely in memory.

Because requests never touch the network, the exact same code runs cleanly under `webcompy start` and on the statically generated `webcompy generate` site with zero failed network calls.

## What this demonstrates

- **Outside-in middleware ordering**: Registering `create_trace_middleware` before `create_notes_mock` wraps `/api/notes` so the tracing middleware records every synthetic `200`/`201` response produced by the mock responder.
- **Full `HttpClient` type decoding on mock responses**: Even though `create_notes_mock` returns an in-memory `Response`, `HttpClient.get("/api/notes", response_type=list[Note])` and `HttpClient.post(..., response_type=Note)` still deserialize and validate `Note` dataclasses normally.
- **Selective delegation via `await next(request)`**: Requests outside `/api/notes` pass downstream untouched so other page assets load normally.

## Key mechanisms and how to adapt

1. **Swap mocks per environment**: Move `create_notes_mock` behind a development/preview condition or register tracing/auth middlewares globally in a `WebComPyPlugin.get_fetch_middlewares()`.
2. **Short-circuit caching cleanly**: Return `await next(request, response=cached_response)` to satisfy inner cache hits while allowing outer logging middlewares to run completion hooks.
3. **Never register middlewares at module import time**: Always call `add_fetch_middleware()` inside component setup or plugin initialization so DI scopes isolate middleware chains per render context.

## Real server wiring

In a production deployment, remove `create_notes_mock()` from the browser component (keeping your outer auth/tracing middleware) and serve `/api/notes` from a real Starlette or FastAPI host integrated with `create_asgi_app`:

```python
from dataclasses import asdict, dataclass
from fastapi import FastAPI
from pydantic import BaseModel
from webcompy_cli.config import WebComPyBuildConfig
from webcompy_server import configure_server_context, create_asgi_app


@dataclass
class Note:
    id: int
    title: str
    tag: str


class CreateNoteBody(BaseModel):
    title: str
    tag: str = "custom"


NOTES: list[Note] = [Note(id=1, title="Real server note", tag="api")]
host = FastAPI()


@host.get("/api/notes")
def list_notes() -> list[dict[str, object]]:
    return [asdict(note) for note in NOTES]


@host.post("/api/notes", status_code=201)
def create_note(body: CreateNoteBody) -> dict[str, object]:
    created = Note(id=max((n.id for n in NOTES), default=0) + 1, title=body.title, tag=body.tag)
    NOTES.append(created)
    return asdict(created)
```

Keep `add_fetch_middleware(create_trace_middleware(...))` if desired — once `create_notes_mock` is removed, `HttpClient` routes `/api/notes` directly over browser `fetch()` (and in-process through `root_app` during SSR once `configure_server_context(app, root_app=host)` is wired).

## Next steps

- Learn streaming interception, header-commit timing, and plugin middleware aggregation in [Middleware](/documents/advanced/middleware).
- Compare ASGI host mounting and `configure_server_context` wiring in [ASGI Integration](/documents/server/asgi-integration).
- See how `Step 5` of the guided tutorial introduces a `FetchMiddleware` API mock in [Step 5: Remote Data](/documents/guides/todo-remote-data) and [HTTP & Async](/documents/basic/http-and-async).
- Next, see contract-first typed RPC synthesis in [RPC Middleware](/documents/examples/rpc-middleware).
