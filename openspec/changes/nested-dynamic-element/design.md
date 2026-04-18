## Context

WebComPy's `DynamicElement` (base class for `RepeatElement` and `SwitchElement`) currently raises a `WebComPyException` when a nested `DynamicElement` is detected in `_create_child_element`. This was a simplifying restriction because refresh propagation between nested dynamic elements was not designed.

In the current architecture:
- `DynamicElement` has no DOM node of its own (`_get_node()` raises, `_init_node()` raises)
- `DynamicElement._parent` is set to the nearest `ElementWithChildren` (which could be another `DynamicElement`)
- `RepeatElement._refresh()` and `SwitchElement._refresh()` call `self._parent._get_node()` to get the DOM parent node for inserting/removing children
- If `_parent` is a `DynamicElement`, `_get_node()` would raise, preventing nesting

The key challenge: nested DynamicElements need to find their nearest **real** DOM ancestor for DOM manipulation, bypassing any intermediate DynamicElements.

## Goals / Non-Goals

**Goals:**
- Allow `repeat` inside `switch` and `switch` inside `repeat` (and arbitrary nesting depth)
- Preserve correct reactive callback registration and cleanup for nested DynamicElements
- Ensure keyed reconciliation works correctly when child elements contain nested DynamicElements
- Maintain backward compatibility — all existing non-nested code continues to work identically

**Non-Goals:**
- SwitchElement internal reconciliation (branches still fully replace their subtree)
- Virtual DOM diffing
- Optimizing SwitchElement to patch rather than replace subtrees

## Decisions

### Decision 1: Remove the nesting guard from `_create_child_element`

**Choice**: Delete the `isinstance(child_element, DynamicElement)` check in `DynamicElement._create_child_element`.

**Rationale**: This guard was the sole blocker. The real challenge is ensuring that DOM operations work correctly with nested DynamicElements, not preventing nesting itself.

**Alternatives considered**:
- Keep the guard and add a special "nesting mode" flag → unnecessarily complex, adds state
- Create a wrapper type that bundles DynamicElements → adds indirection without benefit

### Decision 2: DynamicElement._get_node() traverses ancestors to find real DOM node

**Choice**: Override `_get_node()` on `DynamicElement` to walk up the `_parent` chain until finding a non-DynamicElement ancestor, then return its `_get_node()`. Remove the `NoReturn` return type and `_init_node()` override.

**Rationale**: Every place that calls `self._parent._get_node()` in `RepeatElement` and `SwitchElement` already assumes the parent has a real DOM node. With nesting, `self._parent` might be a DynamicElement, but conceptually DynamicElements are "transparent" — they delegate their DOM operations to their nearest real-DOM ancestor. Making `_get_node()` transparent is the cleanest way to handle this.

**Impact on `_node_count`**: `DynamicElement._node_count` already sums child counts, which is correct — a nested DynamicElement adds its children's node counts to the parent's total.

**Alternatives considered**:
- Add a `_get_dom_parent()` method that skips DynamicElements → more explicit but requires updating all call sites
- Store a `_dom_parent` reference during construction → extra state to maintain, breaks on re-parenting

### Decision 3: Use `_get_node()` instead of `self._parent._get_node()` in DynamicElement refresh methods

**Choice**: In `RepeatElement._refresh()`, `RepeatElement._reconcile_children()`, and `SwitchElement._refresh()`, replace `self._parent._get_node()` with `self._get_node()` for the DOM parent node lookup only when `self._parent` is a DynamicElement.

Wait — actually, we need the **parent's** DOM node, not our own. Since DynamicElements have no DOM node, `self._get_node()` would traverse up. But we want `self._parent._get_node()` — and with the fix, if `self._parent` is a DynamicElement, it will also traverse up correctly.

**Revised choice**: Simply keep `self._parent._get_node()` — with the fix in Decision 2, this works correctly whether `_parent` is a regular `ElementWithChildren` (returns its DOM node directly) or a `DynamicElement` (traverses to find the real DOM ancestor).

### Decision 4: DynamicElement._create_child_element delegates to ElementWithChildren

**Choice**: Remove the override entirely. The `DynamicElement._create_child_element` override currently only contains the nesting guard. After removing the guard, the method is identical to the base class version, so we can delete the override entirely and let `ElementWithChildren._create_child_element` handle child creation normally.

**Rationale**: Fewer overrides = fewer places to maintain. The base class correctly sets `_parent` and `_node_idx` on children.

### Decision 5: _node_count and _re_index_children must handle nested DynamicElements correctly

**Choice**: `DynamicElement._node_count` already returns `sum(child._node_count for child in self._children)`, which naturally handles nesting. `ElementWithChildren._re_index_children` also recursively re-indexes, which works. No changes needed.

**Rationale**: The existing implementations are already recursive/sum-based and handle nested structures correctly.

### Decision 6: Reactive callback cleanup for nested DynamicElements

**Choice**: When a parent DynamicElement removes children (in `_refresh`), it calls `child._remove_element()`. The `_remove_element` method on `ElementAbstract` iterates `_callback_ids` and removes them from `ReactiveStore`. If a removed child is itself a `DynamicElement` with its own reactive callbacks, `_remove_element` will also clean those up via its own `_callback_ids`.

However, `_remove_element` on `ElementWithChildren` only cleans up direct children's DOM nodes (`child._remove_element(True, False)`). For `DynamicElement` children, we need to ensure their reactive callbacks are also cleaned.

**Solution**: The existing `_remove_element` chain is:
- `ElementAbstract._remove_element()` → removes callbacks from ReactiveStore, removes DOM node, clears cache
- `ElementWithChildren._remove_element()` → calls `super()._remove_element()`, then `child._remove_element(True, False)` for each child
- `DynamicElement` doesn't override `_remove_element`

This chain already works correctly because `DynamicElement` extends `ElementWithChildren`, and the recursive cleanup in `ElementWithChildren._remove_element` will call `_remove_element` on all children including nested DynamicElements, which will clean up their callback IDs.

**No changes needed** — the existing cleanup chain handles nesting.

## Risks / Trade-offs

**[Deep nesting performance]** → Not a primary use case, but the ancestor traversal in `_get_node()` is O(depth). Mitigation: In practice, nesting depth is typically 2-3 levels (repeat inside switch or vice versa). The traversal is a simple attribute chain, negligible cost.

**[SSR correctness]** → `_on_set_parent` and `_render_html` must work with nested DynamicElements. The `DynamicElement._render_html` already joins children's HTML, and `_on_set_parent` generates initial children. Both are recursive and should work. Mitigation: Add tests for SSR output of nested structures.

**[SwitchElement full replacement]** → When a `switch` branch changes, it removes all children and regenerates. If a branch contained a `repeat` with keyed reconciliation, the `repeat`'s internal state (key maps, reactive callbacks) gets destroyed. This is acceptable — the `switch` is choosing a completely different branch. No mitigation needed; this is expected behavior.

**[RepeatElement reconciliation with nested DynamicElement children]** → When a `RepeatElement` reconciles and reuses a child (same key), the child stays in place. But if that child is an `ElementWithChildren` that contains a nested DynamicElement, the reconciliation correctly preserves it. If reconciliation removes a child with a nested DynamicElement, `_remove_element` cascades through and cleans up. No changes needed.