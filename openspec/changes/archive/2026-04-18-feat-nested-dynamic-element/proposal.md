## Why

DynamicElement nesting (repeat inside switch, switch inside repeat) is currently forbidden at runtime with `WebComPyException("Nested DynamicElement is not allowed.")`. This blocks common UI patterns like conditional list rendering and tab-based list rendering. The original restriction exists because refresh propagation between nested dynamic elements was not designed — this change designs and implements that propagation.

## What Changes

- Remove the runtime guard in `DynamicElement._create_child_element` that rejects nested `DynamicElement` instances
- Implement refresh propagation so that when a parent `DynamicElement` refreshes (e.g., a `SwitchElement` switches branches), any nested `DynamicElement` children are properly created, mounted, and cleaned up
- Ensure `RepeatElement._refresh` and `SwitchElement._refresh` correctly handle child dynamic elements during reconciliation (key-based) and full-rebuild scenarios
- **BREAKING**: None — the nesting was previously rejected, so all existing code continues to work

## Capabilities

### New Capabilities

- `nested-dynamic-element`: Support for nesting `repeat` and `switch` elements within each other, with correct reactive refresh propagation

### Modified Capabilities

- `elements`: Remove the DynamicElement nesting restriction; add requirements for how nested dynamic elements propagate refreshes
- `list-reconciliation`: Ensure key-based reconciliation works correctly when child elements contain nested DynamicElements

## Impact

- `webcompy/elements/types/_dynamic.py` — Remove nesting guard, add refresh propagation support
- `webcompy/elements/types/_repeat.py` — Ensure `_refresh` and `_reconcile_children` handle nested DynamicElements
- `webcompy/elements/types/_switch.py` — Ensure `_refresh` properly cleans up nested DynamicElements
- `webcompy/elements/types/_base.py` — `_create_child_element` may need adjustments for parent tracking
- Tests — Unit tests for nested repeat/switch combinations, E2E tests for common nesting patterns
- No public API changes (nesting was previously impossible, not deprecated)

## Known Issues Addressed

- "DynamicElement nesting is forbidden (raises exception)" — from Element System known issues

## Non-goals

- SwitchElement internal reconciliation (switch branches still fully replace their subtree — this is a separate concern)
- Virtual DOM diffing (still direct DOM manipulation)
- Supporting more than two levels of nesting depth specifically (the design should work for arbitrary depth, but deep nesting is not a primary use case)