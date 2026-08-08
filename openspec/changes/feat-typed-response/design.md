# Design: feat-typed-response

## Context

`feat-typed-api-client` established that type restoration can be driven by client-held schemas for plain JSON. The residual gap is types whose JSON representation is ambiguous or lossy: `bytes` (no JSON representation at all), `set`/`tuple` (both serialize as arrays), `Decimal` (serializes as number or string with precision questions), and `Any`-typed fields where no annotation exists to drive coercion. The transfer-codec solves the same problem for hydration payloads, but its inline tagged representation (`__webcompy_type__` markers interleaved in the data) would pollute API response bodies and break OpenAPI accuracy. The superjson-style separation — pristine body plus a sidecar metadata map — keeps the body standard while giving a cooperating client full fidelity.

## Goals / Non-Goals

**Goals:**
- A single framework-neutral serialization helper that produces (plain JSON body, metadata) pairs.
- Two wire placements: response header (default) and inline body key for large metadata.
- Zero hard dependency on FastAPI; a thin contrib `TypedJSONResponse` for the common case.
- Client recognition integrated into the existing `response_type` path.

**Non-Goals:**
- Server-side decoding of untrusted metadata (allowlist concern — `feat-json-rpc`).
- Request-body metadata; non-FastAPI contrib modules; OpenAPI tooling.

## Decisions

### D1: Metadata is a path→type map over the pristine JSON body
`encode_with_meta(value)` walks the value and emits `(json_data, meta)` where `meta` maps JSON-ish paths (e.g. `"members[0].avatar"`) to type tags (`"bytes"`, `"set"`, `"tuple"`, `"decimal"`, ...). Path syntax: dot-separated keys with `[index]` for arrays — documented in the spec.

**Why**: keeping the body pristine is the whole point (progressive enhancement: non-WebComPy consumers see a normal API). Inline tags (transfer-codec style) were rejected for API surfaces because they alter the body schema. Alternatives considered for tag granularity — per-field vs whole-payload single tag — per-field paths win because they compose with nested dataclasses naturally.

### D2: Header mode is the default; body mode requires a top-level object
- Header mode: `X-WebComPy-Transfer-Meta: <json>`. Body stays pristine; OpenAPI stays truthful; non-WebComPy clients ignore the header.
- Body mode: metadata injected under `__webcompy_transfer_meta__` (consistent with the existing `__webcompy_*` key family). Required when metadata risks exceeding practical header size limits.
- Body mode with a top-level array/scalar is an explicit error (`WebComPyException` at encode time), NOT an implicit fallback to a wrapper shape. Callers use header mode, or restructure their payload as an object (e.g. `{"items": [...]}`, which also plays well with pagination).

**Why**: an implicit wrapper fallback creates two body shapes for the same endpoint and confuses both clients and OpenAPI. An explicit contract — "body mode requires object payloads" — is one rule, easy to validate and document. In practice, metadata-worthy responses (structured models) are objects; list-returning endpoints are typically simple or can adopt the items-wrapper idiom.

### D3: The helper is the canonical contract; contrib classes are sugar
`encode_with_meta` lives in a framework-neutral, dual-environment module (server-only usage in practice, but no server-only imports so it stays testable and reusable). `TypedJSONResponse(JSONResponse)` overrides `render()` to call the helper and set the header/body key — ~30 lines. Django/Flask/plain-Starlette users call the helper directly per docs recipes.

**Why**: the wire format must have exactly one normative definition. Framework adapters come and go; the contract stays. This also keeps FastAPI out of the dependency graph (lazy import in the contrib module only).

### D4: Client consumption layers meta on top of schema-driven coercion
The `response_type` path in `HttpClient` (and standalone `from_json` via an optional `meta` parameter) first parses the body, then applies metadata-driven restoration at the recorded paths, then runs schema-driven reconstruction. Metadata takes precedence for the exact paths it records (e.g. restoring `bytes` that schema coercion could never produce); everything else flows through `from_json` as before.

**Why**: schema-driven coercion remains the default workhorse; metadata is the exception channel. Precedence is unambiguous because metadata addresses concrete value positions, while annotations describe structure.

### D5: No allowlist in this change
Metadata decoding happens only in the browser/SSR client against responses from servers the app itself talks to. Type tags map to a fixed, closed set of restoration operations (bytes/set/tuple/decimal/datetime/...), not arbitrary class imports — so even a malicious server response cannot trigger code execution through this path. Arbitrary-class reconstruction from wire names remains exclusive to hydration (server-generated payloads) and is not extended here.

## Risks / Trade-offs

- [Header size limits (proxies commonly cap ~8-16KB total headers)] → body mode exists precisely for this; helper computes metadata size and `TypedJSONResponse` documents the trade-off; spec mandates the body-mode object-only contract.
- [Path grammar ambiguity with keys containing dots/brackets] → path segments are percent-encoded per the spec's grammar; tests cover exotic keys.
- [Two wire placements double client recognition logic] → recognition is a single check: body key presence first, else header (HttpClient sees headers; standalone `from_json` takes explicit `meta`). Spec fixes precedence: body key wins if both present (should not happen; servers pick one mode per response).
- [pydantic models as input] → helper accepts dataclasses, pydantic models (via `model_dump()` when available), and plain structures; pydantic handling is duck-typed, no import.

## Migration Plan

None — additive. APIs not using the helper are unaffected.

## Open Questions

- Exact path-grammar encoding (percent-encoding vs JSON Pointer) — finalize in implementation; JSON Pointer (RFC 6901) is the leading candidate since it is an existing standard with escaping rules. Its empty-string root reference naturally addresses top-level scalar/array payloads, which `feat-typed-api-client` now supports as `response_type` targets; body mode remains object-only per D2, so header mode is the sole metadata channel for such payloads.
