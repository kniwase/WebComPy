# Typed API Client

## Purpose

`HttpClient` returns untyped `Response` objects; every caller hand-parses JSON into ad-hoc dicts. Because a WebComPy app package is shipped to the browser as a wheel, both the server and the browser can literally import the same schema module — a unique advantage over TypeScript-style RPC (tRPC/Hono), which needs compiler tricks to share types. A schema-driven typed client delivers typed API access against ANY plain-JSON HTTP API (including pre-existing third-party or in-house FastAPI services) without requiring server cooperation, code generation, or a custom wire format.

The schema-driven deserializer `from_json` reconstructs nested dataclasses from plain JSON using type annotations alone; `HttpClient` verb methods accept an optional `response_type` parameter so typed access flows through the existing `FetchPort`, preserving SSR/SSG in-process fetching and hydration transfer caching.

## Requirements

### Requirement: Schema-driven JSON deserialization
The framework SHALL provide `from_json(cls, data, *, strict=False) -> T`, a pure-Python, Pyodide-compatible deserializer that reconstructs nested dataclasses from plain JSON structures (dict/list/str/int/float/bool/None). It SHALL resolve target types from type annotations and SHALL support: nested dataclasses, `list[T]`, `dict[str, T]`, `Optional[T]`, and `Union` types (matched structurally in declaration order). The top-level target SHALL NOT be limited to dataclasses: supported container targets (`list[T]`, `dict[str, T]`) and scalar targets (`int`, `str`, `float`, `bool`, `datetime`, `date`, `time`, `UUID`, Enum) SHALL be validated/coerced with the same rules as dataclass fields. When a target annotation is `datetime`, `date`, or `time`, an ISO-8601 string value SHALL be parsed into that type; when the annotation is `UUID`, a string value SHALL be parsed via `UUID(...)`; when the annotation is an `Enum` subclass, the value SHALL be matched by enum value. The function SHALL NOT resolve classes from wire data (no module-qualified-name import from payload content).

#### Scenario: Flat dataclass reconstruction
- **WHEN** `from_json(User, {"id": 1, "name": "ada"})` is called for a dataclass `User(id: int, name: str)`
- **THEN** a `User(id=1, name="ada")` instance SHALL be returned

#### Scenario: Nested dataclass reconstruction
- **WHEN** `from_json(Team, {"name": "core", "members": [{"id": 1, "name": "ada"}]})` is called for `Team(name: str, members: list[User])`
- **THEN** the result SHALL be a `Team` whose `members[0]` is a `User` instance, not a dict

#### Scenario: Optional and Union fields
- **WHEN** a dataclass field is annotated `Team | None` and the value is `None`
- **THEN** the result SHALL be `None`
- **AND** when the value is an object, it SHALL be reconstructed as `Team`

#### Scenario: Top-level container and scalar targets
- **WHEN** `from_json(list[User], [{"id": 1, "name": "ada"}])` is called
- **THEN** a list of `User` instances SHALL be returned
- **AND** when `from_json(datetime, "2026-08-05T12:34:56")` is called, a `datetime` instance SHALL be returned
- **AND** scalar targets (`int`, `str`, `float`, `bool`, `UUID`, Enum) SHALL be validated/coerced with the same rules as dataclass fields

#### Scenario: ISO datetime coercion from annotation
- **WHEN** a dataclass field is annotated `created_at: datetime` and the JSON value is `"2026-08-05T12:34:56"`
- **THEN** the field SHALL be a `datetime` instance equal to `datetime.fromisoformat("2026-08-05T12:34:56")`
- **AND** no wire metadata SHALL be required for this coercion

#### Scenario: UUID and Enum coercion
- **WHEN** fields are annotated `id: UUID` and `role: Role` (an Enum) with JSON values `"123e4567-..."` and `"admin"`
- **THEN** the fields SHALL be a `UUID` instance and the `Role.ADMIN` member respectively

#### Scenario: Deserialization raises on schema mismatch
- **WHEN** a declared field is missing from the data or a value cannot be coerced to its annotation
- **THEN** a descriptive error SHALL be raised naming the field and the expected type

#### Scenario: InitVar fields are known but ignored
- **WHEN** a dataclass declares an `InitVar` field (present or absent in the data)
- **THEN** the field SHALL be skipped during reconstruction and never coerced
- **AND** in strict mode the field SHALL NOT be rejected as unknown

### Requirement: Lenient and strict validation modes
`from_json` SHALL default to `strict=False`, in which unknown keys in the data SHALL be ignored (forward compatibility with additive API changes). With `strict=True`, unknown keys SHALL be rejected, missing required fields SHALL be rejected, and any type mismatch SHALL raise an error. The strictness parameter SHALL apply uniformly to nested dataclasses.

#### Scenario: Unknown keys ignored by default
- **WHEN** `from_json(User, {"id": 1, "name": "ada", "new_field": 42})` is called with default strictness
- **THEN** reconstruction SHALL succeed and `new_field` SHALL be ignored

#### Scenario: Unknown keys rejected in strict mode
- **WHEN** `from_json(User, {"id": 1, "name": "ada", "new_field": 42}, strict=True)` is called
- **THEN** an error SHALL be raised naming `new_field`

### Requirement: Typed requests on HttpClient via response_type
`HttpClient` HTTP verb methods SHALL accept an optional keyword-only `response_type: type[T] | None` parameter. When omitted (or `None`), the method SHALL return `Response` exactly as before. When provided, the method SHALL parse the response body as JSON and SHALL return the result of `from_json(response_type, body)`. Typed requests SHALL go through the existing `FetchPort`, preserving self-site in-process fetching during SSR/SSG and hydration transfer caching. The methods SHALL be typed with `@overload` so that static type checkers infer `Response` when `response_type` is omitted and `T` when it is provided. A non-2xx response SHALL raise according to the existing error semantics before any deserialization; a JSON parse or schema mismatch SHALL raise a dedicated framework exception.

#### Scenario: Untyped call returns Response (backward compatible)
- **WHEN** `await HttpClient.get("/api/health")` is called without `response_type`
- **THEN** a `Response` instance SHALL be returned as before this change

#### Scenario: Typed call returns a reconstructed dataclass
- **WHEN** `await HttpClient.get("/api/users/1", response_type=User)` is called and the endpoint returns `{"id": 1, "name": "ada"}`
- **THEN** the result SHALL be a `User` instance
- **AND** static type checkers SHALL infer the result type as `User`

#### Scenario: Typed call returning a top-level list
- **WHEN** `await HttpClient.get("/api/users", response_type=list[User])` is called and the endpoint returns a bare JSON array
- **THEN** the result SHALL be a `list[User]` with dataclass instances
- **AND** static type checkers SHALL infer the result type as `list[User]`

#### Scenario: Typed call against an existing unmodified JSON API
- **WHEN** `response_type` is used against a third-party or pre-existing API that returns plain JSON with no WebComPy-specific metadata
- **THEN** deserialization SHALL succeed using schema-driven coercion alone

#### Scenario: Typed fetch during SSR uses the in-process path
- **WHEN** a component performs a typed self-site fetch during SSR against a mounted endpoint
- **THEN** the request SHALL be dispatched via the ASGI transport (no network I/O)
- **AND** the raw response SHALL be recorded in the hydration transfer cache as with any self-site fetch

#### Scenario: Deserialization errors participate in the error pipeline
- **WHEN** a typed fetch raises a schema-mismatch error during component setup or rendering inside an `ErrorBoundary`
- **THEN** the boundary SHALL engage its fallback as for any descendant error
- **AND** during SSG, an uncontained deserialization error SHALL fail the build

### Requirement: Typed deserialization shall consume transfer metadata when present
The `response_type` path of `HttpClient` and `from_json` SHALL recognize transfer metadata in both wire placements defined by `typed-response`: the `__webcompy_transfer_meta__` body key and the `X-WebComPy-Transfer-Meta` response header. When both are present (non-conforming servers), the body key SHALL take precedence. Metadata-driven restoration SHALL apply at the recorded paths and SHALL take precedence over schema-driven coercion for those exact values (restoring types such as `bytes`, `set`, `tuple`, and `Decimal` that annotations alone cannot identify). When no metadata is present, behavior SHALL remain purely schema-driven. `from_json` SHALL accept an optional `meta` parameter for standalone use.

#### Scenario: Bytes restoration via metadata
- **WHEN** a response body contains base64 text at a path recorded in metadata with type tag `bytes`
- **AND** the target field is annotated `bytes`
- **THEN** the reconstructed object SHALL contain the decoded `bytes` value

#### Scenario: Set restoration via metadata
- **WHEN** a JSON array is recorded in metadata with type tag `set` for a field annotated `set[str]`
- **THEN** the reconstructed field SHALL be a Python `set`, not a `list`

#### Scenario: Absent metadata behaves exactly as schema-driven
- **WHEN** a response carries neither `__webcompy_transfer_meta__` nor `X-WebComPy-Transfer-Meta`
- **THEN** deserialization SHALL behave exactly as specified by the schema-driven requirements

#### Scenario: Body key takes precedence over header
- **WHEN** both `__webcompy_transfer_meta__` and `X-WebComPy-Transfer-Meta` are present
- **THEN** the body key metadata SHALL be used

#### Scenario: Header-mode metadata with a top-level array or scalar body
- **WHEN** a response has a top-level array or scalar body and carries the `X-WebComPy-Transfer-Meta` header
- **THEN** metadata-driven restoration SHALL apply at the recorded paths
- **AND** paths SHALL be interpreted relative to the document root (the root value itself is addressed by the empty path per the path grammar)

### Requirement: Typed deserialization shall not require server cooperation
The typed client SHALL work against any HTTP API returning plain JSON. The framework SHALL NOT require response metadata, custom headers, or server-side WebComPy integration for `response_type` deserialization.

#### Scenario: Plain JSON endpoint
- **WHEN** an endpoint returns ordinary `application/json` with no WebComPy headers or body keys
- **THEN** `response_type` deserialization SHALL succeed

### Requirement: Already-typed values shall pass through from_json unchanged
`from_json` SHALL return a value that is already an instance of the target type unchanged, without re-validation, including when `strict=True`. Strict validation (unknown-key rejection, missing-required-field rejection, and type-mismatch errors) SHALL apply to JSON-derived values (dict/list/scalar inputs) only; a value that is already the target type is not a mismatch. This covers values restored from transfer metadata by registered type decoders (e.g., allowlist-registered custom types), which are reconstructed before schema-driven conversion and must survive it unchanged.

#### Scenario: Dataclass instance passes through in strict mode
- **WHEN** `from_json(User, user_instance, strict=True)` is called for a dataclass `User(id: int, name: str)` and an existing `User` instance `user_instance`
- **THEN** the same `user_instance` SHALL be returned unchanged

#### Scenario: Nested instance field is preserved
- **WHEN** `from_json(Team, {"name": "core", "members": [user_instance]}, strict=True)` is called for `Team(name: str, members: list[User])` and an existing `User` instance `user_instance`
- **THEN** the result SHALL contain the same `user_instance` at `members[0]`

#### Scenario: Dict inputs remain strictly validated
- **WHEN** `from_json(User, {"id": 1, "name": "ada", "extra": true}, strict=True)` is called
- **THEN** a `TypeError` SHALL be raised for the unknown key `extra`