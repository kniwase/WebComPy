## ADDED Requirements

### Requirement: Incrementally injected static scoped CSS shall support `:host`

When a named component's static scoped style contains `:host` or `:host(<compound-selector>)`, the incrementally injected `<style data-webcompy-cid>` content SHALL replace the host pseudo-class with the component's custom-element selector and retain the normal cid attribute scoping. The same transformed CSS SHALL be used for browser runtime injection and SSR/SSG output.

#### Scenario: Injecting a host rule at browser runtime
- **WHEN** a named component with scoped style `{":host": {"display": "block"}}` is registered during browser runtime
- **THEN** its per-component style element SHALL contain a selector for the named custom-element wrapper
- **AND** the selector SHALL include the component cid attribute

#### Scenario: Rendering a host rule during SSG
- **WHEN** SSG emits a named component's scoped style containing `:host(.active)`
- **THEN** the generated per-component style element SHALL contain the equivalent named-element class selector
- **AND** the output SHALL remain wrapped in `@layer webcompy-scope`

#### Scenario: Reconciling a newly resolved host style
- **WHEN** a lazy named component with a `:host` scoped style is resolved after the initial render
- **THEN** the next scoped-style reconciliation SHALL inject exactly one matching style element
- **AND** the generated rule SHALL use the same selector as the initial SSR or runtime path

### Requirement: Incremental scoped CSS shall retain cid-based component isolation

Adding `:host` support SHALL not replace cid-attribute scoping. Existing selectors and nested component boundaries SHALL continue to use `webcompy-cid-*` attributes, and a named-element tag selector SHALL not be used as a general replacement for cid scoping.

#### Scenario: Existing descendant selector remains cid-scoped
- **WHEN** a named component contains both `:host` and `.button` scoped rules
- **THEN** the host rule SHALL target the wrapper
- **AND** the `.button` rule SHALL retain the existing cid-scoped descendant behavior

#### Scenario: Nested component styles remain isolated
- **WHEN** a named component contains a nested component with an element sharing a class name
- **THEN** the parent component's descendant rule SHALL not leak into the nested component's owned subtree
- **AND** the nested component's own scoped style SHALL remain independent
