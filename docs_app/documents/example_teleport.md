---
title: Teleport
description: Relocate modals and floating dropdowns into document.body using Teleport while preserving component signals, event handlers, and scoped CSS.
---

# Teleport

This example demonstrates `Teleport` mounting a modal dialog and a floating menu directly under `<body>` while defining their state, event handlers, and scoped CSS styles inside `TeleportDemo`.

Use `Teleport` whenever overlays must escape ancestor `overflow: hidden`, `transform`, or `z-index` clipping containers without breaking Python parent-child communication.

## What this demonstrates

- **DOM relocation (`to="body"`)**: Wrapping the backdrop in `Teleport({"to": "body"}, ...)` leaves a single `<!--webcompy-teleport-anchor-->` comment inside `.teleport-demo` while placing `.demo-modal-backdrop` and `.demo-dropdown` as direct children of `<body>`.
- **Reactive signal continuity**: Clicking `"Close"` inside the teleported modal mutates `modal_open.value` cleanly in the originating component scope, unmounting both the teleported overlay and its nodes.
- **Scoped style portability**: `TeleportDemo.scoped_style` rules match elements even after relocation to `<body>` because WebComPy stamps `webcompy-cid-*` attributes before moving nodes.

## Key mechanisms and how to adapt

1. **Always target a stable outer container**: Point `to=` to `"body"` or an outer static host element outside `#webcompy-app` — never target an element rendered inside another reactive component tree.
2. **Use first-party overlay primitives for common patterns**: For focus management, Escape key handling, and outside-click dismissal, prefer `Modal`, `Drawer`, `Dropdown`, or `Toast` in `webcompy.ui`.
3. **Disable SSR emission per overlay when needed**: Pass `{"to": "body", "ssr": False}` for client-only overlays that should render only after browser hydration.

## Next steps

- Understand SSR block markers (`wc-teleport-block`), hydration adoption, and target rejection diagnostics in [Teleport](/documents/advanced/teleport).
- Use production-ready overlays built on `Teleport` in [Overlay Components](/documents/basic/overlay).
- Add smooth enter/leave animations to overlays with [Transition](/documents/examples/transition).
