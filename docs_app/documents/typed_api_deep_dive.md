---
title: Typed API Deep Dive
description: Decode plain JSON endpoints with from_json strictness modes, preserve non-JSON Python types via encode_with_meta and FastAPI TypedJSONResponse, and submit multipart forms through FetchPort.
---

# Typed API Deep Dive

Because a WebComPy application package compiles into the browser wheel as well as running on the server, both sides can import the same `@dataclass` schemas without code generation. `HttpClient` (`response_type=...`) and `from_json` decode ordinary `application/json` endpoints purely from type annotations, while `encode_with_meta` and FastAPI's `TypedJSONResponse` attach optional metadata pointers so non-JSON Python types (`bytes`, `set`, `tuple`, `Decimal`, `Path`) survive HTTP cleanly too.

## When to use

- **Calling ordinary REST / third-party JSON endpoints with dataclass validation** — use `HttpClient(..., response_type=...)` and `from_json` (for basics, see [HTTP & Async](/documents/basic/http-and-async)).
- **Controlling a FastAPI or Starlette server API and wanting rich types (`bytes`, `set`, `Decimal`, `Path`) preserved** — add `TypedJSONResponse` or `encode_with_meta`.
- **Starting a new typed WebComPy RPC backend with procedures, batching, streaming, or WebSocket subscriptions** — use declarative [RPC Contracts](/documents/advanced/rpc-contracts).
- **Inspecting how SSR fetch responses embed into initial page HTML** — see [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).

## Setup

Share a schema module imported by both FastAPI and your browser components, return `TypedJSONResponse` from your API route, and pass `response_type=` on the client:

```python
# my_app/schemas.py — shared by FastAPI server and WebComPy browser wheel
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass
class Invoice:
    id: UUID
    total: Decimal
    tags: set[str]
    attachment: bytes
```

```python
# my_app/server_api.py — FastAPI backend
from fastapi import FastAPI
from webcompy_server.contrib.fastapi import TypedJSONResponse
from my_app.schemas import Invoice

api = FastAPI()


@api.get("/api/invoices/{invoice_id}")
def read_invoice(invoice_id: str) -> TypedJSONResponse:
    invoice = load_invoice(invoice_id)
    return TypedJSONResponse(invoice)  # header mode by default
```

```python
# my_app/components/invoice_view.py — browser / SSR client
from webcompy import use_computed
from webcompy.ajax import HttpClient, TypedResponseError
from webcompy.components import ComponentContext, define_component, use_async_result
from webcompy.elements import html
from my_app.schemas import Invoice


@define_component()
def InvoiceView(context: ComponentContext[None]):
    req = use_async_result(lambda: HttpClient.get("/api/invoices/42", response_type=Invoice))

    return html.DIV(
        {},
        use_computed(
            lambda: f"Total: {req.data.value.total}"
            if req.data.value is not None
            else (f"Error: {req.error.value}" if req.is_error.value else "Loading...")
        ),
    )
```

Plain REST APIs returning standard JSON (without `TypedJSONResponse`) work identically via schema-driven coercion in `from_json`.

## Recipes

### 1. Validate external APIs with `from_json` strictness and coercion

Call `from_json(cls, data, *, strict=False, meta=None)` directly or through `HttpClient`. By default (`strict=False`), unknown JSON keys are ignored so additive API changes stay forward-compatible; pass `strict=True` to reject unknown keys as well as missing fields and mismatched types:

```python
from dataclasses import InitVar, dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from webcompy.ajax import TypedResponseError, from_json


class Role(Enum):
    ADMIN = "admin"
    MEMBER = "member"


@dataclass
class UserProfile:
    id: UUID
    role: Role
    joined_at: datetime
    audit_source: InitVar[str] = "api"


# Lenient (default): extra field "experimental_flag" ignored; ISO/UUID/Enum coerced from JSON
profile = from_json(
    UserProfile,
    {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "role": "admin",
        "joined_at": "2026-08-05T12:34:56",
        "experimental_flag": True,
    },
)

# Strict: rejects "experimental_flag" with descriptive TypeError/ValueError
strict_profile = from_json(UserProfile, {"id": "..."}, strict=True)
```

| Target annotation | Plain JSON conversion (`from_json`) | Already an instance? |
|---|---|---|
| Nested `@dataclass`, `list[T]`, `dict[str, T]` | Reconstructed recursively; works as top-level targets (`list[User]`) too | Passes through unchanged (even in `strict=True`) |
| `T \| None`, `Union[A, B]` | Matched in declaration order | Passed through if already an instance |
| `datetime`, `date`, `time` | Parsed from ISO-8601 strings via `fromisoformat` | Unchanged |
| `UUID`, `Enum` | Parsed via `UUID(...)` and matched by enum value | Unchanged |
| `int`, `str`, `float`, `bool` | Validated/coerced against declared scalar types | Unchanged |
| `InitVar[T]` fields | Ignored cleanly (never coerced, not treated as unknown in `strict=True`) | N/A |

### 2. Choose header mode vs. body mode with `TypedJSONResponse`

`TypedJSONResponse` emits **header mode** by default (`transfer_mode="header"`), putting JSON Pointer metadata in `X-WebComPy-Transfer-Meta` so the HTTP body stays pristine JSON for third-party consumers and works with top-level JSON lists or scalars (`list[Invoice]`):

```python
from webcompy_server.contrib.fastapi import TypedJSONResponse

# Default header mode — pristine JSON body, works for arrays/scalars too
@api.get("/api/invoices")
def list_invoices() -> TypedJSONResponse:
    return TypedJSONResponse([load_invoice("1"), load_invoice("2")])


# Body mode — embeds "__webcompy_transfer_meta__" inside top-level JSON object (helpful for huge meta maps)
@api.get("/api/invoices/large/{invoice_id}")
def read_large_invoice(invoice_id: str) -> TypedJSONResponse:
    return TypedJSONResponse(load_invoice(invoice_id), transfer_mode="body")
```

### 3. Apply `encode_with_meta()` in non-FastAPI servers

Import `encode_with_meta`, `META_HEADER_NAME`, and `merge_meta_into_body` from `webcompy.hydration` inside Starlette, Litestar, Django, or Flask handlers — accepting dataclasses, plain nested dicts/lists, and Pydantic models (duck-typed via `model_dump()`, with no Pydantic dependency required):

```python
import json
from starlette.responses import JSONResponse
from webcompy.hydration import META_HEADER_NAME, encode_with_meta


async def invoice_endpoint(request):
    invoice = load_invoice(request.path_params["id"])
    json_data, meta = encode_with_meta(invoice)
    headers = {META_HEADER_NAME: json.dumps(meta, separators=(",", ":"))} if meta else {}
    return JSONResponse(json_data, headers=headers)
```

Pure JSON values (`str`, `int`, `float`, `bool`, `None`, nested plain dataclasses) produce an empty `meta` dict and add zero metadata overhead.

### 4. Submit multipart forms through `HttpClient` across SSR and tests

Use `form_data=` (accepting `str | bytes` field values) to encode `multipart/form-data` payloads through `FetchPort` — preserving in-process SSR self-site calls and testability via `FakeFetchPort`, unlike `form_element=` which requires a browser DOM form node:

```python
from webcompy.ajax import HttpClient

resp = await HttpClient.post(
    "/api/upload",
    form_data={"title": "Quarterly Report", "attachment": b"%PDF-1.4..."},
)
```

If you specify an explicit `Content-Type` header manually, WebComPy keeps your caller-supplied header; otherwise it sets the multipart media type and boundary automatically.

## Behavior notes

- **Built-in transfer meta tag set & security**: Built-in metadata tags cover `"bytes"` (base64 encoded in body), `"set"`, `"frozenset"`, `"tuple"`, `"decimal"`, `"datetime"`, `"date"`, `"time"`, `"path"`, and `"uuid"`. `from_json` and `apply_transfer_meta` operate strictly against that fixed closed table (or explicit custom decoders) and never dynamically import classes from payload strings.
- **JSON Pointer path grammar**: Empty string `""` identifies a top-level root value (used when returning a top-level `list[T]` or `Decimal` in header mode), `"/field"` addresses object properties, and `"/items/0"` addresses array elements.
- **Body vs. header precedence**: If a response carries both `__webcompy_transfer_meta__` and `X-WebComPy-Transfer-Meta`, `__webcompy_transfer_meta__` wins, and metadata restoration always runs ahead of schema-driven conversion for those recorded paths.
- **Error pipeline & SSG gating**: Non-2xx responses raise `WebComPyHttpClientException` (or `TypedResponseError` when `response_type=` is set) before JSON parsing; JSON/schema mismatches raise `TypedResponseError` and integrate cleanly with `ErrorBoundary` (failing static `webcompy generate` builds cleanly when uncontained).
- **SSR in-process dispatch**: During SSR/SSG, typed requests run through `ServerFetchPort` (using in-process ASGI dispatch for self-site and mount endpoints) and cache raw responses inside the hydration payload automatically.

## Pitfalls

- **Using `transfer_mode="body"` with a top-level list or scalar**: Embedding `__webcompy_transfer_meta__` requires a top-level dict; passing a list such as `TypedJSONResponse([item], transfer_mode="body")` raises `WebComPyException` explicitly with instructions to use `transfer_mode="header"` or wrap the list in a dataclass/dict.
- **Importing `TypedJSONResponse` without Starlette/FastAPI installed**: `webcompy_server.contrib.fastapi` imports Starlette lazily so core `webcompy_server` stays usable anywhere, raising a descriptive `ImportError` only when imported without Starlette/FastAPI installed.
- **Calling `HttpClient.post(..., form_element=...)` during SSR**: Passing a DOM form element ref requires a live browser DOM and raises outside the browser — use `form_data=` (or wrap browser form actions in event handlers / `@on_mounted`) when server paths might execute.
- **Expecting `from_json(..., strict=True)` to re-check an existing object instance**: Pre-constructed instances matching the target type pass straight through untouched so custom metadata decoders survive strict conversion intact.

## Next steps

- See object, list, and scalar typed `HttpClient` deserialization in the [HTTP Fetch](/documents/examples/http-fetch) example.
- Learn `HttpClient` basics and `use_async_result()` UI state signals in [HTTP & Async](/documents/basic/http-and-async).
- Combine client-side interceptors and response mocks with [Middleware](/documents/advanced/middleware).
- Compare schema-driven REST with shared [RPC Contracts](/documents/advanced/rpc-contracts).
- Trace hydration payload transfer and `ErrorBoundary` behavior in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer) and [Error Handling](/documents/basic/error-handling).
- Full API: [Data, Forms & i18n API](/documents/api/data).
