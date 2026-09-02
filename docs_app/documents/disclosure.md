---
title: Disclosure & Feedback
description: Tabs, Collapse, Accordion, Alert, Progress, Badge, Skeleton, and Card components.
---

# Disclosure & Feedback

Disclosure and feedback primitives from `webcompy.ui`: tabs and collapsible sections for showing/hiding regions, plus status indicators. Each ships as a headless/themed pair (see [UI Primitives](/documents/basic/ui-primitives)).

## Tabs

`Tabs` implements the WAI-ARIA tabs pattern: `role="tablist"`/`tab`/`tabpanel` wiring, arrow-key navigation with wrapping and automatic activation, Home/End jumps, and roving tabindex. Items are passed as a `tabs` prop — each entry needs a `key`, a `label`, and a `content` generator. The `tabs` list is read once at setup; remount the component to change the item set.

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

## Collapse / Accordion

`Collapse` is an animated disclosure: a trigger button (`aria-expanded`, `aria-controls`) plus a content region that mounts only while open. The animation runs through `Transition` with the `grid-template-rows: 0fr → 1fr` technique — natural height, no measurement. Pass `animated=False` for instant expansion; the transition class set is overridable via `transition_name`.

`Accordion` composes Collapse items under a shared open state with key-based identity: multi-open by default, `single_open=True` to close siblings. Like Tabs, the `items` list is read once at setup; remount to change the item set.

```python
Accordion({"items": [
    {"key": "i1", "label": "First", "content": lambda: html.P({}, "...")},
    {"key": "i2", "label": "Second", "content": lambda: html.P({}, "...")},
], "single_open": True})
```

## Alert

`Alert` maps variants to announcement roles: `error`/`warning` use `role="alert"` (assertive), `info`/`success` use `role="status"` (polite). With `dismissable=True` it renders an accessible dismiss button that hides the alert and calls `on_dismiss`.

## Progress

`Progress` renders `role="progressbar"` with `aria-valuenow/min/max` in determinate mode (`aria-valuenow` is clamped to the bounds); set `indeterminate=True` (omit `aria-valuenow`) for an unknown-duration sweep animation. Supply `aria_label` for the accessible name. `value`, `min`, `max`, and `indeterminate` accept signals for reactive updates.

```python
progress = use_state(lambda: 40)
Progress({"value": progress, "min": 0, "max": 100, "aria_label": "Upload progress"})
```

## Badge / Skeleton / Card

- `Badge` — compact status label with `variant` (`neutral`, `info`, `success`, `warning`, `error`).
- `Skeleton` — loading placeholder marked `aria-hidden="true"`; pair it with a `Spinner` or loading text in the container for assistive tech. Shapes: `rectangle` (default), `line`, `circle`, plus `width`/`height`.
- `Card` — structural container with `header` / `default` / `footer` slots; regions render only when supplied.

## Headless Variants

Headless pairs are available under `webcompy.ui.headless` (`HeadlessTabs`, `HeadlessCollapse`, ...): the same behavior and ARIA contracts with no visual styling, driven through `data-state` attributes and part class hooks.
