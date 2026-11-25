# Delta: docs-site-documents

(Base: applies after `feat-docs-server-tooling` and `feat-docs-migration-guide`, which already reserve the `API Reference` standalone category and its `/documents/api/` prefix.)

## ADDED Requirements

### Requirement: The API Reference category shall be registered last

The `DOCS_SECTIONS` manifest SHALL contain the standalone `API Reference` category with the reference pages defined by the docs-api-reference capability at `/documents/api/`, positioned after all other categories in the manifest.

#### Scenario: Reference pages registered

- **WHEN** the manifest is validated after this change
- **THEN** the API Reference pages resolve under `/documents/api/` and appear last in flattened Prev/Next order
