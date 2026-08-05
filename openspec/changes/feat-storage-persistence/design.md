# Design: Storage Persistence Composables

## Decisions

### D1. API shape

```python
# packages/webcompy/src/webcompy/storage/_composable.py

@overload
def use_local_storage(key: str, default: T) -> Reactive[T]: ...
@overload
def use_local_storage(key: str, default: Callable[[], T]) -> Reactive[T]: ...

@overload
def use_session_storage(key: str, default: T) -> Reactive[T]: ...
@overload
def use_session_storage(key: str, default: Callable[[], T]) -> Reactive[T]: ...
```

- `default` is a value or a zero-argument factory. Detect callables with `callable(default)`; zero-arg validation reuses the same warning philosophy as `use_state`'s `_validate_factory` (a factory requiring arguments → `UserWarning`, treated as a plain value is NOT attempted — call it and let it raise, matching `use_state` behavior of calling the factory).
- Returns a plain `Reactive[T]` (the framework's `Signal` alias). No wrapper class — template/`:bind`/event-handler usage is identical to any other signal.

### D2. Module layout

New package `packages/webcompy/src/webcompy/storage/`:

- `storage/__init__.py` — re-exports `use_local_storage`, `use_session_storage`.
- `storage/_composable.py` — implementation.

Top-level `webcompy/__init__.py` re-exports both names (same treatment as `use_state`).

Rationale for a new package rather than `signal/_composable.py`: storage access is browser-environment-specific I/O, not a signal primitive; a separate package keeps `signal/` free of environment guards beyond what it already has, and gives the File→Spec mapping a clean row (`webcompy/storage/` → `composables`).

### D3. Environment guard and browser access

- Environment detection uses the existing `webcompy.utils._environment.ENVIRONMENT` (`"pyscript"` vs `"other"`, based on `platform.system() == "Emscripten"`).
- Storage access happens ONLY under `if ENVIRONMENT == "pyscript":`. The storage object is obtained via `from pyscript import context` then `context.window.localStorage` / `context.window.sessionStorage` (established pattern: `router/_link.py:93`, `router/_lazy.py:52`, `logging.py:18`).
- On the server, `use_*_storage()` returns `Reactive(_resolve_default())` immediately — no import of `pyscript`, no storage attribute access. This guarantees SSG determinism and makes server-side unit tests trivial.

### D4. Read-on-create, write-on-update

Creation (browser path):

1. `raw = storage.getItem(key)` (PyScript proxy call; returns `None`/`null` when absent — treat both as missing).
2. If missing → initial value = `_resolve_default()`.
3. Else `json.loads(str(raw))`; on `json.JSONDecodeError`/`TypeError`/`ValueError` → `logging.warning(...)` and initial value = `_resolve_default()`. The corrupted entry is left in place (the next successful write overwrites it); it is NOT deleted automatically.

Write-back:

- `sig.on_after_updating(lambda _: _write())` where `_write` does `storage.setItem(key, json.dumps(sig.value))`.
- `on_after_updating` returns a `CallbackConsumerNode` that the signal itself retains (`signal/_base.py:94-96`), so the subscription lives exactly as long as the returned `Reactive` — no explicit cleanup, no leak, no component-context requirement.
- `json.dumps` raising `TypeError` (non-serializable value) → `logging.warning(...)` and the write is skipped (in-memory signal still updates normally).
- `setItem` itself raising (quota exceeded, privacy mode) → caught broadly (`Exception`), logged, swallowed. Storage failure must never break reactivity.

The equality contract (`old is new or old == new` → no notification) automatically suppresses redundant writes for same-value sets.

### D5. No SSR transfer registration

These composables MUST NOT call `_register_transferable` / `_try_resolve_payload_key`. Rationale: during hydration the client setup runs in the browser where storage is readable; if the SSR payload (which can only contain the server-side default) were allowed to shadow the storage read, persisted values would be silently lost on every hydration. Storage is the client-side source of truth.

Consequence: the value rendered by SSR is always the default. Apps that want to avoid a flash of default content can wrap usage in `ClientOnly` or render placeholder UI — documented in the docs section, not enforced by the framework.

### D6. Callable outside component setup

Because no transfer registration and no lifecycle hooks are involved, calling `use_local_storage` outside a component setup is valid and emits NO warning (contrast with `use_state`, which warns). This enables shared/module-level usage patterns. (A module-level instance on the server is just `Reactive(default)`; the "No New Globals" invariant governs framework internals, not user code.)

### D7. JSON, not the transfer codec

Storage format is plain `json.dumps` output. Rationale: human-readable/editable in devtools, interoperable with non-WebComPy JS, and version-resilient. Rich Python types (dataclass, datetime) are out of scope (see Non-goals); users needing them can serialize themselves into a JSON-safe shape.

### D8. Failure policy summary

| Situation | Behavior |
|---|---|
| Server / non-PyScript env | `Reactive(default)`; zero storage access |
| Key absent | initial = default; nothing written until first update |
| Stored value is invalid JSON | warning; initial = default; entry left untouched |
| Value not JSON-serializable on write | warning; write skipped; signal still updates |
| `setItem` raises (quota/privacy) | warning; swallowed; signal still updates |
| Same-value set | no notification → no write (existing signal contract) |

### D9. Testability without a browser

All storage interaction is isolated in two module-private helpers `_read(storage, key, default)` / `_write(storage, key, value)` taking the storage object as a parameter, with the public composables resolving the storage object (or `None` on server) and delegating. Unit tests exercise the helpers with a simple `dict`-backed fake (`getItem`/`setItem`), and the environment guard by asserting the server path performs no storage access.

## Code Structure

```
packages/webcompy/src/webcompy/storage/
├── __init__.py          # re-exports
└── _composable.py       # use_local_storage / use_session_storage / _read / _write
```

Sketch of `_composable.py`:

```python
T = TypeVar("T")
_MISSING: Final = object()

def _resolve_default(default: T | Callable[[], T]) -> T:
    return default() if callable(default) else default

def _read(storage: Any, key: str, default: T | Callable[[], T]) -> T:
    raw = storage.getItem(key)
    if raw is None:
        return _resolve_default(default)
    try:
        return json.loads(str(raw))
    except (ValueError, TypeError):
        logging.warning("webcompy storage: ignoring corrupted value for key %r", key)
        return _resolve_default(default)

def _write(storage: Any, key: str, value: Any) -> None:
    try:
        payload = json.dumps(value)
    except TypeError:
        logging.warning("webcompy storage: value for key %r is not JSON-serializable; write skipped", key)
        return
    try:
        storage.setItem(key, payload)
    except Exception:
        logging.warning("webcompy storage: failed to write key %r", key)

def _make(key: str, default: Any, storage_getter: Callable[[], Any]) -> Reactive[Any]:
    if ENVIRONMENT != "pyscript":
        return Reactive(_resolve_default(default))
    storage = storage_getter()
    sig = Reactive(_read(storage, key, default))
    sig.on_after_updating(lambda _: _write(storage, key, sig.value))
    return sig
```

Public functions pass `lambda: context.window.localStorage` / `...sessionStorage` as `storage_getter` (importing `pyscript` inside the browser-only branch).

## Edge Cases

- **`null` vs missing**: PyScript proxies JS `null` to Python `None`; both mean "absent" for `getItem`.
- **Stored `"null"`** (valid JSON) decodes to Python `None` and is a legitimate stored value, distinct from a missing key.
- **ReactiveList/ReactiveDict values**: supported transparently (they JSON-serialize), but the write-back subscription only fires on the collection's own change events; deeply nested non-reactive mutation is the user's responsibility (same limitation as templates).
- **Concurrent keys**: two signals on the same key in one tab both write; last writer wins. Cross-tab is explicitly out of scope (spike planned).

## Docs

Add a storage section to the composables page in `docs_app`: basic usage, SSR default-flash caveat + `ClientOnly` mitigation, JSON-only limitation, non-goal pointer to cross-tab sync.
