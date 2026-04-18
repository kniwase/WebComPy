## MODIFIED Requirements

### Requirement: Nested DynamicElement children shall be cleaned up on parent refresh
When a parent DynamicElement refreshes and removes children that contain nested DynamicElements, all signal subscriptions registered by the nested DynamicElements SHALL be cleaned up via `consumer_destroy()`.

#### Scenario: Switch branch replacement cleans up nested repeat callbacks
- **WHEN** a `switch` branch contains a `repeat` with keyed reconciliation
- **AND** the `switch` condition changes, causing the branch to be replaced
- **THEN** the `repeat`'s signal subscriptions SHALL be cleaned up via `consumer_destroy()`
- **AND** the `repeat`'s DOM nodes SHALL be removed from the DOM