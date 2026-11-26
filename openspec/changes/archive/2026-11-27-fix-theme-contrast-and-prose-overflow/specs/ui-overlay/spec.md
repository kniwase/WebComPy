# Spec Delta

## MODIFIED Requirements

### Requirement: Drawer shall provide an edge panel with the modal accessibility contract

The headless Drawer SHALL render a panel sliding from a configurable edge (left, right, top, bottom) and SHALL implement the same accessibility contract as Modal (focus trap, focus-in on open, focus return on close, Escape dismissal, Teleport + Transition rendering, `data-state` exposure). The edge SHALL be selectable by prop and reflected for styling. The themed Drawer SHALL supply internal panel padding, a tokenized surface (`--color-bg-elevated` / `--color-fg`), border, `--shadow-lg` elevation, and a dimmed backdrop overlay matching Modal's backdrop contract.

#### Scenario: Drawer from the right edge

- **WHEN** a Drawer configured for the right edge opens
- **THEN** the panel SHALL render at the right edge of the viewport via Teleport
- **AND** focus SHALL move into the panel and be trapped as with Modal
- **AND** its content SHALL have non-zero internal padding and legible foreground/background contrast in both light and dark themes

### Requirement: Overlay components shall ship as headless/themed pairs per the foundation contract

Each overlay component (Modal, Drawer, Dropdown, Toast host and items) SHALL exist as a headless component honoring the headless contract (behavior-only, `data-state`, class pass-through) and a themed component composing it with token-based defaults in the primitives stylesheet, re-exported at the `webcompy.ui` top level. Default open/close transition classes SHALL be provided by the themed layer; users SHALL be able to override them. Overlay backdrops (`.webcompy-modal-backdrop` and Drawer backdrop) SHALL use a dark translucent scrim (rather than inverting with `var(--color-fg)` opacity) so underlying page content dims cleanly in both light and dark themes, and panel surfaces, borders, shadows (`--shadow-lg`), and dismiss/close controls SHALL maintain WCAG 2.1 AA contrast in both themes.

#### Scenario: Themed Modal uses Teleport, Transition, and tokens

- **WHEN** a themed Modal opens
- **THEN** its content SHALL render under the document body via Teleport with the default transition classes applied during open/close
- **AND** its themed styles SHALL consume design tokens (including resolved `--shadow-lg`)
- **AND** its backdrop SHALL darken the underlying page without whitewash in dark mode and its panel text and close controls SHALL remain legible in both light and dark themes
