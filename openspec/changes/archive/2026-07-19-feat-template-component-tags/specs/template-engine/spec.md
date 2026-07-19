## ADDED Requirements

### Requirement: Template engine shall resolve non-HTML tags as components via ComponentStore

Tags not in the `HtmlTags` literal SHALL be resolved as component references. The component name SHALL be converted from kebab-case to PascalCase and looked up in the DI-accessible `ComponentStore`.

#### Scenario: Component tag resolution
- **WHEN** `<user-card>` is used and `UserCard` is registered in the ComponentStore
- **THEN** the `UserCard` component SHALL be instantiated and embedded as a child element

#### Scenario: Component not found with hyphen
- **WHEN** `<my-widget>` is used but no component matches in ComponentStore
- **THEN** `WebComPyException` SHALL be raised with a message that includes the looked-up component name, the available component names, and guidance that component tags require PascalCase component function names (kebab-case tag `<my-widget>` resolves to `MyWidget`)

#### Scenario: Unknown tag without hyphen
- **WHEN** `<widget>` is used and not found in ComponentStore or HtmlTags
- **THEN** the tag SHALL be treated as a regular HTML element (`Element("widget", ...)`)

#### Scenario: Self-closing component tag
- **WHEN** `<user-card title="Hi" />` is used with self-closing syntax
- **THEN** the component SHALL be instantiated with no default slot content

#### Scenario: HTML tags unaffected
- **WHEN** `<div>`, `<p>`, `<span>`, etc. are used
- **THEN** they SHALL continue to be treated as HTML elements (no ComponentStore lookup)

### Requirement: Component tags shall support static and dynamic props

Component attributes SHALL be converted to component props. Plain attributes SHALL be literal strings. `:`-prefixed attributes SHALL be variable references from the context.

#### Scenario: Static prop
- **WHEN** `<user-card title="Hello">` is used
- **THEN** `props = {"title": "Hello"}` SHALL be passed to the component

#### Scenario: Dynamic prop with Signal
- **WHEN** `<user-card :count="my_count">` is used and `my_count` is a Signal
- **THEN** `props = {"count": context["my_count"]}` SHALL be passed (Signal preserved for reactivity)

#### Scenario: Prop name kebab to snake_case conversion
- **WHEN** `<user-card :item-count="items">` is used
- **THEN** the prop name SHALL be converted from `item-count` to `item_count` in the props dict

#### Scenario: Interpolation in component attribute with Signal
- **WHEN** `<user-card title="Hello {{ name }}">` is used with `name` being a `Signal`
- **THEN** `resolve_attr` SHALL be called on the attribute parts
- **AND** a `Computed` SHALL be generated and passed as `props["title"]`
- **AND** the prop SHALL update reactively when the Signal changes

#### Scenario: Interpolation in component attribute without Signal
- **WHEN** `<user-card title="Hello {{ name }}">` is used with `name` being `"Alice"`
- **THEN** the prop value SHALL be the static string `"Hello Alice"`

### Requirement: Component body shall be passed as default slot

The children of a component tag SHALL be parsed and passed as the default slot content.

#### Scenario: Default slot
- **WHEN** `<user-card title="Hi"><p>Content</p></user-card>` is used
- **THEN** `slots = {"default": lambda: Element("p", {}, [TextElement("Content")])}` SHALL be passed

#### Scenario: Multiple children in default slot
- **WHEN** the component body has multiple elements
- **THEN** they SHALL be wrapped in a `FragmentElement` within the slot generator
