---
title: Persistence Patterns
description: Share state safely across browser tabs and page reloads — compare localStorage, sessionStorage, hydration transfer, cookies, and URL state, and understand sync_tabs=True event coalescing and SSR semantics.
---

# Persistence Patterns

WebComPy gives components reactive persistence through `use_local_storage()` and `use_session_storage()`, with opt-in cross-tab synchronization via `sync_tabs=True`. Choosing the right persistence boundary keeps client state synchronized without fighting SSR hydration, triggering write-back loops, or losing shareable URL state.

For introductory `use_local_storage()` and `use_session_storage()` examples, start with [Storage](/documents/basic/storage).

## Choosing a persistence mechanism

| Mechanism | Lifetime | Shared across tabs? | Available in SSR? | Best for |
|---|---|---|---|---|
| `use_local_storage(..., sync_tabs=False)` | Across browser restarts | Yes (next load only) | No (renders `default`) | Per-browser drafts, dismissed banners, UI settings |
| `use_local_storage(..., sync_tabs=True)` | Across browser restarts | **Live reactive updates** across tabs | No (renders `default`) | Theme switches, auth logout flags, cross-tab carts |
| `use_session_storage(...)` | Current browser tab only | No | No (renders `default`) | Multi-step wizard drafts, tab-isolated filters |
| Hydration transfer ([`use_state`](/documents/basic/reactive-state)) | Initial SSR -> browser boot | No | **Yes** | Server-fetched initial page state (`<script id="__webcompy_data__">`) |
| HTTP cookies | Request/response headers + browser | Yes (same origin) | **Yes** | SSR-deterministic locale ([i18n](/documents/advanced/i18n)), auth sessions |
| URL path / query ([Routing](/documents/basic/routing)) | Navigation history / bookmark | Shareable via URL | **Yes** | Pagination, search queries, deep links |

## When to use

- **Saving client-only settings within a single tab or across visits** — see [Storage](/documents/basic/storage).
- **Keeping open tabs in sync live when preferences or session flags change** — use `use_local_storage(..., sync_tabs=True)`.
- **Pre-rendering initial state cleanly without a flash between SSR HTML and saved browser data** — understand SSR transfer boundaries in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer) and server cookies in [Internationalization](/documents/advanced/i18n).

## Setup

Pass `sync_tabs=True` to `use_local_storage()` inside component setup (within an active app DI scope):

```python
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.storage import use_local_storage


@define_component()
def ThemeSyncToggle(context: ComponentContext[None]):
    theme = use_local_storage("ui-theme", "light", sync_tabs=True)

    return html.BUTTON(
        {
            "@click": lambda _ev: setattr(
                theme,
                "value",
                "dark" if theme.value == "light" else "light",
            )
        },
        use_computed(lambda: f"Theme: {theme.value}"),
    )
```

Writing `theme.value = "dark"` in one tab automatically updates `theme.value` to `"dark"` in every other open tab on the same origin watching `"ui-theme"`.

## Recipes

### 1. Synchronize structured preferences with factory defaults and remote resets

Pass a zero-argument callable (`lambda: ...`) as `default` when storing mutable objects (`dict`, `list`) so each instance (and every remote removal/reset) receives a fresh default container:

```python
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.storage import use_local_storage


@define_component()
def WorkspacePrefs(context: ComponentContext[None]):
    prefs = use_local_storage(
        "workspace-prefs",
        lambda: {"sidebar_collapsed": False, "density": "comfortable"},
        sync_tabs=True,
    )

    def toggle_sidebar(_ev):
        current = dict(prefs.value)
        current["sidebar_collapsed"] = not current["sidebar_collapsed"]
        prefs.value = current  # replace value rather than mutating dict in place

    return html.DIV(
        {},
        html.BUTTON({"@click": toggle_sidebar}, "Toggle sidebar"),
        html.SPAN(
            {},
            use_computed(lambda: "Collapsed" if prefs.value["sidebar_collapsed"] else "Expanded"),
        ),
    )
```

When another tab calls `localStorage.removeItem("workspace-prefs")` or `localStorage.clear()`, WebComPy re-invokes `default()` automatically and resets `prefs.value` to `{"sidebar_collapsed": False, "density": "comfortable"}`.

### 2. Share one setting inside the same tab via DI

The browser's native `storage` event only fires in **other** tabs on the same origin — never inside the tab that called `localStorage.setItem()`. To synchronize multiple components inside the **same** tab as well as across tabs, create the storage signal once and share it through `provide()` / `inject()`:

```python
from webcompy.di import InjectKey, inject, provide
from webcompy.signal import Signal
from webcompy.storage import use_local_storage

ThemeKey = InjectKey[Signal[str]]("synced-theme")


def provide_synced_theme() -> Signal[str]:
    theme = use_local_storage("ui-theme", "light", sync_tabs=True)
    provide(ThemeKey, theme)
    return theme
```

Sibling components inside that tab call `inject(ThemeKey)` and react instantaneously in the current tab while staying synchronized across other tabs via `sync_tabs=True`.

## Behavior notes

- **Single shared event listener**: Calling `use_local_storage(..., sync_tabs=True)` does not attach one `window.addEventListener("storage", ...)` per signal. WebComPy stores one `_StorageSyncRegistry` per app DI scope (creating one FFI event proxy) and fans incoming `storage` events out to subscribers registered for `event.key`. Calling `localStorage.clear()` (`event.key is None`) dispatches reset notifications to every subscribed key.
- **Chained teardown on destroy**: When registered inside component setup, removing that component automatically unsubscribes its callback from the registry via a chained `on_before_destroy` hook without disturbing sibling subscribers on the same key.
- **Loop prevention (`applying_remote`)**: Applying an incoming `storage` event runs under an internal guard so updating `sig.value` triggers UI reactivity in the receiving tab **without** writing the key back to `localStorage` or triggering echo broadcasts.
- **Equality deduplication & concurrency**: Writing back or receiving an equal value (`sig.value == new_value`) performs no downstream notification, matching standard `Signal` semantics. Concurrent updates across multiple tabs follow platform **last-writer-wins** event order without custom merging.
- **Error resilience**: Corrupted or non-JSON remote payloads log a warning and fall back cleanly to `default` (calling the factory if provided). Unregistering errors or failed per-key callbacks log warnings while keeping dispatch active for other subscribers.
- **`use_session_storage` isolation & SSR semantics**: `use_session_storage` is per-tab and intentionally does not accept `sync_tabs`. In non-browser environments (SSR, `webcompy generate`, unit tests without PyScript), `use_local_storage(..., sync_tabs=True)` attaches no listeners, reads no browser storage, and renders `Signal(default)` cleanly without transferring storage state in `<script id="__webcompy_data__">`.

## Pitfalls

- **Expecting `storage` events inside the writing tab**: Two separate `use_local_storage("k", ..., sync_tabs=True)` calls inside the **same** tab will not observe each other's writes via the DOM `storage` event because browsers suppress `storage` events on the originating window. Share one `Signal` within the tab via DI.
- **Mutating dicts/lists in place**: `prefs.value["sidebar_collapsed"] = True` mutates Python memory without invoking `Signal`'s setter, so neither UI dependents nor `localStorage` write-back run. Always assign a copied object (`prefs.value = {...}`).
- **Calling `sync_tabs=True` outside an active app DI scope**: In the browser without an active app DI scope, `sync_tabs=True` logs a warning and degrades to a plain local `localStorage` signal with no cross-tab listener.
- **Non-JSON values & sensitive data**: Non-JSON-serializable values log a warning and skip writing to storage. Never store authentication secrets or high-integrity tokens in `localStorage` where XSS scripts can read them.
- **SSR vs browser flash on initial load**: Because SSR always renders `default` rather than client-side `localStorage`, wrap preferences that shift layout dramatically in `ClientOnly` or sync SSR-critical preferences (like locale) via HTTP cookies instead.

## Next steps

- Revisit basic `localStorage` / `sessionStorage` usage in [Storage](/documents/basic/storage).
- Share storage signals across components in the same tab with [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive).
- Compare server-readable cookie persistence in [Internationalization](/documents/advanced/i18n).
- Understand what actually travels inside the SSR payload in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
