---
title: Storage
description: Persist reactive Signal state in browser localStorage and sessionStorage with use_local_storage() and use_session_storage().
---

# Storage

`webcompy.storage` provides two composables — `use_local_storage()` and `use_session_storage()` — that behave like standard writable `Signal`s while persisting updates to the browser's `localStorage` and `sessionStorage`.

Use them for lightweight client preferences, draft inputs, and filter state you want to preserve across reloads without setting up a backend database.

## At a glance

```python
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.storage import use_local_storage, use_session_storage


@define_component()
def PreferencesPanel(context: ComponentContext[None]):
    sidebar_open = use_local_storage("docs.sidebar_open", True)
    draft_filter = use_session_storage("docs.filter", "")

    return html.DIV(
        {},
        html.INPUT({":bind": draft_filter, "placeholder": "Session filter..."}),
        html.BUTTON(
            {"@click": lambda _ev: setattr(sidebar_open, "value", not sidebar_open.value)},
            use_computed(lambda: "Hide sidebar" if sidebar_open.value else "Show sidebar"),
        ),
    )
```

Both helpers are also re-exported directly from top-level `webcompy`.

## `use_local_storage()` vs `use_session_storage()`

| Composable | Browser storage backend | Lifetime |
|---|---|---|
| `use_local_storage(key, default, *, sync_tabs=False)` | `window.localStorage` | Persists across browser restarts |
| `use_session_storage(key, default)` | `window.sessionStorage` | Persists for the current browser tab session |

Key behavior:

- **Initialization**: reads the existing JSON value for `key` if present; otherwise evaluates `default` (either a static value or a zero-argument factory callable `lambda: ...`).
- **JSON serialization**: values are serialized and deserialized as JSON (`str`, `int`, `float`, `bool`, `None`, `list`, `dict`).
- **Reactive signal interface**: mutate `.value` (or bind with `:bind` / read in `use_computed`) like any `Signal[T]`. Every write persists back to browser storage immediately.

> **Tip**: Pass `sync_tabs=True` to `use_local_storage("cart", [], sync_tabs=True)` when multiple open tabs should reflect updates made in another tab automatically.

## Server-side rendering behavior

WebComPy runs storage through an injected storage port. On the server during SSR or `webcompy generate`, browser storage does not exist, so `use_local_storage` and `use_session_storage` fall back to the provided `default` cleanly without raising errors. Once the app initializes in the browser, the stored value is read from the browser's storage if present.

## Notes & caveats

- Values must be JSON-serializable — custom Python classes or non-string dict keys cannot be persisted directly without converting to dicts/primitives first.
- Because `localStorage` and `sessionStorage` are shared per origin, namespace keys carefully (e.g., `"myapp.sidebar_open"`).

## Next steps

- Try live multi-window `localStorage` synchronization in the [Storage Sync](/documents/examples/storage-sync) example.
- Review how reactive signals and equality suppression behave in [Reactive State](/documents/basic/reactive-state).
- Combine persisted preferences with UI appearance in [Styling & Themes](/documents/basic/styling-and-themes).
- Continue to [Persistence Patterns](/documents/advanced/persistence-patterns) for cross-tab synchronization internals (`sync_tabs=True`), multi-tab event behavior, and persistence comparisons.
- Compare client-side storage with SSR-deterministic cookie persistence for locale state in [Internationalization](/documents/advanced/i18n).
