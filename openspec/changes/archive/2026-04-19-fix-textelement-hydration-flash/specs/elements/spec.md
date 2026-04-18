## MODIFIED Requirements

### Requirement: Pre-rendered DOM nodes shall be reused during hydration
When the browser encounters an existing DOM node marked as pre-rendered with a matching tag name, the element SHALL reuse that node instead of creating a new one, enabling efficient hydration of server-rendered content. This requirement applies to all node types including `#text` nodes.

#### Scenario: Hydrating a server-rendered page
- **WHEN** the browser finds an existing DOM node with `__webcompy_prerendered_node__ = True` and a matching tag name
- **THEN** the element SHALL adopt that node rather than creating a new one
- **AND** attributes SHALL be updated to match the element's current state

#### Scenario: Hydrating a server-rendered text node
- **WHEN** the browser finds an existing `#text` node with `__webcompy_prerendered_node__ = True`
- **THEN** the TextElement SHALL adopt that node rather than removing it and creating a new one
- **AND** no visible flash or content change SHALL occur during hydration

#### Scenario: Hydrating a reactive text node
- **WHEN** a TextElement wraps a Signal value
- **AND** the browser finds a pre-rendered `#text` node for it
- **THEN** the TextElement SHALL adopt the existing node without overwriting its content
- **AND** subsequent Signal changes SHALL update the adopted node via the existing `on_after_updating` callback