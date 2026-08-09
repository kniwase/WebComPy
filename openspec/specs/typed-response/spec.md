# Typed Response

## Purpose

The schema-driven typed client (`typed-api-client`) restores rich types from plain JSON using target annotations, which covers most real-world APIs. But some Python types cannot survive plain JSON even with schema knowledge on the client: `bytes` (no JSON representation), `set`/`tuple` (both serialize as arrays), `Decimal` (precision questions), and values behind `Any`-typed or polymorphic fields where the annotation alone cannot identify the concrete type. For APIs a project controls, the server can attach type metadata to responses so the client restores full fidelity — without breaking ordinary JSON consumers of the same API.

The metadata format keeps the response body pristine (progressive enhancement): a framework-neutral `encode_with_meta` helper produces `(plain_json, meta)` pairs where `meta` maps JSON Pointer paths to type tags, and the metadata travels either in the `X-WebComPy-Transfer-Meta` response header (default) or under the body key `__webcompy_transfer_meta__` (for large metadata; body mode requires a top-level object). A thin `TypedJSONResponse` contrib for FastAPI applies the helper; other frameworks call `encode_with_meta` directly. Client-side metadata decoding uses a fixed, closed set of type-tag restoration operations and never resolves classes from wire data, so no type allowlist is required.

## Requirements

### Requirement: Framework-neutral metadata encoder
The framework SHALL provide `encode_with_meta(value) -> tuple[json_data, meta]` where `json_data` is a pristine JSON-compatible structure (dict/list/str/int/float/bool/None) and `meta` is a mapping from value paths to type tags. The helper SHALL accept dataclasses, pydantic models (duck-typed via `model_dump()`, without importing pydantic), and plain structures. Type tags SHALL cover at minimum: `bytes` (base64 in body), `set`, `tuple`, `decimal`, `datetime`, `date`, `time`, `uuid`. Types already representable in JSON without ambiguity (str/int/float/bool/None, and nested dataclass structure) SHALL NOT produce metadata entries. The helper SHALL NOT import any web framework.

#### Scenario: Dataclass with non-JSON-native fields
- **WHEN** `encode_with_meta(record)` is called for a dataclass containing `avatar: bytes`, `tags: set[str]`, and `price: Decimal`
- **THEN** `json_data` SHALL contain base64 text for `avatar`, an array for `tags`, and a string for `price`
- **AND** `meta` SHALL record the type tag for each of those paths
- **AND** `json_data` SHALL contain no `__webcompy_` keys or other inline tags

#### Scenario: Pure-JSON value produces empty metadata
- **WHEN** `encode_with_meta({"a": 1, "b": ["x", True]})` is called
- **THEN** `meta` SHALL be empty and `json_data` SHALL equal the input structure

#### Scenario: pydantic model accepted without pydantic import
- **WHEN** `encode_with_meta(model)` is called for a pydantic model instance
- **THEN** serialization SHALL proceed via `model_dump()` and produce body and metadata as for an equivalent dataclass

### Requirement: Header wire mode
In header mode (the default), the response body SHALL be the pristine JSON representation and the metadata SHALL travel in the `X-WebComPy-Transfer-Meta` response header as JSON. API consumers that do not understand the header SHALL receive a completely ordinary JSON response.

#### Scenario: FastAPI endpoint with header mode
- **WHEN** an endpoint returns a metadata-augmented response in header mode
- **THEN** the response body SHALL be plain JSON with no metadata keys
- **AND** the `X-WebComPy-Transfer-Meta` header SHALL contain the metadata JSON
- **AND** a non-WebComPy HTTP client SHALL be able to consume the response normally

#### Scenario: Array payload in header mode
- **WHEN** a top-level array payload is encoded in header mode
- **THEN** the response body SHALL remain a pristine JSON array
- **AND** the metadata header SHALL record paths relative to the array root

### Requirement: Body wire mode requires a top-level object
In body mode, metadata SHALL be injected into the response body under the key `__webcompy_transfer_meta__`. Body mode SHALL require the payload to serialize to a top-level JSON object. If the payload is a top-level array or scalar, encoding in body mode SHALL raise an explicit error; there SHALL be NO implicit wrapper or fallback shape. Callers with array/scalar payloads SHALL use header mode or restructure the payload as an object.

#### Scenario: Object payload in body mode
- **WHEN** an object payload is encoded in body mode
- **THEN** the original fields SHALL remain at the top level of the body
- **AND** metadata SHALL appear under `__webcompy_transfer_meta__`
- **AND** a non-WebComPy client ignoring unknown keys SHALL still consume the data fields normally

#### Scenario: Array payload rejected in body mode
- **WHEN** a top-level list payload is encoded in body mode
- **THEN** an explicit error SHALL be raised instructing the caller to use header mode or an object payload
- **AND** no fallback wrapper JSON SHALL be produced

### Requirement: FastAPI TypedJSONResponse contrib module
The framework SHALL provide `TypedJSONResponse` in `webcompy_server.contrib.fastapi`, a thin `JSONResponse` subclass that applies `encode_with_meta` and emits the selected wire mode. The module SHALL import FastAPI/Starlette lazily so that neither becomes a dependency of core packages. The default mode SHALL be header mode; body mode SHALL be selectable per response.

#### Scenario: Returning a typed response from FastAPI
- **WHEN** an endpoint returns `TypedJSONResponse(record)`
- **THEN** the response SHALL carry metadata in header mode by default
- **AND** importing `webcompy_server` without FastAPI installed SHALL NOT fail (the contrib module SHALL raise a clear error only when actually imported without FastAPI)

### Requirement: Metadata decoding uses a closed set of type tags
Client-side restoration from metadata SHALL map type tags to a fixed, closed set of restoration operations. The decoder SHALL NOT import or resolve classes from names appearing in metadata. This guarantees metadata decoding cannot trigger code execution, without requiring a type allowlist in this change.

#### Scenario: Unknown type tag handling
- **WHEN** metadata contains a type tag the client does not recognize
- **THEN** the decoder SHALL raise a descriptive error (strict contexts) or leave the value as-is (default lenient behavior)
