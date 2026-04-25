## MODIFIED Requirements

### Requirement: Conditional rendering shall display one branch at a time
The `switch` construct SHALL evaluate a series of conditions and render the template of the first matching condition. When conditions change, the previous branch SHALL be removed and the new branch SHALL be rendered. When the `SwitchElement` is refreshed due to a reactive change (such as a route change), any `on_after_rendering` lifecycle hooks of newly created components SHALL be deferred until after the reactive propagation and DOM updates have completed. The branch template MAY return a `DynamicElement` (such as a `repeat`), and the `SwitchElement` SHALL handle it as a transparent child with no DOM node of its own.

#### Scenario: Switching between display modes
- **WHEN** a developer defines `switch(cases=[(is_admin, lambda: AdminPanel()), (is_user, lambda: UserPanel())], default=lambda: GuestPanel())`
- **AND** `is_admin` becomes `True`
- **THEN** `AdminPanel` SHALL be rendered
- **WHEN** `is_admin` becomes `False` and `is_user` becomes `True`
- **THEN** `AdminPanel` SHALL be removed and `UserPanel` SHALL be rendered

#### Scenario: Switching routes triggers async operations in new component
- **WHEN** a `SwitchElement` is used for routing (as in `RouterView`)
- **AND** the route changes from one page to another
- **AND** the new page component has an `on_after_rendering` hook that starts async operations
- **THEN** the new component SHALL be fully mounted in the DOM before `on_after_rendering` runs
- **AND** async operations SHALL execute in a clean event loop context (not nested within the reactive callback chain)

#### Scenario: Switch branch containing a repeat element
- **WHEN** a developer defines `switch(cases=[(is_list_view, lambda: repeat(items, item_template))])`
- **AND** `is_list_view` becomes `True`
- **THEN** the `repeat` SHALL render its items inside the switch's parent DOM node
- **WHEN** `is_list_view` becomes `False`
- **THEN** the `repeat` and all its rendered items SHALL be removed