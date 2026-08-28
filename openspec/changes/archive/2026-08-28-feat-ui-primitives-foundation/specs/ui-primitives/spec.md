# UI Primitives Foundation Specification (delta)

## ADDED Requirements

### Requirement: Headless components shall provide behavior without visual styling

The `webcompy.ui.headless` package SHALL provide first-party components that own state management, ARIA roles and attributes, keyboard interaction, and focus management. Headless components SHALL NOT emit visual styles (colors, spacing, typography, borders, shadows, decorative animation). Structural CSS required for behavior (positioning, display toggling, visibility) is permitted. Every headless component SHALL expose its interaction state on the DOM through `data-state` attributes with documented per-component vocabularies.

#### Scenario: Headless component exposes state via data-state

- **WHEN** a headless component with an open/closed notion renders in each state
- **THEN** its root element SHALL carry `data-state="open"` or `data-state="closed"` respectively
- **AND** the component SHALL apply no visual styling of its own beyond structural CSS

#### Scenario: Keyboard interaction is built in

- **WHEN** a headless interactive component defines keyboard behavior (e.g. Escape to dismiss, arrow keys to move focus)
- **THEN** the behavior SHALL be implemented by the component itself with correct ARIA attributes, requiring no user code

### Requirement: Headless components shall accept class pass-through styling hooks

Every headless component SHALL accept a `class_name` prop applied to its root element — named `class_name` because `class` is a Python keyword, mapping to the DOM `class` attribute — and multi-part components SHALL accept part-specific class props with documented names. User-supplied classes SHALL be appended after framework classes so that user rules take precedence at equal specificity. Class pass-through and `data-state` attributes together constitute the headless styling surface.

#### Scenario: User class reaches the root element

- **WHEN** a headless component is rendered with `class_name="my-custom"`
- **THEN** the root element's class list SHALL contain both the framework classes and `my-custom`, with `my-custom` last

### Requirement: Themed components shall compose headless components with token-based defaults

The `webcompy.ui.components` package SHALL provide themed variants that render the corresponding headless component and supply default class names styled by rules consuming the framework design tokens (`var(--color-*)`, `var(--space-*)`, and related token families). Themed components SHALL carry no behavior logic; all behavior SHALL come from the composed headless component. Themed components SHALL forward user class pass-through props to the headless component so overrides work identically at both layers.

#### Scenario: Themed component inherits headless behavior

- **WHEN** a themed component is rendered and interacted with (keyboard, state changes)
- **THEN** the behavior SHALL be identical to the underlying headless component
- **AND** the rendered markup SHALL carry the themed default classes consuming design tokens

#### Scenario: Override via class prop

- **WHEN** a themed component is rendered with a user `class` prop
- **THEN** the user class SHALL be appended after the themed defaults so user rules win at equal specificity

### Requirement: Primitive namespaces and exports shall follow the two-layer layout

Headless components SHALL be importable from `webcompy.ui.headless`, themed components from `webcompy.ui.components`, and the `webcompy.ui` top level SHALL re-export the themed components as the default path. Importing a name from `webcompy.ui` SHALL always yield the themed variant.

#### Scenario: Three import paths resolve correctly

- **WHEN** a developer imports `Spinner` from `webcompy.ui.headless`, from `webcompy.ui.components`, and from `webcompy.ui`
- **THEN** the first import SHALL yield the headless component
- **AND** the second and third imports SHALL yield the themed component

### Requirement: Themed primitive styles shall ship through the existing stylesheet cascade

Themed primitive styles SHALL ship in a dedicated stylesheet imported by the framework's aggregated UI stylesheet (`/_webcompy-ui/index.css`) within the existing `@layer` ordering, so that unlayered user CSS overrides themed defaults without specificity escalation. The stylesheet SHALL be served automatically wherever the framework injects its UI stylesheet (SSR, SSG, dev server).

#### Scenario: Primitive styles are present in served pages

- **WHEN** an application using themed primitives is served or generated
- **THEN** the document head SHALL include the framework UI stylesheet containing the primitive rules inside the components layer

### Requirement: Spinner shall be the first headless/themed component pair

The headless `Spinner` SHALL render `role="status"` with an accessible label (explicit label prop rendered as visually hidden text, or `aria-label`) and SHALL expose `data-state="loading"`. The themed `Spinner` SHALL render a token-based animated indicator using design-token colors and SHALL pause or suppress its animation when the user prefers reduced motion. Both SHALL honor the class pass-through requirement.

#### Scenario: Accessible loading indicator

- **WHEN** a themed Spinner renders with the label "Loading data"
- **THEN** the element SHALL have `role="status"` and an accessible name of "Loading data"
- **AND** the element SHALL carry `data-state="loading"`

#### Scenario: Reduced motion is honored

- **WHEN** the user's media preference is reduced motion
- **THEN** the themed Spinner SHALL not animate (static indicator remains visible)
