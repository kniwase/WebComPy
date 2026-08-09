# Proposal: feat-typed-response

## Why

The schema-driven typed client (`feat-typed-api-client`) restores rich types from plain JSON using target annotations, which covers most real-world APIs. But some Python types cannot survive plain JSON even with schema knowledge on the client: `bytes`, `set` vs `list` distinction, `tuple` vs `list`, `Decimal`, and values behind `Any`-typed or polymorphic (`Union`) fields where the annotation alone cannot identify the concrete type. For APIs a project controls (new WebComPy-aware backends), the server can attach type metadata to responses so the client restores full fidelity — without breaking ordinary JSON consumers of the same API.

## What Changes

- New framework-neutral helper `encode_with_meta(value) -> tuple[plain_json, meta]`: serializes a dataclass/pydantic-model/plain-structure value into pristine JSON-compatible data plus a metadata map recording non-JSON-native types by path. No web-framework dependency.
- Wire formats (both produced by the helper and consumed by the client):
  - **Header mode (default)**: response body stays pristine plain JSON; metadata travels in the `X-WebComPy-Transfer-Meta` response header. Non-WebComPy clients are unaffected; OpenAPI schemas stay accurate.
  - **Body mode (for large metadata)**: the response body MUST be a top-level JSON object; metadata is injected under the collision-resistant key `__webcompy_transfer_meta__`. Top-level arrays/scalars are NOT supported in body mode — they must use header mode; attempting body mode with a non-object payload is an explicit error (no silent fallback).
- `TypedJSONResponse` for FastAPI in `webcompy_server.contrib.fastapi` (optional module, lazy FastAPI import): a thin `JSONResponse` subclass that applies `encode_with_meta` and emits header or body mode. FastAPI is NOT a dependency of the core packages; other frameworks (plain Starlette, Django, Flask) use `encode_with_meta` directly per documented recipes.
- Client side: `from_json` / the `response_type` path in `HttpClient` learns to recognize `X-WebComPy-Transfer-Meta` and `__webcompy_transfer_meta__` and applies metadata-driven restoration for the types schema-driven coercion cannot handle (`bytes`, `set`, `tuple`, `Decimal`, and concrete-type hints for `Any`/ambiguous fields). Absent metadata, behavior is exactly as specified in `typed-api-client`.
- Client-side decoding only: the server never decodes client-controlled metadata in this change, so no type allowlist is required here (that concern belongs to `feat-json-rpc`).

## Capabilities

### New Capabilities

- `typed-response`: Metadata-augmented responses (`encode_with_meta`, wire formats, `TypedJSONResponse`, client-side metadata consumption rules).

### Modified Capabilities

- `typed-api-client`: The `response_type` deserialization path SHALL recognize and apply transfer metadata (header and body-key forms) when present, layered on top of schema-driven coercion.

## Impact

- **Code**: core helper in `packages/webcompy/src/webcompy/hydration/` or a shared serde module (framework-neutral, dual-environment); `packages/webcompy-server/src/webcompy_server/contrib/fastapi.py` (new, optional); client recognition in `packages/webcompy/src/webcompy/ajax/` (`from_json`/`HttpClient` typed path).
- **APIs**: new public helpers; no changes to existing signatures.
- **Dependencies**: none required; FastAPI only when using the contrib module (lazy import).
- **Implementation order**: This change's delta targets the `typed-api-client` capability created by `feat-typed-api-client`; that change MUST be implemented and archived first.
- **Specs**: new `typed-response`; delta to `typed-api-client`.

## Known Issues Addressed

(none)

## Non-goals

- Server-side decoding of client-controlled metadata (RPC scope: `feat-json-rpc`, which introduces the allowlist).
- Contrib integrations for frameworks other than FastAPI (recipes documented; first-party modules deferred).
- Automatic OpenAPI schema adjustments for metadata-augmented endpoints.
- Metadata for request bodies (requests to FastAPI are already validated/typed by the server framework).
