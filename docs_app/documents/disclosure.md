---
title: Disclosure & Feedback
description: Show/hide content with Tabs, Collapse, and Accordion, and surface status with Alert, Progress, Badge, Skeleton, and Card components.
---

# Disclosure & Feedback

Disclosure and feedback components from `webcompy.ui` organize collapsible sections, tabbed panels, and status indicators with built-in WAI-ARIA behavior. Every component ships as a headless/themed pair following the two-layer model in [UI Primitives](/documents/basic/ui-primitives).

## At a glance

```python
from webcompy import use_state
from webcompy.elements import html
from webcompy.ui import Tabs

active = use_state(lambda: "a")

Tabs(
    {
        "tabs": [
            {"key": "a", "label": "Alpha", "content": lambda: html.P({}, "First panel")},
            {"key": "b", "label": "Beta", "content": lambda: html.P({}, "Second panel")},
        ],
        "active": active,
    }
)
```

## Component overview

| Component | Purpose | Key props / slots | Headless / Themed |
|---|---|---|---|
| `Tabs` | WAI-ARIA tabbed interface with persistent mounted panels | `tabs`, `active`, `on_select`, `aria_label` | `webcompy.ui.headless.Tabs` / `webcompy.ui.Tabs` |
| `Collapse` | Animated single expandable region | `open`, `on_toggle`, `animated` (themed), slots: `trigger`, `default` | `webcompy.ui.headless.Collapse` / `webcompy.ui.Collapse` |
| `Accordion` | Coordinated collapsible items by key | `items`, `single_open`, `on_toggle` | `webcompy.ui.headless.Accordion` / `webcompy.ui.Accordion` |
| `Alert` | Accessible status banner with optional dismiss | `variant` (`info`\|`success`\|`warning`\|`error`), `dismissable`, `on_dismiss`, slot: `default` | `webcompy.ui.headless.Alert` / `webcompy.ui.Alert` |
| `Progress` | Determinate or indeterminate progress bar | `value`, `min`, `max`, `indeterminate`, `aria_label` | `webcompy.ui.headless.Progress` / `webcompy.ui.Progress` |
| `Badge` | Compact status pill | `variant` (`neutral`\|`info`\|`success`\|`warning`\|`error`), slot: `default` | `webcompy.ui.headless.Badge` / `webcompy.ui.Badge` |
| `Skeleton` | Visual loading placeholder (`aria-hidden="true"`) | `shape` (`rectangle`\|`line`\|`circle`), `width`, `height` | `webcompy.ui.headless.Skeleton` / `webcompy.ui.Skeleton` |
| `Card` | Structural container with optional header/body/footer regions | Slots: `header`, `default`, `footer` | `webcompy.ui.headless.Card` / `webcompy.ui.Card` |

## Tabs

`Tabs` implements the WAI-ARIA tabs pattern: `role="tablist"` / `tab` / `tabpanel` wiring, arrow-key navigation with wrapping and automatic activation, Home/End jumps, and roving tabindex. Items are passed as a `tabs` prop — each entry needs a `key`, a `label`, and a `content` generator. The `tabs` list is read once at setup; remount the component to change the item set.

All panels stay mounted; inactive panels are hidden with the `hidden` attribute, so panel state (typed input, scroll position) survives switches and switching is instant. Panel switching carries no enter/leave animation by design.

```python
active = use_state(lambda: "a")
Tabs({
    "tabs": [
        {"key": "a", "label": "Alpha", "content": lambda: html.P({}, "First")},
        {"key": "b", "label": "Beta", "content": lambda: html.P({}, "Second")},
    ],
    "active": active,  # omit for uncontrolled; a signal is written through on switch
})
```

The `active` prop is optional: omit it and the component manages selection itself; pass a signal or plain value with `on_select` to drive it from your app.

## Collapse and Accordion

`Collapse` is an animated disclosure: a trigger button (`aria-expanded`, `aria-controls`) plus a content region that mounts only while open. The animation runs through `Transition` with the `grid-template-rows: 0fr → 1fr` technique — natural height with no measurement. Pass `animated=False` on themed `Collapse` for instant expansion; headless `Collapse` accepts `transition_name`.

`Accordion` composes collapse items under a shared open state with key-based identity: multi-open by default, `single_open=True` to close siblings. Like `Tabs`, the `items` list is read once at setup; remount to change the item set.

```python
Accordion({"items": [
    {"key": "i1", "label": "First", "content": lambda: html.P({}, "...")},
    {"key": "i2", "label": "Second", "content": lambda: html.P({}, "...")},
], "single_open": True})
```

## Alert and Progress

- **`Alert`**: maps variants to announcement roles (`error`/`warning` use `role="alert"` assertive; `info`/`success` use `role="status"` polite). With `dismissable=True` it renders an accessible dismiss button that hides the alert and calls `on_dismiss`.
- **`Progress`**: renders `role="progressbar"` with `aria-valuenow`/`min`/`max` in determinate mode (`aria-valuenow` is clamped to bounds); set `indeterminate=True` for an unknown-duration sweep animation. Supply `aria_label` for the accessible name. `value`, `min`, `max`, and `indeterminate` accept reactive signals.

```python
progress = use_state(lambda: 40)
Progress({"value": progress, "min": 0, "max": 100, "aria_label": "Upload progress"})
```

## Badge, Skeleton, and Card

- **`Badge`**: compact status label with `variant` (`neutral`, `info`, `success`, `warning`, `error`).
- **`Skeleton`**: loading placeholder marked `aria-hidden="true"`; pair it with a `Spinner` or loading text in the container for assistive tech. Shapes: `rectangle` (default), `line`, `circle`, plus `width`/`height`.
- **`Card`**: structural container with `header` / `default` / `footer` slots; regions render only when supplied.

## Headless variants

Every component above has a matching headless export under `webcompy.ui.headless` (`from webcompy.ui.headless import Tabs, Collapse, Accordion, Alert, Progress, Badge, Skeleton, Card`) carrying the same behavior, keyboard shortcuts, and ARIA contracts with zero visual CSS, driven through `data-state` attributes and part class hooks.

## Notes & caveats

- Keep `Tabs` and `Accordion` item definitions static during a mount — update item contents via reactive signals inside each `content` generator instead of mutating `tabs` / `items` in place.
- Remember that `Transition`-backed animations on `Collapse` rely on the wrapper having a real CSS box (`@define_component` components inside custom animations need `display="block"`).

## Next steps

- Understand headless vs themed layering in [UI Primitives](/documents/basic/ui-primitives).
- See dialogs, drawers, dropdowns, and toasts in [Overlay Components](/documents/basic/overlay).
- Explore validated inputs and form controls in [Forms](/documents/basic/forms).
- Review custom element wrapper behavior in [Custom Elements](/documents/advanced/custom-elements) and the headless contract in [UI Headless Contract](/documents/advanced/ui-headless-contract).
- Full API: [UI & Theme API](/documents/api/ui).
