# Application Lifecycle — Delta: feat-hydration-full

## Changes

### Added: hydrate parameter on WebComPyApp

`WebComPyApp.__init__()` SHALL accept a `hydrate: bool = True` parameter. When `hydrate=True` (default), the application SHALL use `_hydrate_node()` for prerendered nodes during initial render, skipping DOM creation. When `hydrate=False`, the application SHALL recreate all DOM nodes from scratch.

The `AppDocumentRoot._render()` method SHALL use `_hydrate_node()` for each child when `_hydrate=True` and children have not yet been rendered. Unmatched children (no prerendered node) SHALL fall back to `_render()` for normal creation and mounting.