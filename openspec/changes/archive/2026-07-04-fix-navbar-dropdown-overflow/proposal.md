## Why

The docs_app PC site navbar dropdown menu (e.g., "Demos") overflows to the right of the viewport when opened, breaking the page layout. The root cause is that `.navbar-dropdown` uses `left: 0` for absolute positioning, but the parent dropdown items are located on the right side of the navbar layout, causing the dropdown to extend beyond the viewport boundary.

## What Changes

- Change `.navbar-dropdown` positioning from `left: 0` to `right: 0` in `docs_app/components/navigation.py`
- This is a one-line CSS fix — no structural or behavioral changes
- No breaking changes

## Capabilities

### New Capabilities
- `navbar-dropdown-overflow`: Fix the navbar dropdown positioning to prevent horizontal viewport overflow on desktop

### Modified Capabilities
- *(none — existing spec-level behavior is unchanged, only a CSS positioning fix)*

## Impact

- **File changed**: `docs_app/components/navigation.py` (scoped style CSS)
- **Scope**: Docs_app layout only — no framework code, no API changes, no dependency changes
- **Visual**: Dropdown menus will be right-aligned to their parent toggle instead of left-aligned. For items in `.navbar-right` (all current nav items), the dropdown will extend leftward, staying within the viewport.
