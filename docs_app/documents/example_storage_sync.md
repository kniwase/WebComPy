---
title: Storage Sync
description: Live cross-tab and cross-window state synchronization using use_local_storage(sync_tabs=True) demonstrated with two same-origin demo windows.
---

# Storage Sync

This example demonstrates `use_local_storage(..., sync_tabs=True)` keeping state synchronized live across independent browser execution contexts sharing an origin. Two separate PyScript demo iframes (`Window A` and `Window B`) render above — any theme switch, note update, or counter increment in one immediately updates the other, or you can open a second browser tab via **Open demo in new tab** and test across real tabs.

> **Mobile note**: On narrow viewports (`<= 768px`), Window A and Window B stack vertically to keep controls legible. Use **Open demo in new tab** above or resize wider to observe both panes side by side without scrolling.

## What this demonstrates

- **Zero-boilerplate cross-tab binding**: Calling `use_local_storage(STORAGE_KEY, _default_payload, sync_tabs=True)` returns a standard `Signal[dict]` that reads initial JSON state from `localStorage`, persists subsequent `.value` writes, and subscribes to browser `storage` events for the same key.
- **Echo-free updates across windows**: When Window A writes a new dictionary (`shared.value = current`), WebComPy applies the incoming `storage` event inside Window B under an echo guard so Window B updates its UI reactively without rebroadcasting back.
- **Factory defaults on reset**: Passing a factory callable `_default_payload` ensures both initial loads and remote resets (`localStorage.removeItem(...)` / `clear()`) receive a fresh dictionary instance.

## Key mechanisms and how to adapt

1. **Always replace immutable copies**: Replace the whole dictionary (`current = dict(shared.value); current["theme"] = name; shared.value = current`) rather than mutating keys in place so `Signal` change detection and storage write-back both run cleanly.
2. **Use DI for same-tab siblings**: Browser `storage` events do not fire inside the originating window itself; provide one shared `use_local_storage(..., sync_tabs=True)` signal via `provide()` / `inject()` when components in the same tab also read the same key.
3. **Prefer cookies for SSR-critical settings**: `use_local_storage` reads browser storage only after boot (falling back to `default` on SSR); keep locale or server-rendered layout flags in cookies or URL state.

## Next steps

- Review single-tab storage APIs (`use_local_storage` and `use_session_storage`) in [Storage](/documents/basic/storage).
- Explore `_StorageSyncRegistry`, equality suppression, and error resilience in [Persistence Patterns](/documents/advanced/persistence-patterns).
- Compare cookie-based SSR-deterministic state in [i18n Playground](/documents/examples/i18n-playground).
