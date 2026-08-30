# Proposal: feat-ui-overlay-components

## Why

Overlay UI — modals, drawers, dropdown menus, toasts — is ubiquitous in real applications and is exactly the class of UI that requires the Teleport and Transition primitives: overlay content must render at the document root to escape clipping and stacking contexts, and open/close state should animate. With those primitives in place, WebComPy can now ship first-party overlay components. Per the UI primitives foundation, each component arrives as a headless variant (behavior, ARIA, keyboard, focus management — the parts users routinely get wrong) plus a themed variant (token-based defaults), serving both design-control and zero-effort users.

## What Changes

- Four overlay component pairs under the two-layer architecture (`webcompy.ui.headless` / `webcompy.ui.components`, themed re-exported at `webcompy.ui`):
  - **Modal/Dialog**: `role="dialog"` + `aria-modal`, focus trap (Tab cycling within the dialog), Escape to close, optional backdrop-click close, focus returned to the trigger on close, rendered through Teleport (body) with Transition open/close animation. Reactive `open` prop plus `on_close` callback.
  - **Drawer**: sliding panel from a screen edge (left/right/top/bottom prop), sharing the modal accessibility contract (focus trap, Escape, focus return), Teleport + Transition.
  - **Dropdown/Menu**: trigger button (`aria-expanded`, `aria-haspopup`, `aria-controls`) plus a menu (`role="menu"`/`menuitem` or the disclosure pattern for simple lists), arrow-key navigation, Home/End, Escape, outside-click close, Teleport + Transition.
  - **Toast**: `use_toast()` composable for imperative push (message, variant, optional duration) plus a Teleport'd host rendering the queue in an ARIA live region; per-toast auto-dismiss timers and manual dismiss.
- Shared overlay utilities: focus-trap helper, outside-click detection, document-level listener lifecycle management (registered listeners are always removed on close/unmount).
- All components follow the headless contract: `data-state` vocabularies (`open`/`closed` for modal/drawer/dropdown; `visible`/`hidden` for toasts), structural-only CSS in the headless layer, class pass-through; themed styles in `primitives.css` consuming design tokens.

## Capabilities

### New Capabilities

- `ui-overlay`: First-party overlay components — Modal, Drawer, Dropdown, Toast — as headless/themed pairs: dialog accessibility contract (focus trap, Escape, focus return), menu keyboard navigation, toast queue with live region and auto-dismiss, Teleport/Transition integration, and overlay-specific `data-state` vocabularies.

### Modified Capabilities

(none)

## Impact

- **Code**: new headless/themed components in `webcompy/ui/headless/` and `webcompy/ui/components/`; shared overlay utilities; themed rules appended to `_styles/primitives.css`; `use_toast` composable; unit and E2E tests.
- **APIs**: additive only (`Modal`, `Drawer`, `Dropdown`, `Toast` host, `use_toast`). No breaking changes.
- **Dependencies**: requires the `teleport` and `transition` capabilities and the `ui-primitives` foundation (implemented by preceding changes).
- **Docs**: docs_app demo pages for each overlay component; docs_app's navbar dropdown is reworked onto the Dropdown component (dogfooding, replacing the hand-rolled positioning workaround).

## Known Issues Addressed

(none)

## Non-goals

- Tooltip and Popover (positioning-engine components — planned follow-up change).
- Nested modal focus-scope stacking beyond single-level correctness (nested modals work but focus return follows a simple LIFO; advanced multi-scope management is out of scope).
- Toast persistence across navigations or page reloads.
- Portal target customization beyond Teleport's `to` (components default to `body`).
- Drag-to-reposition or resizable overlays.
