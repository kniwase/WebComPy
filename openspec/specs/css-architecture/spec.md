# css-architecture Specification

## Purpose
TBD - created by archiving change feat-ui-toolkit-foundation. Update Purpose after archive.
## Requirements
### Requirement: The framework SHALL declare a fixed CSS `@layer` order

The framework SHALL declare, in a single CSS file (`webcompy/ui/_styles/index.css` or equivalent), the cascade order `@layer reset, tokens, components, webcompy-scope;`. This declaration SHALL appear exactly once in the page output, before any rule that uses one of these layers. The layer list is intentionally minimal: the only unlayered style source is dynamic app-level CSS injected via `app.append_style(...)` (rendered as `<style data-webcompy-dynamic="...">`); see `openspec/specs/app-styles/spec.md`. All scoped component CSS — both static `Component.scoped_style` and `reactive_scoped_style` — IS layered (in `@layer webcompy-scope`, see the Requirement below).

#### Scenario: Layer order is fixed

- **WHEN** a page is rendered with the framework's default CSS
- **THEN** the rendered CSS SHALL contain `@layer reset, tokens, components, webcompy-scope;` as a top-level declaration
- **AND** no application CSS SHALL be able to reorder these layers (later layer declarations with the same names SHALL merge, not replace)

#### Scenario: Dynamic styles are not in the layer list

- **WHEN** a component uses `app.append_style(...)` to inject style at runtime
- **THEN** the emitted `<style data-webcompy-dynamic="...">` element SHALL NOT be wrapped in any `@layer ... { ... }` block
- **AND** those rules SHALL override every layered framework rule without `!important`

### Requirement: The framework SHALL wrap all `scoped_style` rules in `@layer webcompy-scope`

When the framework injects a component's `scoped_style` as a `<style data-webcompy-cid="...">` element (or as a server-rendered `<style>` block), the framework SHALL wrap the rule body in `@layer webcompy-scope { ... }`. This is automatic and requires no opt-in.

#### Scenario: scoped_style output is wrapped

- **WHEN** a component defines `Component.scoped_style = {".btn": {"color": "red"}}`
- **THEN** the emitted CSS SHALL be `@layer webcompy-scope { .btn[webcompy-cid-xxx] { color: red; } }`
- **AND** the rule SHALL have lower priority than any unlayered rule in the same stylesheet (per CSS layer rules)

#### Scenario: scoped_style is wrapped in both SSR and CSR

- **WHEN** the same component is rendered in SSR and then re-rendered after hydration
- **THEN** both the server-rendered and the runtime-injected `<style>` elements SHALL contain the `@layer webcompy-scope` wrapper

### Requirement: The framework SHALL provide a CSS reset file in the `reset` layer

The framework SHALL provide a `reset.css` file (or equivalent) whose rules are placed in the `reset` layer. The file SHALL include a minimal box-sizing reset and a body color/background reset that uses the `var(--color-*)` tokens.

#### Scenario: Reset applies before component styles

- **WHEN** a page is rendered with `reset.css` and a component's `scoped_style`
- **THEN** the body's background and color SHALL match the reset rules
- **AND** any component-specific body overrides SHALL win over the reset (because the reset is in a higher-priority layer)

### Requirement: The framework SHALL provide a components CSS file in the `components` layer

The framework SHALL provide a `components.css` file whose rules are placed in the `components` layer. The file SHALL define framework-level UI component styles (e.g., `pre`, `code`, button-like patterns) that need to override `scoped_style` for utility purposes.

#### Scenario: components.css overrides scoped_style

- **WHEN** `components.css` defines a rule for `pre` (e.g., `pre { overflow-x: auto; }`)
- **AND** a component's `scoped_style` defines a rule for its internal `pre` element
- **THEN** the `components.css` rule SHALL win (because `components` is declared before `webcompy-scope` in the layer order)

### Requirement: The framework SHALL provide a code-block CSS file with `@scope` boundaries

The framework SHALL provide a `code-block.css` file that styles `.tok-*` spans and uses `@scope (.code-block) to (.code-block *)` to scope CodeBlock-specific overrides (e.g., italic comments) to within a CodeBlock instance.

#### Scenario: @scope limits token style overrides

- **WHEN** `code-block.css` contains `@scope (.code-block) to (.code-block *) { .tok-comment { font-style: italic; } }`
- **THEN** the italic style SHALL apply to `.tok-comment` elements inside any `.code-block` element
- **AND** it SHALL NOT apply to `.tok-comment` elements outside a `.code-block`

### Requirement: Dynamic styles are emitted unlayered

The framework SHALL emit dynamic styles (`<style data-webcompy-dynamic="{id}">` elements) without any `@layer` wrapper. The unlayered style wins over any layered framework CSS in the cascade, allowing app-level overrides without needing `!important` on the application's own rules. Users who need to override unlayered application CSS can append `!important` to the relevant declarations. See `openspec/specs/app-styles/spec.md` for the dynamic-style contract.

#### Scenario: Dynamic style has no layer wrapper
- **WHEN** `app.append_style(":root { --x: red; }")` is called
- **THEN** the rendered `<style data-webcompy-dynamic="0">` element's textContent SHALL be `:root { --x: red; }` (no surrounding `@layer ... { ... }`)

