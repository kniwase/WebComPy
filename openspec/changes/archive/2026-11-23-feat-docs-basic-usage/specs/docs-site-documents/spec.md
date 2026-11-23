# Delta: docs-site-documents

## ADDED Requirements

### Requirement: The Basic Usage category shall cover first-day concerns

The `Basic Usage` section SHALL include, in manifest order, pages covering: components (definition forms and name derivation, props, slots, lifecycle, static scoped styles), HTML template syntax (interpolation, safe expressions, filters, conditionals, loops with `loop` metadata, comments, raw blocks, event/`ref`/bind attributes, component tags), reactive state (`Signal`/`Computed`/`ReactiveList`/`ReactiveDict` and the transfer-capable `use_*` family), elements and events, Markdown documents (both rendering APIs, frontmatter, prose preset), routing (flat routes, parameters, link active state, history vs hash), forms (field/form/validators plus the UI form controls), HTTP and async results (basics), styling and themes (basics), storage (basics), and error boundaries (basics) — in addition to the existing UI primitives, overlay, and disclosure pages.

#### Scenario: Required page set

- **WHEN** the manifest is validated
- **THEN** each listed concern has a `/documents/basic/<slug>` entry, ordered so that every page's examples use only concepts from earlier pages or Getting Started

#### Scenario: Split topics link to their Advanced half

- **WHEN** a Basic page covers a topic that has an Advanced continuation (routing, forms, styling, storage, HTTP and async, error handling, components, reactive state)
- **THEN** the page's "Next steps" links to the corresponding Advanced page wherever that Advanced page exists in the manifest, and the Advanced page links back (upcoming Advanced topics whose pages are not yet in the manifest are described in plain text so no link fails manifest validation)

### Requirement: Docs pages shall follow the shared content conventions

Every Basic/Advanced Markdown page SHALL carry flat frontmatter with `title` and `description`, open with a lead paragraph stating what the feature is and when it is used, structure primary topics as H2 sections (the TOC source), and close with a "Next steps" section linking related pages by rendered-site URL.

#### Scenario: Page structure check

- **WHEN** any Basic Usage page is read
- **THEN** it has frontmatter, an H1, H2 topic sections, and a final "Next steps" section whose links are `/documents/...` URLs
