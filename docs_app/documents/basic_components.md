---
title: Components
description: Define Light DOM components with @define_component(), receive props and slots, hook into lifecycle events, and apply static scoped styles.
---

# Components

Components are the building blocks of a WebComPy user interface. In WebComPy, every component is a Python function decorated with `@define_component()` that returns an element tree and renders in the browser as a **Light DOM custom element** (no Shadow DOM).

Use components whenever you want a reusable piece of UI with its own props, slots, local reactive state, lifecycle hooks, or scoped CSS.

## At a glance

A component receives a `ComponentContext` and returns elements built with `html` helpers or `render_template`:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component()
def GreetingCard(context: ComponentContext[dict[str, str]]):
    name = context.props.get("name", "World")
    return html.DIV(
        {"class": "card"},
        html.H2({}, f"Hello, {name}"),
        context.slots("default", fallback=lambda: html.P({}, "Welcome to WebComPy.")),
    )


# Render it inside another component:
GreetingCard(
    {"name": "Alice"},
    slots={"default": lambda: html.P({}, "Glad you are here.")},
)
```

Calling `GreetingCard(...)` emits `<greeting-card webcompy-component="GreetingCard">...</greeting-card>` in both server-rendered HTML and the browser DOM.

## Defining components and tag names

`define_component` is a decorator factory — always call it with parentheses:

- **Derived tag name (default)**: calling `@define_component()` converts the PascalCase function name to kebab-case (`GreetingCard` → `<greeting-card>`, `TodoListPage` → `<todo-list-page>`).
- **Explicit tag name**: pass a tag positionally or by keyword when you want a different custom element tag:

```python
@define_component(custom_element_name="user-badge")
def Badge(context: ComponentContext[None]):
    return html.SPAN({}, "Member")
```

Custom element names in the HTML specification must contain at least one hyphen and cannot use reserved names (such as `font-face`). Single-word function names like `App` derive `app` with no hyphen and raise `WebComPyComponentException` at definition time — rename the function to a multi-word PascalCase name (such as `TodoApp`) or pass `custom_element_name=` explicitly.

### Returning multiple roots

Because the custom element tag acts as a real DOM wrapper, a component can return a single `Element` or a sequence (`list` or `tuple`) of elements without an extra wrapping `<div>`:

```python
@define_component()
def ArticleHeader(context: ComponentContext[None]):
    return [
        html.H1({}, "Release Notes"),
        html.P({}, "Latest framework updates"),
    ]
```

## Props and slots

Components accept `(props, *, slots=None)`:

- **Props (`context.props`)**: any Python value (commonly a `dict`, `TypedDict`, dataclass, or `RouterContext`) annotated via `ComponentContext[PropsType]`. Use `ComponentContext[None]` when a component takes no props.
- **Slots (`context.slots`)**: pass `slots={"slot_name": lambda: ...}` from the parent and invoke `context.slots(name, fallback=...)` inside the component. The primary body slot is named `"default"`.

```python
@define_component()
def PanelCard(context: ComponentContext[dict[str, str]]):
    return html.SECTION(
        {"class": "panel"},
        html.HEADER({}, context.slots("header", fallback=lambda: html.STRONG({}, context.props["title"]))),
        html.DIV({}, context.slots("default")),
        html.FOOTER({}, context.slots("footer", fallback=lambda: "")),
    )
```

> **Note**: Each slot entry is a zero-argument generator (`lambda: ...`) rather than an already-built node, so the component controls when and where the slot renders. Returning `None` from `fallback=lambda: None` omits optional regions cleanly.

## Lifecycle hooks

Register hooks inside component setup using decorators imported from `webcompy.components` (or the equivalent methods on `context`):

| Hook | Timing | Typical use |
|---|---|---|
| `@on_before_rendering` | Before initial render | Reset per-visit state, prepare data |
| `@on_after_rendering` | After render completes | Post-render work |
| `@on_mounted` | After wrapper connects to browser `document` | DOM measurement, focus, third-party widget init |
| `@on_unmounted` | After wrapper disconnects from `document` | Disconnect browser observers |
| `@on_before_destroy` | Before component disposal | Cancel timers, close manual subscriptions |

Both sync functions and `async def` coroutines are accepted:

```python
from webcompy.components import (
    ComponentContext,
    define_component,
    on_before_destroy,
    on_before_rendering,
    on_mounted,
)
from webcompy.elements import html


@define_component()
def StatusPanel(context: ComponentContext[None]):
    @on_before_rendering
    def prepare():
        print("Preparing status panel")

    @on_mounted
    def connected():
        print("Mounted into the browser document")

    @on_before_destroy
    def cleanup():
        print("Disposing component resources")

    return html.DIV({}, "Status: ready")
```

For document metadata inside page components, call `context.set_title("Page Title")` and `context.set_meta(key, {...})` during setup.

## Scoped styles and host display

Attach a static style dictionary to `<Component>.scoped_style` after defining the component. WebComPy scopes selectors to the component using its `webcompy-cid-*` attribute and outputs them in the `webcompy-scope` cascade layer:

```python
@define_component(display="block")
def InfoBanner(context: ComponentContext[None]):
    return html.P({"class": "message"}, "Heads up!")


InfoBanner.scoped_style = {
    ":host": {
        "border": "1px solid var(--color-border)",
        "border-radius": "var(--radius-md)",
        "padding": "var(--space-3)",
    },
    ".message": {
        "margin": "0",
        "font-weight": "600",
    },
}
```

### The `display` keyword argument and `:host`

By default, custom element wrappers use `display: contents` so they remain layout-transparent inside flex/grid parents and do not create an extra CSS box. Pass `display="block"` (or another `ComponentDisplay` value: `"inline"`, `"inline-block"`, `"flex"`, `"inline-flex"`, `"grid"`, `"inline-grid"`, `"flow-root"`, `"contents"`) on `@define_component(...)` — or target `:host` in `scoped_style` — when the component wrapper itself needs a box, background, border, or transition animation.

## Notes & caveats

- Always call `@define_component()` with parentheses; bare `@define_component` without parentheses is not supported.
- Component setup runs once per component mount, not on every reactive update. Read reactive state inside elements, templates, or `use_computed` rather than expecting setup to re-execute.
- Do not register duplicate custom element tags in the same application — WebComPy rejects collisions at definition time.

## Next steps

- See a minimal runnable component app in the [Hello World](/documents/examples/hello-world) example.
- Learn how to write component views with HTML syntax in [HTML Templates](/documents/basic/template-html).
- Explore [Styling & Themes](/documents/basic/styling-and-themes) for cascade layers, `css_text`, and theme tokens.
- When you need `observed_attributes`, browser/test lifecycle nuances, or custom-element JavaScript interop, continue to [Custom Elements](/documents/advanced/custom-elements).
