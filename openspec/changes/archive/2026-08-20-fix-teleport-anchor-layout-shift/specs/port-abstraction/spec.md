# Port Abstraction Specification (delta)

## ADDED Requirements

### Requirement: DOMPort shall provide a comment-node factory method

`DOMPort.create_comment(data: str) -> DOMNode` SHALL create a comment node carrying the given data, as part of `DOMPort`'s document-level node-creation concern. `BrowserDOMPort.create_comment()` SHALL return a raw browser `Comment` node created via `document.createComment`. `ServerDOMPort.create_comment()` SHALL return a virtual comment node. Testing fakes SHALL provide the same signature and return a node satisfying the `DOMNode` Protocol with comment-node properties.

#### Scenario: BrowserDOMPort creates a native comment node

- **WHEN** `BrowserDOMPort.create_comment("webcompy-teleport-anchor")` is called in a PyScript environment
- **THEN** a raw browser `Comment` node SHALL be returned
- **AND** the node's data SHALL be `"webcompy-teleport-anchor"`
- **AND** the node SHALL satisfy the `DOMNode` Protocol structurally

#### Scenario: ServerDOMPort creates a virtual comment node

- **WHEN** `ServerDOMPort.create_comment("webcompy-teleport-anchor")` is called on the server
- **THEN** a `VirtualDOMNode` with `nodeName == "#comment"` and `nodeType == 8` SHALL be returned

#### Scenario: Testing fakes provide comment-node parity

- **WHEN** `create_comment(data)` is called on a testing fake DOM port
- **THEN** a node satisfying the `DOMNode` Protocol SHALL be returned
- **AND** the node SHALL report `nodeName == "#comment"` and its data SHALL be readable via `textContent`
