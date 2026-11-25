---
title: Transition
description: Animate appearing and disappearing conditional elements using WebComPy's Vue-compatible Transition class protocol, duration resolution, and reduced-motion support.
---

# Transition

`Transition` (`webcompy.elements`) animates a single conditional child element as it appears, disappears, or swaps on client-side state updates. WebComPy manages the enter/leave CSS class sequence, delays DOM removal until the leave animation finishes, and cleans up reactive subscriptions safely while you write standard CSS transitions or keyframe animations.

Use `Transition` for single-element show/hide effects, modals, toast cards, or collapsible panels driven by signals. Initial SSR/SSG HTML and the first hydrated render always emit the steady state with zero transition classes—animations trigger only on subsequent client-side changes.

## Basic usage

Pass a config dict (`{"name": "<prefix>"}`, optional `"duration"` in ms and `"on_leave_end"` callback) and a zero-argument generator returning either one element or `None`:

```python
from webcompy import use_state
from webcompy.components import ComponentContext, define_component
from webcompy.elements import Transition, html


@define_component()
def FadeNotice(context: ComponentContext[None]):
    visible = use_state(lambda: False)

    return html.DIV(
        {},
        html.BUTTON(
            {"type": "button", "@click": lambda _ev: setattr(visible, "value", not visible.value)},
            "Toggle Notice",
        ),
        Transition(
            {"name": "fade"},
            lambda: html.DIV({"class": "notice-box"}, "Saved changes.") if visible.value else None,
        ),
    )


FadeNotice.scoped_style = {
    ".notice-box": {"padding": "0.75rem 1rem", "background": "#eef6ff"},
    ".fade-enter-from, .fade-leave-to": {"opacity": "0"},
    ".fade-enter-active, .fade-leave-active": {"transition": "opacity 250ms ease"},
    ".fade-enter-to, .fade-leave-from": {"opacity": "1"},
}
```

## Enter and leave class protocol

`Transition` drives the exact six-class lifecycle of Vue 3's `<Transition>`:

```text
Appearing (None ──► Element):
  mount DOM node + .{name}-enter-from
    │
    ▼  (next animation frame)
  swap to .{name}-enter-active + .{name}-enter-to
    │
    ▼  (transitionend / animationend / timeout)
  remove all enter classes ──► steady state

Disappearing (Element ──► None):
  keep DOM node mounted + .{name}-leave-from
    │
    ▼  (next animation frame)
  swap to .{name}-leave-active + .{name}-leave-to
    │
    ▼  (transitionend / animationend / timeout)
  remove classes, detach node, destroy consumer bindings, invoke on_leave_end()
```

| Phase | Classes applied | When active |
|---|---|---|
| Enter start | `{name}-enter-from` | Synchronously when the new node mounts (initial frame state) |
| Enter active | `{name}-enter-active`, `{name}-enter-to` | Replaced on next `requestAnimationFrame` until enter finishes |
| Leave start | `{name}-leave-from` | Synchronously when generator flips to `None` or a different tag |
| Leave active | `{name}-leave-active`, `{name}-leave-to` | Replaced on next `requestAnimationFrame`; removed only after leave ends |

## Props and configuration

| Prop | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | Yes | Non-empty class prefix used for `{name}-enter-*` and `{name}-leave-*` |
| `duration` | `int \| float \| None` | No | Optional non-negative milliseconds overriding CSS style inspection |
| `on_leave_end` | `Callable[[], None] \| None` | No | Optional callback invoked when a leave sequence completes |

Missing or empty `name`, negative/`bool`/non-finite `duration`, or a non-callable `on_leave_end` raises `WebComPyException` at construction time.

## How durations are resolved

Every enter or leave sequence resolves its duration in strict order and is **always backed by a timeout** so missing CSS end events never leave nodes stuck in the DOM:

1. **Explicit `duration` prop**: when `"duration": ms` is passed (e.g. `100`), WebComPy schedules the timeout for `ms` milliseconds and finalizes early if a matching `transitionend`/`animationend` arrives on the element.
2. **Computed CSS styles (browser)**: otherwise, WebComPy reads the element's computed `transition-duration` + `transition-delay` and `animation-duration` + `animation-delay` (using CSS repeat-last semantics when delay lists are shorter than duration lists):
   - Finalization waits until every **counted layer** (layers with positive `duration + delay`, excluding `animation-iteration-count: infinite` layers which never emit `animationend`) has reported an end event, or until the longest `duration + delay` timeout elapses.
   - Zero-duration layers with positive delay still resolve a positive timeout cleanly without warning.
3. **Zero fallback**: if no explicit `duration` is set and computed styles define no transition or animation duration/delay, WebComPy logs a warning and finalizes immediately.

All end-event listeners are detached cleanly on finalization.

## Single-child rule and replacement behavior

`Transition`'s generator **must** return either `None` or a single element owning **one real DOM node** (any standard `html.*` element or a `Component` wrapper):

- Multi-node structures (`Fragment`, `Teleport`, `switch`, `repeat`, `Suspense`) and non-element values (bare strings, signals, text nodes) raise `WebComPyException` without inserting partial nodes.
- **Replacing element A with element B**: `Transition` runs sequentially—element A completes (or finalizes) its leave sequence *before* element B mounts and starts entering, so two children never occupy the slot simultaneously.
- **Re-showing mid-leave**: if the generator yields a new different-tag child while leaving, the leaving node finalizes immediately before the new child enters. If the generator re-yields the **same tag** while its leave sequence is still active, the leave runs to completion first, then the re-yielded node mounts and runs its enter sequence.
- **Same-tag update in steady state**: outside a leave sequence, swapping between two outputs with the same root tag patches the element in place cleanly without triggering enter/leave classes.
- **Parent node accounting**: while a leave runs, `Transition` keeps reporting the child's node slot so trailing sibling indices remain valid, then triggers a single parent re-index once the node detaches. Removing the `Transition` element itself (e.g. its parent branch hides) cleans up any active child immediately without waiting for a leave animation.

## `prefers-reduced-motion` support

When the browser matches `(prefers-reduced-motion: reduce)` (queried via `MediaQueryPort`), `Transition` skips all enter/leave class sequences completely: appearing nodes mount immediately without enter classes, and disappearing nodes detach immediately without waiting for leave durations.

## Pitfalls

- **Wrapping components default to `display: contents`**: Because `@define_component()` defaults its custom-element wrapper to `display: contents`, CSS transitions/animations cannot execute directly on that host box and never fire `transitionend`. WebComPy detects computed `display` values of `contents` or `none` during style resolution and logs a warning—declare `@define_component(display="block")` (or another box-generating `ComponentDisplay` / `:host` display rule) on transitioned components, or wrap an inner `html.DIV`.
- **Reactive `class` attributes on the transitioned child**: Avoid binding a changing `Signal`/`Computed` directly to the transitioned child's `"class"` attribute if that signal updates while an animation runs. When a bound class signal updates, WebComPy rewrites the full `class` attribute string and overwrites the active `-enter-*` / `-leave-*` classes. Put animated classes on an outer wrapper or toggle visual state classes on a descendant instead.
- **`transition-property: all` with multiple durations**: Browsers can dispatch multiple property end events per duration entry when `all` is used; the timeout fallback guarantees the sequence still settles cleanly at the longest declared duration.

## Next steps

- Watch fade and slide CSS transitions run interactively in the [Transition](/documents/examples/transition) example.
- Configure component wrapper `display` modes in [Custom Elements](/documents/advanced/custom-elements).
- Combine animated state with reactive styles in [Styling Deep Dive](/documents/advanced/styling-deep-dive).
- Render animated dialogs and drawers into `<body>` with [Teleport](/documents/advanced/teleport) and explore built-in disclosures in [Disclosure & Feedback](/documents/basic/disclosure).
