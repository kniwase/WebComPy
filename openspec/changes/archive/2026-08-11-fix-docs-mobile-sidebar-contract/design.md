# Design: fix-docs-mobile-sidebar-contract

## Context

`DocsLayout` (`docs_app/layout/document.py`) renders a sticky desktop sidebar and, below the mobile breakpoint, a sidebar hidden behind a toggle button. The toggle state is a `use_state` (`mobile_open`). On navigation the layout registers `_close_mobile` on `router.after_route_change`, which sets `mobile_open = False` so the transient overlay closes after the user picks a page.

The `docs-site-documents` spec's "Layout persists across sibling navigation" scenario was written to capture the RouterView level-reuse guarantee (the layout instance and its state survive sibling navigation) but overreached by listing the mobile toggle as preserved state. The `docs-e2e` spec and `e2e/docs/test_installation.py::test_mobile_sidebar_toggle_and_close_after_navigation` already assert the opposite: the sidebar closes after navigation.

## Goals / Non-Goals

**Goals:**

- Reconcile the specs so all SHALL-level contracts agree with the implementation.
- Keep the implemented behavior: layout instance and section-open state survive navigation; the transient mobile overlay closes on navigation.

**Non-Goals:**

- No behavior or code change.
- No change to `docs-e2e` or E2E tests.

## Decisions

### 1. Keep the implementation; fix the `docs-site-documents` spec

The implementation is the intended UX: after selecting a page from a mobile drawer, the drawer closes so the destination is visible. This matches the archived design.md note ("a `router.after_route_change` hook closes the mobile sidebar on navigation") and the docs-e2e requirement. The contradiction is confined to one scenario's THEN clause, so the spec is corrected rather than the code.

### 2. MODIFY the existing requirement rather than add a new one

The behavior being specified (layout persistence) is unchanged; only the mobile-overlay detail is corrected. A MODIFIED requirement keeps the delta minimal and preserves the requirement's identity.

## Risks / Trade-offs

- [Another reviewer reads the scenario as still contradictory] → The requirement body and scenario are both rewritten to state the close-on-navigation rule explicitly, so no ambiguity remains.
- [The archived change delta is not updated] → Archived artifacts are historical records; the new change's delta is the source that syncs the current main spec. No archived edit is made.

## Migration Plan

Single branch, spec-only change. Rollback = revert.

## Open Questions

None.