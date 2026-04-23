# Design: Remove hidden attribute from prerendered app root

## Approach

Remove the `hidden=True` override in `AppRootComponent._render_html()`. Currently this method temporarily sets `hidden=True` on the attrs dict, calls `super()._render_html()`, then restores the original value. This override exists to ensure the app root is hidden until PyScript initializes. However, for prerendered pages, the content should be visible immediately so it can be seen through the semi-transparent loading overlay.

## Changes

### `webcompy/app/_root_component.py`

Remove the `hidden` manipulation in `_render_html()`:

```python
# Before:
def _render_html(self, newline=False, indent=2, count=0):
    hidden = self._attrs.get("hidden")
    self._attrs["hidden"] = True
    html = super()._render_html(newline, indent, count)
    if hidden is None:
        del self._attrs["hidden"]
    else:
        self._attrs["hidden"] = hidden
    return html

# After: remove the method entirely (inherits from parent)
```

Since `_render_html` only manipulates `hidden`, removing it means the inherited implementation from `ElementWithChildren` will be used, which respects the actual `hidden` attribute value in `self._attrs` (which is not set for prerender=True).

### `webcompy/cli/_html.py`

No changes needed. The `prerender=False` path already explicitly sets `hidden=""` on the `_HtmlElement`.

### `webcompy/app/_root_component.py` — `_init_node()`

No changes needed. The existing loop at lines 134-136 removes non-id/non-webcompy attributes including `hidden`, which is still needed for the `prerender=False` case.

## Verification

- `prerender=True`: generated HTML has `#webcompy-app` without `hidden` → content visible beneath semi-transparent overlay
- `prerender=False`: generated HTML has `#webcompy-app` with `hidden=""` → content hidden until `_init_node()` removes it
- E2E tests: `test_loading_screen_removed` still passes (same removal timing)