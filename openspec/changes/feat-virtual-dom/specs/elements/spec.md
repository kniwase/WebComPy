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

### Requirement: Elements shall represent DOM nodes and compose into trees

**Reason**: The dual rendering path (`_render()` for browser DOM, `_render_html()` for server HTML) is unified into a single `render()` entry point. The requirement that elements "compose into trees" and "are renderable to browser DOM nodes or HTML strings" (existing spec scenario) still holds — the change is that HTML rendering is now handled by `ServerDOMPort.render_html()` instead of per-element `_render_html()` methods.

**Migration**: All element types remove their `_render_html()` methods. Callers use `ServerDOMPort.render_html(root_node)` instead. Existing HTML string tests should migrate to virtual DOM tree inspection or retain string comparison against `render_html()` output.
