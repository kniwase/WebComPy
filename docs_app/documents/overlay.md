---
title: Overlay Components
description: Modal, Drawer, Dropdown, and Toast overlay components.
---

# Overlay Components

Overlay UI — modals, drawers, dropdown menus, toasts — rendered through `Teleport` and animated with `Transition`.

## Modal

`Modal` implements the dialog accessibility contract: `role="dialog"`, `aria-modal`, focus trap, Escape to close, optional backdrop click, and focus return.

## Drawer

`Drawer` shares the modal contract with an `edge` prop (`left` | `right` | `top` | `bottom`).

## Dropdown

`Dropdown` uses named slots: `trigger` for the button and `default` for `role="menuitem"` items. Keyboard: ArrowDown/Up with wrapping, Home/End, Escape, Enter/Space.

## Toast

`use_toast()` returns `tuple[push, ToastState]` with `push(message, variant, duration)` in seconds. `ToastHost` renders the queue in a Teleport'd live region.

```python
push, toast_state = use_toast()
push("Saved!", "success", 3.0)
ToastHost({"toasts": toast_state.toasts, "on_dismiss": toast_state.dismiss, "on_remove": toast_state._remove})
```
