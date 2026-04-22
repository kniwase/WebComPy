# Components — Delta: feat-switch-patch

## Changes

### Added: _detach_from_node() on Component

When a `Component` is the root of an old branch subtree being patched, `Component._detach_from_node()` SHALL call `super()._detach_from_node()` followed by `on_before_destroy` to dispose the EffectScope and DI child scope. This ensures proper lifecycle cleanup even when the DOM node is adopted by a new Component rather than removed from the DOM.