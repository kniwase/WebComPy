# Virtual DOM Specification (delta)

## ADDED Requirements

### Requirement: VirtualDOMNode shall support comment nodes

`ServerDOMPort.create_comment(data)` SHALL return a `VirtualDOMNode` with `nodeName == "#comment"`, `nodeType == 8`, and `textContent == data`. Comment nodes SHALL participate in tree operations (`appendChild`, `insertBefore`, `replaceChild`, `removeChild`, `remove`, `childNodes`) identically to text nodes.

#### Scenario: Creating a virtual comment node

- **WHEN** `ServerDOMPort.create_comment("webcompy-teleport-anchor")` is called
- **THEN** a `VirtualDOMNode` with `nodeName == "#comment"` SHALL be returned
- **AND** `nodeType == 8` (comment node)
- **AND** `textContent == "webcompy-teleport-anchor"`

#### Scenario: Comment nodes participate in tree operations

- **WHEN** a virtual comment node is appended or inserted into a virtual tree
- **THEN** it SHALL appear in `parent.childNodes` at the expected position
- **AND** `remove()` / `removeChild()` SHALL remove it like any other child node

### Requirement: ServerDOMPort.render_html() shall serialize comment nodes

`ServerDOMPort.render_html()` SHALL serialize virtual comment nodes (`nodeType == 8`) as `<!--data-->`, where `data` is the comment's text content. Comment data SHALL be emitted inside the comment delimiters only and SHALL NOT be HTML-escaped as text content.

#### Scenario: Serializing a comment node

- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual tree containing a comment node with data `webcompy-teleport-anchor`
- **THEN** the output SHALL contain `<!--webcompy-teleport-anchor-->` at the node's position

#### Scenario: Comment data is not rendered text

- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual tree containing a comment node
- **THEN** no character of the comment data SHALL appear in the output outside the `<!-- ... -->` delimiters
