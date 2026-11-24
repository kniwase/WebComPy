# Proposal: feat-docs-i18n-pwa

## Why

i18n (#291) and PWA (#290) arrived as first-pass pages written in spec voice. i18n's most surprising contract — cookie-only locale persistence with deterministic SSR/hydration parity — and PWA's build-time service-worker model (no user JS) each need task-oriented treatment, and both are small enough to deepen in one change.

## What Changes

- Rework `i18n.md` to the Advanced structure: catalog authoring (dot paths, `{param}`), plurals (pipe shorthand, CLDR table, Babel adapter opt-in), fallback chain, `use_i18n` controller in templates (`{{ t("nav.home") }}`-style usage per the actual API), locale switching with cookie-only persistence, and a SSR/hydration parity walkthrough (why the cookie decides deterministically and how a mismatch arises).
- Rework `pwa.md`: declarative config surface, manifest generation/serving/injection, framework-owned service worker template (why no user JS), precache enumeration + clean-URL resolution, runtime caching rules and isolated caches, offline navigation fallback, base-URL-scoped registration, dev-mode-off, and a testing recipe (install/activate/update observation).
- Add both pages' group assignment (`Rendering & Performance` for PWA serving notes; i18n stays in Architecture & Integration adjacent to storage) per ③-5's grouping.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `docs-site-documents`: i18n/PWA page-structure requirement (Advanced structure + parity walkthrough presence).

## Impact

- `docs_app/documents/i18n.md`, `docs_app/documents/pwa.md` rewritten; manifest group keys; E2E page tests extended for new headings; no code changes

## Known Issues Addressed

None.

## Non-goals

- Translating the docs site itself
- Locale data beyond what the i18n spec defines
