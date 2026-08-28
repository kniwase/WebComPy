---
title: UI Primitives
description: The two-layer first-party component model — headless behavior cores and token-themed skins — with the Spinner as the worked example.
---

# UI Primitives

WebComPy ships first-party UI components in two layers so that both "just make it work" and "I want full design control" profiles are served by the same components:

```
webcompy.ui.headless.Spinner     behavior core  (state, ARIA, focus; no styling)
webcompy.ui.components.Spinner   themed skin    (token-based defaults)
webcompy.ui.Spinner              the themed variant (default import path)
```

The **headless layer** owns all behavior: state management, ARIA roles and attributes, keyboard interaction, and focus management. It emits no visual styles — only the structural CSS its behavior requires. The **themed layer** renders the corresponding headless component and adds default class names whose rules ship in the framework stylesheet and consume the design tokens. The themed layer carries zero behavior logic, so a behavior fix lands in exactly one place.

## Three import paths

```python
from webcompy.ui import Spinner           # themed (default, convenient path)
from webcompy.ui.components import Spinner  # themed (explicit)
from webcompy.ui.headless import Spinner    # headless (full control)
```

Importing a name from `webcompy.ui` always yields the themed variant. Use the headless path when you want to supply every visual decision yourself.

## The headless contract

Headless components expose their interaction state on the DOM through `data-state` attributes with a documented per-component vocabulary. `Spinner` uses a single state:

```html
<div class="webcompy-headless-spinner" role="status" data-state="loading">
  <span class="webcompy-sr-only">Loading data</span>
</div>
```

Accessibility is built in: the `label` prop renders visually hidden text (the `webcompy-sr-only` structural style comes from the component itself), and `aria_label` is used as the `aria-label` attribute when `label` is omitted.

Styling hooks: every component accepts a `class_name` prop (named `class_name` because `class` is a Python keyword) applied to its root element, and user classes are appended after the framework classes so user rules win at equal specificity. Multi-part components expose part-specific class props named per component.

```python
from webcompy.ui.headless import Spinner

Spinner({"label": "Loading data", "class_name": "my-spinner"})
```

```css
.my-spinner[data-state="loading"] {
  /* your own visual language, driven by the state attribute */
}
```

## The themed layer

Themed components are thin compositions: they forward your `class_name` (and every other prop) to the headless component and add default classes styled by rules inside the `@layer components` cascade of `/_webcompy-ui/index.css`. The rules consume design tokens (`--color-*`, `--space-*`, ...), so themed components follow the light/dark theme automatically.

```python
from webcompy.ui import Spinner

Spinner({"label": "Loading data"})                 # medium (default)
Spinner({"label": "Loading data", "size": "lg"})   # sm | md | lg
```

The themed `Spinner` draws a token-colored ring and animates it with a CSS rotation. When the user prefers reduced motion, the animation is suppressed and the static ring stays visible.

## Live example

The showcase at the end of this article is rendered by the page component itself — the themed spinners are the real framework components, and the bottom row is the headless `Spinner` styled entirely by this page's scoped CSS through `class_name` and `data-state`.

## Cascade and overrides

Themed defaults live inside `@layer components`, so unlayered user CSS always overrides them without specificity escalation. User CSS placed inside `@layer components` competes by source order — the framework stylesheets are imported first, so later rules win. There is no need for `!important` in application code.
