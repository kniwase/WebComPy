---
title: Overlay Components
description: Build accessible Modal, Drawer, Dropdown, and Toast overlays with Teleport, Transition animations, and keyboard management.
---

# Overlay Components

WebComPy ships accessible overlay primitives — `Modal`, `Drawer`, `Dropdown`, and `ToastHost` (paired with `use_toast()`) — rendered through `Teleport` and animated with `Transition`. Every overlay component ships as a headless/themed pair following the model described in [UI Primitives](/documents/basic/ui-primitives).

## At a glance

Control overlay visibility with reactive `Signal[bool]` state and close callbacks:

```python
from webcompy import use_state
from webcompy.elements import html
from webcompy.ui import Modal

open_modal = use_state(lambda: False)

Modal(
    {"open": open_modal, "on_close": lambda: setattr(open_modal, "value", False), "aria_label": "Confirm action"},
    slots={"default": lambda: html.P({}, "Modal body content.")},
)
```

## Component overview

| Component | Purpose | Key props | Headless / Themed |
|---|---|---|---|
| `Modal` | Centered dialog with backdrop, focus trap, and Escape/backdrop dismiss | `open`, `on_close`, `aria_label`, `aria_labelledby`, `close_on_backdrop`, `close_on_escape` | `webcompy.ui.headless.Modal` / `webcompy.ui.Modal` |
| `Drawer` | Slide-in panel anchored to a viewport edge | `open`, `on_close`, `edge` (`left`\|`right`\|`top`\|`bottom`), `aria_label`, `close_on_backdrop`, `close_on_escape` | `webcompy.ui.headless.Drawer` / `webcompy.ui.Drawer` |
| `Dropdown` | Triggered menu (`role="menuitem"`) with keyboard arrow navigation | `open`, `on_close`, `align`, `positioning`, `render_closed`, slots: `trigger`, `default` | `webcompy.ui.headless.Dropdown` / `webcompy.ui.Dropdown` |
| `ToastHost` | Teleported live-region queue driven by `use_toast()` | `toasts`, `on_dismiss`, `on_remove`, `transition_name` | `webcompy.ui.headless.ToastHost` / `webcompy.ui.ToastHost` |

## Modal

`Modal` implements the dialog accessibility contract: `role="dialog"`, `aria-modal`, focus trap, Escape to close, optional backdrop click, and focus return when dismissed.

## Drawer

`Drawer` shares the modal focus-trap and keyboard contract with an `edge` prop (`left` | `right` | `top` | `bottom`) controlling which side of the viewport slides open.

## Dropdown

`Dropdown` uses named slots: `trigger` for the toggle label/button content and `default` for `role="menuitem"` items. Built-in keyboard handling supports ArrowDown/ArrowUp with wrapping, Home/End, Escape, and Enter/Space.

## Toast

`use_toast()` (from `webcompy.ui.composables`) returns `(push, toast_state)` where `push(message, variant, duration)` enqueues a notification with auto-dismiss duration in seconds. `ToastHost` renders the active queue in a Teleported live region:

```python
from webcompy.ui import ToastHost
from webcompy.ui.composables import use_toast

push, toast_state = use_toast()
push("Saved!", "success", 3.0)
ToastHost({"toasts": toast_state.toasts, "on_dismiss": toast_state.dismiss, "on_remove": toast_state._remove})
```

## Notes & caveats

- Always supply either `aria_label` or `aria_labelledby` on `Modal` and `Drawer` so screen readers announce the dialog's accessible name.
- Place `ToastHost` once at a layout or page level outside scrolling containers.

## Next steps

- Review the two-layer architecture and part class hooks in [UI Primitives](/documents/basic/ui-primitives).
- Explore tabs, accordions, alerts, progress bars, badges, skeletons, and cards in [Disclosure & Feedback](/documents/basic/disclosure).
- Learn how `@layer components` and theme tokens work in [Styling & Themes](/documents/basic/styling-and-themes).
