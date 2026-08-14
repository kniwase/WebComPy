---
title: Custom Elements
description: Define components as Light DOM custom elements for native DOM boundaries, multiple roots, lifecycle hooks, and attribute-based interoperation.
---

# Custom Elements

WebComPy components normally render as their template's single root element. You can opt a component into a **Light DOM custom element** instead: the component becomes a real DOM element with its own tag name, such as `<user-card>`. This gives you a native DOM boundary, lets the template return multiple roots, and unlocks browser lifecycle hooks and attribute-based JavaScript interoperation.

Custom elements in WebComPy are **Light DOM** elements. WebComPy does not use Shadow DOM, so the element's children remain ordinary DOM nodes and global styles apply as usual.

## Defining a named component

Pass the custom element name as the first argument to `define_component`:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component("user-card")
def UserCard(context: ComponentContext[None]):
    return html.DIV({"class": "card"}, "Hello")
```

The component now renders as `<user-card>` in the browser and in server-rendered HTML. The Python name (`UserCard`) stays the component name used for registration and scoped CSS; the DOM name (`user-card`) is explicit and separate.

The name must be a valid custom element name: lowercase, with a hyphen.

## Multiple roots

A named component may return a sequence of children instead of a single root element:

```python
@define_component("article-card")
def ArticleCard(context: ComponentContext[None]):
    return [
        html.HEADER({}, "Title"),
        html.MAIN({}, "Body"),
        html.FOOTER({}, "Footer"),
    ]
```

The wrapper element owns exactly one DOM node from its parent's perspective, so `repeat`, `switch`, and hydration keep working unchanged. Attributes, event handlers, and refs stay on the template children that declared them; they are not copied to the wrapper.

Unnamed components (the bare `@define_component` form) still require a single root element.

## Mounted and unmounted hooks

Named components can react to document connection with `on_mounted` and `on_unmounted`, either through the context or as standalone decorators:

```python
from webcompy.components import on_mounted, on_unmounted


@define_component("live-badge")
def LiveBadge(context: ComponentContext[None]):
    @on_mounted
    def mounted():
        print("connected to the document")

    @on_unmounted
    def unmounted():
        print("disconnected from the document")

    return html.SPAN({}, "live")
```

`on_mounted` fires when the wrapper becomes connected to the document; `on_unmounted` fires when it becomes disconnected. Hooks are coalesced: moving an element within the same document (for example, a keyed `repeat` reorder) fires neither hook. These hooks are only available in named components; using them in an unnamed component raises an error.

In the browser, connection hooks are delivered in a scheduled task after the current render completes, so a hook that reads the wrapper's subtree sees the fully rendered content. When testing with `webcompy_testing.TestRenderer`, the fake DOM does not fire native connect reactions and the fake host port executes scheduled tasks immediately: hooks fire only for binds or adoptions of an already-connected node, and a fresh render never delivers `on_mounted`. Write unit tests that do not depend on hook delivery and cover hook behavior with E2E tests.

When a named component is removed, its wrapper is detached from the document before `on_unmounted` runs, and `on_unmounted` runs before `on_before_destroy`, so the hook observes live component state at the moment of disconnection. Because the wrapper is already detached, an `on_before_destroy` hook of a named component sees the node after removal.

## Observed attributes

Declare `observed_attributes` to receive attribute changes as reactive props:

```python
from webcompy.signal import use_computed


@define_component("user-card", observed_attributes=("theme-color",))
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

Named components can style their own wrapper with `:host` in scoped styles:

```python
UserCard.scoped_style = {
    ":host": {"display": "block"},
    ":host(.compact)": {"padding": "0"},
}
```

`:host` is replaced by the custom element selector and keeps the normal cid scoping. It works in static and reactive scoped styles, and in SSR output. `:host` in an unnamed component raises an error.

## Custom elements are page-global

The browser's `customElements` registry is shared across the whole document. WebComPy reuses a compatible definition when the same tag name is requested with matching metadata, and raises an error for incompatible definitions. Applications that share a document should coordinate their custom element names.

WebComPy defines named custom elements before hydration, so server-rendered markup is upgraded in place. Server-side rendering never touches the browser registry; the tag is serialized as ordinary HTML.
