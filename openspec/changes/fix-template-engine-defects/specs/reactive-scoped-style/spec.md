# Delta Spec: reactive-scoped-style

## ADDED Requirements

### Requirement: Reactive scoping shall be identical to static scoping

The selector-scoping transformation applied to reactive scoped styles SHALL be the same transformation used for static `scoped_style` (a single shared implementation). For any identical style dict input, the scoped selector output of the static and reactive paths SHALL match.

#### Scenario: Same input, same output
- **WHEN** the same selector set (including combinators such as `a~b`, leading `> .child`, and functional pseudo-classes like `:nth-child(2n+1)`) is rendered through the static `scoped_style` setter and through `reactive_scoped_style`
- **THEN** both paths SHALL produce identical scoped selectors
- **AND** neither path SHALL split selectors inside parentheses, brackets, or strings

#### Scenario: Leading combinator at top level
- **WHEN** a top-level selector starts with a combinator (e.g., `> .child`)
- **THEN** both paths SHALL emit a valid scoped selector (e.g., `*[webcompy-cid-{id}]> .child[webcompy-cid-{id}]`)
- **AND** the reactive path SHALL NOT differ from the static path

## MODIFIED Requirements

(none)
