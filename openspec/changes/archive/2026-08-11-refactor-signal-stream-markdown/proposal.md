# Proposal: refactor-signal-stream-markdown

## Why

The signal-stream page is the only docs content page still defined as a hand-written Python component tree (`Section`/`InlineCode`/`CodeBlock` with its own `.page-container` layout), while Installation and Quickstart are Markdown-backed pages rendered through `docs_page_template`. This split gives the page different typography, no TOC aside, and forces content edits through Python code. The content is purely static prose and code examples, so it converts to Markdown without loss.

## What Changes

- Convert the signal-stream page content into a Markdown document `docs_app/documents/signal_stream.md` (frontmatter + body), rendered through the shared `docs_page_template` with prose typography and the TOC aside.
- Rewrite `docs_app/pages/document/signal_stream.py` as an async Markdown-backed page component following the Installation/Quickstart pattern (`load_markdown_document` + `docs_page_template` + `DOCS_PAGE_SCOPED_STYLE`).
- Switch the manifest entry from `component` to `source: "documents/signal_stream.md"`. The derived component reference (`docs_app.pages.document.signal_stream:SignalStreamPage`) and the URL (`/documents/signal-stream`) stay unchanged.
- Unify the page name to "Signals and Streams": manifest label, frontmatter title, and H1 all use this form (current label is "Signal Stream" while the H1 is "Signals and Streams"). Sidebar, Navbar dropdown, Prev/Next link text, and the browser title update accordingly.
- Remove the now-unused component template `docs_app/templates/document/signal_stream.py`.
- Update docs E2E assertions that reference the old title/label, and add TOC coverage for the converted page.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: the signal-stream requirement changes from "component entry, no Markdown conversion" to a Markdown-backed `source` entry with unchanged URL, and the Prev/Next scenario page name updates to "Signals and Streams".

## Impact

- **Code**: `docs_app/docs_manifest.py`, `docs_app/pages/document/signal_stream.py`, new `docs_app/documents/signal_stream.md`, removed `docs_app/templates/document/signal_stream.py`.
- **Tests**: `e2e/docs/test_signal_stream.py`, `e2e/docs/test_quickstart.py`, `e2e/docs/test_documents.py` (label/title text updates + TOC assertions).
- **Specs**: `docs-site-documents` (two modified requirements).
- **No impact** on the manifest schema (`source`/`component` validation unchanged; `DOCS_INDEX` stays component-backed), routing structure, or any package under `packages/`.

## Known Issues Addressed

None.

## Non-goals

- No URL change: `/documents/signal-stream` is preserved.
- No conversion of the `/documents` index page (`DOCS_INDEX` remains component-backed).
- No changes to the manifest schema, `validate_manifest`, or `page_component_ref` derivation rules.
- No content changes beyond the format conversion and the name unification (the prose itself is preserved).
