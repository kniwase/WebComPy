# Spec: docs-site-home

## ADDED Requirements

### Requirement: The Home page shall present a landing layout with four bands

The docs_app Home page SHALL consist of: a hero (h1 headline "Build Frontend in Python" with a subtitle describing Python-native reactive components running in the browser via PyScript, and two links — Get Started pointing at `/documents/getting-started/what-is-webcompy` and View on GitHub pointing at the repository URL), a feature-cards band (at least four cards: reactivity, components & routing, CLI/SSR/SSG, PyScript runtime), a quick-start teaser band (one minimal uv command block and one first-component snippet with a link to the Installation page), and a footer band with the source link. The Home page SHALL NOT restate detailed installation steps (multi-package manager instructions, lock-file configuration tables) that exist in `installation.md`.

#### Scenario: Hero headline and links

- **WHEN** the Home page renders
- **THEN** it shows the h1 headline, and a Get Started link whose href is `/documents/getting-started/what-is-webcompy` and a GitHub link to the project repository

#### Scenario: No duplicated installation instructions

- **WHEN** the Home page content is inspected
- **THEN** no Poetry instructions block and no lock-file command table are present (they live only under `/documents`)

### Requirement: Home code blocks shall have symmetric vertical spacing

The Home page SHALL apply `margin: var(--space-4) 0` to its `CodeBlock` elements via the docs_app-owned stylesheet (`.home-page .code-block` in `docs_app/static/styles/components.css`) so rendered code blocks match the prose preset's rhythm, without the Home page adopting the `.prose` wrapper or modifying framework stylesheets. Component scoped style cannot reach child-component roots because `webcompy-cid` attributes are stamped per component, so the docs_app stylesheet carries this rule instead.

#### Scenario: Code block rhythm matches prose

- **WHEN** a teaser code block is rendered on Home
- **THEN** its computed vertical margins equal the `.prose pre` values from `prose.css`
