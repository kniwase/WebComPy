# Typed Realtime Specification (delta)

## ADDED Requirements

### Requirement: use_websocket shall support typed messages via message_type

When `message_type=T` (a dataclass type) is passed to `use_websocket`, the returned handle SHALL become an `AsyncIterator[T]` and its `.send()` SHALL accept instances of `T`. Every other behavior of the raw handle (connection sharing, reconnection, `.state`, `.last_close`, `.close()`, lifecycle cleanup, SSR fallback) SHALL be unchanged. When `message_type` is `None` (default), the handle SHALL behave exactly as the raw text handle from `feat-websocket-composable`. A non-dataclass `message_type` SHALL raise a descriptive error at call time.

#### Scenario: Typed iteration

- **WHEN** `ws = use_websocket("/ws", message_type=ChatMessage)` for a dataclass `ChatMessage(user: str, text: str)` and a frame `{"user": "ada", "text": "hi"}` arrives
- **THEN** the iterator SHALL yield a `ChatMessage(user="ada", text="hi")` instance, not a `str` or `dict`

#### Scenario: Typed send

- **WHEN** `ws.send(ChatMessage(user="ada", text="hi"))` is called while connected
- **THEN** exactly one text frame SHALL be sent whose JSON body decodes to `{"user": "ada", "text": "hi", "__webcompy_transfer_meta__": {...}}` (meta member present, possibly empty-tagged only when no metadata-typed fields exist)

#### Scenario: Non-dataclass message_type is rejected

- **WHEN** `use_websocket("/ws", message_type=list[int])` is called
- **THEN** a descriptive error SHALL be raised explaining that typed realtime messages require a dataclass target

### Requirement: Typed frames shall use the typed-response body wire envelope

Send-side encoding SHALL use `encode_with_meta` and SHALL place the metadata map in the top-level `__webcompy_transfer_meta__` member of a single JSON object per frame. Receive-side decoding SHALL split off that member and reconstruct the payload via `from_json(T, payload, meta=meta, strict=strict)`. Metadata-typed fields (`datetime`, `UUID`, `Decimal`, Enum, and allowlist-registered custom types) SHALL round-trip with full type fidelity.

#### Scenario: Metadata field round trip

- **WHEN** a dataclass `Event(name: str, at: datetime)` is sent and received through typed handles
- **THEN** the receiver SHALL reconstruct `at` as a `datetime` instance, not a `str`

#### Scenario: Envelope shape

- **WHEN** a typed message is sent
- **THEN** the frame SHALL be a single JSON object containing the payload fields and the `__webcompy_transfer_meta__` member

### Requirement: Malformed typed frames shall be skipped and surfaced on last_error without killing the stream

A text frame that fails JSON parsing, fails `from_json` reconstruction, or references a type tag outside the closed builtin set and the registered allowlist SHALL NOT be yielded. The failure SHALL be recorded on `.last_error: Signal[Exception | None]` and logged as a warning; the subscription and the underlying connection SHALL remain alive and subsequent valid frames SHALL still be delivered. A subsequent successful frame SHALL reset `.last_error` to `None`.

#### Scenario: Bad frame is skipped

- **WHEN** frames `"not json"`, then a valid `ChatMessage` frame arrive on a typed handle
- **THEN** the first frame SHALL set `.last_error` and yield nothing
- **AND** the second frame SHALL be yielded normally and SHALL reset `.last_error` to `None`

#### Scenario: Unknown type tag is rejected, never resolved by name

- **WHEN** a frame's meta member references an unregistered type tag
- **THEN** the frame SHALL be skipped with `.last_error` set
- **AND** no class SHALL be imported or resolved from the wire tag

### Requirement: Typed reconstruction shall be strict by default

Receive-side reconstruction SHALL use `strict=True` unless the caller passes `strict=False`: frames with missing declared fields or undeclared extra fields SHALL be skipped via the skip-on-error path. `strict=False` SHALL use lenient coercion.

#### Scenario: Extra field rejected in strict mode

- **WHEN** a frame contains a field not declared on `message_type` and `strict=True`
- **THEN** the frame SHALL be skipped with `.last_error` set

#### Scenario: Lenient mode opts in

- **WHEN** the same frame arrives on a handle created with `strict=False`
- **THEN** the frame SHALL be reconstructed leniently and yielded

### Requirement: The realtime type allowlist shall be app-scoped and follow the json-rpc allowlist pattern

The framework SHALL provide `register_realtime_type_handler(cls, encoder, decoder)` importable from `webcompy` and `webcompy.realtime`, registering custom type handlers in a registry scoped to the app DI scope (never module-global). Send-side encoding SHALL use the registered encoders; receive-side decoding SHALL accept only builtin tags and registered tags. When no app DI scope is available, registration SHALL emit a `UserWarning` and SHALL be a no-op, and decoding SHALL accept only builtin tags.

#### Scenario: Custom type round trip

- **WHEN** `register_realtime_type_handler(Money, encode, decode)` is called within an app DI scope and a dataclass with a `Money` field is sent and received
- **THEN** the field SHALL round-trip as a `Money` instance

#### Scenario: Registration outside a DI scope warns

- **WHEN** `register_realtime_type_handler(...)` is called with no app DI scope
- **THEN** a `UserWarning` SHALL be emitted and the registration SHALL NOT take effect globally

### Requirement: Typed realtime shall not participate in hydration transfer

Typed messages, `.last_error`, and allowlist registrations SHALL NOT be collected into the hydration transfer payload. During SSR/SSG the typed handle SHALL behave as the raw handle's SSR fallback (empty iterator, `CLOSED`, warning).

#### Scenario: SSG output contains no typed realtime state

- **WHEN** a page using `use_websocket(url, message_type=T)` is statically generated
- **THEN** the hydration payload SHALL contain no typed message, error, or allowlist entry
