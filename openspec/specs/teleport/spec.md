# Teleport

## Purpose

WebComPy provides a `Teleport` element for relocating a subtree of DOM nodes to a different container in the document (for example `body`), which enables modals, dropdowns, and menus that must escape ancestor CSS contexts (overflow clipping, stacking contexts). Teleport renders a single static anchor placeholder at its logical position in the element tree, mounts the children under the resolved target node, preserves the full node identity of the relocated subtree, and cooperates with server-side rendering and hydration so the anchor slot survives HTML parsing.

## Requirements

### Requirement: Teleport shall render children under the resolved target node

`Teleport({"to": "<selector>"}, *children)` SHALL be a public element exported from `webcompy.elements`. At mount time it SHALL resolve the target node via the `DOMPort` `query_selector` with the `to` selector, and its children SHALL be mounted under the target node instead of under the Teleport's logical parent. The `to` value SHALL be a static string; reactive targets are not supported. Teleported children SHALL retain their component attribution (scoped-style attributes), reactive bindings, and event handlers after relocation, because relocation moves the DOM nodes themselves.

#### Scenario: Modal content renders under body

- **WHEN** a component renders `Teleport({"to": "body"}, modal_element)` inside a page component
- **THEN** the modal's DOM node SHALL be a child of `<body>` in the rendered document
- **AND** the modal SHALL NOT be a DOM descendant of the page component's root node

#### Scenario: Reactive updates apply at the target

- **WHEN** a teleported child contains reactive content (e.g. a text interpolation bound to a Signal) and the Signal changes
- **THEN** the update SHALL be applied to the DOM node under the target container
- **AND** no duplicate node SHALL appear at the logical position

#### Scenario: Scoped styles and event handlers survive relocation

- **WHEN** a teleported element has scoped styles and an event handler
- **THEN** its scoped-style attribute SHALL remain on the relocated node so document-global scoped style rules still match
- **AND** the event handler SHALL fire when the relocated node is interacted with

### Requirement: Teleport shall occupy exactly one static anchor node at its logical position

The Teleport element SHALL contribute exactly one DOM node — an empty placeholder — at its logical position in the element tree, and SHALL report a node count of one regardless of how many nodes its teleported subtree contains or how that count changes over time. Sibling node-index accounting SHALL therefore remain stable across any change inside the teleported subtree (conditional children, repeated children, async children).

#### Scenario: Sibling indices are stable while teleported content changes

- **WHEN** an element tree contains a text node, a Teleport, and another text node in sequence, and the teleported subtree gains or loses nodes
- **THEN** the trailing text node SHALL remain at its correct position among the logical parent's child nodes
- **AND** no re-indexing error or node drift SHALL occur at the logical position

#### Scenario: Anchor is a placeholder, not rendered content

- **WHEN** a Teleport with children is mounted
- **THEN** the node at the logical position SHALL be an empty placeholder (no element content)
- **AND** the teleported children SHALL exist only under the target container

### Requirement: Server-side rendering shall emit only the anchor

During server-side rendering and static generation, a Teleport SHALL render only its anchor placeholder at the logical position and SHALL NOT render its children's content anywhere in the document. The browser SHALL mount the children under the target during the client render pass after hydration. Teleported content is therefore absent from SSR HTML by design. The anchor SHALL be serialized as a zero-width-space text node so that, when it is adjacent to element siblings, its node slot survives HTML parsing and positional hydration adoption of the anchor and of the siblings following the Teleport stays aligned. When the anchor is adjacent to bare text nodes, the HTML parser merges the text runs into a single node; hydration SHALL then recover by adopting the merged node as the preceding text sibling and recreating the anchor and following siblings in index order, so that each sibling appears exactly once in the final document. During hydration a Teleport SHALL schedule its own client render whenever its children are not yet rendered, including when the anchor had to be recreated instead of adopted; the teleport's mounting SHALL NOT depend on an app-level post-hydration render pass.

#### Scenario: SSR output contains no teleported content

- **WHEN** a page containing `Teleport({"to": "body"}, modal)` is server-rendered
- **THEN** the SSR HTML SHALL contain the anchor placeholder at the logical position
- **AND** the SSR HTML SHALL NOT contain the modal markup under `<body>` or anywhere else

#### Scenario: SSR anchor occupies a parseable slot

- **WHEN** a tree containing `[element, Teleport, element]` is server-rendered
- **THEN** the SSR HTML SHALL contain the anchor representation between the two elements at the logical position
- **AND** a browser parsing that HTML SHALL produce a distinct text node for the anchor slot

#### Scenario: Text-adjacent SSR anchors merge on parse and recover on hydration

- **WHEN** a tree containing `[text node, Teleport, text node]` is server-rendered
- **THEN** the SSR HTML SHALL contain the anchor representation between the two text nodes at the logical position
- **AND** a browser parsing that HTML SHALL merge the adjacent text runs into a single text node, leaving no distinct anchor slot
- **AND** hydration SHALL adopt the merged node as the preceding text sibling and recreate the anchor and the following text sibling in index order, so that each sibling appears exactly once in the final document
- **AND** the Teleport SHALL schedule its own client render during hydration even though its anchor was recreated, so that its children mount under the target without relying on a post-hydration render pass

#### Scenario: Client mounts teleported content after hydration

- **WHEN** the hydrated application completes its client render pass
- **THEN** the teleported children SHALL be mounted under the target node
- **AND** the anchor placeholder SHALL remain at the logical position

#### Scenario: Hydration adopts the anchor without duplicating siblings

- **WHEN** the browser hydrates the SSR output of a tree containing `[paragraph, Teleport, paragraph]`
- **THEN** the anchor SHALL be adopted as the prerendered node at its logical position
- **AND** each sibling paragraph SHALL appear exactly once in the document (no duplicated or orphaned SSR nodes)
- **AND** the teleported children SHALL be mounted under the target node

### Requirement: Teleport shall degrade to inline rendering with a warning when the target is missing

When the `to` selector matches no node at mount time, the Teleport SHALL log a warning and SHALL render its children inline at the logical position (replacing the anchor with the children's nodes), so that functionality survives misconfiguration. The element SHALL NOT raise an exception into the render tree because of a missing target.

#### Scenario: Unknown selector falls back inline

- **WHEN** a component renders `Teleport({"to": "#nonexistent-root"}, child)` and no element matches the selector
- **THEN** a warning SHALL be logged
- **AND** the child SHALL render at the Teleport's logical position in the element tree

### Requirement: Multiple Teleports targeting the same node shall append in mount order

When multiple Teleport elements resolve to the same target node, each SHALL append its children to the target when it mounts, and no reordering pass SHALL run afterwards. The observable order of teleported content under a shared target SHALL be the mount order of the Teleport elements. Shared-target bookkeeping is scoped per app: the registry tracks Teleports of a single `RenderContext`, so mount-order guarantees apply between Teleports of the same app instance, and the spec's shared-target requirements assume targets are stable nodes outside the app's reactive tree. The shared-target block model derives the first block's base index from the target's current child count minus the mounted teleported counts, which assumes the teleported blocks are the last nodes in the target container; any non-teleported node appended to the target after the teleports mount (external scripts, host-page code, a second app instance sharing the target) falls outside the shared-target guarantee and MAY skew subsequent block re-indexing. Shared-target guarantees SHALL apply only to Teleports that are not nested within one another; a Teleport nested inside another Teleport SHALL NOT target the same node as its ancestor, because the shared-target block model cannot represent such nesting.

#### Scenario: Two teleports to body

- **WHEN** Teleport A mounts with content `A` targeting `body`, and afterwards Teleport B mounts with content `B` targeting `body`
- **THEN** under `<body>`, content `A` SHALL precede content `B` among the teleported nodes

#### Scenario: Same-target nesting is not supported

- **WHEN** a Teleport nested inside another Teleport targets the same node as its ancestor
- **THEN** the ordering guarantees of this requirement SHALL NOT apply
- **AND** the nesting SHALL be restructured into sibling Teleports

#### Scenario: Shared-target order is maintained while teleported subtrees change

- **WHEN** Teleport A and Teleport B target the same node and mount in that order, and A's teleported subtree later grows or shrinks (e.g. a repeated child gains or loses items) before B's teleported subtree changes again
- **THEN** each teleported node SHALL remain within its own teleport's block under the shared target
- **AND** B's teleported content SHALL continue to follow A's teleported content in the target node, with no interleaving

#### Scenario: Shared-target order is maintained while a teleported subtree is pending

- **WHEN** Teleport A and Teleport B target the same node and mount in that order, A's teleported subtree contains an async-setup child whose rendering has not completed, and B's teleported subtree changes (e.g. a repeated child gains or loses items) during that window
- **THEN** B's teleported content SHALL remain positioned after A's block under the shared target, with no interleaving
- **AND** when A's pending child completes, its nodes SHALL be placed within A's own block, preceding B's content
- **AND** subsequent changes to B's subtree SHALL keep both teleports' blocks contiguous

### Requirement: Removing a Teleport shall remove both teleported nodes and the anchor

When a Teleport element is removed from the element tree (conditional removal, parent removal, reconciliation replacement), the framework SHALL remove the teleported child nodes from the target container and the anchor placeholder from the logical parent, and SHALL destroy the element's callback consumers through the standard removal path. No orphaned nodes SHALL remain under the target or at the logical position.

#### Scenario: Conditional removal cleans the target

- **WHEN** a Teleport rendered under a condition is removed because the condition becomes false
- **THEN** the teleported nodes SHALL be removed from the target container
- **AND** the anchor placeholder SHALL be removed from the logical parent
- **AND** no node owned by the Teleport SHALL remain in the document

### Requirement: Teleport targets shall be stable nodes outside the app's reactive tree

Documentation and the spec SHALL require `to` selectors to address stable nodes that are not produced or removed by the application's own rendering — typically `body` or a static element present in the host page. If a target node is removed by external means, the teleported content is detached with it; the framework SHALL NOT re-resolve or re-mount the target automatically.

#### Scenario: Documented constraint for target selection

- **WHEN** a developer chooses a teleport target
- **THEN** the documentation SHALL direct them to stable nodes outside the app's reactive tree (e.g. `body`)
- **AND** the framework SHALL NOT provide automatic recovery if the target node is removed externally
