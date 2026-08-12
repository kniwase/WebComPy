# css-architecture Delta: fix-ssr-scoped-style-layer-order

## MODIFIED Requirements

### Requirement: The framework SHALL provide a CSS reset file in the `reset` layer

The framework SHALL provide a `reset.css` file (or equivalent) whose rules are placed in the `reset` layer. The file SHALL include a minimal box-sizing reset and a body color/background reset that uses the `var(--color-*)` tokens.

#### Scenario: Reset applies before component styles

- **WHEN** a page is rendered with `reset.css` and a component's `scoped_style`
- **THEN** the body's background and color SHALL match the reset rules
- **AND** any component-specific body overrides SHALL win over the reset (because the reset is in the lowest-priority layer)

### Requirement: The framework SHALL provide a components CSS file in the `components` layer

The framework SHALL provide a `components.css` file whose rules are placed in the `components` layer. The file SHALL define framework-level default styles for common elements and UI patterns (e.g., `pre`, `code`, button-like patterns). Because `components` is declared before `webcompy-scope` in the fixed layer order, these defaults yield to author-defined `scoped_style` rules.

#### Scenario: scoped_style overrides components.css defaults

- **WHEN** `components.css` defines a rule for `pre` (e.g., `pre { overflow-x: auto; }`)
- **AND** a component's `scoped_style` defines a rule for its internal `pre` element
- **THEN** the `scoped_style` rule SHALL win (because `webcompy-scope` is declared after `components` in the layer order, with `prose` between them)

## ADDED Requirements

### Requirement: SSR/SSG output SHALL emit layered scoped style elements after the layer-order declaration

In SSR/SSG-generated HTML, all `<style data-webcompy-cid="...">` and `<style data-webcompy-cid-rx="...">` elements (which contain rules layered via `@layer webcompy-scope`) SHALL be emitted after the stylesheet link that declares the fixed layer order (`/_webcompy-ui/index.css`). This ensures the declaration `@layer reset, tokens, components, prose, webcompy-scope;` is the first occurrence of each layer name in document order, per CSS Cascade 5 §6.4.3, so the intended cascade priority holds in SSR output exactly as it does in CSR output.

#### Scenario: Scoped styles follow the index.css link in generated HTML

- **WHEN** an SSR/SSG page is generated for an app whose components define `scoped_style`
- **THEN** in the generated `<head>`, every `<style data-webcompy-cid="...">` and `<style data-webcompy-cid-rx="...">` element SHALL appear after the `<link rel="stylesheet" href=".../_webcompy-ui/index.css">` element
- **AND** the effective cascade layer order SHALL be `reset < tokens < components < prose < webcompy-scope` (lowest to highest priority)

#### Scenario: App without prose.css still gets the full layer order

- **WHEN** an SSR/SSG page is generated for an app that does not link `prose.css`
- **THEN** the layer-order declaration in `index.css` (which lists all five layers including `prose`) SHALL still precede all layered rules
- **AND** scoped styles SHALL retain the highest layered priority
