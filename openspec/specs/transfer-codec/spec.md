# Transfer Codec

## Purpose

The transfer codec is a layered serialization engine that extends JSON to preserve Python type information across the server-to-browser hydration boundary. Plain `json.dumps()` with a `default=str` fallback silently stringifies or drops non-JSON-native values (datetime, set, enum, dataclass, Decimal, bytes, tuple, Path, UUID), breaking hydration fidelity. The codec wraps such values in type-tagged dicts using a reserved `__webcompy_` key prefix, and reconstructs the original typed objects on the browser side.

The codec is pure Python with no external dependencies, so it works in both CPython (server) and PyScript/Emscripten (browser). It is layered: Layer 0 is stdlib JSON passthrough, Layer 1 provides built-in encoders/decoders for common standard-library types, and Layer 2 exposes a plugin API (`register_type_handler`) for custom and third-party types.

## Requirements

### Requirement: The codec shall provide encode and decode functions for hydration data

The `webcompy.hydration._codec` module SHALL provide `encode(value: Any) -> Any` and `decode(value: Any) -> Any` functions. `encode()` recursively transforms a Python value into a JSON-safe structure where non-JSON-native types are wrapped in type-tagged dicts. `decode()` recursively transforms a JSON-parsed structure back into Python objects, reconstructing typed values from type-tagged dicts. Both functions SHALL be pure Python with no external dependencies, ensuring they work in both CPython (server) and PyScript/Emscripten (browser) environments.

#### Scenario: Encoding a plain JSON-native value
- **WHEN** `encode(42)` is called
- **THEN** the return value SHALL be `42` (no type tag)

#### Scenario: Encoding a nested structure with mixed types
- **WHEN** `encode({"name": "Alice", "created": datetime(2026, 7, 4), "tags": {"a", "b"}})` is called
- **THEN** the return value SHALL be a dict with `"name"` as plain string, `"created"` as a type-tagged dict, and `"tags"` as a type-tagged dict

#### Scenario: Decoding a type-tagged structure
- **WHEN** `decode({"name": "Alice", "created": {"__webcompy_type__": "datetime", "__webcompy_value__": "2026-07-04T00:00:00"}})` is called
- **THEN** the return value SHALL be a dict with `"name"` as `"Alice"` and `"created"` as a `datetime.datetime(2026, 7, 4)` instance

#### Scenario: Round-trip encode then decode preserves value
- **WHEN** a value containing datetime, set, enum, and dataclass instances is encoded then decoded
- **THEN** the decoded value SHALL be equal to the original value (same types, same data)

### Requirement: Type tags shall use the reserved __webcompy_ key prefix

All type-tagged dicts SHALL use exactly two keys: `"__webcompy_type__"` (string identifying the type) and `"__webcompy_value__"` (the type-specific payload). The `"__webcompy_"` key prefix is framework-reserved. During decode, a dict SHALL be treated as a type tag if and only if it contains the key `"__webcompy_type__"`. A user dict without this key SHALL be decoded as a normal dict.

#### Scenario: Type-tagged dict structure
- **WHEN** `encode(datetime(2026, 7, 4))` is called
- **THEN** the return value SHALL be `{"__webcompy_type__": "datetime", "__webcompy_value__": "2026-07-04T00:00:00"}`

#### Scenario: User dict without reserved key is not treated as type tag
- **WHEN** `decode({"name": "Alice", "age": 30})` is called
- **THEN** the return value SHALL be `{"name": "Alice", "age": 30}` (decoded as a normal dict, no type reconstruction)

#### Scenario: Reserved key violation emits a warning
- **WHEN** `encode({"__webcompy_type__": "custom", "data": 123})` is called (user data contains the reserved key)
- **THEN** a warning SHALL be logged about the reserved-key violation
- **AND** the encode behavior for the violating dict is undefined (the decode side may interpret it as a type tag)

### Requirement: Layer 1 built-in encoders shall cover common standard-library types

The codec SHALL include built-in type handlers for the following types: `datetime.datetime`, `datetime.date`, `datetime.time`, `set`, `frozenset`, `enum.Enum`, `bytes`, `decimal.Decimal`, dataclass instances (via `dataclasses.is_dataclass`), `tuple`, `pathlib.Path`, and `uuid.UUID`. Each handler SHALL produce a type-tagged dict that round-trips correctly through `decode()`.

#### Scenario: Encoding datetime
- **WHEN** `encode(datetime.datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc))` is called
- **THEN** the type tag SHALL be `"datetime"` and the value SHALL be the ISO-format string
- **AND** `decode(result)` SHALL reconstruct an equal `datetime` instance with the same timezone

#### Scenario: Encoding set
- **WHEN** `encode({1, 2, 3})` is called
- **THEN** the type tag SHALL be `"set"` and the value SHALL be a list representation
- **AND** `decode(result)` SHALL reconstruct a `set` equal to `{1, 2, 3}`

#### Scenario: Encoding enum
- **WHEN** `encode(MyEnum.ACTIVE)` is called where `MyEnum` is defined in module `myapp.enums`
- **THEN** the type tag SHALL be `"enum"` and the value SHALL include the module name, enum class name, and member value
- **AND** `decode(result)` SHALL reconstruct the `MyEnum.ACTIVE` member via `importlib.import_module`

#### Scenario: Encoding a dataclass instance
- **WHEN** `encode(UserProfile(name="Alice", age=30))` is called where `UserProfile` is a dataclass in module `myapp.models`
- **THEN** the type tag SHALL be `"dataclass"` and the value SHALL include the module name, class name, and field dict
- **AND** each field value SHALL be encoded via the codec's recursive `encode()` (using `dataclasses.fields()`, NOT `dataclasses.asdict()`)
- **AND** `decode(result)` SHALL reconstruct a `UserProfile` instance via `importlib.import_module` and `cls(**decoded_fields)` where each field value is decoded recursively

#### Scenario: Encoding a nested dataclass preserves type fidelity
- **WHEN** `encode(User(name="Alice", address=Address(city="NYC")))` is called where both `User` and `Address` are dataclasses
- **THEN** the `address` field value SHALL be a type-tagged dict (`{"__webcompy_type__": "dataclass", ...}`), NOT a plain dict
- **AND** `decode(result)` SHALL reconstruct the `User` instance with `address` as an `Address` instance (not a dict)
- **AND** the encoder SHALL NOT use `dataclasses.asdict()` (which recursively strips type information from nested dataclasses)

#### Scenario: Encoding bytes
- **WHEN** `encode(b"hello")` is called
- **THEN** the type tag SHALL be `"bytes"` and the value SHALL be the base64-encoded string `"aGVsbG8="`
- **AND** `decode(result)` SHALL reconstruct `b"hello"`

#### Scenario: Encoding Decimal
- **WHEN** `encode(Decimal("3.14159"))` is called
- **THEN** the type tag SHALL be `"decimal"` and the value SHALL be the string `"3.14159"`
- **AND** `decode(result)` SHALL reconstruct `Decimal("3.14159")`

#### Scenario: Encoding tuple
- **WHEN** `encode((1, 2, 3))` is called
- **THEN** the type tag SHALL be `"tuple"` and the value SHALL be `[1, 2, 3]`
- **AND** `decode(result)` SHALL reconstruct `(1, 2, 3)` as a tuple (not a list)

### Requirement: The codec shall support a pluggable type-handler registry (Layer 2)

The codec SHALL provide `register_type_handler(cls: type, encoder: Callable[[Any], Any], decoder: Callable[[Any], Any]) -> None`. The encoder returns the JSON-safe *inner payload*; the codec wraps it as `{"__webcompy_type__": <qualified class name>, "__webcompy_value__": <encoder result>}`, so the plugin author never constructs the tag dict themselves. The decoder receives *only the inner payload* (the codec strips the `__webcompy_type__` envelope) and returns the reconstructed instance. The codec derives the type tag from the registered class's fully-qualified name (`{module}.{qualname}`), so the encoder and decoder never need to agree on a string identifier. Registered handlers SHALL be checked **first** during encode (before Layer 1 built-in handlers), allowing custom types to override built-in behavior. Registration is module-global and happens at import time. Both server and browser environments run the same app code, so both register the same handlers.

#### Scenario: Registering and using a custom type handler
- **WHEN** `register_type_handler(MyClass, my_encoder, my_decoder)` is called at import time
- **AND** `encode(MyClass(...))` is called during SSR
- **THEN** `my_encoder` SHALL be invoked to produce the inner payload, which the codec wraps as the type-tagged dict
- **AND** `decode(result)` SHALL strip the type-tag envelope and invoke `my_decoder` with the inner payload to reconstruct the `MyClass` instance

#### Scenario: Layer 2 handler takes precedence over Layer 1
- **WHEN** a handler for `datetime.datetime` is registered via `register_type_handler`
- **AND** `encode(some_datetime)` is called
- **THEN** the registered handler SHALL be used instead of the built-in datetime encoder

### Requirement: The codec shall detect and handle circular references

`encode()` SHALL maintain a set of `id()` values for objects currently in the encoding ancestor chain. If a circular reference is detected (an object's `id()` is already in the set), the encoder SHALL log a warning and return `None` for that value. The key containing the circular reference SHALL be preserved in the parent structure with a `None` value.

#### Scenario: Circular reference is dropped with warning
- **WHEN** `encode` encounters a dict that contains a reference to itself (directly or transitively)
- **THEN** a warning SHALL be logged indicating a circular reference was detected and dropped
- **AND** the circular value SHALL be replaced with `None` in the encoded output

### Requirement: The codec shall be backward-compatible with plain JSON values

Values that are already JSON-native (`str`, `int`, `float`, `bool`, `None`, `list`, `dict` without type tags) SHALL pass through `encode()` and `decode()` unchanged. This ensures existing v1 payloads without type tags decode correctly, and values that do not need type wrapping remain compact.

#### Scenario: Plain dict passes through unchanged
- **WHEN** `encode({"key": "value", "count": 42})` is called
- **THEN** the return value SHALL be `{"key": "value", "count": 42}` (no type tags added)

#### Scenario: v1 payload without type tags decodes correctly
- **WHEN** `decode({"async_results": {"cid": {"state": "success", "data": {"name": "Alice"}}}})` is called
- **THEN** the structure SHALL be returned as-is (no type reconstruction, since no `__webcompy_type__` keys are present)
