# Proposal: Partial Hydration — Skip Redundant DOM Operations

## Summary

Optimize the browser-side hydration phase by skipping redundant DOM operations when a prerendered node matches the expected content. Specifically: skip `textContent` updates for `TextElement` nodes whose content matches, and skip attribute re-setting for `Element` nodes whose prerendered attributes already match the component's current state. This reduces browser-side DOM manipulation time during app startup.

## Motivation

Currently, even when WebComPy reuses a prerendered DOM node (detected via `__webcompy_prerendered_node__`), it still performs redundant operations:
- `TextElement._init_node()` always calls `existing_node.textContent = self._get_text()` even when the text is identical
- `Element._init_node()` always calls `node.setAttribute()` for every attribute, even when the attribute already has the same value

These operations are individually cheap, but in a page with thousands of nodes, they add up. Since SSG pre-renders the exact same content, we know the values should match — we can skip these operations.

## Known Issues Addressed

- **TextElement does not hydrate pre-rendered text nodes** (from config.yaml known issues): This proposal addresses it by adding content-comparison checks.

## Non-goals

- This does not add a full "hydration mode" where the Python component tree is reconstructed from the DOM rather than built from scratch. That is addressed in a separate proposal (feat/hydration-full).
- This does not change the SSG output format or add new metadata attributes.
- This does not skip Python object construction — only DOM operations.

## Dependencies

- Depends on `feat/hydration-measurement` for validating the performance impact.

## Design

### Approach

Add content-equality checks in `_init_node()` for `TextElement` and `Element` when a prerendered node is reused.

### TextElement Optimization

Currently (`_text.py:67`):
```python
if (
    getattr(existing_node, "__webcompy_prerendered_node__", False)
    and existing_node.nodeName.lower() == "#text"
):
    existing_node.textContent = self._get_text()  # ← always sets, even if same
    node = existing_node
    self._mounted = True
```

Proposed:
```python
if (
    getattr(existing_node, "__webcompy_prerendered_node__", False)
    and existing_node.nodeName.lower() == "#text"
):
    current_text = self._get_text()
    if existing_node.textContent != current_text:
        existing_node.textContent = current_text
    node = existing_node
    self._mounted = True
```

### Element Optimization

Currently (`_element.py:48-67`):
```python
if (
    getattr(existing_node, "__webcompy_prerendered_node__", False)
    and existing_node.nodeName.lower() == self._tag_name
):
    node = existing_node
    self._mounted = True
    attr_names_to_remove = set(...)
    for name, value in self._get_processed_attrs().items():
        if value is not None:
            node.setAttribute(name, value)  # ← always sets, even if same
```

Proposed: Only call `setAttribute` when the new value differs from the current value:
```python
for name, value in self._get_processed_attrs().items():
    if value is not None:
        existing = node.getAttribute(name)
        if existing != value:
            node.setAttribute(name, value)
```

### Performance Consideration

`getAttribute()` and `textContent` property access are fast DOM reads. The net effect should be positive when attribute/text values match (which they always will during initial hydration after SSG), since `setAttribute()` triggers style recalculation and potential reflow, while `getAttribute()` is a pure read.

### Risk

In rare cases where SSG output and browser state diverge (e.g., browser extensions modifying the DOM, or user-specific pre-rendering), the old values might be stale. However, since `_get_processed_attrs()` always computes the current reactive values, this divergence would only matter if someone modifies the prerendered HTML between SSG and hydration — which is not a supported use case.

## Specs Affected

- `elements` — updates the "Pre-rendered DOM nodes shall be reused during hydration" requirement to add content-preservation behavior
- `app` — may want to reference this optimization in the hydration requirement