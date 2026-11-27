# Spec Delta

## MODIFIED Requirements

### Requirement: The Home page shall present a landing layout with four bands

The docs_app Home page SHALL consist of: a hero (h1 headline "Build Frontend in Python" with a subtitle describing Python-native reactive components running in the browser via PyScript, and two links — Get Started pointing at `/documents/getting-started/what-is-webcompy` and View on GitHub pointing at the repository URL), a feature-cards band (a balanced grid of cards covering reactivity, components & routing, CLI/SSR/SSG, PyScript runtime without trailing orphan grid gaps or compounding card vertical margins), a quick-start teaser band (one minimal uv command block and one first-component snippet with a link to the Installation page), and a footer band with the source link. The Home page SHALL NOT restate detailed installation steps (multi-package manager instructions, lock-file configuration tables) that exist in `installation.md`.

#### Scenario: Hero headline and links

- **WHEN** the Home page renders
- **THEN** it shows the h1 headline, and a Get Started link whose href is `/documents/getting-started/what-is-webcompy` and a GitHub link to the project repository

#### Scenario: Feature cards align without orphan grid slots or margin drift

- **WHEN** the Home page feature-cards grid renders on desktop (`1280px`–`1440px`), tablet (`1024px`), and mobile (`390px`)
- **THEN** rows fill evenly without leaving a lone orphan card in an underfilled row and card spacing matches the CSS grid gap uniformly

#### Scenario: No duplicated installation instructions

- **WHEN** the Home page content is inspected
- **THEN** no Poetry instructions block and no lock-file command table are present (they live only under `/documents`)
