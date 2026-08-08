# Design: feat-typed-api-client

## Context

`HttpClient` (packages/webcompy/src/webcompy/ajax/_fetch.py) exposes classmethod HTTP verbs returning `Response`, delegating to `inject(FETCH_PORT_KEY).fetch(...)`. The hydration transfer codec (`webcompy/hydration/_codec.py`) already serializes rich Python types, but its dataclass reconstruction resolves classes by module-qualified name — fine for server-generated hydration payloads, unnecessary for client-side decoding of ordinary JSON API responses. The key insight behind this design: when the client already holds the target schema (a dataclass it can import), the type annotations themselves carry all the information needed to restore rich types from plain JSON — no wire metadata required.

## Goals / Non-Goals

**Goals:**
- Typed API access against any plain-JSON HTTP API, client-side only, zero server cooperation.
- Full generics support so `HttpClient.get(url, response_type=User)` is statically typed as `User`.
- Nested dataclass reconstruction including containers (`list`/`dict`/`Optional`/`Union`) and leaf coercion (`datetime`, `date`, `time`, `UUID`, `Enum`).
- SSR/SSG in-process fetching and hydration bake continue to work transparently; explicit opt-out (`transfer=False`) for runtime-only data.

**Non-Goals:**
- Server-side meta production/consumption (`feat-typed-response`).
- RPC dispatch (`feat-json-rpc`).
- Chained proxy clients, OpenAPI codegen, pydantic integration.

## Decisions

### D1: Self-contained deserializer instead of dacite/cattrs
`from_json` is implemented in ~100 lines using `dataclasses.fields()` + `typing.get_type_hints()` + `typing.get_origin()/get_args()`.

**Why**: external serde libraries would need to be resolvable as browser dependencies (Pyodide wheel availability), adding supply-chain and bundle risk for a small, well-understood problem. Alternatives considered: dacite (pure Python but an extra dependency to vendor into the browser), pydantic (heavyweight in Pyodide, and forces pydantic on browser code). The transfer-codec stays untouched — it serves hydration; `from_json` serves API responses.

### D2: Type-annotation-driven leaf coercion
When the target annotation is `datetime`, an ISO-8601 string value is parsed via `datetime.fromisoformat()`; similarly `date`/`time`/`UUID`/`Enum`. No tagging on the wire.

**Why**: ISO strings are what real JSON APIs (FastAPI included) already emit. The annotation tells us the intended type, so the wire stays pristine plain JSON and existing APIs work unchanged.

### D3: Asymmetric validation — lenient client by default
`strict=False`: unknown keys ignored, coercion failures raise a descriptive `TypeError`/`ValueError` only for fields the schema actually declares. `strict=True`: unknown keys rejected, missing required fields rejected.

**Why**: deployed static frontends can lag behind API evolution; a client that hard-fails on unknown keys breaks under routine additive API changes. Strictness belongs to trust boundaries (servers), and `feat-json-rpc` will reuse `from_json` with `strict=True`-style semantics plus an allowlist.

### D4: `response_type` on existing `HttpClient` methods via overloads
```python
@overload
async def get(url: str, *, response_type: None = None, ...) -> Response: ...
@overload
async def get(url: str, *, response_type: type[T], ...) -> T: ...
```
**Why**: keeps one entry point, is discoverable, and preserves backward compatibility. A separate `typed_get()` family would fork the API surface. Overloads are the established pyright-friendly pattern for "return type depends on an optional argument".

Error handling: non-2xx responses raise for status before deserialization (existing `raise_for_status` semantics preserved); JSON parse or schema mismatch raises a dedicated `TypedResponseError` (a plain `Exception` subclass, deliberately NOT a `WebComPyException`, so that `ErrorBoundary` and the error pipeline can catch it) carrying the response excerpt.

### D5: `transfer=False` on `use_async_result` implemented at collection time
The async-result entry is marked non-transferable; `collect_transfer_data()` skips marked entries. On hydration the browser finds no transferred entry and executes the fetch on the client (existing fallback behavior of `use_async_result`).

**Why**: marking at the composable is the least invasive point — components declare intent where the fetch is defined. Alternative (URL-pattern exclusion lists in config) was rejected: it splits intent away from the call site and is fragile under refactors. During SSG the fetch still executes at build time (the page needs content), but its result is not persisted — matching the semantics "never bake this into artifacts".

Note: for data that must NOT even be fetched at build time, `ClientOnly` remains the tool; `transfer=False` governs persistence, not execution timing. The spec states this explicitly.

Precedent: the storage persistence composables (`use_local_storage`/`use_session_storage`, `composables` spec) already establish the same exclusion pattern ("Storage-backed signals are excluded from SSR transfer"). The implementation SHOULD follow that established pattern (and reuse shared exclusion plumbing where it exists) rather than introducing a parallel mechanism.

## Risks / Trade-offs

- [`get_type_hints()` on browser-shipped modules may hit forward-reference edge cases] → resolve hints at call time with the module's globalns; add tests for `from __future__ import annotations` schemas, which the wheel builder must keep functional.
- [Union coercion ambiguity (e.g. `Union[int, str]` matching both)] → coercion tries alternatives in declaration order; first structural match wins; documented.
- [Deeply nested schemas cost runtime reflection per call] → cache resolved type hints per class (`functools.lru_cache`-style dict on the module); Pyodide-safe.
- [Users expect pydantic-style validation strictness] → documented non-goal; `strict=True` covers structural checks only, not value constraints (no `gt=0`-style validators).
- [Deserialization errors raised during component setup/render interact with the error pipeline] → Desirable, no special handling: `TypedResponseError` is an ordinary (non-`WebComPyException`) error, so an `ErrorBoundary` can catch it and render a fallback (`error-handling` spec); during SSG an uncontained error fails the build, so pages with schema mismatches never ship as static artifacts.

## Migration Plan

None — additive API. Existing `HttpClient` calls are unchanged.

## Open Questions

- Exact module placement (`webcompy/ajax/_serde.py` vs a new `webcompy/serde/` package if `feat-typed-response`/`feat-json-rpc` reuse grows) — decide at implementation; public import path is re-exported from `webcompy.ajax` either way.
- Non-object top-level bodies (bare arrays, scalars) cannot carry in-body wire metadata. `feat-typed-response` already resolves this: header mode (the default) is the sole metadata channel for such payloads, and body mode is object-only by explicit contract (its D2).
