# Proposal: refactor-docs-sections-restructure

## Why

The docs section has grown to 17 pages in two flat categories (Getting Started + a 15-page "Guides" that is actually a feature reference). The planned documentation system has four top categories — Getting Started / Guides (step-by-step tutorial) / Basic Usage / Advanced Usage — and the later content changes assume that structure. This change performs the structural migration first, so every subsequent docs change adds pages into a settled skeleton instead of reshuffling it.

## What Changes

- Restructure `DOCS_SECTIONS` into the category model: `Getting Started` (existing two pages, URLs unchanged), `Basic Usage`, and `Advanced Usage`. The `Guides` category is introduced later (by the tutorial change) once its pages exist; no empty sections are added.
- Move the 15 current guide pages to category-prefixed URLs — 3 to `/documents/basic/*` (UI Primitives, Overlay Components, Disclosure & Feedback) and 12 to `/documents/advanced/*` (Custom Elements, Signals and Streams, Read-only Signals, Internationalization, Loading Screen, Server-Sent Events, WebSocket, Typed Realtime, RPC, RPC Contracts, RPC over WebSocket, Progressive Web App). Within `Advanced`, pages are ordered for the intended reading flow (Custom Elements first; RPC before RPC Contracts).
- **No legacy URLs and no redirects**: old flat paths (`/documents/signal-stream`, …) are removed and fall through to the 404 page. The site's external surface is young and internal-only; keeping stale URLs would be debt.
- Fix cross-links inside document bodies: relative `.md` file links (broken at render time — they link to the source file, not the page) become absolute rendered-site URLs, and existing `/documents/...` links are updated to the new paths.
- A new normative rule: cross-links in Markdown bodies SHALL use rendered-site URLs (optionally with heading anchors), never `.md` source paths; a scan test also resolves every absolute `/documents` target against the manifest page paths.
- Manifest validation enforces the category model: a section with an unknown or missing title, a wrong section order, an empty `pages` list, or page paths outside the category prefix is rejected at import time.
- Update E2E tests and unit tests that reference the old paths.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: manifest section model gains the category URL scheme (`/documents/<category>/...`) with import-time validation of section titles, order, and non-empty pages; the signal-stream URL-preservation requirement is superseded (the page moves like the others); Prev/Next scenario generalized; new requirement for body cross-link correctness including manifest-path resolution of absolute targets.

## Impact

- `docs_app/docs_manifest.py`: section restructure and 15 `path` updates (labels and `source` file names unchanged — page-component derivation by stem keeps working)
- `docs_app/documents/*.md`: 3 relative `.md` links → URLs; ~7 absolute links updated to new paths
- `e2e/docs/test_*.py`: navigation paths updated
- `tests/`: manifest-related tests (prev/next order, validation fixtures) updated; docs Markdown body link scan tests added (dual-run classification baseline refreshed)
- No framework package changes; no URL redirects (intentional)

## Known Issues Addressed

None.

## Non-goals

- Rewriting or merging any page content (later changes handle content)
- Adding the Guides/tutorial section or any new pages
- Splitting combined topics across Basic/Advanced halves (later changes do this; ③-0 moves whole pages to their best-fit category)
- Redirect/compat shims for old URLs
- `.md` file renames (page component derivation would churn for no user-facing benefit)
