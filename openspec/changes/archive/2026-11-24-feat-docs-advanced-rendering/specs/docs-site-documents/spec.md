# Delta: docs-site-documents

## ADDED Requirements

### Requirement: The Rendering & Performance block shall cover the dual-environment pipeline

The Advanced Usage category SHALL contain, within the `Rendering & Performance` group and in this order: `ssr-and-ssg` (render pipeline, dev/prod/generate modes, blocked paths, context isolation), `hydration-and-transfer` (payload lifecycle incl. initial-window gating, signal-value transfer, codec, compression, flicker-free resource transfer), `async-rendering-and-boundaries` (async setup, Suspense, ClientOnly, scheduler reveal), `transition`, `teleport`, `loading-screen`, and `styling-deep-dive` (`css_text`/`css_text_template`, reactive scoped styles, unlayered app styles, full cascade model). Numeric behavior contracts quoted in prose SHALL match the owning behavior at authoring time.

#### Scenario: Pipeline pages present and ordered

- **WHEN** the manifest is validated
- **THEN** the seven pages exist at `/documents/advanced/...` in reading order with populated TOCs and cross-links between them

#### Scenario: Hydration page states the gating contract

- **WHEN** `hydration-and-transfer` is read
- **THEN** it documents that the payload applies to the initial window only and tells readers how per-instance transfer ids avoid cross-page collisions

### Requirement: Advanced pages may be visually grouped inside a category

`DocsPageEntry` SHALL accept an optional `group` label; the sidebar SHALL render a sub-header when consecutive entries change group, while route generation and Prev/Next ordering SHALL treat groups as invisible.

#### Scenario: Group header renders, ordering unaffected

- **WHEN** the Advanced category has entries with groups `Realtime & RPC`, then `Rendering & Performance`
- **THEN** the sidebar shows two sub-headers and Prev/Next walks all pages in manifest order ignoring groups

## MODIFIED Requirements

### Requirement: A manifest shall be the single source of truth for the docs structure

docs_app SHALL define a `DOCS_SECTIONS` manifest in `docs_app/docs_manifest.py`: an ordered list of sections, each with a `title` and an ordered list of page entries. Each page entry SHALL have `label` (nav label) and `path` (absolute route path), MAY have a `group` label, and exactly one of `source` (Markdown resource path, relative to the app package) or `component` (`"module:Attr"` lazy reference). docs_app SHALL also define a `DOCS_INDEX` entry representing the `/documents` index route. The route children under `/documents` SHALL be generated from the manifest (the `DOCS_INDEX` entry first, then the section page entries in order). The docs sidebar, the Navbar "Documents" dropdown, and Prev/Next ordering SHALL be generated from the section page entries only — the index SHALL NOT appear in navigation or paging. Paths SHALL be unique across the manifest. Every page path SHALL equal the docs root (`DOCS_ROOT`) or be a path under it, so the manifest-owned routes always live inside the `/documents` subtree. Page paths SHALL additionally follow the category section model prefixes defined by that requirement.

#### Scenario: Routes generated from manifest

- **WHEN** the router is constructed
- **THEN** the `/documents` parent route's children correspond one-to-one with manifest entries (the `DOCS_INDEX` entry followed by the section page entries), in manifest order, each using `lazy()` loading

#### Scenario: Invalid entry rejected

- **WHEN** a manifest entry sets both `source` and `component`, or neither
- **THEN** a `WebComPyException` (or assertion error at import/validation time) identifies the offending entry

#### Scenario: Path outside docs root rejected

- **WHEN** a manifest entry's `path` is not equal to `DOCS_ROOT` and does not start with `DOCS_ROOT + "/"`
- **THEN** a `WebComPyException` at import/validation time identifies the offending entry

#### Scenario: Manifest consistency test

- **WHEN** the docs manifest unit test runs
- **THEN** it verifies paths are unique, every `source` file exists in `docs_app/documents/`, and generated routes match the manifest
