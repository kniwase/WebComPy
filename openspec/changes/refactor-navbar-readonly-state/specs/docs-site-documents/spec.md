## ADDED Requirements

### Requirement: The Navbar dropdown state shall be read-only snapshot state driven by state-event composables

The docs_app Navbar SHALL manage measured dropdown positions as a single read-only snapshot signal created with `use_readonly_signal({})`, holding a dict of dropdown index to `(top, right)` position tuples, with the composable's update function as the sole write path. Scroll (document) and resize (window) state events SHALL be bridged via `use_document_event` / `use_window_event`, whose `transform` re-measures the open dropdowns, writes the fresh snapshot through the update function, and returns it; an unchanged snapshot SHALL NOT notify consumers. Toggling a dropdown SHALL measure immediately after opening and write through the same update function. The outside-click listener SHALL remain a manually registered document listener with `on_before_destroy` cleanup, since every outside click must close the menus (occurrence semantics, not state-event semantics).

#### Scenario: Dropdown follows its toggle on scroll or resize

- **WHEN** a dropdown is open and a scroll or resize event fires
- **THEN** the dropdown position re-measures from its toggle element
- **AND** the snapshot updates only when a measured position actually changed

#### Scenario: Toggle measures immediately

- **WHEN** the user clicks a dropdown toggle
- **THEN** the dropdown opens at the toggle's current position without waiting for a scroll or resize event

#### Scenario: Outside click closes all dropdowns on every occurrence

- **WHEN** the user clicks anywhere outside the dropdowns
- **THEN** every open dropdown closes, and the closing is driven by the manual listener rather than by a state-event composable
