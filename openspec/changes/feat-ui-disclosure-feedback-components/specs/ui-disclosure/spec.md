# UI Disclosure & Feedback Components Specification (delta)

## ADDED Requirements

### Requirement: Tabs shall implement the tablist accessibility contract

The headless Tabs SHALL render `role="tablist"` containing `role="tab"` elements, each with `aria-selected` and `aria-controls` referencing its `role="tabpanel"`. The active tab state SHALL be reactive (prop-driven) with a change callback. All panels SHALL be rendered; inactive panels SHALL stay mounted and be hidden via the boolean `hidden` attribute, preserving their internal state across switches. Tabs and panels SHALL expose `data-state="active" | "inactive"` on tab and panel elements.

#### Scenario: Panel state survives tab switches

- **WHEN** a user switches from tab A (containing a form input with entered text) to tab B and back to tab A
- **THEN** the input SHALL retain the entered text because panel A remained rendered (hidden) while inactive

### Requirement: Tabs shall provide arrow-key navigation with automatic activation

While focus is within the tablist, Left/Right arrows SHALL move focus to the previous/next tab with wrapping and SHALL activate it (automatic activation); Home/End SHALL jump to the first/last tab. Activation SHALL update the reactive active state and the visible panel. The active tab SHALL carry `tabindex="0"` and inactive tabs `tabindex="-1"` (roving tabindex).

#### Scenario: Arrow navigation wraps and activates

- **WHEN** focus is on the last of three tabs and the user presses Right Arrow
- **THEN** focus SHALL move to the first tab and the first tab SHALL become active

### Requirement: Tabs and Collapse shall generate per-instance hydration-stable DOM ids

The Tabs and Collapse SHALL derive their generated DOM ids (tablist, tab, panel, trigger, content) from the component instance's hydration-stable transfer id (sanitized for HTML id use), not from a name-only hash. Ids SHALL be unique among the instances rendered on a page and identical between the server-rendered output and the hydrated client tree, so `aria-controls` and `aria-labelledby` references resolve to the correct instance.

#### Scenario: Two tabs groups on one page have distinct ids

- **WHEN** two Tabs components render on the same page
- **THEN** their tab and panel elements SHALL have different `id` attribute values
- **AND** each tab's `aria-controls` SHALL reference its own panel's id

### Requirement: Collapse shall provide an accessible animated disclosure

The headless Collapse SHALL render a trigger with `aria-expanded` and `aria-controls` and a content region that expands/collapses when the trigger activates. Expand/collapse SHALL animate through the Transition capability (themed default uses a natural-height CSS technique without measurement); animation SHALL be disable-able. The trigger SHALL expose `data-state="open" | "closed"`; the content element SHALL expose `data-state="open"` while it is mounted (including during its leave sequence) and is removed from the DOM once closed. The open state SHALL be reactive with a change callback.

#### Scenario: Trigger toggles content with state exposure

- **WHEN** a Collapse trigger is activated while closed
- **THEN** `aria-expanded` SHALL become true, the content SHALL expand with the transition classes applied, and `data-state` SHALL read `open`

### Requirement: Accordion shall compose Collapse items with an open policy

The Accordion SHALL compose multiple Collapse items under a shared open-state and SHALL support a single-open policy (opening one item closes the others) as well as multi-open (default). Item identity SHALL be key-based. A change callback SHALL report every item whose open state changed, including items closed by the single-open policy.

#### Scenario: Single-open policy closes siblings

- **WHEN** an Accordion with the single-open policy has item A open and the user opens item B
- **THEN** item A SHALL close and item B SHALL be the only open item

#### Scenario: Policy-driven closures reach the change callback

- **WHEN** an Accordion with the single-open policy and a change callback has item A open and the user opens item B
- **THEN** the callback SHALL be invoked for item A with a closed state and for item B with an open state

### Requirement: Alert shall map variants to announcement roles

The headless Alert SHALL render inline feedback with variant semantics: error and warning variants SHALL use `role="alert"`, info and success variants SHALL use `role="status"`. An accessible message SHALL be announced according to the role's politeness. A dismiss action SHALL be available by prop with an accessible button. Dismissing SHALL hide the alert (the root carries the boolean `hidden` attribute, removing it from the accessibility tree) and invoke the optional dismiss callback.

#### Scenario: Error alert announces assertively

- **WHEN** an Alert with the error variant renders
- **THEN** the element SHALL carry `role="alert"`

### Requirement: Progress shall expose determinate and indeterminate states with correct ARIA

The headless Progress SHALL render `role="progressbar"` with an accessible label. In determinate mode it SHALL set `aria-valuenow`, `aria-valuemin`, and `aria-valuemax` from value props; in indeterminate mode it SHALL omit `aria-valuenow` and expose `data-state="indeterminate"`. Determinate mode SHALL expose `data-state="determinate"`.

#### Scenario: Determinate values are exposed

- **WHEN** a Progress renders with value 40 of 100
- **THEN** `aria-valuenow` SHALL be 40 with `aria-valuemin` 0 and `aria-valuemax` 100 (or the configured bounds)

### Requirement: Badge, Skeleton, and Card shall provide themed structural primitives

Badge SHALL render a compact status label with variant styling hooks. Skeleton SHALL render loading placeholders marked `aria-hidden="true"` (decorative), with documented guidance to pair them with an accessible loading indicator. Card SHALL provide structural header/body/footer regions with class pass-through. None of the three carries interaction state.

#### Scenario: Skeleton is hidden from assistive technology

- **WHEN** a Skeleton renders inside a loading section
- **THEN** the placeholder elements SHALL carry `aria-hidden="true"`

### Requirement: Disclosure/feedback components shall ship as headless/themed pairs per the foundation contract

Each component in this family SHALL exist as a headless component honoring the headless contract (behavior-only, `data-state`, class pass-through) and a themed component composing it with token-based defaults in the primitives stylesheet, re-exported at the `webcompy.ui` top level.

#### Scenario: Themed variants consume tokens

- **WHEN** any themed component of this family renders
- **THEN** its default styles SHALL consume design tokens and be overridable through class pass-through
