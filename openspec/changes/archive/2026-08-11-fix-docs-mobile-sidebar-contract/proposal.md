# Proposal: fix-docs-mobile-sidebar-contract

## Why

The `docs-site-documents` spec currently claims that sibling navigation preserves the sidebar's mobile toggle state (spec.md "interactive state (open sections, mobile toggle) is preserved"), but `DocsLayout` intentionally closes the transient mobile overlay on every route change (`_close_mobile` on `router.after_route_change`). The `docs-e2e` spec and the E2E test both assert that the mobile sidebar closes after navigation. Three SHALL-level contracts thus disagree with each other and with the implementation.

## What Changes

- MODIFY the `docs-site-documents` requirement "The docs section shall use a nested-route shared layout": the layout instance and section-open state SHALL survive sibling navigation, while the transient mobile overlay SHALL close on navigation.
- Update the "Layout persists across sibling navigation" scenario's THEN clause to reflect that the mobile overlay closes while the layout and section state persist.
- No code change: the implementation already matches the reconciled contract.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: the nested-route shared layout requirement is clarified so the mobile-overlay-close behavior (already implemented and covered by docs-e2e) is consistent with the layout-preservation contract.

## Impact

- **Specs**: `docs-site-documents` (one MODIFIED requirement, scenario text updated).
- **Code**: none.
- **Tests**: none (docs-e2e already asserts the closing behavior).

## Known Issues Addressed

None.

## Non-goals

- No change to the implementation behavior (the mobile overlay continues to close on navigation).
- No change to `docs-e2e` requirements or E2E tests.
- No change to desktop sidebar behavior or section-collapse state handling.