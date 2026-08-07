# Spec: typed-api-client

## ADDED Requirements

### Requirement: Schema-driven JSON deserialization
The framework SHALL provide `from_json(cls, data, *, strict=False) -> T`, a pure-Python, Pyodide-compatible deserializer that reconstructs nested dataclasses from plain JSON structures (dict/list/str/int/float/bool/None). It SHALL resolve target types from type annotations and SHALL support: nested dataclasses, `list[T]`, `dict[str, T]`, `Optional[T]`, and `Union` types (matched structurally in declaration order). When a target annotation is `datetime`, `date`, or `time`, an ISO-8601 string value SHALL be parsed into that type; when the annotation is `UUID`, a string value SHALL be parsed via `UUID(...)`; when the annotation is an `Enum` subclass, the value SHALL be matched by enum value. The function SHALL NOT resolve classes from wire data (no module-qualified-name import from payload content).

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

### Requirement: Typed deserialization shall not require server cooperation
The typed client SHALL work against any HTTP API returning plain JSON. The framework SHALL NOT require response metadata, custom headers, or server-side WebComPy integration for `response_type` deserialization.

#### Scenario: Plain JSON endpoint
- **WHEN** an endpoint returns ordinary `application/json` with no WebComPy headers or body keys
- **THEN** `response_type` deserialization SHALL succeed
