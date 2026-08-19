# Teleport Specification (delta)

## MODIFIED Requirements

### Requirement: Teleport shall occupy exactly one static anchor node at its logical position

The Teleport element SHALL contribute exactly one DOM node — a placeholder — at its logical position in the element tree, and SHALL report a node count of one regardless of how many nodes its teleported subtree contains or how that count changes over time. The placeholder SHALL be a comment node whose data is `webcompy-teleport-anchor` in both the server-rendered output and the browser-created anchor, so that the anchor slot survives HTML parsing without creating a layout box. Sibling node-index accounting SHALL therefore remain stable across any change inside the teleported subtree (conditional children, repeated children, async children).

#### Scenario: Sibling indices are stable while teleported content changes

- **WHEN** an element tree contains a text node, a Teleport, and another text node in sequence, and the teleported subtree gains or loses nodes
- **THEN** the trailing text node SHALL remain at its correct position among the logical parent's child nodes
- **AND** no re-indexing error or node drift SHALL occur at the logical position

#### Scenario: Anchor is a placeholder, not rendered content

- **WHEN** a Teleport with children is mounted
- **THEN** the node at the logical position SHALL be a comment node with data `webcompy-teleport-anchor`
- **AND** the anchor SHALL introduce no rendered content or text into the document
- **AND** the teleported children SHALL exist only under the target container

### Requirement: Server-side rendering shall emit only the anchor

During server-side rendering and static generation, a Teleport SHALL render only its anchor placeholder at the logical position and SHALL NOT render its children's content anywhere in the document. The browser SHALL mount the children under the target during the client render pass after hydration. Teleported content is therefore absent from SSR HTML by design. The anchor SHALL be serialized as a comment node with data `webcompy-teleport-anchor` (`<!--webcompy-teleport-anchor-->`), so that its node slot survives HTML parsing without creating a layout box and positional hydration adoption of the anchor and of the siblings following the Teleport stays aligned. Because comment nodes break text runs during HTML parsing, bare text siblings adjacent to the anchor SHALL remain distinct nodes after parsing; hydration SHALL adopt the anchor and each sibling in index order, so that each sibling appears exactly once in the final document. During hydration a Teleport SHALL schedule its own client render whenever its children are not yet rendered, including when the anchor had to be recreated instead of adopted; the teleport's mounting SHALL NOT depend on an app-level post-hydration render pass.

#### Scenario: SSR output contains no teleported content

- **WHEN** a page containing `Teleport({"to": "body"}, modal)` is server-rendered
- **THEN** the SSR HTML SHALL contain the anchor placeholder at the logical position
- **AND** the SSR HTML SHALL NOT contain the modal markup under `<body>` or anywhere else

#### Scenario: SSR anchor occupies a parseable slot

- **WHEN** a tree containing `[element, Teleport, element]` is server-rendered
- **THEN** the SSR HTML SHALL contain `<!--webcompy-teleport-anchor-->` between the two elements at the logical position
- **AND** a browser parsing that HTML SHALL produce a distinct comment node whose data is `webcompy-teleport-anchor` for the anchor slot

#### Scenario: Text-adjacent SSR anchors preserve sibling order through parsing

- **WHEN** a tree containing `[text node, Teleport, text node]` is server-rendered
- **THEN** the SSR HTML SHALL contain `<!--webcompy-teleport-anchor-->` between the two text runs at the logical position
- **AND** a browser parsing that HTML SHALL produce three distinct nodes — text, comment, text — with no merging of the text runs
- **AND** hydration SHALL adopt the comment anchor and each text sibling in index order, so that each sibling appears exactly once in the final document
- **AND** the Teleport SHALL schedule its own client render during hydration, so that its children mount under the target without relying on a post-hydration render pass

#### Scenario: Text-adjacent SSR anchors merge on parse and recover on hydration

- **WHEN** a tree containing `[text node, Teleport, text node]` is server-rendered and the anchor comment is absent from the parsed DOM at the teleport position (for example a third-party sanitizer stripped comments)
- **THEN** the adjacent text runs SHALL be merged by the parser into a single text node, leaving no distinct anchor slot
- **AND** hydration SHALL adopt the merged node as the preceding text sibling and recreate the anchor and the following text sibling in index order, so that each sibling appears exactly once in the final document
- **AND** the Teleport SHALL schedule its own client render during hydration even though its anchor was recreated, so that its children mount under the target without relying on a post-hydration render pass

#### Scenario: Client mounts teleported content after hydration

- **WHEN** the hydrated application completes its client render pass
- **THEN** the teleported children SHALL be mounted under the target node
- **AND** the anchor placeholder SHALL remain at the logical position

#### Scenario: Hydration adopts the anchor without duplicating siblings

- **WHEN** the browser hydrates the SSR output of a tree containing `[paragraph, Teleport, paragraph]`
- **THEN** the comment anchor SHALL be adopted as the prerendered node at its logical position
- **AND** each sibling paragraph SHALL appear exactly once in the document (no duplicated or orphaned SSR nodes)
- **AND** the teleported children SHALL be mounted under the target node
