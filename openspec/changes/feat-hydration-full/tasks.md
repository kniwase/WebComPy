# Tasks: Full Hydration — DOM-First Component Reconstruction

## Task 1: Implement `_adopt_node()` on `ElementBase` and `TextElement`

**Estimated time: ~1 hour**

### Steps

1. Open `webcompy/elements/_element.py`.
2. Add `ElementBase._adopt_node(self, node: DOMNode)` method with the logic from `design.md`:
   - Assign `_node_cache` and set `_mounted=True`
   - Set `node.__webcompy_node__ = True`
   - Remove stale attributes (present on node but not in `current_attrs`)
   - Set matching attributes with equality check (reuse from `feat/hydration-partial`)
   - Register Signal callbacks for reactive attributes
   - Attach event handlers
   - Initialize `DomNodeRef` if present
3. Open `webcompy/elements/_text.py`.
4. Add `TextElement._adopt_node(self, node: DOMNode)` method:
   - Assign `_node_cache` and set `_mounted=True`
   - Set `node.__webcompy_node__ = True`
   - Conditionally update `textContent`
5. Verify that both methods do NOT call `_mount_node()`, as the node is assumed to already be in the DOM.

### Acceptance Criteria

- `ElementBase._adopt_node()` exists with full attribute/event/signal/ref binding.
- `TextElement._adopt_node()` exists with conditional text update.
- Both methods set `self._mounted = True` and `self._node_cache`.
- Neither method calls `node.createElement` or any mount operation.

---

## Task 2: Implement `_hydrate_node()` on `ElementAbstract`

**Estimated time: ~0.5 hours**

### Steps

1. Open `webcompy/elements/_abstract_element.py`.
2. Add `ElementAbstract._hydrate_node(self)` method:
   ```python
   def _hydrate_node(self) -> DOMNode:
       existing = self._get_existing_node()
       if existing and getattr(existing, "__webcompy_prerendered_node__", False):
           self._adopt_node(existing)
           return existing
       else:
           return self._init_node()
   ```
3. Verify that `_get_existing_node()` is accessible from `ElementAbstract`.

### Acceptance Criteria

- `_hydrate_node()` returns a DOM node.
- When a prerendered node exists and matches, it calls `_adopt_node()` and returns the existing node.
- When no prerendered node exists, it calls `_init_node()` and returns the newly created node.

---

## Task 3: Add `hydrate` parameter to `AppConfig` and `WebComPyApp`

**Estimated time: ~0.5 hours**

### Steps

1. Open `webcompy/app/__init__.py`.
2. Add `hydrate: bool = True` to `AppConfig` dataclass.
3. Update `WebComPyApp.__init__()` to accept `hydrate: bool = True` and store `self._hydrate`.
4. In `WebComPyApp.__init__()`, set `self._hydrate = self.config.hydrate if config else hydrate` (or equivalent logic to prefer config value).

### Acceptance Criteria

- `AppConfig(hydrate=False)` stores the value.
- `WebComPyApp.__init__(..., hydrate=False)` stores the value.
- Default is `True` for browser and `False` for server (handled by caller, not by `WebComPyApp` itself).

---

## Task 4: Integrate `_hydrate_node()` into `AppDocumentRoot._render()`

**Estimated time: ~1 hour**

### Steps

1. Open `webcompy/app/__init__.py` (or wherever `AppDocumentRoot` is defined).
2. In `AppDocumentRoot._render()`, add hydration mode check before the normal render loop:
   ```python
   def _render(self):
       if self._app._hydrate and not self._rendered_children:
           # Hydration pass: try _hydrate_node() for each child
           for child in self._children:
               child._hydrate_node()
           # Fallback for unmatched children
           for child in self._children:
               if not child._mounted:
                   child._render()
       else:
           for child in self._children:
               child._render()
       # Remove loading indicator
       loading = browser.document.getElementById("webcompy-loading")
       if loading:
           loading.remove()
           self._app._record_phase("loading_removed")
           self._app._emit_profile_summary()
   ```
3. Ensure the `_rendered_children` check prevents re-hydration on subsequent renders (e.g., if `_render()` is called multiple times).

### Acceptance Criteria

- When `_hydrate=True` and `_rendered_children` is empty, children use `_hydrate_node()`.
- Unmatched children (no prerendered node) still get `_render()` called and are properly mounted.
- The loading indicator is still removed correctly.
- When `_hydrate=False`, behavior is unchanged.

---

## Task 5: Add unit and integration tests

**Estimated time: ~1.5 hours**

### Steps

1. Create `tests/unit/test_full_hydration.py`:
   - `test_element_adopts_prerendered_node`: Mock a DOM with a prerendered div, create `Element("div")`, call `_adopt_node()`, assert `_node_cache` is set and `_mounted=True`.
   - `test_text_element_adopts_prerendered_node`: Mock a `#text` node, create `TextElement("hello")`, call `_adopt_node()`, assert text content is correct.
   - `test_hydrate_node_falls_back_to_init`: Mock NO prerendered node, call `_hydrate_node()`, assert `_init_node()` was called and a new node was created.
   - `test_app_hydrate_false_does_not_hydrate`: Create `WebComPyApp(hydrate=False)`, assert `AppDocumentRoot._render()` does not call `_hydrate_node()`.
2. Create `tests/e2e/test_hydration_full.py` (or update existing e2e test):
   - Generate a static site with profiling enabled.
   - Open the generated page in a browser.
   - Capture browser console output.
   - Assert that `[WebComPy Profile]` shows `run_start → run_done` is faster than without full hydration.
3. Test edge cases:
   - Conditional content (SwitchElement with non-matching branch) falls back to creation.
   - Nested hydration: parent element adopts, children are hydrated recursively.

### Acceptance Criteria

- `_adopt_node()` correctly binds attributes, events, signals, and refs.
- `_hydrate_node()` correctly falls back when no prerendered node exists.
- Full hydration reduces `run_start → run_done` timing by a measurable amount.
- No visual regressions or console errors during e2e tests.

---

## Dependencies

- **Depends on:** `feat/hydration-partial` (Task 1) — `_adopt_node()` reuses the conditional attribute/text writes.
- **Depends on:** `feat/hydration-measurement` (Task 1) — `_record_phase` and `_emit_profile_summary` are needed.

## Specs to Update

- `openspec/specs/elements/spec.md` — add `_adopt_node()` and `_hydrate_node()` to the "Pre-rendered DOM nodes shall be reused during hydration" requirement.
- `openspec/specs/app-lifecycle/spec.md` — add `hydrate` parameter to `WebComPyApp.__init__()` requirement.
- `openspec/specs/app-config/spec.md` — add `AppConfig.hydrate` field description.
