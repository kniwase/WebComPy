# Delta: docs-site-documents

## ADDED Requirements

### Requirement: The Getting Started category shall include orientation pages

The `Getting Started` section SHALL include, in order: `what-is-webcompy` (framework positioning and the dual-environment model), `why-webcompy` (a truthful Why / Why NOT WebComPy discussion that names real trade-offs such as the PyScript payload and cold start), `installation`, `quickstart`, and `project-structure` (app package layout, build vs server configuration, static files, resources, and lockfile), each at a `/documents/getting-started/` path with flat frontmatter carrying `title` and `description`.

#### Scenario: Orientation pages reachable

- **WHEN** `/documents/getting-started/what-is-webcompy`, `/documents/getting-started/why-webcompy`, or `/documents/getting-started/project-structure` is requested
- **THEN** each renders as a Markdown docs page with its frontmatter title in the `<title>` and a populated TOC

#### Scenario: Why page names trade-offs

- **WHEN** the `why-webcompy` page is inspected
- **THEN** it contains a "Why not" section that states concrete drawbacks, not only marketing points

### Requirement: Docs examples shall reflect the current component-definition form

Markdown docs examples that define components SHALL use the current `@define_component` form: the bare factory call with parentheses when the custom-element tag derives from the function name, and an explicit `custom_element_name=` only where the tag intentionally differs from the derivation. Examples and prose SHALL NOT present the removed round-trip name-matching rule as current.

#### Scenario: Derived-name example

- **WHEN** a docs example defines a `HomePage` component for the current API
- **THEN** it shows `@define_component()` (no positional name) with the tag explained as derived

#### Scenario: Stale rule text removed

- **WHEN** `custom_elements.md` is read
- **THEN** it documents optional name derivation and no longer claims the function name must round-trip with the tag
