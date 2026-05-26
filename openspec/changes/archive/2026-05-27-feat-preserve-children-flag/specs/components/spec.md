# Components Delta

## ADDED Requirements

### Requirement: Component shall inherit :preserve_children from root element

When a `Component` is created, the `__init_component()` method SHALL copy the `_preserve_children` boolean flag from the root `Element` node (the template root returned by the component setup function), following the same pattern as `_tag_name` and `_ref`. The flag SHALL control whether the component's `_render()` cleanup loop is skipped, just as it does for `Element` instances.

#### Scenario: Component preserves children when root element sets the flag
- **WHEN** a component's setup function returns `html.DIV({":preserve_children": True}, ...)`
- **THEN** the `Component` instance SHALL have `_preserve_children = True`
- **AND** the component's `_render()` SHALL skip the excess-child-node cleanup loop

#### Scenario: Component does not preserve children when root element does not set the flag
- **WHEN** a component's setup function returns `html.DIV({}, ...)` without `:preserve_children`
- **THEN** the `Component` instance SHALL have `_preserve_children = False`
- **AND** the component's `_render()` SHALL execute the cleanup loop normally
