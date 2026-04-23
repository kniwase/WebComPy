# Application Lifecycle — Delta: feat-hydration-full

## ADDED Requirements

### Requirement: WebComPyApp shall accept a hydrate parameter for full hydration control
`WebComPyApp.__init__()` SHALL accept a `hydrate: bool = True` parameter. When `hydrate=True` (default), the application SHALL use `_hydrate_node()` for prerendered nodes during initial render, skipping DOM creation. When `hydrate=False`, the application SHALL recreate all DOM nodes from scratch.

#### Scenario: Running an app with hydration enabled
- **WHEN** a developer creates `WebComPyApp(..., hydrate=True)` or uses the default
- **THEN** the application SHALL use `_hydrate_node()` for prerendered nodes during initial render
- **AND** only unmatched nodes SHALL be created via `_init_node()`

#### Scenario: Running an app with hydration disabled
- **WHEN** a developer creates `WebComPyApp(..., hydrate=False)`
- **THEN** the application SHALL recreate all DOM nodes from scratch
- **AND** no prerendered DOM node reuse SHALL occur

### Requirement: AppDocumentRoot._render() shall use _hydrate_node() when hydration is enabled
The `AppDocumentRoot._render()` method SHALL use `_hydrate_node()` for each child when `_hydrate=True` and children have not yet been rendered. Unmatched children (no prerendered node) SHALL fall back to `_render()` for normal creation and mounting.

#### Scenario: Rendering children with hydration and matching prerendered nodes
- **WHEN** `AppDocumentRoot._render()` is called with `_hydrate=True` and prerendered nodes exist
- **THEN** each child SHALL use `_hydrate_node()` to adopt or create nodes
- **AND** children with matching prerendered nodes SHALL be adopted

#### Scenario: Rendering children with hydration but no prerendered nodes
- **WHEN** `AppDocumentRoot._render()` is called with `_hydrate=True` but no prerendered nodes exist for some children
- **THEN** unmatched children SHALL fall back to normal `_render()` for DOM creation and mounting