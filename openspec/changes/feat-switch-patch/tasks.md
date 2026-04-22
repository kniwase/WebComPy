# Tasks: Switch Patch — DOM Node Reuse on Structural Changes

- [ ] **Task 1: Add `_adopt_node()` to `ElementBase` and `TextElement`**

**Estimated time: ~1.5 hours**

### Steps

1. Open `webcompy/elements/_element.py`.
2. Implement `ElementBase._adopt_node(node)`:
   - Assign `_node_cache` and set `_mounted=True`
   - Set `node.__webcompy_node__ = True`
   - Remove stale attributes (present on node but not in current attrs)
   - Set matching attributes with equality check (reuse from `feat/hydration-partial`)
   - Register Signal callbacks for reactive attributes
   - Attach event handlers via `create_proxy`
   - Initialize `DomNodeRef` if present
   - Do NOT call `_mount_node()`
3. Open `webcompy/elements/_text.py`.
4. Implement `TextElement._adopt_node(node)`:
   - Assign `_node_cache` and set `_mounted=True`
   - Set `node.__webcompy_node__ = True`
   - Conditionally update `textContent` if it differs
5. Write unit tests for both methods.

### Acceptance Criteria

- `ElementBase._adopt_node()` exists with full attribute/event/signal/ref binding.
- `TextElement._adopt_node()` exists with conditional text update.
- Neither method creates new DOM nodes or calls mount operations.
- All existing tests pass.

---

- [ ] **Task 2: Add `_detach_from_node()` to `ElementBase` and `Component`**

**Estimated time: ~1.5 hours**

### Steps

1. Open `webcompy/elements/_element.py`.
2. Implement `ElementBase._detach_from_node()`:
   - Remove event handlers from the node and call `handler.destroy()` on each proxy
   - Destroy Signal callbacks via `consumer_destroy()`
   - Reset `DomNodeRef` if present
   - Clear `_node_cache` and `_mounted`
   - Call `__purge_signal_members__()`
   - Do NOT call `node.remove()` or recurse into children
3. Open `webcompy/components/_component.py`.
4. Override `_detach_from_node()` on `Component`:
   - Call `super()._detach_from_node()`
   - Call `on_before_destroy` to dispose EffectScope and DI child scope
5. Write unit tests verifying no DOM node removal and complete cleanup.

### Acceptance Criteria

- `ElementBase._detach_from_node()` releases all Python-side resources without DOM removal.
- `Component._detach_from_node()` additionally disposes EffectScope and DI scope.
- No `node.remove()` calls occur.
- All existing tests pass.

---

- [ ] **Task 3: Implement `_patch_children()` and `_is_patchable()`**

**Estimated time: ~2 hours**

### Steps

1. Open `webcompy/elements/_dynamic.py` (or appropriate module).
2. Implement `_is_patchable(old, new)`:
   - Two TextElement instances → True
   - Two ElementBase instances with same `_tag_name` → True
   - Any DynamicElement → False
   - Otherwise → False
3. Implement `_patch_children(old_children, new_children)`:
   - Iterate new children, find patchable matches in old children
   - Call `_adopt_node()` for matches, recurse for ElementBase children
   - Call `_reposition_node()` to correct DOM position
   - Cleanup matched old elements via `_detach_from_node()`
   - Cleanup unmatched old elements via `_remove_element()`
4. Implement `_reposition_node(element, new_index)` utility.
5. Write unit tests for: identical structure, partial overlap, complete replacement, Component-to-Component patching.

### Acceptance Criteria

- `_patch_children()` correctly adopts matching nodes and cleans up non-matching ones.
- `_is_patchable()` returns correct results for all element type combinations.
- DOM node positions are corrected after adoption.
- All existing tests pass.

---

- [ ] **Task 4: Integrate into `SwitchElement._refresh()`**

**Estimated time: ~1 hour**

### Steps

1. Open `webcompy/elements/_dynamic.py` (or wherever `SwitchElement` is defined).
2. Replace the full-destroy-and-regenerate logic with `_patch_children()`.
3. Only call `_render()` on new children that were not adopted (`not child._mounted`).
4. Preserve the deferred rendering mechanism (`start_defer_after_rendering` / `end_defer_after_rendering`).
5. Write integration tests including routing scenarios via Playwright MCP.

### Acceptance Criteria

- `SwitchElement._refresh()` uses `_patch_children()` instead of full destroy+recreate.
- Non-adopted children are rendered normally.
- `on_after_rendering` hooks run after all DOM mutations.
- Visual regression tests pass (no rendering differences).
- All existing tests pass.

---

- [ ] **Task 5: Evaluate Component patching and decide on rollback**

**Estimated time: ~1 hour**

### Steps

1. Run integration tests for Component patching scenarios.
2. If issues arise, restrict `_is_patchable()` to exclude `Component` instances and document the limitation.
3. If successful, proceed with Component-inclusive patching.
4. Document the decision in the change artifacts.

### Acceptance Criteria

- A clear decision is documented: Component patching is enabled or restricted.
- If restricted, `_is_patchable()` excludes Component and all tests pass.
- If enabled, Component patching scenarios pass without regressions.

---

## Dependencies

- **Informed by:** `feat/hydration-full` — `_adopt_node()` is the same method.
- **Informs:** `feat/hydration-full` — `_adopt_node()` converges on a single implementation.
- **Depends on:** `feat/hydration-measurement` — profiling validates runtime improvement.

## Specs to Update

- `openspec/specs/elements/spec.md` — add `_adopt_node()`, `_detach_from_node()`, `_patch_children()`, and `_is_patchable()` to element requirements.
- `openspec/specs/components/spec.md` — add `Component._detach_from_node()` lifecycle behavior.