# Design: feat-ui-overlay-components

## Context

This change builds directly on three preceding capabilities: `teleport` (overlay content mounts under `body`, anchor-only SSR), `transition` (open/close animation via the Vue-compatible class protocol), and `ui-primitives` (two-layer architecture, headless contract, `data-state`, class pass-through, `primitives.css` delivery). The overlay family is the primary consumer of all three.

Grounded facts (verified in codebase):

- Component model: function-style `@define_component` with `TypedDict` props; reactive prop values flow as `Computed`/`Signal` and re-render the component subtree (established across `components/` and docs_app usage).
- Event listeners on elements are wired through the element system and destroyed with the element (event-handler leak invariant); document-level listeners needed for Escape/outside-click must be registered through the DOM port and removed explicitly on close/unmount.
- Focus APIs (`document.activeElement`, element `focus()`) are reachable through the DOM port surface in the browser.
- SSR renders overlays closed: with anchor-only Teleport and condition-driven children, a closed overlay contributes nothing to SSR HTML, which is the desired behavior.

## Goals / Non-Goals

**Goals:**

- Four headless/themed overlay pairs (Modal, Drawer, Dropdown, Toast) with correct accessibility behavior implemented by the framework.
- Shared overlay utilities (focus trap, outside click, listener lifecycle) used uniformly.
- Teleport + Transition integration as the standard overlay rendering pattern.

**Non-Goals:**

- Tooltips/Popovers (positioning engine), advanced multi-scope focus management, toast persistence, drag/resize (see proposal Non-goals).

## Decisions

### D1: API model — declarative `open` prop for modal-like components, composable for toasts

Modal, Drawer, and Dropdown are controlled by a reactive `open` value (Signal/Computed bool prop) plus an `on_close` callback prop that the component invokes on Escape/backdrop/outside-click dismissal; the parent owns the state. Rationale: declarative open state composes with application logic (guards, async confirmation) and matches the reactive prop model. Toast is inherently imperative (push at arbitrary moments from anywhere), so it ships as `use_toast()` (component-scoped composable returning a push function with message/variant/duration arguments) plus a host component rendering the queue; the queue state lives inside the composable. Alternative (everything composable) rejected for modal-like components: it splits rendering and state unnecessarily.

### D2: Focus trap via Tab interception

While a Modal/Drawer is open, keydown Tab/Shift+Tab at the trap boundary cycles focus among the overlay's focusable elements (queried at trap time, so dynamically shown controls are included); focus attempts leaving the overlay are redirected to the first/last focusable element. On open, focus moves to the overlay (first focusable element or the panel itself with `tabindex="-1"`). Rationale: Tab interception through a keydown listener on the overlay root is the standard, dependency-free technique; query-at-trap-time handles dynamic content.

### D3: Focus return on close

On open, the currently focused element (`document.activeElement`) is captured; on close, focus returns to it if still in the document. LIFO behavior for nested overlays falls out naturally from per-instance capture. This is specified because focus loss on dialog close is a common accessibility defect.

### D4: Escape and outside-click dismissal with strict listener cleanup

Escape dismissal uses a document-level keydown listener registered when the overlay opens and removed when it closes or unmounts; outside-click (Dropdown, optional backdrop-click for Modal) uses a document-level pointer/click listener with the same lifecycle. Registration and removal SHALL go through tracked handles so no listener outlives the overlay (event-handler leak invariant). The trigger element is excluded from "outside" for Dropdown so the trigger toggles rather than immediately re-closes.

### D5: Teleport + Transition composition pattern

Each overlay renders: `Teleport({"to": "body"}, Transition({"name": <component-default>}, lambda: overlay_content if open else None))`. Backdrop (Modal) is part of the teleported content. The default transition names (`webcompy-modal`, `webcompy-drawer`, `webcompy-dropdown`) have themed CSS in `primitives.css`; users can override classes or supply their own transition CSS. Because Teleport is anchor-only in SSR and the child is condition-driven, closed overlays contribute nothing to SSR output and open/close animates via the transition protocol.

### D6: Dropdown keyboard model

The trigger is a real button with `aria-expanded`, `aria-haspopup="menu"`, `aria-controls`. The menu uses `role="menu"` with `role="menuitem"` items (or `role="listbox"`/links for navigation-style menus — the component supports a simple menuitem model in v1). Keyboard: ArrowDown/ArrowUp move focus among items (wrapping), Home/End jump, Escape closes and returns focus to the trigger, Enter/Space activates the focused item and closes. Type-ahead is not in v1 scope. This follows the WAI-ARIA menu button pattern.

### D7: Toast queue semantics

`use_toast()` returns a push function; each call appends a toast (id, message, variant, duration). The host renders the queue (oldest first, newest appended) inside a Teleport'd container that is an ARIA live region (`aria-live="polite"`, with `role="alert"` semantics for error variants). Each toast auto-dismisses after its duration (default provided, per-toast override, `duration=None` disables auto-dismiss) and has a manual dismiss button. Timers are cancelled on dismiss and on component destruction (no orphaned timers). The queue is unbounded in v1; capping is documented as future work.

### D8: data-state vocabularies

- Modal/Drawer root: `data-state="open" | "closed"` (closed state exists only transiently during leave animation).
- Dropdown trigger: `data-state="open" | "closed"`; menu likewise.
- Toast items: `data-state="visible" | "hidden"` (hidden transiently during leave).
These follow the foundation contract and give user CSS stable state hooks.

## Risks / Trade-offs

- **Focus trap edge cases**: elements becoming focusable/unfocusable while open are handled by query-at-trap-time; if the overlay contains no focusable element, the panel itself receives focus (`tabindex="-1"`). Specified as required behavior.
- **Outside-click vs trigger toggle race**: click events bubble — the trigger exclusion (D4) prevents the toggle-then-immediately-close bug; ordering is specified.
- **Transition interruption**: rapid open/close toggling relies on the Transition element's interruption semantics (leaving node finalized immediately when re-entering); overlay components add no extra state beyond `open`.
- **Nested overlays**: LIFO focus return works for typical nesting; pathological interleaving is out of scope (documented).
- **Toast timer leaks**: timers tracked per toast and cleared on dismiss/destroy; specified as a requirement, tested.
