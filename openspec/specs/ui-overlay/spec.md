# ui-overlay Specification

## Purpose

TBD - created by archiving change feat-ui-overlay-components. Update Purpose after archive.

## Requirements

### Requirement: Modal shall implement the dialog accessibility contract

The headless Modal SHALL render `role="dialog"` with `aria-modal="true"` and an accessible name (labelled-by prop wiring or `aria-label`). While open, focus SHALL be trapped: Tab and Shift+Tab at the boundary SHALL cycle among the overlay's focusable elements, queried at trap time so dynamic content is included; if no focusable element exists, the panel itself SHALL receive focus. On open, focus SHALL move into the dialog. On close, focus SHALL return to the element focused before the modal opened, if still in the document. The Modal SHALL render through Teleport to the document body wrapped in a Transition, and SHALL expose `data-state="open"` while open.

#### Scenario: Focus is trapped while open

- **WHEN** a Modal is open and the user presses Tab on the last focusable element inside it
- **THEN** focus SHALL move to the first focusable element inside the Modal
- **AND** focus SHALL never reach content behind the Modal while it is open

#### Scenario: Focus returns to the trigger on close

- **WHEN** a button opens a Modal and the Modal is subsequently closed
- **THEN** focus SHALL return to that button

### Requirement: Modal shall support Escape and backdrop dismissal through the open/close contract

The Modal SHALL accept a reactive `open` value and an `on_close` callback. Pressing Escape while open SHALL invoke `on_close`. Backdrop-click dismissal SHALL invoke `on_close` and SHALL be disable-able by prop. The document-level listeners used for these dismissals SHALL be registered on open and removed on close or unmount; no listener SHALL outlive the Modal.

#### Scenario: Escape closes the modal

- **WHEN** a Modal is open and the user presses Escape
- **THEN** the `on_close` callback SHALL be invoked
- **AND** after closing, the Escape listener SHALL be removed from the document

### Requirement: Drawer shall provide an edge panel with the modal accessibility contract

The headless Drawer SHALL render a panel sliding from a configurable edge (left, right, top, bottom) and SHALL implement the same accessibility contract as Modal (focus trap, focus-in on open, focus return on close, Escape dismissal, Teleport + Transition rendering, `data-state` exposure). The edge SHALL be selectable by prop and reflected for styling.

#### Scenario: Drawer from the right edge

- **WHEN** a Drawer configured for the right edge opens
- **THEN** the panel SHALL render at the right edge of the viewport via Teleport
- **AND** focus SHALL move into the panel and be trapped as with Modal

### Requirement: Dropdown shall implement the menu button pattern

The headless Dropdown SHALL render a trigger button with `aria-expanded`, `aria-haspopup="menu"`, and `aria-controls` referencing the menu, plus a menu with `role="menu"` whose items carry `role="menuitem"`. Activating the trigger SHALL toggle the menu; the menu SHALL render through Teleport + Transition and expose `data-state` on both trigger and menu. Keyboard behavior while open: ArrowDown/ArrowUp SHALL move focus among items with wrapping, Home/End SHALL jump to first/last, Escape SHALL close and return focus to the trigger, and Enter/Space SHALL activate the focused item and close.

#### Scenario: Arrow key navigation

- **WHEN** a Dropdown is open with three items and focus is on the first item
- **THEN** ArrowDown SHALL move focus to the second item, and ArrowDown from the last item SHALL wrap to the first

#### Scenario: Escape returns focus to the trigger

- **WHEN** a Dropdown is open and the user presses Escape
- **THEN** the menu SHALL close and focus SHALL return to the trigger button

### Requirement: Dropdown shall close on outside interaction without toggle races

A document-level listener SHALL close the Dropdown when the user clicks outside it; the trigger element SHALL be excluded from outside detection so that clicking the trigger toggles rather than immediately re-closes. The listener SHALL be registered on open and removed on close or unmount.

#### Scenario: Outside click closes the menu

- **WHEN** a Dropdown is open and the user clicks an element that is neither the trigger nor inside the menu
- **THEN** the menu SHALL close

#### Scenario: Trigger click toggles without race

- **WHEN** a Dropdown is open and the user clicks the trigger
- **THEN** the menu SHALL close exactly once (toggle), not close-and-reopen

### Requirement: Toast shall provide an imperative queue rendered in a live region

`use_toast()` SHALL be a component-scoped composable returning a tuple of a push function and the queue state (`push(message, variant, duration)` and `ToastState` containing `toasts` and `dismiss`). Duration SHALL be in seconds (`float | None`, default `3.0`, `None` disables auto-dismiss); `use_toast()` is provided from `webcompy.ui.composables` while the host is provided from `webcompy.ui.headless`/`components`. Pushed toasts SHALL be appended to a queue rendered by a Toast host through Teleport, inside an ARIA live region (`aria-live="polite"`; error variants SHALL use alert semantics). Each toast SHALL expose a manual dismiss action and `data-state="visible"` while shown; dismissal SHALL mark `hidden` before the leave handling (via `Transition.on_leave_end`) removes the record. The composable SHALL be torn down with its component. Dropdown items SHALL be supplied as children via the framework's named slots (`slots={"trigger": ..., "default": ...}`), not via an `items` prop.

#### Scenario: Push and render

- **WHEN** a component calls the push function with the message "Saved"
- **THEN** a toast with that message SHALL appear in the host's live region
- **AND** screen-reader announcements SHALL follow the live region's politeness

### Requirement: Toast auto-dismiss timers shall be tracked and cleaned up

Each toast SHALL auto-dismiss after its duration in seconds (default `3.0` unless overridden; `None` disables auto-dismiss). Dismissal SHALL run the leave handling (marking `hidden` and running `Transition.on_leave_end`) before removal. Timers SHALL be cancelled on manual dismiss, on auto-dismiss, and on component destruction; no timer SHALL fire after its toast was removed or its component destroyed.

#### Scenario: Auto-dismiss after duration

- **WHEN** a toast is pushed with a 2-second duration
- **THEN** the toast SHALL be dismissed approximately 2 seconds later

#### Scenario: Timers do not outlive the component

- **WHEN** a component with pending toast timers is destroyed
- **THEN** all pending timers SHALL be cancelled and SHALL NOT dismiss or error afterwards

### Requirement: Overlay components shall ship as headless/themed pairs per the foundation contract

Each overlay component (Modal, Drawer, Dropdown, Toast host and items) SHALL exist as a headless component honoring the headless contract (behavior-only, `data-state`, class pass-through) and a themed component composing it with token-based defaults in the primitives stylesheet, re-exported at the `webcompy.ui` top level. Default open/close transition classes SHALL be provided by the themed layer; users SHALL be able to override them.

#### Scenario: Themed Modal uses Teleport, Transition, and tokens

- **WHEN** a themed Modal opens
- **THEN** its content SHALL render under the document body via Teleport with the default transition classes applied during open/close
- **AND** its themed styles SHALL consume design tokens
