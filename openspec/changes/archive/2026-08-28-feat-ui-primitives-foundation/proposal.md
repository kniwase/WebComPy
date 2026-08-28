# Proposal: feat-ui-primitives-foundation

## Why

WebComPy ships the skeleton of a UI toolkit — design tokens (`tokens.css` with light/dark palettes, spacing, typography), a DI-managed theme system, and auto-served stylesheets at `/_webcompy-ui/` — but no general-purpose components: the only first-party component is `CodeBlock`, while reusable pieces (buttons, cards, dropdowns) live ad hoc inside docs_app. Real applications need accessible, working primitives, and WebComPy's "no JavaScript" promise means users cannot adopt a JS component library instead; the framework must provide them. Two user profiles exist — those who want working UI with zero effort and those who want full design control — so the foundation must define a two-layer architecture (headless logic core + token-themed skin) that serves both, before the overlay/disclosure/form component changes build on it.

## What Changes

- Two-layer component architecture in `webcompy.ui`:
  - `webcompy.ui.headless` — behavior-only components: state management, ARIA roles/attributes, keyboard interaction, and focus management. No visual styling: emitted classes are structural only (positioning/display/visibility), and component state is exposed on the DOM via `data-state` attributes so user CSS can react to it. Every headless component accepts class pass-through props for user styling.
  - `webcompy.ui.components` — themed components composed from the headless layer, styled with the existing design tokens and overridable through class props. Themed components are re-exported from the `webcompy.ui` top level as the convenient default path.
- Component CSS delivery: themed primitive styles ship as a new stylesheet imported by the existing `/_webcompy-ui/index.css` cascade (inside `@layer components`), consistent with the token/reset/components layering already in place.
- First component pair proving the architecture: `Spinner` (headless: `role="status"`, live-region labeling; themed: token-based animation).
- Component authoring follows the established function-style pattern (`@define_component` + `ComponentContext[Props]` with `TypedDict` props).

## Capabilities

### New Capabilities

- `ui-primitives`: The two-layer first-party UI component architecture — headless contract (logic/a11y/state via `data-state`, structural-only CSS, class pass-through), themed layer contract (token-based defaults, class overrides), namespacing and exports, stylesheet delivery through `/_webcompy-ui/`, and the initial Spinner component pair.

### Modified Capabilities

(none)

## Impact

- **Code**: new `webcompy/ui/headless/` and `webcompy/ui/components/` packages; new primitive stylesheet wired into `webcompy/ui/_styles/index.css`; public exports; unit tests.
- **APIs**: additive only (`webcompy.ui.headless.Spinner`, `webcompy.ui.Spinner`, etc.). No breaking changes to `webcompy.ui.theme` or `webcompy.ui.code_block`.
- **Dependencies**: none.
- **Downstream**: foundation for the overlay components (Modal, Toast, Dropdown, Drawer), disclosure/feedback components (Tabs, Collapse, Alert, Progress, Badge, Skeleton, Card), and form controls changes, which will add component pairs under the same architecture.
- **Docs**: docs_app section describing the two-layer model with the Spinner example; docs_app adopts the themed Spinner where loading indicators are used.

## Known Issues Addressed

(none)

## Non-goals

- The overlay, disclosure/feedback, and form-control components themselves — separate changes building on this foundation.
- A full design system (opinionated layouts, navbar/page scaffolding) — layout-level composition stays application-level.
- Headless components emitting visual styles (colors, spacing, typography) — forbidden by the headless contract.
- Server-side component registries or theming beyond the existing theme system.
- Component-level i18n (labels/aria text defaults) — components accept explicit label props; i18n integration comes with the i18n change.
