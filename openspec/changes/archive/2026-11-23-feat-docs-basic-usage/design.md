# Design: feat-docs-basic-usage

## Context

Basic Usage must teach what a newcomer needs in one day. Feature classification (Basic vs Advanced) was settled during planning with the heuristic: Basic = required to ship a CRUD-style SPA, browser-only mental model suffices; Advanced = dual-environment, distributed state, optimization, interop. The manifest category model (③-0) and orientation pages (③-1) already landed in the planned merge order.

## Goals / Non-Goals

**Goals:** complete the Basic category in dependency order; consistent per-page voice (concept → minimal runnable example → behavior notes → next steps); each split topic cross-linked to its Advanced half.

**Non-Goals:** exhaustiveness (API Reference does that); tutorial narrative (Guides does that); Advanced mechanics.

## Decisions

### 1. Page list and ordering (manifest order = reading order)

```
Core:  components → template-html → reactive-state → elements-and-events → markdown-documents
App:   routing → forms → http-and-async → styling-and-themes → storage → error-handling
(existing: ui-primitives → overlay → disclosure — relocated by ③-0, revised here;
 kept at the end of the Basic ordering as "component library" block)
```

**Why this order**: each page only uses concepts from earlier ones (reactive basics before template reactivity nuance; template before components' slot content; components before forms' `:bind` + controls). `markdown-documents` sits in Core because writing docs *for your own site* is a first-day need given the framework renders Markdown itself.

### 2. Per-page outline convention

```
H1 + lead (what/when)
H2 "At a glance"  — minimal runnable snippet pair (setup → render)
H2 topic sections — behavior with small examples, tables where enumerable
H2 "Notes & caveats" — equality, SSR visibility ONLY if needed for correct basic use
H2 "Next steps" — Advanced counterpart link + related page links
```

Frontmatter `description` written as the search-result sentence. Headings sized for the TOC (H2 = TOC entries).

### 3. Topic boundary rules (what the Basic page must NOT include)

| Topic | Basic stops at | Advanced half (which change) |
|---|---|---|
| components | naming/derivation, props/slots, 4 hooks, static scoped dict | reactive scoped styles, custom-element interop details (③-5/③-6) |
| template-html | syntax + filters + loop metadata | `css_text_template`, expression internals (③-5) |
| reactive-state | primitives + `use_*` factory-skip mention | transfer codec, signal-value-transfer internals (③-5) |
| routing | flat routes, params, active link, hash vs history | nested children, lazy, guards, scroll restoration (③-6) |
| forms | field/form, `:bind`, UI controls themed usage | headless contracts, DI-confined FormField deep dive (③-6) |
| http-and-async | `HttpClient` verbs, `use_async_result`, states | `watch`, `transfer=False`, scheduler scoping (③-5) |
| storage | get/set persistence | `sync_tabs` (③-6) |
| error-handling | ErrorBoundary usage | SSR/SSG policy, implicit boundaries (③-5) |

### 4. Existing UI trio revision

`ui-primitives` becomes the conceptual entry (two-layer contract, three import paths, stylesheet delivery); `overlay` and `disclosure` keep their catalog role, gain component tables (name, purpose, key props, headless/themed availability) and a link back to primitives; all three adopt the outline convention.

### 5. Verification without a docs test harness

Each code block is checked manually at authoring time against current APIs (`docs_app` itself is the compile check for component examples: pages' snippets get a minimal mirrored E2E assertion where cheap — e.g. forms page's controls appear in the new Examples demo). Full copy-paste test coverage is out of scope; the AI review perspective (webcompy-review) treats stale example APIs as must-fix.

## Risks / Trade-offs

- [11 pages authored in one change is large] → Ordered task groups allow incremental PR review per page; the change stays one spec unit (category completion).
- [Boundary drift (Basic page teaching Advanced content)] → §3 table is the review checklist; spec scenario asserts the required links exist.
- [Examples rot as the API moves (see #286)] → Every snippet uses the current recommended form; ③-1 established the sweep rule.

## Migration Plan

Additive manifest entries + content. No URL moves.

## Open Questions

None — page titles/labels finalized in the implementation tasks.
