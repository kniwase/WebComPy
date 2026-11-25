# Delta: docs-site-documents

(Base: applies after `feat-docs-server-tooling`, whose category-model update already reserves the `Migration` standalone category and `/documents/migration/` prefix.)

## ADDED Requirements

### Requirement: The Migration category shall register the migration guides

The `DOCS_SECTIONS` manifest SHALL contain the standalone `Migration` category with pages `from-jinja2-fastapi` and `compatibility-notes` at `/documents/migration/`. Among the standalone categories the order SHALL be `Examples`, `Migration`, `API Reference` (relative to each other), following `Server & Tooling`.

#### Scenario: Migration pages registered

- **WHEN** the manifest is validated after this change
- **THEN** the two Migration pages exist at their prefixed paths and Prev/Next walks them in order within the standalone block
