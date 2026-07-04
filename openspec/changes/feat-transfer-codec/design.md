# Design: Transfer Codec Engine

## Context

WebComPy's hydration data transfer serializes server-side state into a JSON payload embedded in HTML. The current serializer (`hydration/_payload.py`) uses `json.dumps(value, default=str)` — a blunt instrument that stringifies any non-JSON-native value, losing type information. When the browser deserializes, it receives a string instead of a `datetime`, `set`, or `dataclass` instance.

The upcoming `feat-signal-value-transfer` will extend transfer to all Signal values, where the type variety is much broader. A robust codec is a prerequisite.

The codec must work in **both environments**:
- **Server (CPython)**: Encoding during SSR/SSG.
- **Browser (PyScript/Emscripten)**: Decoding during hydration.

This rules out native-extension-backed libraries (Pydantic v2's `pydantic-core` is Rust and may not run under Emscripten). The codec must be pure Python, with no external dependencies.

## Goals / Non-Goals

**Goals:**

- Encode/decode common Python standard-library types (datetime, set, enum, dataclass, Decimal, bytes, tuple, Path, UUID) in pure Python.
- Provide a plugin API (`register_type_handler`) for custom and third-party types.
- Avoid key collisions with user data via a reserved `__webcompy_` key prefix.
- Detect and gracefully handle circular references (drop with warning).
- Be backward-compatible with existing plain-JSON payloads.

**Non-Goals:**

- Signal value collection/restoration (that's `feat-signal-value-transfer`).
- Payload compression (that's `feat-payload-compression`).
- Pydantic/msgspec/marshmallow integration (future plugins via the Layer 2 API).
- Streaming or incremental encoding (single-pass encode/decode).

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  encode(value) -> JSON-safe structure                        │
│  decode(value) -> Python object                              │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Layer 2: Pluggable Type Registry                      │  │
│  │  register_type_handler(cls, encoder, decoder)          │  │
│  │  • Checked first during encode                         │  │
│  │  • Pydantic/custom classes plug in here (future)       │  │
│  └──────────────────────────┬────────────────────────────┘  │
│                              ▼                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Layer 1: Built-in Extended Encoders (pure Python)     │  │
│  │  datetime → {"__webcompy_type__":"datetime",            │  │
│  │             "__webcompy_value__":"2026-07-04T12:00:00"} │  │
│  │  set      → {"__webcompy_type__":"set",                 │  │
│  │             "__webcompy_value__":[...]}                 │  │
│  │  enum    → {"__webcompy_type__":"enum",                 │  │
│  │            "__webcompy_value__":{"module":...,"name":...,│  │
│  │                              "value":...}}              │  │
│  │  dataclass→ {"__webcompy_type__":"dataclass",           │  │
│  │             "__webcompy_value__":{"module":...,"name":...,│  │
│  │                              "fields":{...}}}           │  │
│  │  ... (date, time, frozenset, bytes, Decimal, tuple,    │  │
│  │       Path, UUID)                                      │  │
│  └──────────────────────────┬────────────────────────────┘  │
│                              ▼                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Layer 0: stdlib json (passthrough)                    │  │
│  │  str, int, float, bool, None, list, dict               │  │
│  │  → encoded as-is (no type tag)                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Decisions

### D1: Inline type-tagged dicts with reserved `__webcompy_` prefix

Each non-JSON-native value is wrapped in a two-key dict:

```python
{
    "__webcompy_type__": "datetime",
    "__webcompy_value__": "2026-07-04T12:00:00"
}
```

**Key collision avoidance:**
- The `__webcompy_` prefix is **framework-reserved**, analogous to Python's `__dunder__` convention. User data dicts should not use keys starting with `__webcompy_`.
- During decode, a dict is treated as a type tag **if and only if** it contains the key `"__webcompy_type__"`. A user dict without this key is decoded as a normal dict.
- During encode, if a user dict legitimately contains `__webcompy_type__` (a reserved-key violation), the encoder SHALL detect this and emit a warning. The value is still encoded, but the decode side will interpret it as a type tag — this is documented as undefined behavior for reserved-key violations.

**Alternatives considered:**
- **Separated format (superjson style)**: `{"json": <clean data>, "meta": {"paths": {"0.key": ["Date"]}}}` — keeps data clean and readable by external tools. But requires path tracking and two-pass encoding. Rejected for implementation complexity; the payload is internal, not consumed by external JSON tools.
- **Opaque base64 wrapper**: Encode the entire value as a base64 blob. Loses readability and debuggability entirely. Rejected.

### D2: Layer 2 plugin API — global registry, checked first

```python
_type_handlers: dict[type, tuple[Callable, Callable]] = {}

def register_type_handler(
    cls: type,
    encoder: Callable[[Any], dict],   # instance -> {"__webcompy_type__": "...", ...}
    decoder: Callable[[dict], Any],   # {"__webcompy_value__": ...} -> instance
) -> None:
    _type_handlers[cls] = (encoder, decoder)
```

During `encode()`, the encoder checks `_type_handlers` **first** (Layer 2), then built-in handlers (Layer 1), then JSON-native passthrough (Layer 0). This allows custom handlers to override built-in behavior if desired (e.g., a Pydantic handler that handles dataclass-like models differently).

Registration is **module-global** (not per-request). App code calls `register_type_handler(MyClass, ...)` at import time. Both server and browser run the same app code (bundled in the wheel), so both sides register the same handlers.

**Rationale:** Global registry is simplest and matches Python's module-level singleton pattern. Per-request registries would require DI plumbing and complicate the codec's usage in `_payload.py`.

### D3: dataclass and enum reconstruction via importlib

For `dataclass` and `enum` types, the encoder stores the fully-qualified module and class name:

```python
# dataclass
{"__webcompy_type__": "dataclass",
 "__webcompy_value__": {"module": "myapp.models", "name": "UserProfile",
                         "fields": {"name": "Alice", "age": 30}}}

# enum
{"__webcompy_type__": "enum",
 "__webcompy_value__": {"module": "myapp.enums", "name": "Status",
                         "value": "active"}}
```

The decoder uses `importlib.import_module(module)` to retrieve the class, then reconstructs:
- dataclass: `cls(**{k: decode(v) for k, v in fields.items()})` — each field value is decoded recursively before being passed to the constructor
- enum: `cls(value)` (lookup by value)

**Critical: nested dataclass fidelity.** The encoder MUST NOT use `dataclasses.asdict()`, because `asdict()` recursively converts nested dataclass instances to plain dicts before the codec's `encode()` can process them. A dataclass like `User(name="Alice", address=Address(city="NYC"))` would lose the `Address` type tag if `asdict()` were used. Instead, the encoder SHALL use `dataclasses.fields(instance)` and call `encode()` on each field value individually, so nested dataclasses (and any other non-JSON-native field types) are type-tagged correctly:

```python
fields = {f.name: encode(getattr(instance, f.name)) for f in dataclasses.fields(instance)}
```

The decoder SHALL apply `decode()` to each field value before passing them to the constructor, so nested type tags are reconstructed:

```python
decoded_fields = {k: decode(v) for k, v in fields.items()}
instance = cls(**decoded_fields)
```

**Key assumption:** The app code is bundled into the browser wheel via PyScript. The same modules exist on both server and browser. `importlib.import_module()` must work under PyScript — this is a **validation spike** (see Risks).

### D4: Circular reference detection via id() tracking

`encode()` maintains a `set[int]` of `id()` values for objects currently being encoded (the ancestor chain). If an object's `id()` is already in the set, a circular reference is detected. The encoder SHALL:

1. Log a warning: "Circular reference detected in transfer value; dropping."
2. Return `None` for the circular reference (the key is preserved with a `None` value).

This is consistent with the existing AsyncResult behavior of dropping non-serializable values with a warning.

### D5: bytes encoding via base64

`bytes` values are base64-encoded as strings:

```python
{"__webcompy_type__": "bytes",
 "__webcompy_value__": "aGVsbG8="}
```

Base64 is used (not hex) for compactness with large byte sequences.

### D6: Decimal encoding as string

`Decimal` values are encoded as their string representation to preserve precision:

```python
{"__webcompy_type__": "decimal",
 "__webcompy_value__": "3.14159"}
```

`Decimal(str)` reconstructs the exact value on decode.

### D7: tuple vs list distinction

JSON has no tuple type. Tuples are encoded with a type tag to distinguish them from lists:

```python
{"__webcompy_type__": "tuple",
 "__webcompy_value__": [1, 2, 3]}
```

Lists are encoded as plain JSON arrays (no tag).

## Risks / Trade-offs

- **[importlib under PyScript]** → Mitigation: Validation spike before full implementation. Use `webcompy inspect` CLI to test `importlib.import_module("myapp.models")` in a PyScript context. If importlib is unavailable, dataclass/enum reconstruction falls back to dict representation with a warning.

- **[Payload size increase from type tags]** → Mitigation: Type tags are only added for non-JSON-native values. Plain JSON values (the majority of typical payloads) are unchanged. For large data, `feat-payload-compression` addresses size at a higher layer.

- **[Reserved key violation by user data]** → Mitigation: The `__webcompy_` prefix is documented as reserved. The encoder warns on detection. The probability of natural collision is near-zero for well-named data.

- **[Global registry thread safety]** → Mitigation: Registration happens at import time (single-threaded module load). The registry is read-only during encode/decode. No locking needed.

- **[Performance of recursive encode/decode]** → Mitigation: The codec processes typical payloads ( dozens of entries, not millions). Recursive traversal of nested structures has acceptable overhead. A hot-path optimization (pre-checking `json.dumps` success before codec traversal) can be added if profiling indicates a need.

## Open Questions

1. **Should `datetime` encoding include timezone info?** `datetime.isoformat()` includes timezone if present. This should be sufficient for round-trip fidelity. Verify during implementation.

2. **Should the codec support `NamedTuple`?** NamedTuples are tuples with field names. They can be encoded as regular tuples (losing field names) or with a dedicated handler. Deferred — regular tuple encoding is the baseline; a NamedTuple handler can be added via Layer 2 if needed.

3. **Should the codec handle `__slots__`-based classes?** These are not dataclasses and have no standard serialization protocol. Deferred to Layer 2 custom handlers.
