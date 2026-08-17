# Elements — Hydration "Adopt & Render" Deltas

## MODIFIED Requirements

### Requirement: Pre-rendered DOM nodes shall be reused during hydration via adopt-and-hydrate

When full hydration is enabled, elements SHALL use `_hydrate_node()` instead of `_init_node()` for prerendered nodes. `_hydrate_node()` SHALL check for an existing prerendered node and delegate to `_adopt_node()` if found, or fall back to `_init_node()` if not. This enables efficient hydration of server-rendered content. This requirement applies to all node types including `#text` nodes, and to content under dynamic containers (RouterView, Suspense, Transition, ErrorBoundary) whose children are created during the hydration pass. During hydration, attribute values and text content SHALL only be written if they differ from the prerendered values to avoid redundant DOM operations. Adoption SHALL NOT end an element's hydration: adopted elements SHALL still complete exactly one hydration render pass so reactive registrations are established (see "Adopted children of dynamic containers shall complete a hydration render").

#### Scenario: Hydrating an existing prerendered element
- **WHEN** `_hydrate_node()` is called and a prerendered node with matching tag exists
- **THEN** `_adopt_node(node)` SHALL be called to adopt the existing DOM node
- **AND** the framework SHALL NOT call `_mount_node()` since the node is already in the DOM

#### Scenario: No prerendered node available during hydration
- **WHEN** `_hydrate_node()` is called and no prerendered node exists
- **THEN** the element SHALL fall back to `_init_node()` for normal DOM creation and mounting

#### Scenario: Hydration fallback creates the node exactly once
- **WHEN** `_hydrate_node()` falls back because no matching prerendered node exists (or the existing node's tag mismatches)
- **THEN** the fallback SHALL create exactly one node for the element
- **AND** the created node SHALL be recorded as the element's node so a later `_get_node()`/render reuses it (no orphan node)
- **AND** node initialization (`_init_new_node`: attributes, event handlers, ref binding) SHALL run once on the reused node

#### Scenario: Hydrating a server-rendered page
- **WHEN** the browser finds an existing DOM node with `__webcompy_prerendered_node__ = True` and a matching tag name
- **THEN** the element SHALL adopt that node rather than creating a new one
- **AND** attributes SHALL be updated to match the element's current state
- **AND** attributes whose values already match SHALL NOT be rewritten to the DOM

#### Scenario: Hydrating an element with identical attributes
- **WHEN** a prerendered element node's attribute values match the Element's current attribute state
- **THEN** the framework SHALL NOT call `setAttribute` for matching attributes
- **AND** attributes with value resolved to `None` in the component state SHALL still be removed via `removeAttribute` if present on the node

#### Scenario: Hydrating an element with differing attributes
- **WHEN** a prerendered element node's attribute differs from the Element's current state
- **THEN** the framework SHALL call `setAttribute` only for the differing attributes
- **AND** matching attributes SHALL remain untouched

#### Scenario: Hydrating a server-rendered text node
- **WHEN** the browser finds an existing `#text` node with `__webcompy_prerendered_node__ = True`
- **THEN** the TextElement SHALL adopt that node rather than removing it and creating a new one
- **AND** if the node's `textContent` matches the element's current value, no DOM write SHALL occur
- **AND** if the node's `textContent` differs, it SHALL be updated to the element's current value
- **AND** no visible flash SHALL occur during hydration

#### Scenario: Hydrating a reactive text node
- **WHEN** a TextElement wraps a Signal value
- **AND** the browser finds a pre-rendered `#text` node for it
- **THEN** the TextElement SHALL adopt the existing node and update its content to the Signal's current value
- **AND** subsequent Signal changes SHALL update the adopted node via the existing `on_after_updating` callback

#### Scenario: Prerendered route content under a dynamic container is reused
- **WHEN** the browser hydrates a page whose routed content (RouterView subtree) was prerendered by SSR/SSG
- **AND** the client-side component tree matches the prerendered structure
- **THEN** the prerendered DOM nodes of the routed content SHALL be adopted
- **AND** the number of DOM nodes removed during hydration SHALL be zero for the matching content

#### Scenario: Hydrating a raw-HTML wrapper with matching content
- **WHEN** the browser finds an existing prerendered node for a `RawHTMLElement` (wrapper tag matches)
- **AND** the node's current content (`innerHTML`, or `textContent` when `innerHTML` is unavailable) equals the element's rendered value
- **THEN** the wrapper node SHALL be adopted
- **AND** the framework SHALL NOT rewrite the content
- **AND** the wrapper's existing child nodes SHALL remain in the document (neither removed nor recreated)
- **AND** no mismatch record SHALL be created

## ADDED Requirements

### Requirement: Adopted children of dynamic containers shall complete a hydration render

Every child of a hydrated dynamic container (`DynamicElement` subclasses: RouterView, ErrorBoundary, Switch, Repeat, Suspense, Transition, ClientOnly) SHALL complete exactly one hydration render, even when its DOM node was adopted during `_hydrate_node()` (which marks it mounted). During hydration, the parent SHALL schedule the child's render through the `ASYNC_SCHEDULER_PORT_KEY`, and the hydration render SHALL NOT skip children because they are mounted. The render's mount operations SHALL be no-ops on adopted nodes, and all DOM writes SHALL remain diff-only, so the hydration render is visually neutral when server and client content match. Outside the initial hydration, the existing render-skip semantics for mounted children SHALL be preserved.

#### Scenario: Hydration render is visually neutral for matching content
- **WHEN** a dynamic container's adopted children complete their hydration render after SSR with matching content
- **THEN** no DOM node REMOVAL or insertion SHALL occur as a result of the hydration render
- **AND** the element's reactive registrations (signal callbacks, key maps, rendered-branch state) SHALL be established

#### Scenario: Reactive behavior works after adopting a hydrated switch
- **WHEN** a `Switch` branch was adopted from prerendered DOM inside a hydrated dynamic container
- **AND** a user interaction flips the switch condition after hydration completes
- **THEN** the DOM SHALL update to the new branch
- **AND** the adopted branch's DOM nodes SHALL be reused when the branch structure matches (patching), preserving node identity

#### Scenario: Adopted switch branch containing a dynamic element stays wired
- **WHEN** the adopted branch of a hydrated `Switch` contains a dynamic element (e.g., a `Repeat` over a transferred list)
- **THEN** the branch subtree SHALL complete exactly one hydration render (the scheduled hydration-render wrappers SHALL NOT be cancelled by the unchanged-branch first refresh)
- **AND** the nested dynamic element's reactive wiring SHALL be established (e.g., list mutations update the DOM after hydration)

#### Scenario: Refresh outside hydration keeps mounted-skip behavior
- **WHEN** a dynamic container refreshes after hydration (signal-triggered refresh)
- **THEN** mounted children SHALL NOT be re-rendered merely because they are mounted (existing refresh semantics SHALL be preserved)

### Requirement: Repeat shall preserve adopted SSR children on the first hydration refresh

When a `Repeat` element's children were adopted from prerendered DOM during hydration, the first refresh SHALL NOT remove and re-create them (the pre-change full-rebuild path). Instead, the first refresh SHALL treat adopted children as already-materialized items: it SHALL reposition them to match the current sequence, SHALL rebuild the key map (`_populate_key_map()` equivalent), and SHALL render only children that have no adopted node. Subsequent refreshes SHALL follow the existing keyed-reconciliation semantics.

#### Scenario: Repeat over transferred list value preserves SSR nodes after hydration
- **WHEN** a `Repeat` renders a `ReactiveList` whose value was transferred from SSR
- **AND** the repeat's children were adopted from the prerendered DOM during hydration
- **AND** the hydration render triggers the repeat's first refresh
- **THEN** the adopted DOM nodes SHALL remain in the document (no removal)
- **AND** the key map SHALL be populated from the current sequence

#### Scenario: Repeat list mutation after hydration reconciles correctly
- **WHEN** a `Repeat` with a transferred list value receives a mutation after hydration (e.g., `pop`, `append`)
- **THEN** the DOM SHALL reconcile to the new sequence
- **AND** key-based reuse SHALL apply for keyed repeats as before

#### Scenario: Repeat with partial SSR coverage preserves matched nodes
- **WHEN** a `Repeat`'s SSR DOM covers only a subset of the sequence (fewer nodes than items, or a per-item tag mismatch at one position)
- **AND** the first hydration refresh runs
- **THEN** the adopted (matched) DOM nodes SHALL remain in the document
- **AND** the missing positions SHALL be created and rendered (via the scheduled plain-render tasks), matching the current sequence

### Requirement: Switch shall inherit the rendered branch from SSR content during hydration

When a `Switch` element's active branch was prerendered by SSR, hydration SHALL initialize the switch's rendered-branch state so that the first refresh with an unchanged condition SHALL NOT regenerate the branch. The adopted branch's DOM nodes SHALL be reused. If the condition already changed relative to SSR (e.g., restored state differs), the switch SHALL patch to the new branch via the existing `_patch_children` flow.

#### Scenario: First refresh with unchanged condition does not regenerate
- **WHEN** a hydrated `Switch` receives a refresh triggered by an unrelated signal (or its own render runs)
- **AND** the active branch condition matches the SSR-rendered branch
- **THEN** the branch SHALL NOT be removed and re-generated
- **AND** the adopted DOM nodes SHALL remain in the document

#### Scenario: Condition changed after hydration patches to the new branch
- **WHEN** the switch condition changes after hydration so a different branch becomes active
- **THEN** the DOM SHALL switch to the new branch via patching (existing behavior)
- **AND** matching single-node branches SHALL reuse their adopted nodes

### Requirement: Hydration mismatches shall be recorded with recovery or repair

During hydration, five classes of divergence between the prerendered DOM and the client element tree SHALL be detected and recorded: text mismatch and attribute mismatch (recoverable — the mismatch SHALL be patched by writing the expected value into the adopted node), raw-HTML mismatch (recoverable — when an adopted raw-HTML wrapper's existing content differs from the element's rendered value, the mismatch SHALL be patched by re-applying the rendered value into the adopted node), and tag mismatch and node-count mismatch (structural — the mismatch SHALL be repaired by removing the stale node and creating the expected one). Each record SHALL capture the mismatch class, the expected value, the actual value, and the owning component ID when known. Records SHALL be collected for aggregation and reporting by the app layer (see the async-rendering capability). Records SHALL NOT be emitted as individual console messages.

#### Scenario: Recoverable text mismatch is patched and recorded
- **WHEN** hydration adopts a prerendered `#text` node whose content differs from the client element's expected text
- **THEN** the node content SHALL be updated to the expected text
- **AND** a text-mismatch record SHALL be created
- **AND** no DOM node SHALL be removed

#### Scenario: Structural tag mismatch is repaired and recorded
- **WHEN** hydration finds a prerendered node whose tag differs from the client element's tag at the same position
- **THEN** the stale node SHALL be removed and the expected node SHALL be created (repair)
- **AND** a tag-mismatch record SHALL be created

#### Scenario: Recoverable raw-HTML mismatch is patched and recorded
- **WHEN** hydration adopts a prerendered raw-HTML wrapper whose existing content differs from the element's rendered value
- **THEN** the wrapper's content SHALL be updated to the rendered value
- **AND** a raw_html-mismatch record SHALL be created
- **AND** the wrapper node itself SHALL be preserved (not removed or recreated)

#### Scenario: Matching content produces no records
- **WHEN** hydration adopts prerendered content that fully matches the client element tree
- **THEN** no mismatch records SHALL be created