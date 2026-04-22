# Design: Partial Hydration — Skip Redundant DOM Operations

## Design Decisions

### D1: Content-equality checks only on prerendered nodes
The optimization applies **only** when `__webcompy_prerendered_node__` is set on the reused node. For newly created nodes (non-hydration path), the existing unconditional `setAttribute`/`textContent` behavior is preserved.

### D2: Equality comparison for attributes uses `getAttribute()`
For each attribute in `_get_processed_attrs()`, we read the current DOM value via `node.getAttribute(name)` and compare it to the computed value before calling `node.setAttribute(name, value)`. This adds one DOM read per attribute, but avoids a DOM write + potential reflow when values already match.

### D3: Text comparison before assignment
For `TextElement`, we read `existing_node.textContent` once and compare it to `self._get_text()` before assignment. If equal, no DOM write occurs.

### D4: No new API surface — purely internal optimization
This change modifies only the `_init_node()` methods of `Element` and `TextElement`. No new public API is introduced.

## Architecture

```
Element._init_node()  (prerendered branch)
═══════════════════════════════════════════════
  existing = self._get_existing_node()
  if existing and existing.__webcompy_prerendered_node__
               and existing.nodeName.lower() == self._tag_name:
      node = existing
      self._mounted = True

      # Attribute diff (NEW)
      current_attrs = self._get_processed_attrs()
      for name, value in current_attrs.items():
          if value is not None:
              existing_val = node.getAttribute(name)   # ← read
              if existing_val != value:              # ← compare
                  node.setAttribute(name, value)     # ← write (conditional)
          else:
              node.removeAttribute(name)

      # Event handlers and Signal callbacks (unchanged)
      ...

TextElement._init_node()  (prerendered branch)
═══════════════════════════════════════════════
  existing = self._get_existing_node()
  if existing and existing.__webcompy_prerendered_node__
               and existing.nodeName.lower() == "#text":
      current_text = self._get_text()
      if existing.textContent != current_text:       # ← compare
          existing.textContent = current_text          # ← write (conditional)
      node = existing
      self._mounted = True
```

## Algorithm Details

### Element attribute diff

```python
for name, value in self._get_processed_attrs().items():
    if value is not None:
        existing = node.getAttribute(name)
        if existing != value:
            node.setAttribute(name, value)
    elif node.hasAttribute(name):
        node.removeAttribute(name)
```

**Why `getAttribute` is acceptable:** In the WebComPy fine-grained reactivity model, attribute updates are already triggered by signals on a per-attribute basis. The `getAttribute` call is a pure DOM read that does not trigger style recalculation. The `setAttribute` call avoided is a write that would trigger at minimum an attribute change observation and potentially a style recalculation.

### TextElement text diff

```python
current_text = self._get_text()
if existing_node.textContent != current_text:
    existing_node.textContent = current_text
```

**Why `textContent` comparison is correct:** `TextElement._get_text()` returns the string representation of the current value (whether a raw string or a Signal's current value). For SSG output, this value matches the prerendered text exactly. For rare divergence cases (browser extension modified DOM), the comparison ensures we still update to the correct value.

### Risk: Browser extension modified DOM
If a browser extension modifies the prerendered DOM between page load and app initialization, the old values could be stale. However:
- The framework does not support "external DOM modification" as a supported use case.
- The comparison ensures we update to the component's true state if divergence is detected.
- The `setAttribute` fallback is always available.

## Performance Model

For a page with N DOM nodes and M attributes per node:

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| DOM reads per node | 0 | M (getAttribute) | — |
| DOM writes per node | M (setAttribute all) | ≤ M (only changed) | up to 100% on hydration |
| textContent writes per text node | 1 (always) | 0 or 1 | 100% on matching text |
| style recalculations | up to N×M | 0 (if all match) | up to 100% |

**Key assumption:** After SSG, prerendered attribute values match component state exactly. This is guaranteed because SSG runs the same Python code that the browser will run.

## Rollback Path

If `getAttribute`-based comparison introduces any issues:
1. Remove the equality check and restore unconditional `setAttribute`/`textContent`.
2. The change is localized to `_init_node()` in two files and can be reverted in minutes.

## Integration with Measurement

This change is designed to be validated by `feat/hydration-measurement`:
- The `run_start → run_done` timing should decrease measurably for apps with many DOM nodes.
- If measurement shows no improvement (e.g., C-extension DOM implementations that optimize no-op setAttribute), the change is still correct and harmless.
