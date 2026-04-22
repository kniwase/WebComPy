# Tasks: Partial Hydration — Skip Redundant DOM Operations

- [x] **Task 1: Add content-equality check to TextElement._init_node()**

**Estimated time: ~0.5 hours**

### Steps

1. Open `webcompy/elements/_text.py`.
2. In `TextElement._init_node()`, locate the prerendered-node branch:
   ```python
   if (
       getattr(existing_node, "__webcompy_prerendered_node__", False)
       and existing_node.nodeName.lower() == "#text"
   ):
       existing_node.textContent = self._get_text()
       node = existing_node
       self._mounted = True
   ```
3. Modify to compare before writing:
   ```python
   current_text = self._get_text()
   if existing_node.textContent != current_text:
       existing_node.textContent = current_text
   node = existing_node
   self._mounted = True
   ```
4. Verify the `if` block structure remains valid (the `node` and `self._mounted = True` assignments must execute regardless of whether the write occurred).

### Acceptance Criteria

- `TextElement._init_node()` no longer unconditionally calls `existing_node.textContent = ...` for prerendered nodes.
- When text matches, no DOM write occurs.
- When text differs, the DOM is updated to the component's current value.
- All existing tests pass.

---

- [x] **Task 2: Add content-equality check to Element._init_node()**

**Estimated time: ~0.5 hours**

### Steps

1. Open `webcompy/elements/_element.py`.
2. In `ElementBase._init_node()`, locate the prerendered-node branch.
3. Find the attribute-application loop:
   ```python
   for name, value in self._get_processed_attrs().items():
       if value is not None:
           node.setAttribute(name, value)
   ```
4. Wrap with equality check:
   ```python
   for name, value in self._get_processed_attrs().items():
       if value is not None:
           existing = node.getAttribute(name)
           if existing != value:
               node.setAttribute(name, value)
       elif node.hasAttribute(name):
           node.removeAttribute(name)
   ```
5. Verify that the existing `attr_names_to_remove` logic is compatible. If the `attr_names_to_remove` set is already being used, ensure the new equality-check loop supersedes or integrates cleanly. The simplest approach is to replace the existing attribute loop entirely with the conditional version.

### Acceptance Criteria

- `ElementBase._init_node()` no longer unconditionally calls `setAttribute` for prerendered nodes.
- When an attribute value matches, no DOM write occurs for that attribute.
- When an attribute value differs, the DOM is updated.
- Attributes that are `None` in `_get_processed_attrs()` but present on the node are still removed.
- All existing tests pass.

---

- [x] **Task 3: Add unit tests for conditional writes**

**Estimated time: ~1 hour**

### Steps

1. In `tests/unit/test_elements.py` (or create a new file), add tests using the real DOM (Playwright MCP) or a mock DOM abstraction:
   - `test_text_element_hydration_skips_same_text`: Create a `<div id="app">hello</div>`, create a `TextElement(Signal("hello"))`, call `_init_node()`, assert `div.firstChild.textContent == "hello"` and there was no DOM `characterDataModified` mutation.
   - `test_text_element_hydration_updates_different_text`: Same setup but Signal("world"), assert textContent becomes "world".
   - `test_element_hydration_skips_same_attribute`: Create a `<div id="app"><span class="test"></span></div>`, create an `Element("span", {"class": "test"})`, assert `className` stays "test" and no `attributes` mutation.
   - `test_element_hydration_updates_different_attribute`: Same setup but `{"class": "changed"}`, assert `className` becomes "changed".
   - `test_element_hydration_removes_stale_attribute`: Create `<span class="stale">`, create `Element("span", {"class": None})`, assert `className` is gone.

2. If mock DOM is not available, verify the behavior using the browser runtime via Playwright MCP for at least one representative test per element type.

### Acceptance Criteria

- Tests demonstrate that matching values are skipped.
- Tests demonstrate that differing values are updated.
- Tests demonstrate that stale attributes are removed.
- All existing tests pass.

---

- [x] **Task 4: Make loading screen semi-transparent**

**Estimated time: ~0.5 hours**

### Steps

1. Open `webcompy/cli/_html.py`.
2. In `_Loadscreen._style`, add a semi-transparent dark background to the `#webcompy-loading` element (via `.container` style):
   ```python
   ".container": {
       "width": "100%",
       "height": "100%",
       "display": "flex",
       "flex-direction": "column",
       "align-items": "center",
       "justify-content": "center",
       "position": "fixed",
       "background": "rgba(0, 0, 0, 0.5)",
       "z-index": "9999",
   },
   ```
3. Verify that the pre-rendered content is visible beneath the loading overlay.
4. Verify that removing the loading element (after hydration) reveals the fully interactive content.

### Acceptance Criteria

- The loading screen has a semi-transparent dark background (`rgba(0, 0, 0, 0.5)`).
- Pre-rendered content is visible beneath the loading overlay.
- The loading spinner remains clearly visible on the semi-transparent background.
- After hydration, the loading element is removed and content is fully visible as before.
- All existing E2E tests pass (loading screen wait logic still works).

---

- [x] **Task 5: Validate perf improvement with profiling**

**Estimated time: ~0.5 hours**

### Steps

1. Enable profiling (`AppConfig(profile=True)`) on a representative app (e.g., `docs_src`).
2. Measure `run_start → run_done` before and after applying the partial hydration change.
3. Document the result in a comment on the change or in test output.
4. If no measurable improvement is seen, document the finding and proceed anyway — the change is still correct and eliminates unnecessary DOM operations.

### Acceptance Criteria

- Profiling data is collected for at least one app.
- `run_start → run_done` timing is recorded and compared.
- Result is documented.

---

## Dependencies

- **Depends on:** `feat/hydration-measurement` (Task 1 must be complete so that `_record_phase` is available).

## Specs to Update

- `openspec/specs/elements/spec.md` — append "AND attributes SHALL be preserved without rewriting when values match the prerendered state" to the hydration requirement scenario.
- `openspec/specs/cli/spec.md` — update loading screen requirement to specify semi-transparent background.