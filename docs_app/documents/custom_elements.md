---
title: Custom Elements
description: Author Light DOM custom-element components with @define_component() — multi-root wrappers, document connection hooks, observed attributes, registry reuse, hydration upgrade order, and :host styling.
---

# Custom Elements

Every `@define_component()` component renders as a native **Light DOM custom element** (`<user-card>`, `<nav-bar>`) with no Shadow DOM encapsulation. This wrapper boundary lets components return multiple root nodes cleanly, exposes document-connection lifecycle hooks (`@on_mounted` / `@on_unmounted`), bridges external DOM attribute mutations into reactive props via `observed_attributes`, and lets `:host` scoped styles target the wrapper directly.

For everyday component syntax, props, slots, static `scoped_style`, and custom-element name derivation rules, start with [Components](/documents/basic/components).

## When to use

- **Writing standard single-file components with props, slots, and element-name basics** — start with [Components](/documents/basic/components).
- **Returning multiple root elements cleanly, controlling layout boxes via `display` / `:host`, or writing JavaScript attribute interop** — use the custom-element contracts below.
- **Using reactive scoped CSS variables or full `@layer` cascade rules** — see [Styling Deep Dive](/documents/advanced/styling-deep-dive).
- **Styling first-party headless components (`headless-*`) and themed pairs (`webcompy-*`)** — see [UI Headless Contract](/documents/advanced/ui-headless-contract).

## Setup

Always invoke `@define_component(...)` as a decorator factory with parentheses. Omit arguments to derive the kebab-case tag from the function name (`UserCard` -> `<user-card>`), or supply `custom_element_name=`, `display=`, and `observed_attributes=`:

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component(custom_element_name="app-status-card", display="block")
def StatusCard(context: ComponentContext[None]):
    return [
        html.HEADER({}, "System"),
        html.MAIN({}, "All services operational"),
    ]
```

## Recipes

### 1. Return multiple roots with a single parent-facing DOM node

Returning a sequence (`list` / `tuple`) renders those elements directly as Light DOM children of the custom-element wrapper while preserving the parent's single-node identity contract (`repeat`, `switch`, and hydration reconciliation treat `<article-card>` as one node):

```python
@define_component()
def ArticleCard(context: ComponentContext[None]):
    return [
        html.HEADER({}, "Title"),
        html.MAIN({}, "Body"),
        html.FOOTER({}, "Footer"),
    ]
```

Template-child attributes, event handlers, and `DomNodeRef` stay on those child elements and are not hoisted onto the wrapper node.

### 2. Run DOM integration code with `on_mounted` and `on_unmounted`

Use `@on_mounted` / `@on_unmounted` (or `context.on_mounted(...)` / `context.on_unmounted(...)`) to manage third-party DOM widgets or document measurements once the wrapper connects to or disconnects from the document:

```python
from webcompy.components import ComponentContext, define_component, on_mounted, on_unmounted
from webcompy.elements import html


@define_component()
def ChartWidget(context: ComponentContext[None]):
    @on_mounted
    def connected():
        print("Wrapper connected to document")

    @on_unmounted
    def disconnected():
        print("Wrapper disconnected from document")

    return html.DIV({"class": "chart-host"})
```

In the browser, connection callbacks run after the current render commits so the wrapper's children are already in the DOM, and temporary moves within the same document (such as keyed `repeat` reordering) are coalesced so neither hook fires spuriously. When a component is removed, its wrapper detaches first, then `on_unmounted` runs, and finally `on_before_destroy` runs.

### 3. Bridge external JavaScript attributes with `observed_attributes`

Declare `observed_attributes=("theme-color", ...)` to expose DOM attribute changes reactively on `context.props` using snake-case keys (`"theme-color"` -> `context.props["theme_color"]`):

```python
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html


@define_component(observed_attributes=("theme-color",))
def ThemeBadge(context: ComponentContext[dict]):
    label = use_computed(lambda: context.props["theme_color"] or "default")
    return html.SPAN({}, label)
```

External JavaScript updating the custom element drives WebComPy reactively without recreating the wrapper:

```js
document.querySelector("theme-badge").setAttribute("theme-color", "dark");
```

Attribute values stay strings (`""` for valueless present attributes, `None` when removed). Binding is strictly one-way (`attribute -> prop`); WebComPy never writes prop changes back via `setAttribute` or `removeAttribute`.

### 4. Control wrapper layout boxes and `:host` cascade precedence

Because unknown custom elements default to `display: inline`, WebComPy emits `[webcompy-component] { display: contents; }` once per document in an early cascade layer (`components`, ordered before `webcompy-scope`) so wrappers generate no layout box by default. Override this per component with `display=` (`ComponentDisplay`: `"contents"`, `"block"`, `"inline"`, `"inline-block"`, `"flex"`, `"inline-flex"`, `"grid"`, `"inline-grid"`, `"flow-root"`) or via `:host` in scoped styles:

```python
@define_component(display="block")
def CardPanel(context: ComponentContext[None]):
    return html.DIV({"class": "body"}, "Box-generating wrapper")


CardPanel.scoped_style = {
    ":host(.compact)": {"display": "flex", "gap": "var(--space-2)"},
}
```

Cascade precedence runs strictly: `[webcompy-component] { display: contents; }` < `display=` parameter < `:host` scoped styles (`@layer webcompy-scope`), regardless of whether the framework UI stylesheet is linked.

## Behavior notes

- **Page-global registry & hydration upgrade order**: Browser `customElements` definitions live at document scope. During `app.run()`, WebComPy defines all known custom elements **before** child hydration begins so server-rendered `<user-card>` tags upgrade in place and are adopted rather than replaced. Lazy components (`lazy()`) register their tag before creating or adopting their first node.
- **Compatible definition reuse vs conflict**: Re-registering the same tag name with identical custom-element and observed-attribute metadata reuses the existing browser definition while keeping each node's Python instance separate; conflicting non-WebComPy or mismatched definitions raise `WebComPyComponentException` explicitly rather than clobbering existing definitions.
- **SSR and destruction cleanup**: During SSR/SSG, custom element tags and Light DOM children render as ordinary HTML without touching browser registries. On component teardown, per-node attribute and lifecycle FFI proxies are released cleanly.
- **`TestRenderer` connection hook behavior**: In unit tests using `webcompy_testing.TestRenderer`, the fake DOM does not trigger native custom-element `connectedCallback` reactions automatically; `on_mounted` fires only when binding/adopting already-connected nodes, so test DOM-connection hooks in Playwright E2E suites.

## Pitfalls

- **Structural CSS selectors across component wrappers**: Every component contributes one real DOM node (`<user-card>`), so sibling/child selectors like `.parent > div` or `:first-child` see the custom-element tag unless styled inside the template or via `:host`.
- **Root attribute hoisting assumptions**: Placing `id`, `class`, or `@click` on the outermost returned template element attaches them to that child, not `<my-component>`.
- **Mutating caller prop dicts with `observed_attributes`**: When `observed_attributes` is set, `context.props` receives a copied snapshot merged with observed attribute state, so mutating the caller's original dict afterwards has no effect.
- **Omitting `display="block"` inside `Transition`**: Components wrapped directly inside `Transition` require a real CSS box (`display="block"` or `:host { display: block; }`); layout-transparent (`display: contents`) wrappers cannot animate dimensions/transforms.
- **Legacy bare `@define_component` decorator**: The old un-parenthesized `@define_component` form is removed — always write `@define_component(...)` (and verify `lazy("mod:Attr", __file__)` strings after any component rename).

## Next steps

- Review everyday component syntax, props, slots, and element-name derivation rules in [Components](/documents/basic/components).
- Explore `:host` reactive variables and full `@layer` CSS precedence in [Styling Deep Dive](/documents/advanced/styling-deep-dive) and [Styling & Themes](/documents/basic/styling-and-themes).
- See how headless `headless-*` and themed `webcompy-*` wrappers layer behavior and styling in [UI Headless Contract](/documents/advanced/ui-headless-contract).
- Animate box-generating custom elements in [Transition](/documents/advanced/transition) and review hydration adoption in [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
