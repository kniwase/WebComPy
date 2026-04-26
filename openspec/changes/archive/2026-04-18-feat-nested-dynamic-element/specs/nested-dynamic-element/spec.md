## ADDED Requirements

### Requirement: DynamicElements shall support nesting within each other
Developers SHALL be able to nest `repeat` and `switch` elements within each other at arbitrary depth. A `repeat` inside a `switch` branch, a `switch` inside a `repeat` template, and deeper nesting SHALL all be supported without raising exceptions.

#### Scenario: Repeat inside switch branches
- **WHEN** a developer writes `switch(cases=[(is_list_view, lambda: repeat(items, item_template)), (is_grid_view, lambda: repeat(items, grid_template))])`
- **THEN** the selected branch SHALL render the `repeat` element correctly
- **WHEN** the condition changes from `is_list_view` to `is_grid_view`
- **THEN** the list view `repeat` SHALL be fully removed (including its reactive callbacks) and the grid view `repeat` SHALL be rendered

#### Scenario: Switch inside repeat template
- **WHEN** a developer writes `repeat(tabs, lambda tab, key: switch(cases=[(tab.active, lambda: active_panel)]))`
- **THEN** each tab item SHALL render a `switch` element
- **WHEN** a tab's `active` state changes
- **THEN** the switch inside that tab's rendered child SHALL update correctly without affecting other tabs

#### Scenario: Arbitrary nesting depth
- **WHEN** a developer nests `repeat` inside `switch` inside another `repeat`
- **THEN** the innermost `repeat` SHALL render correctly and respond to reactive changes

### Requirement: Nested DynamicElements shall resolve DOM parent via ancestor traversal
A `DynamicElement` that is a child of another `DynamicElement` SHALL traverse up the parent chain to find the nearest non-DynamicElement ancestor for DOM operations. The `DynamicElement._get_node()` method SHALL return the DOM node of the nearest non-DynamicElement ancestor, rather than raising an exception.

#### Scenario: Getting the DOM parent node for a nested DynamicElement
- **WHEN** a `RepeatElement` is nested inside a `SwitchElement`
- **AND** the `SwitchElement` is a child of a `div` element
- **THEN** the `RepeatElement._parent._get_node()` SHALL return the `div` element's DOM node
- **AND** the `RepeatElement` SHALL correctly insert and remove child DOM nodes within that `div`

### Requirement: Nested DynamicElement children shall be cleaned up on parent refresh
When a parent DynamicElement refreshes and removes children that contain nested DynamicElements, all reactive callbacks registered by the nested DynamicElements SHALL be cleaned up via the existing `_remove_element` cascade.

#### Scenario: Switch branch replacement cleans up nested repeat callbacks
- **WHEN** a `switch` branch contains a `repeat` with keyed reconciliation
- **AND** the `switch` condition changes, causing the branch to be replaced
- **THEN** the `repeat`'s reactive callbacks SHALL be removed from `ReactiveStore`
- **AND** the `repeat`'s DOM nodes SHALL be removed from the DOM

### Requirement: SSR rendering shall support nested DynamicElements
When rendering to HTML (server-side), nested `repeat` and `switch` elements SHALL produce correct HTML output by recursively rendering each DynamicElement's children.

#### Scenario: SSR output for repeat inside switch
- **WHEN** a `switch` element with a `repeat` in its active branch is rendered to HTML
- **THEN** the HTML output SHALL contain the repeated items inside the switch branch