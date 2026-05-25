# Element Preserve Children

## Purpose

The `:preserve_children` attribute allows elements to declare that external JavaScript (e.g., syntax highlighters, rich text editors, third-party widgets) may manage their child DOM nodes. When this attribute is set, WebComPy skips the excess-child-node cleanup that normally runs during rendering and hydration, leaving externally-managed child nodes intact.

## Requirements

### Requirement: Element shall accept :preserve_children attribute

An `Element` or `Component` SHALL accept a `:preserve_children` boolean attribute that controls whether the framework's child-node cleanup is suppressed. The attribute SHALL follow the same pattern as `:ref`: extracted in `create_element()`, stored internally as `_preserve_children`, and never rendered as a DOM attribute. The default value SHALL be `False`.

#### Scenario: Setting :preserve_children on an element
- **WHEN** a developer writes `html.CODE({"class": "language-python", ":preserve_children": True})`
- **THEN** the resulting `Element` SHALL have `_preserve_children = True`
- **AND** no `preserve-children` attribute SHALL appear in the rendered DOM

#### Scenario: Default value when :preserve_children is not specified
- **WHEN** a developer writes `html.CODE({"class": "language-python"})` without `:preserve_children`
- **THEN** the resulting `Element` SHALL have `_preserve_children = False`

#### Scenario: Component inherits :preserve_children from root element
- **WHEN** a component's root `Element` has `_preserve_children = True`
- **THEN** the `Component` instance SHALL have `_preserve_children = True`

### Requirement: Render shall skip child cleanup when :preserve_children is set

When `ElementWithChildren._render()` executes on an element with `_preserve_children = True`, the framework SHALL skip the excess-child-node cleanup loop. The render of the element's own node and its children SHALL proceed normally. When `_preserve_children` is `False` (default), the cleanup loop SHALL execute as before.

#### Scenario: Render preserves externally-managed child nodes
- **WHEN** an element has `_preserve_children = True` and `_children_length = 0`
- **AND** an external JavaScript library has injected 10 `<span>` child nodes into the element's DOM node
- **AND** the element's `_render()` is called
- **THEN** all 10 externally-managed `<span>` nodes SHALL remain in the DOM
- **AND** `node.childNodes.length` SHALL still be 10 after the render

#### Scenario: Render without :preserve_children still cleans up
- **WHEN** an element has `_preserve_children = False` (default) and `_children_length = 0`
- **AND** external nodes have been injected into the element's DOM node
- **AND** the element's `_render()` is called
- **THEN** the external nodes SHALL be removed by the cleanup loop
- **AND** `node.childNodes.length` SHALL be 0 after the render

#### Scenario: Children of preserved element still render normally
- **WHEN** an element with `_preserve_children = True` has WebComPy-managed children
- **AND** the element's `_render()` is called
- **THEN** each child SHALL call `_render()` normally
- **AND** the parent element's cleanup loop SHALL be skipped

### Requirement: Hydrate shall skip child cleanup when :preserve_children is set

When `ElementWithChildren._hydrate_node()` executes on an element with `_preserve_children = True`, the framework SHALL skip the excess-child-node cleanup loop. Re-indexing and child hydration SHALL proceed normally.

#### Scenario: Hydrate preserves pre-rendered external nodes
- **WHEN** an element with `_preserve_children = True` and `_children_length = 0` is being hydrated
- **AND** the server-rendered DOM already contains child `<span>` nodes from an external library
- **THEN** those `<span>` nodes SHALL remain after hydration
- **AND** the cleanup loop SHALL NOT remove them

### Requirement: :preserve_children shall not apply to DynamicElement types

`DynamicElement` types (`SwitchElement`, `RepeatElement`) SHALL NOT support the `:preserve_children` attribute. These types have no DOM node of their own and delegate to their parent.

#### Scenario: :preserve_children is ignored on DynamicElement subtypes
- **WHEN** `:preserve_children` is somehow set on a `DynamicElement` instance
- **THEN** it SHALL have no effect on the element's behavior
- **AND** the flag SHALL NOT propagate to the parent element
