# Elements (Virtual DOM)

## Purpose

The element system is how WebComPy represents and manipulates the user interface. Rather than requiring developers to write HTML templates or JSX, WebComPy provides a Python API for constructing element trees — each element corresponds to a DOM node, and signal values can be used directly as attributes, text content, or list sources.

The system does not use virtual DOM diffing. Instead, it takes a direct approach: when a reactive value changes, the specific DOM node that depends on that value is updated in place. For dynamic content (conditional rendering and list rendering), the entire subtree is regenerated when the controlling value changes. This trades fine-grained efficiency for implementation simplicity.

**What WebComPy does not yet provide:** WebComPy's `repeat` now supports key-based reconciliation and dict-based rendering for efficient DOM updates. However, conditional branches (`switch`) still completely replace their subtree rather than patching it, and `TextElement` does not hydrate pre-rendered text nodes in SSR output.

## Requirements

### Requirement: Elements shall represent DOM nodes and compose into trees
Developers SHALL be able to create element trees using a Python API where each element corresponds to a DOM node, with support for nested children, attributes, event handlers, and DOM references.

#### Scenario: Creating a simple element tree
- **WHEN** a developer writes `html.DIV({"class": "container"}, html.H1({}, "Hello"), html.P({}, "World"))`
- **THEN** an element tree SHALL be created with a `div` containing an `h1` and a `p`
- **AND** the tree SHALL be renderable to browser DOM nodes or HTML strings

### Requirement: Signal values in elements shall update the DOM automatically
When a signal value is used as an element attribute or text content, any change to that value SHALL automatically update the corresponding DOM node without manual intervention.

#### Scenario: Using a signal attribute
- **WHEN** a developer writes `html.INPUT({"value": my_reactive_text})`
- **AND** later sets `my_reactive_text.value = "new text"`
- **THEN** the input element's `value` attribute SHALL update in the DOM

#### Scenario: Using signal text content
- **WHEN** a developer writes `TextElement(my_count)` where `my_count` is a `Signal`
- **AND** later increments `my_count`
- **THEN** the text content in the DOM SHALL update to reflect the new count

### Requirement: Conditional rendering shall display one branch at a time
The `switch` construct SHALL evaluate a series of conditions and render the template of the first matching condition. When conditions change, the previous branch SHALL be removed and the new branch SHALL be rendered. The branch template MAY return a `DynamicElement` (such as a `repeat`), and the `SwitchElement` SHALL handle it as a transparent child with no DOM node of its own. When the `SwitchElement` is refreshed due to a signal change (such as a route change), any `on_after_rendering` lifecycle hooks of newly created components SHALL be deferred until after the reactive propagation and DOM updates have completed.

#### Scenario: Switching between display modes
- **WHEN** a developer defines `switch(cases=[(is_admin, lambda: AdminPanel()), (is_user, lambda: UserPanel())], default=lambda: GuestPanel())`
- **AND** `is_admin` becomes `True`
- **THEN** `AdminPanel` SHALL be rendered
- **WHEN** `is_admin` becomes `False` and `is_user` becomes `True`
- **THEN** `AdminPanel` SHALL be removed and `UserPanel` SHALL be rendered

#### Scenario: Switching routes triggers async operations in new component
- **WHEN** a `SwitchElement` is used for routing (as in `RouterView`)
- **AND** the route changes from one page to another
- **AND** the new page component has an `on_after_rendering` hook that starts async operations
- **THEN** the new component SHALL be fully mounted in the DOM before `on_after_rendering` runs
- **AND** async operations SHALL execute in a clean event loop context (not nested within the signal callback chain)

#### Scenario: Switch branch containing a repeat element
- **WHEN** a developer defines `switch(cases=[(is_list_view, lambda: repeat(items, item_template))])`
- **AND** `is_list_view` becomes `True`
- **THEN** the `repeat` SHALL render its items inside the switch's parent DOM node
- **WHEN** `is_list_view` becomes `False`
- **THEN** the `repeat` and all its rendered items SHALL be removed

### Requirement: List and dict rendering shall map signal collections to element templates with type-safe overloads
The `repeat` construct SHALL support five type-safe overload signatures:

1. `repeat(ReactiveDict[K, V], template: (V,) -> ChildNode)` — dict value-only, keyed by dict keys
2. `repeat(ReactiveDict[K, V], template: (V, K) -> ChildNode)` — dict value+key, keyed by dict keys
3. `repeat(ReactiveList[V], template: (V,) -> ChildNode)` — list unkeyed (backward compatible, full rebuild)
4. `repeat(ReactiveList[V], template: (V, int) -> ChildNode)` — list with index as key
5. `repeat(ReactiveList[V], template: (V, K) -> ChildNode), key: (V) -> K)` — list with custom key function

When `key` is provided (overloads 2, 4, 5) or dict mode is used (overloads 1, 2), `RepeatElement` SHALL reuse existing DOM elements for items whose keys persist across mutations. When no `key` is provided and single-arg template is used (overload 3), all rendered items SHALL be removed and regenerated (full rebuild behavior).

#### Scenario: Rendering a list of items with key function
- **WHEN** a developer writes `repeat(items, lambda item, id: html.LI({"data-id": id}, item.name), key=lambda item: item.id)`
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** only the new `<li>` SHALL be created and appended
- **AND** existing `<li>` elements SHALL remain in the DOM unchanged

#### Scenario: Rendering a list of items without keys (backward compatible)
- **WHEN** a developer writes `repeat(items, lambda item: html.LI({}, item.name))` without a `key` parameter
- **THEN** one `<li>` SHALL be rendered for each item in `items`
- **WHEN** `items.append(new_item)` is called
- **THEN** the entire list SHALL be regenerated with the new item included

#### Scenario: Rendering a ReactiveDict with value-only template
- **WHEN** a developer writes `repeat(my_dict, lambda value: html.LI({}, value))`
- **THEN** one `<li>` SHALL be rendered for each value in `my_dict`
- **AND** dict keys SHALL be used as reconciliation identifiers for efficient DOM updates

#### Scenario: Rendering a ReactiveDict with value-key template
- **WHEN** a developer writes `repeat(my_dict, lambda value, key: html.LI({}, f"{key}: {value}"))`
- **THEN** one `<li>` SHALL be rendered for each key-value pair in `my_dict`
- **AND** dict keys SHALL be used as reconciliation identifiers for efficient DOM updates

### Requirement: Pre-rendered DOM nodes shall be reused during hydration
When the browser encounters an existing DOM node marked as pre-rendered with a matching tag name, the element SHALL reuse that node instead of creating a new one, enabling efficient hydration of server-rendered content.

#### Scenario: Hydrating a server-rendered page
- **WHEN** the browser finds an existing DOM node with `__webcompy_prerendered_node__ = True` and a matching tag name
- **THEN** the element SHALL adopt that node rather than creating a new one
- **AND** attributes SHALL be updated to match the element's current state

### Requirement: Event handlers shall propagate user interactions to Python
Developers SHALL be able to attach event handlers to elements using `@event_name` attribute syntax. In the browser, these handlers SHALL be properly proxied for PyScript interop and cleaned up when the element is removed.

#### Scenario: Handling a button click
- **WHEN** a developer writes `html.BUTTON({"@click": on_click}, "Click me")`
- **THEN** clicking the button in the browser SHALL invoke the `on_click` Python function
- **AND** the event handler SHALL receive the DOM event object

### Requirement: DOM references shall allow direct access to real DOM nodes
Developers SHALL be able to create a `DomNodeRef` and pass it as a `:ref` attribute to any element. After the element is rendered, the ref SHALL provide access to the underlying DOM node for imperative operations.

#### Scenario: Focusing an input element
- **WHEN** a developer creates `input_ref = DomNodeRef()` and passes it as `":ref"` on an input element
- **AND** the element is rendered
- **THEN** `input_ref.element` SHALL return the actual DOM input element
- **AND** `input_ref.element.focus()` SHALL focus the input in the browser