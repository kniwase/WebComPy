# Delta: docs-site-documents

## ADDED Requirements

### Requirement: The Guides category shall be a linear build-to-completion tutorial

The `DOCS_SECTIONS` manifest SHALL contain a `Guides` section between `Getting Started` and `Basic Usage`, holding an overview page plus six sequential ToDo-application step pages at `/documents/guides/` paths: app shell with reactive state, component extraction, navigation, forms, remote data (served by an in-app `FetchMiddleware` mock so it works in static hosting), and deployment. Each step page SHALL render a live demo iframe of that step's complete standalone app (registered under `docs_app/static/_demos/todo_tutorial/`) and the step's full source, and SHALL add only concepts defined in Getting Started or earlier steps.

#### Scenario: Step ordering and progression

- **WHEN** the manifest is validated
- **THEN** the Guides pages appear overview-first in step order, and Prev/Next walks the sequence naturally

#### Scenario: Step 5 works without a server

- **WHEN** the remote-data step demo runs on the statically generated site
- **THEN** the task list loads and submits succeed through the in-app middleware mock with no network errors in the console

#### Scenario: Curriculum containment

- **WHEN** a step page is reviewed
- **THEN** it uses only Basic-level APIs (no guards, middleware registries beyond the provided mock recipe, hydration internals, or other Advanced topics)
