# Suspense — Hydration "Adopt & Render" Deltas

## MODIFIED Requirements

### Requirement: Suspense hydration shall use has_resolved_data

`SuspenseElement._hydrate_node()` SHALL call `has_resolved_data(component_id)` (from the `hydration-data-transfer` capability) for each child component to decide whether to render the children immediately or keep the fallback. If `True` for all children, the children SHALL be hydrated directly: their prerendered DOM nodes SHALL be adopted, and they SHALL complete exactly one hydration render (reactive setup) per the adopt-and-render contract — adoption alone SHALL NOT end their hydration. If `False` (or the payload is missing) for any child, the fallback SHALL be hydrated and async resolution SHALL be scheduled.

#### Scenario: Suspense hydrates children directly when data is in payload
- **WHEN** `SuspenseElement._hydrate_node()` runs in the browser and `has_resolved_data(component_id)` returns `True` for all children
- **THEN** the resolved children SHALL be adopted from the prerendered DOM and rendered directly
- **AND** their hydration render SHALL run (reactive setup completes)
- **AND** the fallback SHALL NOT appear in the DOM after hydration

#### Scenario: Resolved suspense children keep their SSR nodes
- **WHEN** all Suspense children have resolved data in the transfer payload
- **AND** the prerendered DOM contains the resolved content
- **THEN** the prerendered DOM nodes SHALL remain in the document through hydration (no removal and rebuild)

#### Scenario: Suspense hydrates fallback when data is not in payload
- **WHEN** `SuspenseElement._hydrate_node()` runs in the browser and `has_resolved_data(component_id)` returns `False` for any child
- **THEN** the fallback SHALL be hydrated
- **AND** async resolution SHALL be scheduled to swap fallback for resolved children when the data arrives