---
title: Custom Elements
description: Every WebComPy component is a Light DOM custom element with a derivable or explicit name, layout-transparent wrapper, and universal lifecycle hooks.
---

# Custom Elements

Every WebComPy component renders as a **Light DOM custom element**: a real DOM element with its own tag name, such as `<user-card>`. This gives every component a native DOM boundary, lets the template return multiple roots, and unlocks browser lifecycle hooks and attribute-based JavaScript interoperation.

Custom elements in WebComPy are **Light DOM** elements. WebComPy does not use Shadow DOM, so the element's children remain ordinary DOM nodes and global styles apply as usual.

## Defining a component

`define_component` is a decorator factory — always call it. When the custom element name can be derived from the function name, call it without arguments:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component()
def UserCard(context: ComponentContext[None]):
    return html.DIV({"class": "card"}, "Hello")
```

The component renders as `<user-card>` in the browser and in server-rendered HTML.

To pick an element name that differs from the Python name, pass it explicitly (positionally or by keyword):

```python
@define_component("user-card")          # or @define_component(custom_element_name="user-card")
def Card(context: ComponentContext[None]):
    return html.DIV({"class": "card"}, "Hello")
```

### Naming rules

When the name is omitted, WebComPy derives it from the function name by converting PascalCase/camelCase to kebab-case:

```
UserCard  →  user-card
ToDoListPage  →  to-do-list-page
HTTPRequest  →  http-request
```

Derivation only validates the **derived result** against the custom-element naming rules, so acronym-style names like `HTTPRequest` work as-is. Derived names that cannot form a valid custom element raise `WebComPyComponentException` with guidance:

- `App` derives `app`, which has no hyphen — rename the function to a multi-word name such as `TodoApp`, or pass an explicit tag.
- `FontFace` derives `font-face`, which is reserved by the custom-elements specification.
- Non-PascalCase names such as `my_card` or `_Card` fail derivation outright.

When a tag is passed explicitly, only the tag itself is validated; there is no constraint on the function name. Duplicate tags within one application are rejected regardless of how they were named.

## Multiple roots

A component may return a sequence of children instead of a single root element:

```python
@define_component()
def ArticleCard(context: ComponentContext[None]):
    return [
        html.HEADER({}, "Title"),
        html.MAIN({}, "Body"),
        html.FOOTER({}, "Footer"),
    ]
```

The wrapper element owns exactly one DOM node from its parent's perspective, so `repeat`, `switch`, and hydration keep working unchanged. Attributes, event handlers, and refs stay on the template children that declared them; they are not copied to the wrapper.

## The wrapper is layout-transparent by default

An unknown custom element defaults to `display: inline`, which would break layouts. WebComPy instead injects a framework rule `[webcompy-component] { display: contents; }` in an early cascade layer, so the wrapper generates **no layout box**: parent flex/grid item identity, inline flow, and percentage sizing stay with your template children.

To give the wrapper a real box, declare `display` at the definition site:

```python
@define_component("user-card", display="block")
def Card(context: ComponentContext[None]):
    return html.DIV({}, "Hello")
```

Valid values are the `ComponentDisplay` literal: `contents`, `block`, `inline`, `inline-block`, `flex`, `inline-flex`, `grid`, `inline-grid`, `flow-root`. Invalid values are rejected at definition time.

Cascade precedence: framework default `contents` < `display` argument < your own `:host` scoped styles. Components used as `Transition` children need a box-generating display (`display="block"`) for animations to run; the framework warns when it detects a layout-transparent transition child.

## Mounted and unmounted hooks

Components can react to document connection with `on_mounted` and `on_unmounted`, either through the context or as standalone decorators:

```python
from webcompy.components import on_mounted, on_unmounted


@define_component()
def LiveBadge(context: ComponentContext[None]):
    @on_mounted
    def mounted():
        print("connected to the document")

    @on_unmounted
    def unmounted():
        print("disconnected from the document")

    return html.SPAN({}, "live")
```

`on_mounted` fires when the wrapper becomes connected to the document; `on_unmounted` fires when it becomes disconnected. Hooks are coalesced: moving an element within the same document (for example, a keyed `repeat` reorder) fires neither hook.

In the browser, connection hooks are delivered in a scheduled task after the current render completes, so a hook that reads the wrapper's subtree sees the fully rendered content. When testing with `webcompy_testing.TestRenderer`, the fake DOM does not fire native connect reactions and the fake host port executes scheduled tasks immediately: hooks fire only for binds or adoptions of an already-connected node, and a fresh render never delivers `on_mounted`. Write unit tests that do not depend on hook delivery and cover hook behavior with E2E tests.

When a component is removed, its wrapper is detached from the document before `on_unmounted` runs, and `on_unmounted` runs before `on_before_destroy`, so the hook observes live component state at the moment of disconnection.

## Observed attributes

Declare `observed_attributes` to receive attribute changes as reactive props:

```python
from webcompy.signal import use_computed


@define_component(observed_attributes=("theme-color",))
def UserCard(context: ComponentContext[dict]):
    theme = use_computed(lambda: context.props["theme_color"] or "none")
    return html.DIV({}, theme)
```

Attributes are exposed under snake-case prop keys (`theme-color` → `theme_color`). Values are always strings; a present attribute without a value is `""`, and a removed attribute is `None`. Changing the attribute from JavaScript updates the prop and any UI that reads it — without recreating the wrapper:

```js
document.querySelector("user-card").setAttribute("theme-color", "dark");
```

The direction is one-way: the framework never writes prop values back to attributes. Caller-supplied props for keys that are not observed are preserved. With `observed_attributes`, `context.props` is a snapshot copied from the caller mapping, so later mutations of the original mapping do not propagate into the component; update the component's own reactive values instead.

## Styling the wrapper with :host

Every component can style its own wrapper with `:host` in scoped styles:

```python
UserCard.scoped_style = {
    ":host": {"display": "block"},
    ":host(.compact)": {"padding": "0"},
}
```

`:host` is replaced by the custom element selector and keeps the normal cid scoping. It works in static and reactive scoped styles, and in SSR output.

## Custom elements are page-global

The browser's `customElements` registry is shared across the whole document. WebComPy reuses a compatible definition when the same tag name is requested with matching metadata, and raises an error for incompatible definitions. Applications that share a document should coordinate their custom element names.

WebComPy defines custom elements before hydration, so server-rendered markup is upgraded in place. Server-side rendering never touches the browser registry; the tag is serialized as ordinary HTML.

## Migrating from the bare decorator form

Older WebComPy code used a bare `@define_component` form whose component node was the template root element. That form no longer exists; apply the decorator factory with parentheses:

```python
# before
@define_component
def UserCard(context):
    return html.DIV({"class": "card"}, "Hello")

# after (name derived from the function)
@define_component()
def UserCard(context):
    return html.DIV({"class": "card"}, "Hello")

# after (explicit tag)
@define_component("user-card")
def UserCard(context):
    return html.DIV({"class": "card"}, "Hello")
```

Watch for these behavior changes:

- **Wrapper insertion**: every component gains one DOM wrapper node. CSS that relies on structural pseudo-classes (`:first-child`, `:nth-child`) or sibling combinators (`+`, `~`) across component boundaries changes meaning; target the inner elements or use the layout-transparent default.
- **Root attribute hoisting**: attributes, event handlers, and refs declared on the template root stay on that element (now a child of the wrapper) instead of the component node.
- **Names are validated at definition time** (see [Naming rules](#naming-rules)): derived names that cannot form a valid custom element fail unless you pass an explicit tag.
- **`lazy()` import paths** reference components as `"module:Attribute"` strings — update them when you rename a component.
- **Transitions**: a component used as a `Transition` child needs a box-generating display, e.g. `display="block"`; see [The wrapper is layout-transparent by default](#the-wrapper-is-layout-transparent-by-default).
