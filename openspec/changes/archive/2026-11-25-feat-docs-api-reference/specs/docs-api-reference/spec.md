# Spec: docs-api-reference

## ADDED Requirements

### Requirement: Generated skeletons shall back the API Reference pages

A script `scripts/generate_api_reference.py` SHALL resolve the public API surface (reusing the shared resolver with the docstring checker) and emit/update Markdown skeleton sections for the API Reference pages: per public symbol a heading, signature line, and docstring-derived parameter/returns/raises listing, leaving author regions untouched. Running the script with `--check` SHALL exit non-zero when any committed page's generated region differs from current code.

#### Scenario: Public API changes without reference refresh

- **WHEN** a public symbol signature changes in `packages/*/src` and the reference pages are regenerated with `--check`
- **THEN** the check fails listing the drifted pages and symbols

#### Scenario: Author prose survives regeneration

- **WHEN** the generator runs against a page containing `<!-- author:start -->` regions
- **THEN** only generated regions are rewritten and author regions are preserved verbatim

### Requirement: The API Reference category shall cover all four packages

docs_app SHALL register an `API Reference` category at `/documents/api/` whose pages cover: core runtime packages (`app`/`config`, `components`, `elements`, `signal`, `template`, `router`+`di`, data-layer modules), `webcompy.ui` (theme, code block, components, styles), server/CLI packages (`webcompy_server`, `webcompy_cli`, `rpc`, `hydration`, ports), and `webcompy_testing`. Each page SHALL list symbols alphabetically within topic clusters and cross-link to the Basic/Advanced pages that teach the concepts.

#### Scenario: Coverage check

- **WHEN** the reference coverage test runs
- **THEN** every symbol in the resolved public API surface appears on exactly one API Reference page

### Requirement: The reference layer shall not duplicate conceptual prose

API Reference pages SHALL confine hand-written content to lookup aids (links, see-also, deprecation notes); explanatory prose SHALL live in Basic/Advanced pages and be referenced by link.

#### Scenario: Conceptual prose lives elsewhere

- **WHEN** an API Reference page needs to explain reactivity semantics
- **THEN** it links to the Basic reactive-state page instead of restating the explanation
