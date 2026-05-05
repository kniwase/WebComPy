# Port Abstraction (delta)

## MODIFIED Requirements

### Requirement: Server port implementations shall provide equivalent behavior

Server port implementations SHALL provide the same method signatures and return types as browser implementations. ServerDOMPort SHALL construct a virtual DOM tree via `VirtualDOMNode` instances instead of raising exceptions. `ServerDOMPort.create_element()` SHALL return a `VirtualDOMNode`. `ServerDOMPort.create_text_node()` SHALL return a virtual text node. `ServerDOMPort.query_selector()` and `get_element_by_id()` SHALL return `None` (SSG does not query existing DOM). `ServerDOMPort.set_title()` SHALL be a no-op. `ServerDOMPort.schedule_macro_task()` SHALL execute the callback synchronously.

ServerDOMPort SHALL additionally provide `render_html(node: DOMNode) -> str` for serializing virtual trees to HTML strings.

#### Scenario: ServerDOMPort creates elements for virtual tree
- **WHEN** `ServerDOMPort.create_element("div")` is called on the server
- **THEN** a `VirtualDOMNode` SHALL be returned instead of raising an exception
- **AND** the node SHALL have `nodeName == "DIV"` and `nodeType == 1`

#### Scenario: ServerDOMPort serializes virtual tree to HTML
- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual tree
- **THEN** a valid HTML string SHALL be returned
- **AND** void elements SHALL be self-closing and text SHALL be escaped
