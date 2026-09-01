# Design: feat-docs-advanced-integration

## Context

③-2 established the split-policy table: every Basic page that stops at a boundary must link to an Advanced continuation. This change creates that continuation set for architecture concerns. Middleware (#283) supplies the documented interception model; routing depth exists since #226/#234/#235; DI ports/registries per port-provisioning and di-scope specs.

## Goals / Non-Goals

**Goals:** complete split-policy link targets; make integration surfaces discoverable; uniform Advanced page structure.

**Non-Goals:** framework changes; Basic-level retreading.

## Decisions

### 1. Page list and grouping

All pages carry `group: "Architecture & Integration"`, ordered by dependency: `dependency-injection-deep-dive` (everything else uses scopes) → `middleware` (registered on DI) → `routing-deep-dive` → `plugins` (hooks into DI/middleware registries) → `typed-api-deep-dive` → `ui-headless-contract` → `custom-elements` (revision in place, keeps position) → `persistence-patterns`.

### 2. Recipe orientation over concept orientation

Advanced readers need patterns: middleware page leads with three recipes (auth header injector, response cache logger, offline fetch mock — cross-linked to Examples ③-9); routing page leads with an admin-console pattern (nested layout + guard redirect); DI page leads with "service + fake in tests".

### 3. `persistence-patterns` scope

Single page (not two): sync-tabs mechanics, coalescing behavior, storage-event model, and a decision box (storage vs hydration transfer vs URL state). **Rejected**: folding into middleware page — unrelated mental model.

### 4. custom-elements revision boundary

The page teaches authoring interop components; naming/derivation basics link back to Basic Components (③-2) instead of repeating. Include the `:host` cascade note with `display` precedence.

### 5. Cross-change hygiene

Back-link placeholders from ③-2 ("Next steps → …(Advanced)") resolve at merge time; a link-check unit test (from ③-1's link scanner, extended) validates every in-doc `/documents/...` href resolves to a manifest path — catches drift from stacked changes.

## Risks / Trade-offs

- [Seven rewrites could be trimmed to five by merging plugins into middleware] → kept separate: plugin surface predates middleware; plugin authors need a standalone entry.
- [Admin-console pattern grows code samples that no demo runs] → accepted (code is reviewed copy-paste level; runtime proof lives with ③-9 Examples).

## Migration Plan

Additive + one revision; merge after ③-0/③-2/③-4/③-5 (groups and back-link targets exist).

## Open Questions

None.
