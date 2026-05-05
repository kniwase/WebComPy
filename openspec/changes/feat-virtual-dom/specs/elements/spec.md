# Elements (Virtual DOM) (delta)

## ADDED Requirements

### Requirement: Rendering shall use a single unified code path in both environments

All element types SHALL use the same `render()` → `_get_node()` → `_init_node()` → `_create_node()` call chain regardless of environment. On the browser, `_create_node()` SHALL delegate to `BrowserDOMPort.create_element()` which returns a `BrowserDOMNode`. On the server, `_create_node()` SHALL delegate to `ServerDOMPort.create_element()` which returns a `VirtualDOMNode`. All subsequent operations (attribute setting, child appending, event listener registration) SHALL work identically through the `DOMNode` Protocol on both implementations.

#### Scenario: Rendering a div in the browser
- **WHEN** `element.render()` is called in the browser
- **THEN** `_create_node()` SHALL call `BrowserDOMPort.create_element("div")`
- **AND** return a `BrowserDOMNode` wrapping a real JS DOM element
- **AND** `_init_new_node()` SHALL set attributes and event listeners on the returned node

#### Scenario: Rendering a div on the server
- **WHEN** `element.render()` is called on the server
- **THEN** `_create_node()` SHALL call `ServerDOMPort.create_element("div")`
- **AND** return a `VirtualDOMNode` with `nodeName == "DIV"`
- **AND** `_init_new_node()` SHALL set attributes and event listeners on the returned node
- **AND** no exception SHALL be raised

## REMOVED Requirements

### Requirement: Elements shall represent DOM nodes and render to HTML strings via _render_html()

**Reason**: The dual rendering path (`render()` for browser DOM, `_render_html()` for server HTML) is unified. Server-side HTML generation is handled by `ServerDOMPort.render_html()` which serializes the virtual DOM tree.

**Migration**: All element types remove their `_render_html()` methods. Callers use `ServerDOMPort.render_html(root_node)` instead. Existing HTML string tests should migrate to virtual DOM tree inspection or retain string comparison against `render_html()` output.
