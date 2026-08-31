# Proposal: feat-i18n

## Why

Internationalization is a baseline expectation for production web applications: Angular ships i18n in the core, and Vue/Svelte/React ecosystems all have quasi-official solutions. WebComPy has none, and its "no JavaScript" promise means users cannot adopt JS i18n libraries — the framework must provide at least the core: reactive locale state, message catalogs with interpolation and pluralization, and SSR-correct locale resolution. The existing theme system already demonstrates the exact patterns needed (DI-managed state, cookie persistence, SSR-safe initial resolution from request headers), so i18n can be built on proven ground.

## What Changes

- New `webcompy.i18n` package:
  - `I18nManager` — DI-managed (ThemeManager pattern): holds the `locale: Signal[str]`, message catalogs, fallback locale, and exposes the translation function.
  - `use_i18n()` composable returning `(locale, t, controller)` — `locale` signal, `t(key, **params)` translation function, controller for switching.
  - Reactive translation: `t()` reads `locale.value` internally, so template interpolations using `t(...)` automatically re-render on locale switch through normal signal tracking — no special mechanism.
- Message catalogs: nested dicts per locale with dot-path keys (`"nav.home"`), `{name}`-style interpolation, and CLDR-category plural dicts (`{"one": ..., "other": ...}`) with a pipe shorthand for two-category languages. Missing keys resolve through a fallback chain (`de-AT → de → fallback_locale`) and finally return the key itself.
- Pluralization: built-in minimal CLDR plural-rule table covering common locales; an opt-in Babel adapter provides full CLDR coverage for projects that add the Babel dependency (same opt-in pattern as the CodeBlock Pygments adapter).
- Locale resolution and persistence: browser reads/writes a locale cookie via the existing cookie port; SSR resolves from the request cookie (provided to the manager automatically through `ServerCookiePort`), then the default locale. First-visit language negotiation is intentionally excluded so SSR/SSG output and browser hydration always agree (see D6).
- docs_app gains a multilingual demo as dogfooding.

## Capabilities

### New Capabilities

- `i18n`: Internationalization core — DI-managed locale state, `use_i18n()` composable, message catalogs with dot-path keys, interpolation, CLDR pluralization (built-in minimal table + opt-in Babel adapter), fallback chains, cookie persistence, and SSR locale resolution.

### Modified Capabilities

(none)

## Impact

- **Code**: new `packages/webcompy/src/webcompy/i18n/` package; DI key and app-level wiring following the theme pattern; request-cookie resolution helper in the core package (theme `_server.py` pattern); unit tests.
- **APIs**: additive only (`webcompy.i18n`, `use_i18n`). No breaking changes.
- **Dependencies**: none required (built-in plural table); Babel optional for the adapter.
- **Docs**: docs_app multilingual demo page (EN/JA) exercising switching, interpolation, and pluralization.

## Known Issues Addressed

(none)

## Non-goals

- First-visit language negotiation (`navigator.language` in the browser, `Accept-Language` on the server). These signals are mutually invisible across the SSR/client boundary, so without a hydration transfer of the resolved value they break first-render/hydration agreement (e.g. SSG + a non-default browser locale). Deferred to a follow-up change that pairs them with an app-scoped locale transfer.
- Number/date/time formatting in v1 (deferred to the Babel adapter path in a later change).
- Lazy loading of per-locale catalogs (v1 catalogs are provided statically at setup).
- RTL layout support.
- Translation tooling (extraction, XLIFF/PO file formats, machine-translation integration).
- Per-component catalog scoping beyond plain key namespaces (applications namespace via key structure).
