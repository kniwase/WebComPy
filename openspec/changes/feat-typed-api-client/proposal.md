# Proposal: feat-typed-api-client

## Why

`HttpClient` returns untyped `Response` objects; every caller hand-parses JSON into ad-hoc dicts. Because a WebComPy app package is shipped to the browser as a wheel, both the server and the browser can literally import the same schema module — a unique advantage over TypeScript-style RPC (tRPC/Hono), which needs compiler tricks to share types. A schema-driven typed client delivers typed API access against ANY plain-JSON HTTP API (including pre-existing third-party or in-house FastAPI services) without requiring server cooperation, code generation, or a custom wire format.

## What Changes

- New schema-driven deserializer `from_json(cls, data, *, strict=False) -> T` (pure Python, Pyodide-compatible):
  - Reconstructs nested dataclasses from plain JSON (dict/list/primitives).
  - Resolves `list[T]`, `dict[str, T]`, `Optional[T]`, and `Union` types structurally from type annotations.
  - Coerces ISO-8601 strings into `datetime`/`date`/`time`, and strings into `UUID`/`Enum`, driven by the target type annotation (no wire metadata required).
  - `strict=False` (default, client-appropriate): unknown keys are ignored (forward compatibility against API version skew); `strict=True` rejects unknown keys, missing required fields, and type mismatches.
- `HttpClient` methods (`get`/`post`/`put`/`delete`/`patch`/`head`/`options`) gain an optional `response_type: type[T] | None` parameter. When provided, the method returns `T` (deserialized via `from_json`); when omitted, it returns `Response` exactly as today. Typing uses `@overload` + `TypeVar` so static checkers infer the return type.
- Typed requests go through the existing `FetchPort`, so SSR/SSG self-site fetches remain in-process and are baked into hydration payloads with no extra work.
- `use_async_result` gains `transfer: bool = True`; `transfer=False` marks the result runtime-only: it is NOT recorded into the hydration transfer payload during SSR/SSG, so user-specific or real-time data is fetched fresh in the browser and never baked into static artifacts.
- No server-side dependency: works against any existing HTTP API that returns plain JSON.

## Capabilities

### New Capabilities

- `typed-api-client`: Schema-driven typed deserialization (`from_json`) and the `response_type` typed request API on `HttpClient`, including validation strictness modes and container/leaf type coercion rules.

### Modified Capabilities

- `composables`: `use_async_result` gains the `transfer` parameter controlling whether results are recorded into the hydration transfer payload (SSG bake opt-out).

## Impact

- **Code**: new module under `packages/webcompy/src/webcompy/ajax/` (e.g. `_serde.py`), `packages/webcompy/src/webcompy/ajax/_fetch.py` (`HttpClient` signatures), `packages/webcompy/src/webcompy/components/_hooks.py` (`use_async_result`), transfer collection (`webcompy/hydration/_collect.py`) respecting the opt-out.
- **APIs**: additive only; existing `HttpClient` calls behave identically.
- **Dependencies**: none (stdlib `dataclasses`, `typing`, `datetime`, `uuid`, `enum`).
- **Specs**: new `typed-api-client`; delta to `composables`.

## Known Issues Addressed

(none)

## Non-goals

- Chained/proxy-style API clients (Hono RPC-style path builders) — Python-idiomatic design would need separate exploration; deferred.
- OpenAPI-schema-driven client generation.
- Wire-metadata (superjson-style `__webcompy_transfer_meta__`) production or consumption — that is `feat-typed-response`; this change's deserializer is schema-driven only.
- Server-side request validation for RPC endpoints — `feat-json-rpc` scope.
- pydantic as a shared schema layer (dataclasses only; pydantic models can still be used server-side independently).
