# Delta: docs-site-documents

## ADDED Requirements

### Requirement: The docs manifest shall follow the category section model

The `DOCS_SECTIONS` manifest SHALL consist of top-level category sections in the order `Getting Started`, `Basic Usage`, `Advanced Usage`, with a `Guides` category inserted between `Getting Started` and `Basic Usage` when tutorial pages exist. Each page's manifest `path` SHALL start with the category's URL prefix: `/documents/getting-started/`, `/documents/guides/`, `/documents/basic/`, or `/documents/advanced/`. Section titles other than these category names SHALL NOT be introduced by structural changes. A category without pages SHALL be omitted from the manifest rather than carried as an empty section, and manifest validation SHALL reject a section that omits its `title` or contains an empty `pages` list.

#### Scenario: Page paths carry the category prefix

- **WHEN** the manifest is validated
- **THEN** every page entry's `path` starts with its category's prefix, and the category sections appear in the defined order

#### Scenario: Empty section rejected

- **WHEN** the manifest is validated and a category section has an empty `pages` list
- **THEN** a `WebComPyException` at import/validation time identifies the offending section

#### Scenario: Missing section title rejected

- **WHEN** the manifest is validated and a section omits its `title`
- **THEN** a `WebComPyException` at import/validation time identifies the offending section

### Requirement: Docs body cross-links shall use rendered-site URLs

Cross-document links inside `docs_app/documents/*.md` bodies SHALL use absolute rendered-site URLs (category-prefixed paths, optionally with a `#heading-id` fragment) and SHALL NOT link to `.md` source files. A unit test SHALL scan all docs Markdown bodies for link targets ending in `.md` and fail when any is found. The same scan SHALL fail when any absolute `/documents`-rooted link target, after stripping a `#heading-id` fragment and a trailing slash, matches neither the docs root nor a manifest page path.

#### Scenario: Relative source-file link rejected

- **WHEN** a docs body contains `[Text](./other.md)`
- **THEN** the docs link scan test fails naming the file and line

#### Scenario: Cross-page anchor link is valid

- **WHEN** a docs body links to `/documents/advanced/websocket#the-gaprefetch-recipe`
- **THEN** the scan test passes and the browser performs a same-path anchor navigation

#### Scenario: Unknown target rejected

- **WHEN** a docs body links to an absolute `/documents/...` path that is not a manifest page path (ignoring any `#heading-id` fragment)
- **THEN** the docs link scan test fails naming the file and line

## MODIFIED Requirements

### Requirement: A manifest shall be the single source of truth for the docs structure

docs_app SHALL define a `DOCS_SECTIONS` manifest in `docs_app/docs_manifest.py`: an ordered list of sections, each with a `title` and an ordered list of page entries. Each page entry SHALL have `label` (nav label) and `path` (absolute route path), and exactly one of `source` (Markdown resource path, relative to the app package) or `component` (`"module:Attr"` lazy reference). docs_app SHALL also define a `DOCS_INDEX` entry representing the `/documents` index route. The route children under `/documents` SHALL be generated from the manifest (the `DOCS_INDEX` entry first, then the section page entries in order). The docs sidebar, the Navbar "Documents" dropdown, and Prev/Next ordering SHALL be generated from the section page entries only — the index SHALL NOT appear in navigation or paging. Paths SHALL be unique across the manifest. Every page path SHALL equal the docs root (`DOCS_ROOT`) or be a path under it, so the manifest-owned routes always live inside the `/documents` subtree. Page paths SHALL additionally follow the category section model prefixes defined by that requirement.

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

### Requirement: The docs layout shall provide Prev/Next navigation

`DocsLayout` SHALL render Prev/Next footer links computed reactively from the current route path and the flattened manifest page order. On the first page the Prev link SHALL be omitted; on the last page the Next link SHALL be omitted. Both Markdown and component-backed pages SHALL receive Prev/Next. Paging crosses category boundaries in manifest order.

#### Scenario: Middle page shows both links

- **WHEN** the user is on any docs page that is neither first nor last in flattened manifest order
- **THEN** the footer links to its predecessor (Prev) and successor (Next), even across category boundaries

#### Scenario: Reactive update on navigation

- **WHEN** the user navigates between docs pages
- **THEN** the Prev/Next links update without the layout remounting

## REMOVED Requirements

### Requirement: The existing signal-stream page shall join the docs section without URL change

**Reason**: the category URL scheme assigns every page a category-prefixed path; the signal-stream page moves to `/documents/advanced/signal-stream` like the other guide pages, so the URL-preservation guarantee is superseded.

**Migration**: the page keeps its file (`documents/signal_stream.md`), label, title, and rendering; only the path changes. Manifest, cross-links, and E2E navigation are updated in the same change.
