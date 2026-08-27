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

### Requirement: Server-side rendering shall emit teleported children at the resolved target by default

During server-side rendering and static generation, a Teleport SHALL render its children's content under the resolved target node unless explicitly opted out via `"ssr": False` in its props. Emission SHALL occur after the application tree and document scaffold have fully rendered and pending async work has settled: the teleport registers itself in a per-render-context ordered registry during the main pass, and the HTML assembly drains that registry by resolving each `to` selector against the completed virtual document tree, rendering the children under the resolved target wrapped in start/end block markers, before serializing the final HTML. Reactive initial state (including computed inline styles such as a closed dropdown's `display: none`) SHALL be evaluated normally so that emitted markup represents the true initial UI state. A Teleport whose target cannot be resolved on the server, or whose resolution is rejected, SHALL fall back to emitting only the anchor comment at its logical position (current behavior) after logging a warning. When emission succeeds, the logical position SHALL still contain exactly the anchor comment.

#### Scenario: SSR output contains teleported content under the target

- **WHEN** a page containing `Teleport({"to": "body"}, modal)` is server-rendered with default props
- **THEN** the SSR HTML SHALL contain the modal markup under `<body>`, delimited by block markers
- **AND** the SSR HTML SHALL contain the anchor placeholder at the modal's logical position
- **AND** the anchor SHALL remain the teleport's single node contribution at the logical position

#### Scenario: Opted-out teleport emits anchor only

- **WHEN** a page contains `Teleport({"to": "body", "ssr": False}, child)` and is server-rendered
- **THEN** the SSR HTML SHALL NOT contain the child's markup anywhere
- **AND** the SSR HTML SHALL contain the anchor comment at the logical position
- **AND** the child SHALL be mounted client-side during hydration as today

#### Scenario: Unresolvable target falls back to anchor-only

- **WHEN** a Teleport with default props targets a selector that matches no node in the completed virtual document tree
- **THEN** a warning SHALL be logged
- **AND** the SSR HTML SHALL contain only the anchor comment for that teleport
- **AND** the client SHALL mount the children itself during hydration without requiring any server-emitted block

#### Scenario: Async children settle before emission

- **WHEN** a teleported child performs an async setup during server rendering
- **THEN** the emitted markup SHALL reflect the setup's result
- **AND** SSG error policy for errors surfacing from that child SHALL follow the standard SSG fail-fast behavior

### Requirement: Teleport block markers shall delimit emitted blocks for deterministic hydration consumption

Each server-emitted Teleport block SHALL be delimited by a start marker comment and an end marker comment carrying a per-document ordinal and the URL-encoded `to` selector (`wc-teleport-block:<n>:<selector>` / `wc-teleport-block-end:<n>`), such that: markers survive HTML parsing as distinct comment nodes; ordinals are assigned in registry order, which equals the application's document-order traversal of Teleports and is identical in the server render pass and the client hydration pass; a hydration Teleport can locate its own block by scanning its resolved target for the first unclaimed start marker that matches its selector sequence. Markers SHALL carry no styling or layout impact.

#### Scenario: Marker format survives parsing

- **WHEN** the SSR output of a teleporting page is parsed by an HTML parser
- **THEN** each emitted block boundary SHALL appear as a distinct comment node
- **AND** no text-run merging around markers SHALL occur

#### Scenario: Ordinals match between server and client passes

- **WHEN** a page contains multiple Teleports, some sharing a target and some targeting different targets
- **THEN** the ordinal assignment order in the SSR output SHALL equal the ordinal consumption order in the client hydration pass
- **AND** each Teleport claims exactly one block, so every emitted block is consumed at most once

#### Scenario: Divergent ordinal discovery degrades safely

- **WHEN** client hydration cannot find an unclaimed marker matching a Teleport (e.g. serving stale HTML generated before this change, or ordinals diverged due to out-of-tree DOM edits)
- **THEN** the Teleport SHALL log a warning and mount its children via the normal client path
- **AND** no duplicate visible content SHALL exist beyond the leftover inert server-emitted block, which remains part of the served document's original content

### Requirement: Server emission shall reject targets produced by the application subtree and head

When a Teleport's `to` selector resolves, during server emission, to the application's own rendered subtree, to the app mount container itself, or to the `<head>` element, the resolver SHALL treat the target as rejected: log a warning naming the selector, skip emission, and emit only the anchor (same fallback as unresolvable targets). This enforces the documented rule that teleport targets must be stable nodes outside the reactive tree. Resolution MAY proceed for stable scaffolding containers outside the app subtree (typically `body`).

#### Scenario: Target inside app subtree is rejected

- **WHEN** a component renders a container `<div id="inner-root">` and a Teleport targeting `#inner-root`, and the page is server-rendered
- **THEN** a warning naming `#inner-root` SHALL be logged
- **AND** the SSR output SHALL emit only the anchor comment for that Teleport
- **AND** the client SHALL resolve `#inner-root` normally at mount time and behave per existing client rules

#### Scenario: Head target is rejected

- **WHEN** a Teleport targets `head` during server rendering
- **THEN** a warning SHALL be logged
- **AND** the SSR output SHALL contain no teleported content inside `<head>`

### Requirement: Teleport shall degrade to inline rendering with a warning when the target is missing

When the `to` selector matches no node at mount time, the Teleport SHALL log a warning and SHALL render its children inline at the logical position (replacing the anchor with the children's nodes), so that functionality survives misconfiguration. The element SHALL NOT raise an exception into the render tree because of a missing target.

#### Scenario: Unknown selector falls back inline

- **WHEN** a component renders `Teleport({"to": "#nonexistent-root"}, child)` and no element matches the selector
- **THEN** a warning SHALL be logged
- **AND** the child SHALL render at the Teleport's logical position in the element tree

### Requirement: Multiple Teleports targeting the same node shall append in mount order

When multiple Teleport elements resolve to the same target node, each SHALL append its children to the target when it mounts, and no reordering pass SHALL run afterwards. The observable order of teleported content under a shared target SHALL be the mount order of the Teleport elements, both for client-mounted blocks and for server-emitted blocks consumed during hydration. Shared-target bookkeeping SHALL be anchored at each block's start marker (client-side, at the claimed block's insertion slot) instead of assuming teleported blocks are the trailing nodes of the target; nodes appended to the target by anything other than Teleports (hydration payload scripts, host-page code, external widgets) SHALL NOT skew sibling-block positioning. Shared-target guarantees SHALL apply only to Teleports that are not nested within one another; a Teleport nested inside another Teleport SHALL NOT target the same node as its ancestor, because the block model cannot represent such nesting. Shared-target bookkeeping is scoped per app: the registry tracks Teleports of a single `RenderContext`, so mount-order guarantees apply between Teleports of the same app instance.

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

#### Scenario: External appends do not skew shared-target blocks

- **WHEN** a non-Teleport script or widget appends nodes to the shared target after Teleport A and Teleport B have mounted
- **THEN** subsequent A/B block growth SHALL remain anchored at the respective block positions
- **AND** external nodes SHALL NOT be absorbed into either block

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
