# Delta Spec: components

## ADDED Requirements

### Requirement: Selector scoping shall be depth-aware

When splitting selectors on combinators for `[webcompy-cid-{id}]` insertion, the framework SHALL only split at combinators appearing at depth zero — never inside parentheses `()`, attribute-selector brackets `[]`, or quoted strings. Whitespace runs of any kind (spaces, newlines, tabs) at depth zero SHALL be treated as descendant combinators.

#### Scenario: Functional pseudo-class preserved
- **WHEN** a scoped style contains the selector `.x:nth-child(2n+1)`
- **THEN** the generated CSS SHALL be `.x:nth-child(2n+1)[webcompy-cid-{id}]` (or equivalent valid selector with the cid attached to the compound)
- **AND** the `+` inside `:nth-child(...)` SHALL NOT be treated as a combinator

#### Scenario: Attribute selector value preserved
- **WHEN** a scoped style contains the selector `[data-x="a>b"]` or `[title="Hello, World"]`
- **THEN** the attribute value SHALL be preserved verbatim
- **AND** the cid attribute SHALL be attached without splitting inside the brackets

#### Scenario: Tilde combinator without spaces
- **WHEN** a scoped style contains the selector `a~b`
- **THEN** both `a` and `b` SHALL receive the cid attribute: `a[webcompy-cid-{id}]~b[webcompy-cid-{id}]`

#### Scenario: Newline descendant combinator
- **WHEN** a selector list spans multiple lines (e.g., `.a\n.b` within a multi-line CSS text key)
- **THEN** the newline SHALL be treated as a descendant combinator and both compounds SHALL be scoped

### Requirement: Scoped attribute selector shall be inserted before trailing pseudo-elements

When attaching `[webcompy-cid-{id}]` to a compound selector that ends with a pseudo-element chain (`::before`, `::after`, `::placeholder`, functional pseudo-elements such as `::slotted(...)`), the cid attribute selector SHALL be inserted **before** the pseudo-element chain so the resulting selector is valid CSS.

#### Scenario: Pseudo-element selector
- **WHEN** a scoped style contains the flat selector `.x::before`
- **THEN** the generated CSS selector SHALL be `.x[webcompy-cid-{id}]::before` (not `.x::before[webcompy-cid-{id}]`)

#### Scenario: Pseudo-class then pseudo-element
- **WHEN** a scoped style contains the selector `.x:hover::before`
- **THEN** the generated CSS selector SHALL be `.x:hover[webcompy-cid-{id}]::before` or `.x[webcompy-cid-{id}]:hover::before` — in both forms the cid SHALL precede `::before`

### Requirement: Declaration-body at-rules shall be rendered unscoped

At-rules whose body consists of declarations rather than nested rules — `@font-face`, `@page`, `@property`, `@counter-style` — SHALL be rendered without `[webcompy-cid-{id}]` scoping and SHALL NOT raise an error. Keyframes at-rule detection SHALL be case-insensitive and SHALL recognize vendor prefixes (`@-webkit-keyframes`, `@-moz-keyframes`, `@-o-keyframes`).

#### Scenario: @font-face rendered unscoped
- **WHEN** a scoped style contains `{"@font-face": {"font-family": "'X'", "src": "url(x.woff2)"}}`
- **THEN** the generated CSS SHALL contain `@font-face { font-family: 'X'; src: url(x.woff2); }` with no cid attribute
- **AND** no exception SHALL be raised

#### Scenario: Vendor-prefixed keyframes
- **WHEN** a scoped style contains `{"@-webkit-keyframes spin": {"0%": {"opacity": "0"}}}`
- **THEN** the inner `0%` key SHALL NOT receive a cid attribute
- **AND** the generated CSS SHALL be valid

### Requirement: CSS nesting parent selector shall be rejected

Selectors containing the CSS-nesting parent selector `&` SHALL raise `WebComPyException` with a message stating that CSS nesting with `&` is not supported in scoped styles and suggesting the implicit-nesting dict form (e.g., `{".btn": {":hover": {...}}}`) instead.

#### Scenario: Ampersand selector rejected
- **WHEN** a scoped style or `css_text` source contains `.btn { &:hover { color: red; } }`
- **THEN** `WebComPyException` SHALL be raised naming the `&` selector and suggesting the nested dict form

## MODIFIED Requirements

(none — existing scoping scenarios already describe the corrected behavior; the defects were implementation-level divergences from them)
