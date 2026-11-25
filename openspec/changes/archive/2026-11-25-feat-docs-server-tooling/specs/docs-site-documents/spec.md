# Delta: docs-site-documents

(Base: applies after `refactor-docs-sections-restructure`.)

## MODIFIED Requirements

### Requirement: The docs manifest shall follow the category section model

The `DOCS_SECTIONS` manifest SHALL consist of top-level category sections in the order `Getting Started`, `Guides`, `Basic Usage`, `Advanced Usage`, `Server & Tooling`, with the standalone categories (`Examples`, `Migration`, `API Reference`) following when present. Each page's manifest `path` SHALL start with the category's URL prefix: `/documents/getting-started/`, `/documents/guides/`, `/documents/basic/`, `/documents/advanced/`, `/documents/server/`, or a standalone category's prefix once it exists (`/documents/examples/`, `/documents/migration/`, `/documents/api/`). Section titles other than these category names SHALL NOT be introduced by structural changes. A category without pages SHALL be omitted from the manifest rather than carried as an empty section, and manifest validation SHALL reject a section that omits its `title` or contains an empty `pages` list.

#### Scenario: Page paths carry the category prefix

- **WHEN** the manifest is validated
- **THEN** every page entry's `path` starts with its category's prefix, and the category sections appear in the defined order

#### Scenario: Empty section rejected

- **WHEN** the manifest is validated and a category section has an empty `pages` list
- **THEN** a `WebComPyException` at import/validation time identifies the offending section

#### Scenario: Missing section title rejected

- **WHEN** the manifest is validated and a section omits its `title`
- **THEN** a `WebComPyException` at import/validation time identifies the offending section

## ADDED Requirements

### Requirement: The Server & Tooling category shall cover the build and operations surface

The `Server & Tooling` category SHALL contain pages: `cli-reference` (all `python -m webcompy` subcommands and flags, cross-checked against the parser by a unit test), `project-configuration` (two-file config model, config field guide, resources, lockfile), `asgi-integration` (embedding WebComPy in a host ASGI app and mounting ASGI apps under WebComPy, including the canonical host-mount snippet reused by the migration guide), `serving-modes` (runtime/wasm sourcing, standalone, wheel modes, offline operation), and `testing` (`webcompy_testing` utilities and tier guidance).

#### Scenario: CLI docs match the parser

- **WHEN** the CLI-reference test runs
- **THEN** every subcommand and flag name documented on the page appears in the actual argument parser configuration

#### Scenario: Canonical host-mount snippet

- **WHEN** the asgi-integration page is read
- **THEN** it contains the complete FastAPI host-mount example (base_url pairing, `configure_server_context`, mount) and the migration guide links to this page instead of duplicating it
