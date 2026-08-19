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

`ServerDOMPort.render_html()` SHALL serialize virtual comment nodes (`nodeType == 8`) as `<!--data-->`, where `data` is the comment's text content. Comment data SHALL be emitted inside the comment delimiters only and SHALL NOT be HTML-escaped as text content. Comment data SHALL be comment-safe: serializing a comment whose data contains `--` or ends with `-` (which would produce invalid HTML) SHALL raise `ValueError`.

#### Scenario: Serializing a comment node

- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual tree containing a comment node with data `webcompy-teleport-anchor`
- **THEN** the output SHALL contain `<!--webcompy-teleport-anchor-->` at the node's position

#### Scenario: Comment data is not rendered text

- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual tree containing a comment node
- **THEN** no character of the comment data SHALL appear in the output outside the `<!-- ... -->` delimiters

#### Scenario: Unsafe comment data is rejected at serialization

- **WHEN** `ServerDOMPort.render_html(root)` is called on a virtual tree containing a comment node whose data contains `--` or ends with `-`
- **THEN** a `ValueError` SHALL be raised
- **AND** no partial comment markup SHALL be emitted

### Requirement: Comment data shall not contribute to element text aggregation

For element nodes (`nodeType == 1`), `VirtualDOMNode.textContent` SHALL concatenate only the text content of non-comment child nodes, mirroring the DOM `Element.textContent` semantics. Comment data SHALL NOT appear in an element's aggregated `textContent`, while a comment node's own `textContent` SHALL continue to return its data.

#### Scenario: Comment children are invisible to element text content

- **WHEN** a virtual element contains text nodes and a comment node with data `webcompy-teleport-anchor`
- **THEN** the element's `textContent` SHALL contain the text nodes' content only
- **AND** the comment's data SHALL NOT appear in the element's `textContent`

#### Scenario: Comment node keeps its own text content

- **WHEN** `textContent` is read on a virtual comment node
- **THEN** it SHALL return the comment's data
