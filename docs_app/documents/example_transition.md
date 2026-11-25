---
title: Transition
description: CSS-driven enter and leave animations for conditional elements using WebComPy's Transition wrapper, timed cleanup, and reduced-motion support.
---

# Transition

This example showcases `Transition` animating appearing and disappearing elements with standard CSS classes (`fade-*` for opacity and `slide-*` for transforms), delaying DOM removal until leave animations complete cleanly.

Use `Transition` whenever banners, drawers, modals, or status notices should animate cleanly out of the DOM rather than snapping away immediately on state changes.

## What this demonstrates

- **Six-class Vue-compatible lifecycle**: `Transition({"name": "fade"}, ...)` applies `{name}-enter-from` on mount, swaps to `{name}-enter-active` and `{name}-enter-to` on the next animation frame, and reverses the sequence (`-leave-from` -> `-leave-active` / `-leave-to`) on hide before detaching the DOM node.
- **Automatic CSS duration detection**: Because no explicit `"duration"` prop is passed, WebComPy inspects computed `transition-duration` and waits for `transitionend` (or its computed fallback timeout) automatically.
- **Independent named transitions**: Notice the fade box (`name="fade"`) and slide box (`name="slide"`) animate independently through dedicated `.fade-*` and `.slide-*` selectors in `TransitionDemo.scoped_style`.

## Key mechanisms and how to adapt

1. **Wrap a single concrete element**: The generator callback inside `Transition(...)` must return either `None` or one real element (`html.DIV`, etc.) — do not pass multi-root `Fragment`s or bare strings directly.
2. **Use box layout modes on component children**: If transitioning a component wrapper directly, pass `@define_component(display="block")` so the host custom element generates a real CSS box instead of defaulting to `display: contents`.
3. **Avoid reactive `"class"` bindings on the animated node**: Keep visual state classes on a wrapper or child element so signal re-renders do not overwrite active `-enter-*` or `-leave-*` classes mid-animation.

## Next steps

- Read the complete duration resolution order and `prefers-reduced-motion` behavior in [Transition](/documents/advanced/transition).
- Combine CSS transitions with portal overlays in [Teleport](/documents/examples/teleport) and [Overlay Components](/documents/basic/overlay).
- Explore reactive CSS generation in [Styling Deep Dive](/documents/advanced/styling-deep-dive).
