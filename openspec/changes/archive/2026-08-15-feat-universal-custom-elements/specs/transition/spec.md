# Delta Spec: transition

## ADDED Requirements

### Requirement: Transition shall warn when the child's computed display prevents transitions from running

When the enter/leave duration resolves from computed styles (no explicit `duration` prop), the framework SHALL additionally read the child node's computed `display`. If the computed display is `contents` or `none`, CSS transitions and animations cannot run on the node and no `transitionend`/`animationend` events will fire; the framework SHALL log a warning naming the transition and advising a box-generating display (for a component child, declaring `display="block"` or another box value via the `define_component` display argument). The sequence SHALL still finalize via the existing timeout fallback, so behavior remains correct but non-animated; the warning exists to convert this silent visual regression into a diagnosable message.

#### Scenario: Warning for a layout-transparent component child

- **WHEN** a `Transition` wraps a component whose wrapper computes to `display: contents` (the framework default) and the enter or leave sequence resolves its duration from computed styles
- **THEN** a warning SHALL be logged naming the transition and advising a box-generating display value
- **AND** the sequence SHALL finalize via the timeout fallback without hanging

#### Scenario: No warning for box-generating children

- **WHEN** a `Transition` wraps a child whose computed `display` generates a box (for example a component declared with `display="block"`)
- **THEN** no display warning SHALL be logged
- **AND** the enter/leave class sequence SHALL animate normally
