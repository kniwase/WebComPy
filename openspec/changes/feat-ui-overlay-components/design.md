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

Modal, Drawer, and Dropdown are controlled by a reactive `open` value (Signal/Computed bool prop) plus an `on_close` callback prop that the component invokes on Escape/backdrop/outside-click dismissal; the parent owns the state. Rationale: declarative open state composes with application logic (guards, async confirmation) and matches the reactive prop model. Toast is inherently imperative (push at arbitrary moments from anywhere), so it ships as `use_toast()` (component-scoped composable returning `tuple[ToastPush, ToastState]` — a push function `ToastPush(message, variant, duration)` plus `ToastState` containing `toasts: Signal[list[ToastRecord]]` and `dismiss: Callable[[str], None]`; the queue state lives inside the composable). The host (`ToastHost`) receives `toasts`/`on_dismiss` from `ToastState` and renders through Teleport + per-item Transition with `on_leave_end` removal. Duration is in **seconds** (`float | None`, default `3.0`, `None` disables auto-dismiss). Alternative (everything composable) rejected for modal-like components: it splits rendering and state unnecessarily.

### D2: Focus trap via Tab interception

While a Modal/Drawer is open, keydown Tab/Shift+Tab at the trap boundary cycles focus among the overlay's focusable elements (queried at trap time, so dynamically shown controls are included); focus attempts leaving the overlay are redirected to the first/last focusable element. On open, focus moves to the overlay (first focusable element or the panel itself with `tabindex="-1"`). Rationale: Tab interception through a keydown listener on the overlay root is the standard, dependency-free technique; query-at-trap-time handles dynamic content.

### D3: Focus return on close

On open, the currently focused element (`document.activeElement`) is captured; on close, focus returns to it if still in the document. LIFO behavior for nested overlays falls out naturally from per-instance capture. This is specified because focus loss on dialog close is a common accessibility defect.

### D4: Escape and outside-click dismissal with strict listener cleanup

Escape dismissal uses a document-level keydown listener registered when the overlay opens and removed when it closes or unmounts; outside-click (Dropdown, optional backdrop-click for Modal) uses a document-level pointer/click listener with the same lifecycle. Registration and removal SHALL go through tracked handles so no listener outlives the overlay (event-handler leak invariant). The trigger element is excluded from "outside" for Dropdown so the trigger toggles rather than immediately re-closes.

### D5: Teleport + Transition composition pattern

Each overlay renders: `Teleport({"to": "body"}, Transition({"name": <component-default>}, lambda: overlay_content if open else None))`. Backdrop (Modal) is part of the teleported content. The default transition names (`webcompy-modal`, `webcompy-drawer`, `webcompy-dropdown`) have themed CSS in `primitives.css`; users can override classes or supply their own transition CSS. Because Teleport is anchor-only in SSR and the child is condition-driven, closed overlays contribute nothing to SSR output and open/close animates via the transition protocol.

### D6: Dropdown keyboard model

Dropdown uses the framework's **named slots** contract: `slots={"trigger": lambda: element}` supplies the trigger button and `slots={"default": lambda: items}` supplies the menu items as children (children-only API, no `items` prop; see spinner precedent and Radix/Headless UI pattern). The headless layer accepts a caller-created trigger element, merges `aria-expanded`/`aria-haspopup="menu"`/`aria-controls`/`data-state` onto it, and renders the menu items inside `<ul role="menu" data-state>` through Teleport + Transition (menu id is auto-generated for `aria-controls` — dangles while closed, accepted as v1 behavior). Items carry `role="menuitem"`; callers provide them as `create_element("li", {"role": "menuitem", "on_click": ...})` children — headless does not synthesize items. Keyboard: ArrowDown/ArrowUp move focus among items (wrapping, skipping `aria-disabled="true"`), Home/End jump, Escape closes and returns focus to the trigger, Enter/Space activates the focused item and closes. Type-ahead is not in v1 scope. This follows the WAI-ARIA menu button pattern.

### D7: Toast queue semantics

`use_toast()` returns `tuple[ToastPush, ToastState]`; each `push(message, variant, duration)` appends a toast (id, message, variant, duration in **seconds**; default `3.0`, `duration=None` disables auto-dismiss). The host receives `toasts`/`on_dismiss` from `ToastState` and renders the queue (oldest first, newest appended) inside a Teleport'd container that is an ARIA live region (`aria-live="polite"`, with `role="alert"` semantics for error variants). Each toast item is wrapped in its own `Transition` (host wraps many items, so a single host-level Transition is invalid) with `on_leave_end` performing the actual queue removal — dismissal marks `leaving=True` (`data-state="hidden"`) and the Transition leave runs before `on_leave_end` removes the record. `use_toast()` is provided from `webcompy.ui.composables` (logic-only), while `ToastHost`/`ToastItem` are in `webcompy.ui.headless`/`components`. Timers are scheduled via `TransitionPort.schedule_timeout` (available in browser; SSR/test environments degrade gracefully with no auto-dismiss — documented as a v1 limitation) and are cancelled on dismiss and on component destruction (no orphaned timers). The queue is unbounded in v1; capping is documented as future work.

### D8: data-state vocabularies

- Modal/Drawer panel: `data-state="open"` while mounted; closed overlays contribute no content (the generator-returning-None pattern means `data-state="closed"` does not appear in v1 — leave animation retains the last state). The `closed`/`hidden` values are reserved for user-managed markup.
- Dropdown trigger and menu: `data-state="open" | "closed"` likewise (menu absent while closed; trigger exposes the logical state).
- Toast items: `data-state="visible" | "hidden"` (`hidden` marks leaving before `on_leave_end` removes the record).
These follow the foundation contract and give user CSS stable state hooks. The requirement "expose `data-state="open"` while open" is always satisfied; transient leave states retain the last visible state in v1.

### D9: Transition `on_leave_end` extension

`Transition` gains an optional `on_leave_end: Callable[[], None] | None` prop — additive only, validated as callable. The callback fires exactly once at the end of a completed leave (both the normal `_finalize_leave` path and the immediate `_finalize_leave_now` path for `prefers-reduced-motion`/`enabled=False`). Toast per-item leave relies on this for actual queue removal; other overlays do not use it. Error handling routes exceptions to the boundary.

### D10: Component lifecycle hook ordering for overlay cleanup

`Context.__on_before_destroy` is changed from a single callable to a `list[Callable]` with LIFO insertion for composable helpers (`_register_before_destroy_chained` inserts at index 0). This guarantees overlay document listeners and toast timers are removed before user-registered `on_before_destroy` hooks, and multiple helpers (focus trap, escape, outside-click, timers) each register independently without overwriting. The public `on_before_destroy` API remains additive; `__get_lifecyclehooks__` exposes a combined wrapper that iterates the list.

### D11: Dropdown trigger activation stops event propagation

The headless Dropdown's trigger click handler (`_on_trigger_click`) SHALL stop propagation after toggling. Rationale (found by verification): the toggle mutates the `open` signal during the button's own handler; any application-level document `click` listener (e.g. a navbar "close all menus" handler) runs later in the same bubble phase and immediately re-closes the menu, so the dropdown can never open. The Dropdown's own outside-click exclusion (D4) already treats trigger clicks as "inside", so stopping propagation is behavior-neutral for the component itself and removes the dependence on document listeners running after an exclusion check. Other overlay components have no trigger element (they are opened by prop), so this applies to Dropdown only. The `stopPropagation` call is guarded (`hasattr`) because fake test events may not implement it.

### D12: Overlay DOM ids are derived from the per-instance transfer id

`generate_id(name)` is a hash of the component *name* — constant across instances — so the v1 overlays produced duplicate DOM ids whenever a page hosted two or more of the same overlay (`id="webcompy-dropdown-trigger-ad973c25"` twice on the docs navbar), silently breaking outside-click target resolution, keyboard focus return, Escape lookups, and `aria-controls` for the second and later instances. Dropdown, Modal, and Drawer SHALL derive their generated DOM ids (trigger, menu, panel, backdrop) from the component context's transfer id (`context._transfer_id`, exposed via a `transfer_id` property), sanitized for use in an HTML id (the `#` ordinal separator replaced with `-`). The transfer id is `{name-hash}#{ordinal}` with the ordinal assigned by the app render context's per-name counter (`_next_transfer_id`), which is the same mechanism the hydration value transfer relies on for server/browser identity — so ids are unique per instance within a page and identical between SSR output and the hydrated client tree. Environments without an app render context (bare test renderer) degrade to the name hash (ids may collide there), matching the framework-wide `transfer_id or generate_id(name)` fallback; uniqueness requirements are specified and tested where an app context is present. Toast does not generate DOM ids and is unaffected.

### D13: docs_app navbar consumes the Dropdown component without the old measurement layer

The reworked navbar drops the hand-rolled positioning workaround (toggle-rect measurement into `--nav-dropdown-top`/`--nav-dropdown-right`), which left the scoped styles referencing undefined custom properties. The navbar integration is fixed by design instead of by measurement:

- Trigger styling: navbar scoped styles target both `.navbar-list a` and `.navbar-list button` (the Dropdown trigger is a `<button>`), with a button reset (background, border, text alignment, full-width in the mobile list) so no browser-default button styling leaks.
- Menu positioning (desktop): the teleported menu is `position: fixed`, anchored to the top of the viewport just below the navbar and right-aligned to the page gutter. Per-toggle measurement is intentionally not reinstated: the two menus are mutually exclusive (opening one closes the other via each Dropdown's outside-click close), so a single shared anchor is visually equivalent without measurement code.
- Menu positioning (mobile): the menu is `position: static` inside the expanded mobile panel — an in-flow accordion section rather than an overlay.
- Menu semantics: menu links carry `role="menuitem"` so the headless keyboard navigation (`[role="menuitem"]` lookup) operates on them.

## Risks / Trade-offs

- **Focus trap edge cases**: elements becoming focusable/unfocusable while open are handled by query-at-trap-time; if the overlay contains no focusable element, the panel itself receives focus (`tabindex="-1"`). Specified as required behavior. `AUDIO`/`VIDEO` are considered focusable only when `controls` is present; otherwise they are skipped.
- **Outside-click vs trigger toggle race**: click events bubble — the trigger exclusion (D4) prevents the toggle-then-immediately-close bug; ordering is specified.
- **Transition interruption**: rapid open/close toggling relies on the Transition element's interruption semantics (leaving node finalized immediately when re-entering); overlay components add no extra state beyond `open`.
- **Nested overlays**: LIFO focus return works for typical nesting; pathological interleaving is out of scope (documented).
- **Toast timer leaks**: timers tracked per toast and cleared on dismiss/destroy; specified as a requirement, tested.
- **Initial-open macro-task guard**: when `open=True` on mount, listener setup is deferred via `HostPort.schedule_macro_task`; a `destroyed` guard prevents registration after unmount racing the task.
- **Trigger propagation change (D11)**: stopping propagation on trigger clicks means host document-level listeners no longer observe trigger clicks; hosts relying on observing every click must instead rely on the Dropdown's `on_close`/`open` contract. Accepted: observing trigger clicks from outside contradicts the component's own toggle ownership.
- **Transfer-id-derived DOM ids (D12)**: ids depend on the app render context's ordinal counter; renders without an app context (bare test renderer) fall back to the name hash and may collide — the same fallback every hydration transfer id has. Renders inside Suspense probing skip ordinals (existing `_transfer_probe_depth` behavior), matching transfer-id semantics.
