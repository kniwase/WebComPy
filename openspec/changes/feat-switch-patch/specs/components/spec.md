# Components — Delta: feat-switch-patch

## ADDED Requirements

### Requirement: Component._detach_from_node() shall dispose DI scope and EffectScope when node is adopted
When a `Component` is the root of an old branch subtree being patched, `Component._detach_from_node()` SHALL call `super()._detach_from_node()` followed by `on_before_destroy` to dispose the `EffectScope` and DI child scope. This ensures proper lifecycle cleanup even when the DOM node is adopted by a new `Component` rather than removed from the DOM.

#### Scenario: Detaching a component whose node is adopted during patching
- **WHEN** a `Component`'s DOM node is adopted by a new `Component` during `_patch_children()`
- **THEN** `_detach_from_node()` SHALL call `super()._detach_from_node()` to release Python-side resources
- **AND** `on_before_destroy` SHALL be invoked to dispose the `EffectScope` and DI child scope
- **AND** the DOM node SHALL NOT be removed from the document