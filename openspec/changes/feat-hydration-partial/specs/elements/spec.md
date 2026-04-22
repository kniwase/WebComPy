# Elements — Delta: feat-hydration-partial

## MODIFIED Requirements

### Requirement: Pre-rendered DOM nodes shall skip redundant writes during hydration
When attributes or text content on a prerendered node already match the component's current state, the framework SHALL NOT perform `setAttribute` or `textContent` assignment. This optimization applies only to prerendered nodes (those with `__webcompy_prerendered_node__ = True`); newly created nodes retain unconditional writes.

#### Scenario: Hydrating a text node with identical content
- **WHEN** a prerendered `#text` node's `textContent` matches the TextElement's current value
- **THEN** the framework SHALL NOT assign `textContent` on the node
- **AND** the TextElement SHALL still adopt the node and mark it as mounted

#### Scenario: Hydrating an element with identical attributes
- **WHEN** a prerendered element node's attribute values match the Element's current attribute state
- **THEN** the framework SHALL NOT call `setAttribute` for matching attributes
- **AND** attributes with `None` value in the component state SHALL still be removed via `removeAttribute` if present on the node

#### Scenario: Hydrating an element with differing attributes
- **WHEN** a prerendered element node's attribute differs from the Element's current state
- **THEN** the framework SHALL call `setAttribute` only for the differing attributes
- **AND** matching attributes SHALL remain untouched

## ADDED Requirements

### Requirement: Loading screen overlay shall be semi-transparent during hydration
The loading screen overlay (`#webcompy-loading`) SHALL use a semi-transparent dark background (e.g., `rgba(0, 0, 0, 0.5)`) instead of an opaque background. This allows the pre-rendered content beneath to remain visible during hydration.

#### Scenario: User sees pre-rendered content during hydration
- **WHEN** the browser displays the loading screen overlay over pre-rendered content
- **THEN** the overlay SHALL have a semi-transparent background
- **AND** the pre-rendered content beneath SHALL remain visible to the user