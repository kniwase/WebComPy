# Design: feat-docs-i18n-pwa

## Context

`i18n` spec: DI-managed `I18nManager`, locale `Signal`, dot-path catalogs with `{param}` interpolation, CLDR plurals with pipe shorthand + opt-in Babel, fallback chain, cookie-only persistence with SSR/hydration determinism. `pwa` spec: build-time template SW (no user JS), precache enumeration with clean-URL index resolution, same-origin runtime rules, immediate activation + cache cleanup, offline fallback, base-URL-scoped registration, dev off. Both pages exist as first-pass docs at `/documents/advanced/...`.

## Decisions

1. **i18n parity walkthrough** is the page's centerpiece: sequence diagram cookie → SSR locale → baked signals → browser restore; includes the failure recipe (setting locale in `on_mounted` breaks parity) to teach the constraint rather than assert it. **Rejected**: parity as a one-line note — it's the concept readers get wrong.
2. **PWA page splits into "what gets generated" (manifest, SW file, injection) and "what runs" (caches, activation, offline)** so a reader can preview without memorizing; caching rules presented as a decision table (cache-first / network-first / stale-while-revalidate per resource kind).
3. Both pages adopt the Advanced structure defined in ③-4 (lead/when-to-use/setup/recipes/notes/pitfalls/next-steps) — they're the last pre-restructure voice pages.
4. Groups: i18n → `Architecture & Integration`; pwa → `Rendering & Performance` (serving-adjacent). Cross-links: i18n↔storage↔readonly signals; pwa↔ssr-ssg↔resource transfer.
5. No Babel adapter tutorial depth — one recipe showing opt-in enablement; CLDR table maintenance is a spec concern.

## Risks

- [i18n API surface still young — examples may drift] → link-check + E2E headings; API Reference (③-11) becomes the canonical symbol list.
- [PWA service-worker behavior is hard to E2E in the docs CI] → E2E limited to page rendering; SW behavior verification stays in the pwa spec's own test tier.

## Migration Plan

Content-only rewrites at existing URLs. Merge after ③-5/③-6 (groups exist).

## Open Questions

None.
