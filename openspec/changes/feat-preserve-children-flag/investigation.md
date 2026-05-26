# SPA Navigation Bug Investigation

## Status
- **Date**: 2026-05-27
- **Investigator**: opencode
- **Issue**: Code card disappears after SPA client-side navigation between demo pages

## Symptom

When navigating between demo pages via client-side routing (SPA), the "Code" card (containing syntax-highlighted source code) disappears completely. Direct page loads work correctly.

### Reproduction Steps

1. Open `/sample/helloworld` directly → 3 cards visible (title, iframe, code)
2. Click "Demos" → "FizzBuzz" → 2 cards visible (title, iframe) — **Code card missing**
3. Click "Demos" → "HelloWorld" → 2 cards visible — **Code card still missing**
4. Refresh page (direct load) → 3 cards visible again

### DOM Structure Comparison

**Direct Load (HelloWorld)**:
```
article
  .container
    .demo-display-root
      .card
        .card-body
          h5.card-title       ← "HelloWorld"
          .card               ← iframe container
            .card-body
              iframe
          br
          .card               ← Code container ← **PRESENT**
            .card-header      ← "Code"
            .card-body
              pre
                code
```

**After SPA Nav (FizzBuzz)**:
```
article
  .container
    .demo-display-root
      .card
        .card-body
          h5.card-title       ← "FizzBuzz"
          .card               ← iframe container
            .card-body
              iframe
          br
          <!-- Code card completely missing -->
```

## Investigation Results

### Hypothesis 1: `:preserve_children` conflict
- **Test**: Removed `:preserve_children` from SyntaxHighlighting component
- **Result**: ❌ No improvement — bug persists

### Hypothesis 2: `SyntaxHighlighting` component / external JS (hljs)
- **Test 1**: Replaced `SyntaxHighlighting` with static `<pre><code>` element — bug persists (❌)
- **Test 2**: Completely removed `SyntaxHighlighting` import, used plain `html.PRE(html.CODE(source_code))` — **bug still persists** (❌)
- **Conclusion**: External JS (hljs) is **NOT the cause**. The bug is purely in WebComPy's internal DOM reconciliation.

### Hypothesis 3: iframe influence
- **Test**: Removed iframe from DemoDisplay
- **Result**: ❌ No improvement — bug persists

### Hypothesis 4: Signal/on_after_rendering timing
- **Test**: Passed static string instead of Signal to SyntaxHighlighting
- **Result**: ❌ No improvement — bug persists

### Hypothesis 5: `_render()` cleanup loop
- **Test**: Disabled the excess child node removal loop in `_render()`
- **Result**: ❌ No improvement — bug persists
- **Conclusion**: The cleanup loop is not the direct cause

### Hypothesis 6: Nested `.card` structure
- **Test**: Flattened structure (removed outer `.card > .card-body` wrapper)
- **Result**: ✅ **Bug disappears** — all cards render correctly after SPA nav
- **Conclusion**: The bug is triggered by **nested `.card` elements** (or deeply nested component structures)

## Key Finding

The bug is **structural**: when there are sibling elements with identical class names inside a nested component structure, the last sibling disappears during SPA reconciliation.

Specifically:
- Working: `.demo-display-root > h5 + .card + .card` (flat)
- Broken: `.demo-display-root > .card > .card-body > h5 + .card + .card` (nested)

## Root Cause Identified (2026-05-27)

### Problem: Detached DOM Nodes in Nested Adopted Elements

When `_patch_children()` reuses a node from an old element to a new element (`_adopt_node()`), it sets `new_child._node_cache = old_node`. However, it does **NOT** verify that the `old_node` is still attached to its parent DOM.

### Trigger Chain

1. **Initial render (HelloWorldPage)**: DOM tree has the outer `.card` with 4 children in `.card-body`
2. **SPA navigate to FizzBuzzPage**: `SwitchElement._refresh()` is called
3. **`_patch_children()`**: The outer `div.card` is matched and adopted (same tag name, `_node_cache` exists)
4. **Problem**: The `old_node` for the outer `div.card` was **already detached** from its parent DOM during the previous cleanup cycle
5. **`_adopt_node()`**: Sets `new_child._node_cache = old_node`, `new_child._mounted = True`
6. **`ElementWithChildren._render()`** for the new outer `div.card`: iterates children and calls `child._render()`
7. **`_mount_node()`** for children: checks `if not self._mounted` — but children were already `_mounted=True` from the old tree, so **no re-insertion happens**
8. **`_render()` cleanup loop**: checks `node.childNodes.length > self._children_length` — but since the outer `div.card` node is detached from DOM, `node.parentNode` is the old `.card-body` which now has fewer children, so cleanup removes nodes incorrectly

### Critical Evidence from Instrumentation

```
[DEEP] div.card _render() START parent=DIV children=2   ← outer div.card, 2 children
[DEEP] div.card _render() END parent=DIV dom_children=2  ← OK

[DEEP] div.card _render() START parent=None children=2   ← inner Code card, parent=None!
[DEEP] div.card _render() END parent=None dom_children=2 ← detached from DOM
```

The inner Code card's `div.card` has `parentNode=None`, meaning it was never re-inserted into the DOM after `_patch_children()` adopted the outer `div.card`.

### Root Cause Location

**File**: `webcompy/elements/types/_dynamic.py`
**Function**: `_patch_children()`
**Line**: `new_child._adopt_node(old_node)` (around line 124 and 138)

When adopting a node:
- The old node is assigned to the new child
- The new child is NOT re-inserted into the parent DOM
- If the old node was already detached, it remains detached
- All descendants of the adopted node also remain detached

### Why Flat Structure Works

In a flat structure, the siblings are direct children of the parent, not nested inside an adopted element. Each sibling is independently matched and re-inserted by `_reposition_node()`.

In a nested structure, the outer element's node is adopted but detached. Its children (inner elements) are also detached and never re-inserted because `_mounted=True` prevents `_mount_node()` from running.

## Proposed Fix

After `_adopt_node()` in `_patch_children()`, if the adopted node is not attached to the new parent's DOM, it must be re-inserted. This can be done by:

1. After `_patch_children()` returns, call `_re_index_children()` on the parent
2. In `_render()` for adopted elements, check if `node.parentNode` matches the expected parent, and if not, re-insert
3. Or: In `_adopt_node()`, set `_mounted = False` if `node.parentNode is None`, forcing `_mount_node()` to re-insert

## Files to Fix

- `webcompy/elements/types/_dynamic.py`: `_patch_children()` — add re-insertion check after adoption
- `webcompy/elements/types/_abstract.py`: `_adopt_node()` — set `_mounted = False` if detached

## Impact of Fix

- Fixes SPA navigation bug for all nested component structures
- Maintains backward compatibility with existing tests
- No API changes required

## Merge Status

- `origin/main` merged into `feat/preserve-children-flag` (2026-05-27)
- Includes major changes: RenderContext introduction, agent restructure
- Bug persists after merge — **not resolved by upstream changes**

## Next Investigation Plan

### Phase 1: Minimal Reproduction (1 hour)
1. Create a minimal test case using `TestRenderer` (browserless) that reproduces the nested sibling issue
2. Use `webcompy.testing` module to render two versions of a nested structure and compare VDOM trees

### Phase 2: VDOM Trace (2 hours)
1. Add instrumentation to `_patch_children()` to log:
   - Which nodes are being adopted vs created
   - `_node_idx` values before/after patching
   - Which child nodes are being removed by the cleanup loop
2. Run the minimal test case and analyze the trace

### Phase 3: Root Cause Fix (2 hours)
1. Based on trace results, identify whether the bug is in:
   - `_patch_children()` node adoption logic
   - `_re_index_children()` index recalculation
   - `_render()` cleanup loop ordering
   - `_mount_node()` insert position calculation
2. Apply targeted fix
3. Verify fix with both minimal test case and full demo pages

### Phase 4: Regression Testing (1 hour)
1. Run existing unit tests (`tests/test_preserve_children.py`)
2. Run E2E tests for demo pages
3. Run full test suite to ensure no regressions

## Related Specs
- `openspec/specs/elements/spec.md` — Element DOM reconciliation
- `openspec/specs/nested-dynamic-element/spec.md` — Nested dynamic elements
- `openspec/specs/list-reconciliation/spec.md` — Key-based reconciliation
- `openspec/specs/router/spec.md` — Client-side routing
