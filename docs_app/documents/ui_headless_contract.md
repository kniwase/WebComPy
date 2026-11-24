---
title: UI Headless Contract
description: Understand WebComPy's two-layer UI architecture — zero-style webcompy.ui.headless behavior primitives, data-state vocabularies, class_name pass-through, DI-scoped FormField wiring, and custom theme authoring.
---

# UI Headless Contract

Every first-party widget in `webcompy.ui` splits into two clean layers: a behavior-only primitive under `webcompy.ui.headless` (owning ARIA attributes, keyboard shortcuts, focus management, Teleport/Transition wiring, and state) and a themed wrapper under `webcompy.ui.components` (also re-exported directly from `webcompy.ui`) that supplies token-based classes. Use the headless layer directly whenever you want total visual control or want to build your own company design system without fighting default CSS.

## When to use

- **Shipping fast with built-in design tokens (`var(--color-*)`, `var(--space-*)`) and overrides** — import directly from `webcompy.ui` (see [UI Primitives](/documents/basic/ui-primitives), [Overlay Components](/documents/basic/overlay), [Disclosure & Feedback](/documents/basic/disclosure), and [Forms](/documents/basic/forms)).
- **Replacing visual CSS completely or wrapping a brand design system around WebComPy's ARIA and keyboard logic** — import from `webcompy.ui.headless` and compose your own `@define_component()` wrapper.
- **Inspecting CSS `@layer` cascade precedence** — see [Styling Deep Dive](/documents/advanced/styling-deep-dive).

## Setup

All 21 primitives expose consistent modules across three import paths (`Spinner`, `Modal`, `Drawer`, `Dropdown`, `ToastHost`, `Tabs`, `Collapse`, `Accordion`, `Alert`, `Progress`, `Badge`, `Skeleton`, `Card`, `FormField`, `Input`, `Textarea`, `Select`, `Checkbox`, `Switch`, `Radio`, `RadioGroup`):

```python
from webcompy.ui.headless import Input as HeadlessInput   # behavior-only (<headless-input>), no visual CSS
from webcompy.ui.components import Input as ThemedInput   # token-styled (<webcompy-input>)
from webcompy.ui import Input                             # alias to ThemedInput
```

Headless primitives render `<headless-*>` Light DOM wrappers with zero colors, borders, shadows, or spacing rules beyond minimal structural positioning/visibility. Toast state comes from `use_toast` (`from webcompy.ui.composables import use_toast`).

### Data-state vocabulary and part-class hooks

Style any state transition and inner part without JavaScript polling using `[data-state="..."]` attributes and `class_*` pass-through props:

| Component(s) | `data-state` values | Class pass-through props | Key ARIA / behavior contract |
|---|---|---|---|
| `Spinner` | `"loading"` | `class_name` | `role="status"`, accessible label text / `aria-label` |
| `Modal`, `Drawer` | `"open"` (when mounted) | `class_name`, `class_backdrop`, `class_panel` | `role="dialog"`, `aria-modal="true"`, focus trap + restore, Escape & backdrop close, `Teleport` + `Transition` |
| `Dropdown` | `"open"` \| `"closed"` (root, trigger, menu) | `class_name`, `class_trigger`, `class_menu` | `aria-expanded`, `aria-haspopup="menu"`, `role="menu"` / `"menuitem"`, capture-phase outside click, trigger anchor positioning, optional `render_closed` |
| `ToastHost` | `"visible"` \| `"hidden"` (per toast item) | `class_name`, `class_item`, `class_dismiss` | `aria-live="polite"` / alert semantics, auto-dismiss timers cancelled on dismiss/destroy |
| `Tabs` | `"active"` \| `"inactive"` (tabs & panels) | `class_name`, `class_tablist`, `class_tab`, `class_panel` | `role="tablist"` / `"tab"` / `"tabpanel"`, hidden inactive panels preserve state, roving `tabindex` + Arrow/Home/End |
| `Collapse`, `Accordion` | `"open"` \| `"closed"` (trigger), `"open"` (mounted content) | `class_name`, `class_trigger`, `class_content` | `aria-expanded`, `aria-controls`, `Transition`-animated panel, single-open or multi-open policy |
| `Alert`, `Badge`, `Skeleton`, `Card`, `Progress` | `Progress`: `"determinate"` \| `"indeterminate"` | `class_name`, `class_dismiss` (`Alert`), `class_fill` (`Progress`), `class_header`/`class_body`/`class_footer` (`Card`) | `Alert`: `role="alert"` \| `"status"`; `Skeleton`: `aria-hidden="true"`; `Progress`: clamped `aria-valuenow` |
| `FormField`, `Input`, `Textarea`, `Select`, `Checkbox`, `Switch`, `Radio`, `RadioGroup` | `"valid"` \| `"invalid"` (gated on `touched and invalid`) | `class_name`, `class_label` (`FormField`/`Checkbox`/`Switch`), `class_control`/`class_error` (`FormField`), `class_legend` (`RadioGroup`) | Native inputs (`<input>`, `<select>`, `<textarea>`), `Switch`: `role="switch"` + `aria-checked`, `aria-invalid="true"` + `aria-describedby` |

## Recipes

### 1. Author a custom themed component pair over a headless core

Wrap a `webcompy.ui.headless` primitive inside your own `@define_component(...)`, attach default design classes ahead of caller-supplied `class_name` / part classes, and forward slots and props cleanly:

```python
from typing import TypedDict

from webcompy.components import ComponentContext, define_component
from webcompy.ui.headless import Spinner as HeadlessSpinner


class BrandSpinnerProps(TypedDict, total=False):
    label: str
    class_name: str
    size: str


@define_component(custom_element_name="brand-spinner")
def BrandSpinner(context: ComponentContext[BrandSpinnerProps]):
    props = context.props or {}
    user_class = props.get("class_name", "")
    classes = " ".join(part for part in ("brand-spinner", f"brand-spinner--{props.get('size', 'md')}", user_class) if part)

    return HeadlessSpinner(
        {
            "label": props.get("label", "Loading"),
            "class_name": classes,
        }
    )


BrandSpinner.scoped_style = {
    " .brand-spinner[data-state='loading']": {
        "color": "var(--color-accent)",
        "display": "inline-flex",
        "align-items": "center",
    }
}
```

User classes are always appended **after** framework/default classes so consumer CSS rules win cleanly at equal specificity without `!important`.

### 2. Wire accessible labels and touched-invalid styling via `FormField`

`FormField` generates hydration-stable `control_id` and `error_id` strings from its transfer ID and provides them via a slot-scoped DI pass — binding any control inside its default slot without leaking IDs to sibling controls outside:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.forms import Field, required
from webcompy.ui.headless import FormField, Input


@define_component()
def CustomEmailField(context: ComponentContext[None]):
    email = Field("", validators=[required()])

    return html.DIV(
        {},
        FormField(
            {
                "field": email,
                "label": "Work Email",
                "class_name": "field-row",
                "class_label": "field-label",
                "class_error": "field-error",
            },
            slots={"default": lambda: Input({"field": email, "class_name": "field-input"})},
        ),
        # Rendered outside FormField's slot: does NOT receive the email control_id or aria-describedby
        Input({"value": "", "aria_label": "Standalone note", "class_name": "field-input"}),
    )


CustomEmailField.scoped_style = {
    " .field-input[data-state='invalid']": {
        "border": "1px solid var(--color-error)",
    }
}
```

Before blur (`email.touched.value == False`), both `FormField` and `Input` carry `data-state="valid"`, omitting error messages and `aria-invalid`. Once blurred while invalid, `data-state` switches to `"invalid"`, error text mounts, and `aria-describedby` links input and error cleanly across both SSR HTML and browser hydration.

### 3. Override themed primitives cleanly via `class_name` and part hooks

Themed exports (`from webcompy.ui import ...`) delegate directly to the headless layer, so passing `class_name=` or part props (`class_panel`, `class_menu`, `class_tab`) appends your custom class last on top of the `@layer components` stylesheet:

```python
from webcompy.ui import Card

Card(
    {"class_name": "pricing-card", "class_header": "pricing-card-head"},
    slots={
        "header": lambda: "Pro Plan",
        "default": lambda: "$20 / month",
    },
)
```

## Behavior notes

- **Hydration-stable generated IDs**: Multi-part widgets (`Tabs`, `Collapse`, `Dropdown`, `Modal`, `Drawer`, `RadioGroup`, `FormField`) compute `id`, `aria-controls`, `aria-labelledby`, `aria-describedby`, and radio group `name` from per-instance transfer IDs so SSR markup matches client hydration without ID collisions when multiple instances appear on the same page.
- **`Field` vs. raw value mode on form controls**: Supplying `field=` connects a native input via `:bind` (`dirty` on edit, `touched` on blur, `data-state` validation gating). Omitting `field=` allows raw `value=` + `on_change=`: a plain scalar `value` seeds the control once, whereas passing a `Signal` synchronizes bidirectionally (`data-state` stays `"valid"` in raw mode).
- **Capture-phase outside click on `Dropdown`**: Opening a `Dropdown` attaches a capture-phase document click listener (stopping trigger click propagation cleanly) so clicking a second `Dropdown` closes the first without toggle races, and listeners clean up automatically on close or unmount.
- **Toast timer lifecycle**: `use_toast()` clears auto-dismiss timers (`float` seconds, default `3.0`, or `None` to disable) on manual dismissal, timeout completion, and component destruction.

## Pitfalls

- **Passing both `field=` and `value=` on a form control**: Supplying both props on `Input`, `Textarea`, `Select`, `Checkbox`, `Switch`, or `RadioGroup` raises an explicit conflict error. Choose either `:bind` via `field=` or raw controlled props.
- **Expecting raw plain `value="abc"` strings to react externally**: Passing a non-`Signal` plain value seeds initial control state only; pass a `Signal[str]` / `Signal[bool]` as `value=` when programmatic updates must reflect inside the widget.
- **Using `class` instead of `class_name` on components**: Because `class` is a reserved Python keyword in signatures and TypedDicts (though `"class"` works on raw HTML element attribute dicts), headless and themed primitives use `class_name` for the root class hook.
- **Placing an `Input` outside `FormField`'s slot**: `FormField` confines its `FormFieldContext` DI provision strictly to its own slot render pass, so inputs rendered outside `slots={"default": ...}` stay independent.
- **Passing bare `class` or mutating `Tabs`/`Accordion` items in place**: Keep `Tabs` / `Accordion` definitions structural and put mutable per-panel signals inside each item's content generator.

## Next steps

- Review all themed primitives and quick-start component examples in [UI Primitives](/documents/basic/ui-primitives), [Overlay Components](/documents/basic/overlay), [Disclosure & Feedback](/documents/basic/disclosure), and [Forms](/documents/basic/forms).
- Customize `@layer components` CSS rules and tokens in [Styling Deep Dive](/documents/advanced/styling-deep-dive).
- Learn how `<headless-*>` and `<webcompy-*>` custom-element tags upgrade during hydration in [Custom Elements](/documents/advanced/custom-elements).
- Inspect DI scoping rules powering `FormField` slot isolation in [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive).
