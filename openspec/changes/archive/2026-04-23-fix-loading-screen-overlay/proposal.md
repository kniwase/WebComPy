## Why

The loading screen overlay in generated HTML is visually broken when users include popular CSS frameworks like Bootstrap. The inner overlay `<div>` uses the generic class name `container`, which conflicts with Bootstrap's `.container` that adds `max-width` and `margin-right: auto`, cutting the overlay short and leaving the right side of the page uncovered. The loading screen also injects a global `body` style rule that overrides the page's own body styles. Generic class names (`container`, `loader`) are fragile to collision with any user-provided CSS.

## What Changes

- Refactor `_Loadscreen` in `webcompy/cli/_html.py` to make `#webcompy-loading` itself the overlay, removing the need for an intermediate wrapper `<div>`.
- Replace generic class names (`container`, `loader`) with framework-prefixed names (`wc-loader`) to prevent collision with user stylesheets.
- Remove the global `body` CSS selector from the loading screen inline `<style>` block; the overlay will be sized via `position: fixed; inset: 0` on `#webcompy-loading` itself, removing interference with page-level body styling.
- Verify E2E tests that check `#webcompy-loading` continue to pass (no selector changes required, only structural change inside the div).
- Format the generated inline style string for readability (optional — keep consistent with existing style generation).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None — this is an internal HTML/CSS structure fix that does not change spec-level requirements.

## Impact

- `webcompy/cli/_html.py` — `_Loadscreen` class (DOM structure and inline styles)
- `tests/e2e/test_bootstrap.py` — no expected breakage (still queries `#webcompy-loading` by ID)
- Generated `index.html` — slight change in the `<div id="webcompy-loading">` subtree (no more `.container` div wrapper, `.loader` renamed to `.wc-loader`, `body` rules removed from inline `<style>`)
- No public API or CLI behavior changes

## Non-goals

- Not redesigning the spinner visual appearance (same colors, same animation)
- Not changing the loading screen removal lifecycle or timing
- Not making loading screen appearance configurable
- Not changing behavior of prerender, `hidden` attribute, or PyScript bootstrap

## Known Issues Addressed

- None.
