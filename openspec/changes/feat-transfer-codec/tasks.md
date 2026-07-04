## 1. Codec Core

- [ ] 1.1 Create `packages/webcompy/src/webcompy/hydration/_codec.py` with `encode(value: Any) -> Any` and `decode(value: Any) -> Any` function signatures
- [ ] 1.2 Implement the Layer 0 passthrough: JSON-native types (`str`, `int`, `float`, `bool`, `None`, `list`, `dict`) are returned as-is by `encode()` and `decode()` (with dict/list recursive traversal)
- [ ] 1.3 Implement circular reference detection in `encode()` using an `id()` set tracking the ancestor chain; on detection, log a warning and return `None`

## 2. Layer 1 Built-in Type Handlers

- [ ] 2.1 Implement `datetime.datetime` handler — encode via `isoformat()`, decode via `datetime.fromisoformat()`
- [ ] 2.2 Implement `datetime.date` handler — encode via `isoformat()`, decode via `date.fromisoformat()`
- [ ] 2.3 Implement `datetime.time` handler — encode via `isoformat()`, decode via `time.fromisoformat()`
- [ ] 2.4 Implement `set` handler — encode as list, decode via `set()`
- [ ] 2.5 Implement `frozenset` handler — encode as list with `"frozenset"` tag, decode via `frozenset()`
- [ ] 2.6 Implement `enum.Enum` handler — encode as `{"module": ..., "name": ..., "value": ...}`, decode via `importlib.import_module(module).Name(value)`
- [ ] 2.7 Implement `bytes` handler — encode via `base64.b64encode()`, decode via `base64.b64decode()`
- [ ] 2.8 Implement `decimal.Decimal` handler — encode as string, decode via `Decimal(str)`
- [ ] 2.9 Implement `dataclass` instance handler — encode via `dataclasses.fields()` with per-field recursive `encode()` (NOT `asdict()`, which strips nested type info), plus module/name metadata; decode via `importlib.import_module(module).Name(**{k: decode(v) for k, v in fields.items()})`
- [ ] 2.10 Implement `tuple` handler — encode as list with `"tuple"` tag, decode via `tuple()`
- [ ] 2.11 Implement `pathlib.Path` handler — encode as string, decode via `Path(str)`
- [ ] 2.12 Implement `uuid.UUID` handler — encode as string, decode via `UUID(str)`
- [ ] 2.13 Register all Layer 1 handlers in the encode/decode dispatch tables

## 3. Layer 2 Plugin API

- [ ] 3.1 Implement `register_type_handler(cls: type, encoder: Callable, decoder: Callable) -> None` storing handlers in a module-global `_type_handlers` dict
- [ ] 3.2 Ensure Layer 2 handlers are checked **first** in `encode()` (before Layer 1 built-in handlers)
- [ ] 3.3 Implement reserved-key violation detection in `encode()`: if a plain dict contains `"__webcompy_type__"`, log a warning

## 4. Public API Exports

- [ ] 4.1 Export `encode`, `decode`, `register_type_handler` from `packages/webcompy/src/webcompy/hydration/__init__.py`

## 5. Payload Integration

- [ ] 5.1 Modify `_try_serialize_value()` in `packages/webcompy/src/webcompy/hydration/_payload.py` to use `encode()` instead of `json.dumps()` probing
- [ ] 5.2 Modify `serialize_payload()` to apply `encode()` to `TransferAsyncResultEntry.data` before `json.dumps()`
- [ ] 5.3 Modify `deserialize_payload()` to apply `decode()` after `json.loads()`
- [ ] 5.4 Modify `_collect.py` to pass `AsyncResult` data through `encode()` when building `TransferAsyncResultEntry`
- [ ] 5.5 Verify `__webcompy_transfer_version__` remains `1` (the codec does not change the payload schema; version bump to 2 is deferred to `feat-signal-value-transfer`)

## 6. Validation Spike

- [ ] 6.1 Verify `importlib.import_module("myapp.models")` works under PyScript using `webcompy inspect` CLI with a minimal test app containing a dataclass — confirm dataclass reconstruction is feasible in the browser environment

## 7. Unit Tests

- [ ] 7.1 Test round-trip encode/decode for each Layer 1 type (datetime, date, time, set, frozenset, enum, bytes, Decimal, dataclass, tuple, Path, UUID)
- [ ] 7.2 Test nested structures (dict containing set containing datetime, etc.) round-trip correctly
- [ ] 7.2a Test nested dataclass round-trip: a dataclass field whose value is another dataclass instance SHALL preserve the inner type tag through encode/decode (verify `asdict()` is NOT used)
- [ ] 7.3 Test circular reference detection (dict containing self-reference) drops the value with warning
- [ ] 7.4 Test Layer 2 plugin registration and precedence over Layer 1
- [ ] 7.5 Test reserved-key violation detection (user dict with `__webcompy_type__`) emits warning
- [ ] 7.6 Test backward compatibility: plain JSON values pass through unchanged
- [ ] 7.7 Test that existing AsyncResult transfer still works (payload v1 compatibility)
- [ ] 7.8 Test non-serializable value (e.g., file object) is dropped with warning

## 8. Verification

- [ ] 8.1 Run `uv run ruff check .` and `uv run ruff format --check .`
- [ ] 8.2 Run `uv run pyright`
- [ ] 8.3 Run `uv run python -m pytest tests/ --tb=short`
- [ ] 8.4 Run `scripts/run-e2e-tests.sh` (no regression in existing hydration data transfer)
- [ ] 8.5 `npx @fission-ai/openspec@latest validate` passes
