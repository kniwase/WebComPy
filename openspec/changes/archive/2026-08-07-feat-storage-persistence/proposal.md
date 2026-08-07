# Proposal: Storage Persistence Composables (`use_local_storage` / `use_session_storage`)

## Why

WebComPy has no way to persist component state across page reloads. Everyday app requirements — remembering a theme choice, a sidebar toggle, a draft input, a dismissed banner — currently force developers to drop down to raw `localStorage` calls guarded by environment checks, with manual JSON handling and no reactive integration. Every major framework ecosystem ships this as a composable (VueUse `useStorage`, React `useLocalStorage` hooks, Svelte persisted stores). For an official release, WebComPy needs a first-class, SSR-safe, reactive answer.

## What Changes

- **New composables** `use_local_storage(key, default)` and `use_session_storage(key, default)`, following the `use_*` naming convention, returning a `Reactive[T]`:
  - On creation in the browser, the current stored value is read (JSON-decoded) and used as the initial value; when the key is absent, the default is used.
  - Every subsequent update of the returned signal is automatically written back to storage (JSON-encoded) via `on_after_updating`.
  - `default` accepts either a value or a zero-argument factory (consistent with `use_state`).
- **SSR-safe**: on the server (and in any non-PyScript environment) no storage API is touched; the composable returns `Reactive(default)` so SSR/SSG render deterministically. During client hydration, component setup re-runs in the browser and reads storage at that point.
- **Not transfer-registered**: storage-backed signals are deliberately NOT registered in the SSR transfer payload — the browser storage is the source of truth on the client, and a payload restore must not shadow it.
- **JSON serialization**: values are encoded with `json.dumps` / decoded with `json.loads` (human-readable in devtools, interoperable with plain JS). A value that is not JSON-serializable logs a warning and skips the write; a corrupted stored value logs a warning and falls back to the default.
- **Callable anywhere**: unlike transfer composables, these do not require an active component setup context (no transfer registration is involved) and emit no warning when called outside setup.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `composables`: adds the storage persistence composables (read-on-create, write-on-update, JSON codec, SSR fallback, failure policy).

## Impact

- **Code**: new package `packages/webcompy/src/webcompy/storage/` (`__init__.py`, `_composable.py`); top-level exports in `webcompy/__init__.py`.
- **Specs**: delta to `openspec/specs/composables/spec.md`.
- **Docs**: `docs_app` composables documentation page gains a storage section (follow-up change may own the docs page if preferred).
- **Tests**: unit tests with a fake storage object (server-side, no browser required), covering read/write round-trip, missing key, corrupted JSON, non-serializable value, SSR no-access guarantee, environment guard. Browser behavior verified via `webcompy_testing` fake ports and/or e2e.
- No breaking changes.

## Known Issues Addressed

- No framework-level mechanism to persist state across reloads (developers hand-roll `if browser:` + `json` boilerplate per use).

## Non-goals

- **Cross-tab synchronization via the `storage` event** — deferred to a spike after the practical-pack changes land; if the spike proves feasible in PyScript it becomes its own change (`feat-storage-tab-sync`), otherwise it is cancelled. This change's design keeps the door open (single read/write choke point) but implements nothing.
- Transfer-codec (`__webcompy_`-tagged) serialization of rich Python types (dataclasses, datetime) into storage — plain JSON only; rich-type support can be revisited later.
- Storage key namespacing/prefixing, TTL/expiry, encryption, IndexedDB backends.
- Migration/versioning of stored schemas.
