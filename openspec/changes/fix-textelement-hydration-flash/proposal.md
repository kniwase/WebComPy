## Why

When a server-rendered WebComPy page hydrates in the browser, `TextElement` always removes the existing pre-rendered `#text` node and creates a new one, causing a visible flash (text disappears then reappears). `ElementBase` and `NewLine` correctly reuse pre-rendered nodes, but `TextElement` was implemented with the opposite logic — deleting instead of adopting.

## What Changes

- Fix `TextElement._init_node()` to reuse the existing pre-rendered `#text` node when it matches, instead of removing it and creating a new one
- Set `self._mounted = True` on hydration, consistent with `ElementBase` and `NewLine`

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `elements`: Extend the hydration requirement to explicitly cover `#text` nodes — pre-rendered text nodes shall be reused rather than replaced

## Known Issues Addressed

- "TextElement does not hydrate pre-rendered text nodes (always creates new text node)" — from the Element System known issues list

## Non-goals

- Adding content-diffing logic for text nodes (unnecessary since SSR output and initial signal values are identical)
- Changing how `ElementBase` or `NewLine` hydrate (they work correctly)
- Modifying `MultiLineTextElement` directly (it inherits `TextElement` behavior, so fixing `TextElement` resolves it implicitly)

## Impact

- `webcompy/elements/types/_text.py` — `TextElement._init_node()` logic change
- Existing tests for `TextElement` hydration may need updating