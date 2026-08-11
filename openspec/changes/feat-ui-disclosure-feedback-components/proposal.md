# Proposal: feat-ui-disclosure-feedback-components

## Why

The second component family for the first-party UI toolkit covers disclosure and feedback patterns: tabs and collapsible sections (showing/hiding content regions), and status indicators (alerts, progress, badges, skeletons, cards). These appear in nearly every application, are cheap to get wrong accessibly (tab roles, expanded states, progressbar values, live announcements), and — under WebComPy's "no JavaScript" promise — cannot be sourced from a JS ecosystem library. Per the foundation architecture, each ships as a headless component (behavior, ARIA, keyboard) plus a themed component (token-based defaults). Tabs and Collapse additionally consume the Transition capability for animated panel switching and expand/collapse.

## What Changes

- Seven component pairs under the two-layer architecture (`webcompy.ui.headless` / `webcompy.ui.components`, themed re-exported at `webcompy.ui`):
  - **Tabs**: `role="tablist"`/`tab`/`tabpanel` with `aria-selected` and `aria-controls`, arrow-key navigation (Left/Right with wrapping, Home/End), automatic activation, optional Transition on panel switch, reactive active-tab state.
  - **Collapse**: disclosure trigger (`aria-expanded`, `aria-controls`) plus collapsible content with animated expand/collapse via Transition; **Accordion** composition of Collapse items with optional single-open policy.
  - **Alert**: inline feedback with variant semantics (info/success/warning/error), `role="alert"` for assertive variants and `role="status"` for polite ones, optional dismiss action.
  - **Progress**: `role="progressbar"` with `aria-valuenow`/`aria-valuemin`/`aria-valuemax` for determinate state and an indeterminate mode with correct ARIA.
  - **Badge**: compact status label with variants.
  - **Skeleton**: loading placeholder marked decorative to assistive technology, with container-level labeling guidance.
  - **Card**: structural container (header/body/footer regions) promoted from the docs_app ad-hoc implementation.
- Themed styles for all seven appended to `_styles/primitives.css` consuming design tokens; Collapse/Tabs use default transition class sets.

## Capabilities

### New Capabilities

- `ui-disclosure`: First-party disclosure and feedback components — Tabs, Collapse/Accordion, Alert, Progress, Badge, Skeleton, Card — as headless/themed pairs with their accessibility contracts, keyboard behavior, Transition integration for disclosure animation, and `data-state` vocabularies.

### Modified Capabilities

(none)

## Impact

- **Code**: new headless/themed components in `webcompy/ui/headless/` and `webcompy/ui/components/`; themed rules appended to `_styles/primitives.css`; unit and E2E tests.
- **APIs**: additive only. No breaking changes.
- **Dependencies**: requires the `transition` capability and the `ui-primitives` foundation (preceding changes). No Teleport dependency.
- **Docs**: docs_app demo page for the family; docs_app's ad-hoc Card replaced by the primitive (dogfooding).

## Known Issues Addressed

(none)

## Non-goals

- Vertical tab orientation and tab reordering/drag — horizontal tabs only in v1.
- Nested accordions beyond one level (documented limitation).
- Alert queues/toasts (covered by the Toast component in the overlay change).
- Skeleton shape variants beyond rectangle/line/circle basics.
- Automatic content lazy-loading tied to tab/collapse state (state is exposed; loading strategies belong to application code).
