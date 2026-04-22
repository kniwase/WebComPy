# Proposal: Remove hidden attribute from prerendered app root

## Problem

When the CLI generates static HTML with `prerender=True`, the `#webcompy-app` div includes a `hidden` attribute. This means the browser renders the page with the app content invisible, and the semi-transparent loading screen overlay (`rgba(0, 0, 0, 0.5)`) sits on top of nothing visible.

The user sees:
1. A semi-transparent dark overlay with a spinner — but no content beneath
2. After PyScript initializes, `hidden` is removed (content briefly visible behind the overlay)
3. Then the loading overlay is removed

The semi-transparent loading screen added in `feat-hydration-partial` is rendered useless because there is nothing to see through it.

## Root Cause

`AppRootComponent._render_html()` unconditionally sets `hidden=True` on the app root div before generating HTML. It does not distinguish between prerender and non-prerender modes.

## Proposed Fix

Remove the forced `hidden` attribute injection from `_render_html()`. The `generate_html()` function already correctly handles the distinction:
- `prerender=True`: uses `app._root` (no `hidden` needed — content should be visible)
- `prerender=False`: creates a `_HtmlElement("div", {"id": "webcompy-app", "hidden": ""})` (explicitly hidden)

## Non-goals

- Changing the loading screen removal timing
- Changing the `_init_node()` attribute cleanup logic (it still needs to remove `hidden` for the `prerender=False` case)
- Refactoring the root component rendering pipeline

## Known Issues Addressed

None (this is a regression from the semi-transparent loading screen change).

## Affected Specs

- `app-lifecycle`: prerendered app root SHALL NOT include `hidden` attribute in generated HTML
- `cli`: prerendered output SHALL produce visible app content beneath the loading overlay