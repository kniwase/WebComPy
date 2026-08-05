# Delta: router

## ADDED Requirements

### Requirement: RouterView shall wrap each chain level in an implicit error boundary

Each route level component rendered by a `RouterView` SHALL be contained in an implicit error boundary (see the `error-handling` capability) whose fallback renders nothing. A failure in one level SHALL NOT destroy or unmount ancestor levels. The implicit boundary SHALL reset on navigation when in error state, so re-navigating (including re-selecting the current route) retries the level. The implicit boundary SHALL NOT alter the level-reuse rule: identity comparison, instance preservation, and remount semantics are unchanged; error state exists only on the boundary wrapping a preserved instance and is cleared by the navigation reset.

#### Scenario: Level failure isolated
- **WHEN** the component at chain level N raises during render
- **THEN** levels 0..N-1 (layouts) SHALL remain mounted with their state intact
- **AND** level N's view SHALL render empty

#### Scenario: Navigation resets errored level
- **WHEN** level N is in implicit-boundary error state and a navigation occurs that preserves level N's identity
- **THEN** the implicit boundary SHALL reset and level N SHALL attempt to render again

#### Scenario: Remount drops error state
- **WHEN** a navigation changes level N's identity (param change)
- **THEN** the new level-N instance SHALL render with no residual error state
