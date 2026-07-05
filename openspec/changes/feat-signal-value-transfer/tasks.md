## 1. __signal_members__ Key Type Migration

- [x] 1.1 Change `SignalReceivable.__signal_members__` from `WeakValueDictionary[int, SignalBase]` to `dict[str, SignalBase]` in `packages/webcompy/src/webcompy/signal/_container.py`
- [x] 1.2 Update `__set_signal_member__` signature to accept `name: str` parameter: `__set_signal_member__(self, name: str, value: SignalBase)`
- [x] 1.3 Update `__setattr__` to pass the attribute name: `self.__set_signal_member__(name, value)`
- [x] 1.4 Update `computed_property` in `packages/webcompy/src/webcompy/signal/_computed.py` to register by method name (it already uses `instance.__dict__[name]`; ensure `__set_signal_member__(name, _computed)` is called)
- [x] 1.5 Verify `__purge_signal_members__()` still works correctly (iterates `.values()`, unaffected by key type)
- [x] 1.6 Grep for any code that accesses `__signal_members__` keys directly (expecting `id()` keys) and update

## 2. Payload Schema — signals Section

- [x] 2.1 Add `signals: dict[str, dict[str, Any]]` field to `TransferPayload` dataclass in `packages/webcompy/src/webcompy/hydration/_payload.py`
- [x] 2.2 Bump `__webcompy_transfer_version__` default to `2` and update `_SUPPORTED_VERSION = 2`
- [x] 2.3 Update `_to_serializable()` to include the `signals` section in the output dict
- [x] 2.4 Update `serialize_payload()` to encode signal values via `encode()` from `webcompy.hydration._codec`
- [x] 2.5 Update `deserialize_payload()` to parse the `signals` section and decode values via `decode()`
- [x] 2.6 Handle version 1 backward compatibility in `deserialize_payload()` — if version is 1, default `signals` to `{}`

## 3. Signal Value Collection

- [x] 3.1 Add Signal collection to `collect_transfer_data()` in `packages/webcompy/src/webcompy/hydration/_collect.py`
- [x] 3.2 Extend the `_walk_component_*` tree traversal to also collect `__signal_members__` from each `Component`
- [x] 3.3 For each `(name, signal)` in `__signal_members__`, call `encode(signal._value)` and store in `signals[component_id][name]`
- [x] 3.4 Handle codec failures gracefully — if `encode()` raises or returns a non-serializable value, drop the entry with a warning
- [x] 3.5 Ensure collection happens after `await scheduler.await_pending()` in the SSR/SSG entry points (coordinate with `feat-async-scheduler-port` call ordering)

## 4. Signal Value Restoration

- [x] 4.1 Create `packages/webcompy/src/webcompy/hydration/_restore.py` with `restore_signal_values(component, signals_data: dict[str, Any]) -> None`
- [x] 4.2 For each `(name, encoded_value)` in `signals_data`, look up `component.__signal_members__.get(name)` and set `signal._value = decode(encoded_value)` directly (no `set_value()`)
- [x] 4.3 Handle missing `attr_name` in `__signal_members__` gracefully (skip with no error — best-effort)
- [x] 4.4 Export `restore_signal_values` from `packages/webcompy/src/webcompy/hydration/__init__.py`

## 5. Browser Restoration Integration

- [x] 5.1 Modify `Component._render()` in `packages/webcompy/src/webcompy/components/_component.py` to call `restore_signal_values(self, ...)` after `__init_component()` / `__setup()` completes and before template evaluation
- [x] 5.2 Read the component's signal data from `payload.signals.get(self._property["component_id"], {})` via `HYDRATION_DATA_KEY`
- [x] 5.3 Ensure restoration only runs in browser environment (or when transfer data is present)
- [x] 5.4 Guard: if `HYDRATION_DATA_KEY` is not provided (no transfer data), skip restoration entirely

## 6. SSR Collection Integration

- [x] 6.1 Verify `collect_transfer_data(root)` is called after `await scheduler.await_pending()` in `generate_html()` (`packages/webcompy-server/src/webcompy_server/_html.py`)
- [x] 6.2 Verify the same call ordering in the ASGI HTML handler (`packages/webcompy-cli/src/webcompy_cli/_server.py`)
- [x] 6.3 Verify the same call ordering in the SSG route fetch path (`packages/webcompy-cli/src/webcompy_cli/_generate.py`)

## 7. Unit Tests

- [x] 7.1 Test `__signal_members__` tracks Signals by attribute name (assign, reassign, non-Signal values)
- [x] 7.2 Test `computed_property` registers Computed by method name
- [x] 7.3 Test `collect_transfer_data()` collects Signal, Computed, ReactiveList, ReactiveDict values
- [x] 7.4 Test collection drops non-serializable values with warning
- [x] 7.5 Test `restore_signal_values()` restores `_value` directly without triggering notifications
- [x] 7.6 Test Computed cached value is restored without recompute
- [x] 7.7 Test missing attr_name in `__signal_members__` is handled gracefully
- [x] 7.8 Test version 2 payload serialization/deserialization with signals section
- [x] 7.9 Test version 1 payload backward compatibility (signals defaults to `{}`)
- [x] 7.10 Test component with no `self`-assigned Signals produces empty signals entry
- [x] 7.11 Test round-trip: SSR collect → encode → serialize → deserialize → decode → browser restore produces correct values

## 8. Verification

- [x] 8.1 Run `uv run ruff check .` and `uv run ruff format --check .`
- [x] 8.2 Run `uv run pyright`
- [x] 8.3 Run `uv run python -m pytest tests/ --tb=short`
- [x] 8.4 Run `scripts/run-e2e-tests.sh` — verify no flash of default values during hydration on pages with Signal-based state
- [x] 8.5 `npx @fission-ai/openspec@latest validate` passes
