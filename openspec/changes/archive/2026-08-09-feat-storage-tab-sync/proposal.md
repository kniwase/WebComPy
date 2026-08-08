# Proposal: Cross-Tab Synchronization for `use_local_storage` (`sync_tabs`)

## Why

`use_local_storage` persists state across reloads, but when a user opens the same app in two tabs, the tabs diverge: changing a theme or a preference in one tab leaves the other tab stale until reload. The Web platform already provides the answer — the `storage` event, which fires in every *other* tab of the same origin when `localStorage` changes — and ecosystem equivalents synchronize by default (VueUse `useStorage`). Whether this works from WebComPy's PyScript runtime is **unverified**, so this change is gated on an implementation spike (Task 1): if the spike shows the `storage` event cannot be reliably received and inspected from Python, the change is abandoned and cross-tab sync remains a documented non-goal of storage persistence.

## What Changes

- **Opt-in cross-tab sync**: `use_local_storage(key, default, *, sync_tabs: bool = False)`. When `sync_tabs=True`, the returned signal listens for `storage` events from other tabs:
  - Another tab writes the same key → this tab's signal updates to the new value (JSON-decoded), triggering normal reactivity (templates re-render, `:bind` updates).
  - Another tab removes the key (`removeItem`, or `clear` covering it) → this tab's signal resets to `default`.
- **`use_local_storage` only**: `sessionStorage` is per-tab by design and does not fire cross-tab `storage` events; `use_session_storage` gains no parameter.
- **Loop safety by construction**: remote applications bypass the automatic write-back (a dedicated apply path, not the public `.value` setter), so receiving an event never causes this tab to re-broadcast. Combined with the browser guarantee that the writing tab never receives its own event, synchronization cannot loop.
- **Failure policy aligned with storage persistence**: a corrupted JSON payload arriving from another tab logs a warning and falls back to `default`; listener setup/cleanup follows the framework's `create_proxy` / `removeEventListener` / `destroy` lifecycle rules.
- **SSR/SSG unaffected**: no listener is created outside the PyScript environment; `sync_tabs=True` is a no-op on the server beyond rendering the default.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `composables`: adds opt-in cross-tab synchronization to `use_local_storage` (event reception, remote-apply semantics, removal reset, loop safety, lifecycle).

## Impact

- **Code**: `packages/webcompy/src/webcompy/storage/_composable.py` (new kwarg, listener wiring); possibly a small module-private registry for a shared listener (design decision D1). No new dependencies.
- **Specs**: delta to `openspec/specs/composables/spec.md`.
- **Docs**: storage section of the `docs_app` composables page documents `sync_tabs`.
- **Tests**: unit tests with a fake event dispatch (listener registration/apply/removal/cleanup, loop-safety); the spike's Playwright two-tab verification becomes the permanent e2e scenario if the spike succeeds.
- No breaking changes: default `sync_tabs=False` preserves current behavior exactly.

## Known Issues Addressed

- Multiple tabs of the same app show divergent persisted state until manual reload.

## Non-goals

- Same-tab or cross-tab sync for `use_session_storage` (per-tab semantics; events do not fire).
- General-purpose cross-tab messaging (`BroadcastChannel`, SharedWorker) or cross-tab signal sync for non-storage signals.
- Conflict resolution/merging of concurrent writes in two tabs (last writer wins, per the platform event model).
- Sync of non-JSON-serializable values (unchanged from storage persistence: write skipped with warning).
