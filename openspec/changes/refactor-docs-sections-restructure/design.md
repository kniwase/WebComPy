# Design: refactor-docs-sections-restructure

## Context

`docs_app/docs_manifest.py` defines `DOCS_SECTIONS` with two sections (Getting Started with 2 nested-URL pages; Guides with 15 flat-URL pages). Page components are auto-derived from the `source` file stem (`documents/signal_stream.md` → `docs_app.pages.document.signal_stream:SignalStreamPage`), so URL changes do not require file renames. `prev_next()` flattens section order; the sidebar renders sections with their titles.

## Goals / Non-Goals

**Goals:**

- Land the 4-category skeleton's first three categories with category-prefixed URLs.
- Make body cross-links correct (URL-based) and enforce it as a spec rule.
- Leave every subsequent docs change working on a settled structure.

**Non-Goals:**

- Content rewrite; Guides section creation; new pages; `.md` renames; old-URL redirects.

## Decisions

### 1. Page-to-category mapping

| Page (file) | From | To |
|---|---|---|
| installation / quickstart | `/documents/getting-started/*` | unchanged |
| ui_primitives | `/documents/ui-primitives` | `/documents/basic/ui-primitives` |
| overlay | `/documents/overlay` | `/documents/basic/overlay` |
| disclosure | `/documents/disclosure` | `/documents/basic/disclosure` |
| custom_elements | `/documents/custom-elements` | `/documents/advanced/custom-elements` |
| signal_stream | `/documents/signal-stream` | `/documents/advanced/signal-stream` |
| readonly_signal | `/documents/readonly-signal` | `/documents/advanced/readonly-signal` |
| i18n | `/documents/i18n` | `/documents/advanced/i18n` |
| loading_screen | `/documents/loading-screen` | `/documents/advanced/loading-screen` |
| event_source | `/documents/event-source` | `/documents/advanced/event-source` |
| websocket | `/documents/websocket` | `/documents/advanced/websocket` |
| typed_realtime | `/documents/typed-realtime` | `/documents/advanced/typed-realtime` |
| rpc | `/documents/rpc` | `/documents/advanced/rpc` |
| rpc_contracts | `/documents/rpc-contracts` | `/documents/advanced/rpc-contracts` |
| rpc_websocket | `/documents/rpc-websocket` | `/documents/advanced/rpc-websocket` |
| pwa | `/documents/pwa` | `/documents/advanced/pwa` |

Rationale for edge cases:

- **UI trio → Basic**: themed-component usage is what most apps need daily; the headless-contract deep dive later gets its own Advanced page (③-6), not a move.
- **custom-elements → Advanced**: as a dedicated page it documents wrapper boundaries, `observed_attributes`, and registration ordering — interop detail. Its basic naming essentials move into the Basic Components page when ③-2 rewrites content; meanwhile the Advanced page carries the recommended `@define_component()` form (post-#286) since stale-example cleanup of the round-trip validation text belongs to ③-1's sweep — ③-0 only relocates.
- **i18n / pwa / loading-screen → Advanced**: dual-environment parity and build-integration concerns.

### 2. Section titles are the category names

`Getting Started`, `Basic Usage`, `Advanced Usage` in that order. The sidebar renders sections as today (one level); a later change may introduce visual subsection grouping inside Basic/Advanced — the manifest schema keeps `title: str` unchanged here, so no schema work.

### 3. No redirects (hard migration)

**Why**: the moved URLs exist for weeks, are mostly referenced internally, and the router's guard-based redirect machinery would add machinery for pages nobody has bookmarked yet. Old paths 404 via the existing `NotFound` default. **Alternative rejected**: `before_route_change` redirect map — dead code once internal links are fixed, external risk judged negligible.

### 4. Links as site URLs, enforced in-spec

Three `.md` relative links (`rpc.md:101`, `rpc_websocket.md:160-161`) currently render as `<a href="./rpc_websocket.md">` and 404 in the site. They and the moved targets become absolute paths (`/documents/advanced/rpc-websocket`), optionally with heading anchors (`/documents/advanced/websocket#the-gaprefetch-recipe`). The new spec requirement makes the rendered-link rule testable: a unit test scans `docs_app/documents/*.md` for `](` targets that end with `.md` and fails.

### 5. Tests follow mechanically

Unit: manifest validation fixtures, prev/next order expectations (first page is now Installation; last is PWA under Advanced), and the new `.md`-link scanner. E2E: all `docs_page_on("/documents/...")` navigation targets updated; group names unchanged.

## Risks / Trade-offs

- [Any external link to old flat URLs breaks] → Accepted: no redirects per decision 3; low exposure window.
- [Subsequent stacked changes assume this mapping; a late merge could renumber categories] → Each stacked design references this change by name and the archive-sync order (this change first).
- [The Prev/Next spec scenario pins stale page names] → MODIFIED to a generalized "middle page" scenario.

## Migration Plan

Single docs_app commit set; deployment is `webcompy generate` as usual. Rollback = revert (URLs revert with it).

## Open Questions

None.
