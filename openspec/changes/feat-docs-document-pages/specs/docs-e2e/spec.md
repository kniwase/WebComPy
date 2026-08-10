# Delta: docs-e2e

## ADDED Requirements

### Requirement: Docs E2E tests shall cover the documentation section pages

The docs E2E suite SHALL include tests for the documentation section (`/documents` and its child pages) exercising: page titles, sidebar presence and active state, TOC anchor navigation, Markdown-rendered content (heading ids, highlighted code blocks), and Prev/Next navigation. These tests SHALL run in both prod and static serving modes via the existing `docs_page_on` fixture, and SHALL assert no console errors per the existing conventions.

#### Scenario: Sidebar and active state

- **WHEN** the E2E test visits `/documents/getting-started/installation`
- **THEN** the sidebar is visible and the Installation entry has the active class

#### Scenario: TOC anchor jump

- **WHEN** the E2E test clicks a TOC link on a Markdown docs page
- **THEN** the URL hash updates and the target heading is scrolled into view, without a full page reload

#### Scenario: Prev/Next navigation

- **WHEN** the E2E test clicks the Next link on a docs page
- **THEN** the browser navigates to the manifest-successor page and the sidebar active state follows

#### Scenario: Static mode parity

- **WHEN** the same docs section tests run against the statically generated site
- **THEN** titles, sidebar, TOC, and Prev/Next behave identically to prod mode
