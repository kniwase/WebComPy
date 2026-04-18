## Context

WebComPy's SSR→hydration flow works as follows:

1. Server renders the full DOM tree to HTML (via `_render_html`)
2. Browser renders the static HTML
3. `AppDocumentRoot._init_node()` finds the existing DOM and marks all nodes with `__webcompy_prerendered_node__ = True`
4. Each element's `_init_node()` runs: if an existing node matches (prerendered + correct nodeName), it reuses it; otherwise it removes the old node and creates a new one

`ElementBase` (tag elements) and `NewLine` (`<br>`) correctly reuse pre-rendered nodes. `TextElement` (`#text` nodes) does not — it always deletes the existing node and calls `createTextNode()`, causing a visible flash.

Current `TextElement._init_node()`:
```
existing_node = self._get_existing_node()
if (
    existing_node
    and getattr(existing_node, "__webcompy_prerendered_node__", False)
    and existing_node.nodeName.lower() == "#text"
):
    existing_node.remove()                    # ← BUG: deletes instead of reuses
node = browser.document.createTextNode(self._get_text())
```

Correct pattern (from `NewLine` and `ElementBase`):
```
existing_node = self._get_existing_node()
if existing_node and prerendered and nodeName matches:
    node = existing_node                      # ← reuse
    self._mounted = True                      # ← skip appendChild
```

## Goals / Non-Goals

**Goals:**
- Eliminate the text flash during hydration of SSR pages
- Make `TextElement` hydration behavior consistent with other element types

**Non-Goals:**
- Content diffing for text nodes (SSR output and initial signal values are identical; reactive updates are handled by `on_after_updating` callbacks)
- Changing `ElementBase` or `NewLine` hydration (already correct)

## Decisions

### 1. Reuse pre-rendered `#text` nodes without content overwrite

**Decision**: When a pre-rendered `#text` node is found during hydration, adopt it as-is without setting `textContent`.

**Rationale**: The SSR output uses `_render_html()` → `_get_text()`, and the browser-side `_init_node()` computes the same `_get_text()`. The values are guaranteed to be identical at hydration time. For reactive text (`SignalBase`), the `on_after_updating` callback registered in `__init__` handles all subsequent changes via `_update_text`.

**Alternatives considered**:
- **Reusing + overwriting `textContent`**: Redundant since values match; adds unnecessary DOM mutation
- **Reusing + diffing `textContent`**: Comparison cost is negligible but adds complexity for no benefit

### 2. Follow the same hydration pattern as `NewLine` / `ElementBase`

**Decision**: Set `node = existing_node` and `self._mounted = True` when hydration succeeds, mirroring the existing pattern.

**Rationale**: Consistency. The `_mount_node()` method checks `self._mounted` to decide whether to `appendChild`/`insertBefore` — setting `True` skips this, leaving the pre-rendered node in place.

## Risks / Trade-offs

- **SSR/initial-value mismatch**: If someone manually mutates the DOM between SSR output and hydration, the adopted text node may have different content. → Mitigation: this applies to all element types already, and manual DOM mutation before hydration is not a supported use case.
- **`MultiLineTextElement`**: Uses `RepeatElement` which creates `TextElement` children. The fix to `TextElement` resolves this transitively. No separate handling needed.