---
title: HTTP Fetch
description: Fetching JSON endpoints with HttpClient and decoding objects, lists, scalars, and raw responses using dataclass response_type annotations.
---

# HTTP Fetch

This example shows `HttpClient.get(...)` fetching static JSON payloads (`sample_object.json`, `sample_array.json`, and `sample_scalar.json`) and automatically decoding them into typed Python `@dataclass` models, `list[User]`, and scalar `int` values alongside raw response inspection.

Use `HttpClient` with `response_type=` whenever reading REST endpoints or static JSON assets from browser or SSR code without writing manual dict parsing helpers.

## What this demonstrates

- **Schema-driven deserialization (`response_type=`)**: Passing `UsersResponse`, `list[User]`, or `int` instructs `HttpClient` to validate HTTP status, parse JSON, and reconstruct typed Python objects via `from_json`.
- **Untyped raw access**: Calling `await HttpClient.get(url)` without `response_type` returns a standard `Response` exposing `.text`, `.json()`, `.status_code`, and `.ok`.
- **Post-render async triggers**: Wrapping async functions with `@AsyncWrapper()` and triggering them in `@context.on_after_rendering` populates `use_reactive_list` and `use_state` cleanly once mounted.

## Key mechanisms and how to adapt

1. **Prefer `use_async_result` for loading and error UI**: When views need spinner, error retry, and automatic SSR data transfer without manual hooks, wrap `HttpClient.get(...)` with `use_async_result(lambda: ...)`.
2. **Add strict schema validation**: Import `from_json(..., strict=True)` to reject unexpected API keys explicitly in security-sensitive handlers.
3. **Intercept or mock endpoints locally**: Attach a `FetchMiddleware` via `add_fetch_middleware()` when prototyping endpoints or adding authorization headers before a backend is deployed.

## Next steps

- Learn `HttpClient` and `use_async_result()` lifecycle signals in [HTTP & Async](/documents/basic/http-and-async).
- Explore `from_json` strictness, `TypedJSONResponse`, and multipart uploads in [Typed API Deep Dive](/documents/advanced/typed-api-deep-dive).
- Add client-side request interception and offline REST mocks next in [Fetch Middleware](/documents/examples/fetch-middleware).
