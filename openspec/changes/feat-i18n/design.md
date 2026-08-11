# Design: feat-i18n

## Context

WebComPy's theme system provides the exact architectural pattern i18n needs: `ThemeManager` is DI-managed under a key, injected by the `use_theme()` composable (raising `LookupError` when absent) and returning `(signal, controller)` (`ui/composables/_theme.py`); persistence uses `COOKIE_PORT_KEY` (`ui/theme/_cookie.py`); SSR-safe initial resolution parses request headers (`read_theme_from_cookie(headers)` in `ui/theme/_server.py`, accepting Mapping or Sequence header forms). The CodeBlock lexer system provides the opt-in heavy-dependency pattern: small built-in coverage, with the Pygments adapter shipped but never imported unless the user adds the dependency and registers it.

Grounded facts (verified in codebase):

- DI provide/inject with app-scoped managers and composable accessors is the established state-sharing pattern (theme).
- Cookie read/write ports exist for both browser (`COOKIE_PORT_KEY`) and SSR (header parsing helper).
- Template interpolations track signal dependencies automatically; a function reading a Signal inside an interpolation registers the dependency.
- `webcompy.i18n` does not exist; `ui/` holds visual toolkit concerns, so i18n ships as its own top-level package (core infrastructure, not UI).

## Goals / Non-Goals

**Goals:**

- Reactive locale state with automatic re-render of translations on switch.
- Catalogs with dot-path keys, interpolation, CLDR pluralization.
- Built-in minimal plural rules + opt-in Babel adapter.
- Fallback chains and missing-key behavior.
- Cookie persistence + SSR locale resolution (cookie → Accept-Language → default).

**Non-Goals:**

- Formatting (number/date), lazy catalogs, RTL, translation tooling (see proposal Non-goals).

## Decisions

### D1: I18nManager in DI, use_i18n() composable (theme pattern)

`I18nManager` is provided in the app DI scope under an i18n key; `use_i18n()` injects it (raising `LookupError` when absent, matching `use_theme`) and returns `(locale, t, controller)`. The manager holds catalogs, fallback locale, and the `locale: Signal[str]`. Rationale: identical lifecycle/scope semantics to the theme system — per-app state, SSR-safe, testable with the testing scope helpers. Alternative (module-global registry) rejected: violates the no-new-globals invariant.

### D2: Reactivity for free — t() reads locale.value

`t(key, **params)` resolves the catalog for `locale.value` at call time. Because template interpolations (`{{ t("nav.home") }}`) track any Signal read during evaluation, every translation automatically depends on the locale signal; switching locale re-renders all translations through the existing reactive graph. No subscription registry, no special template support. This is the central simplicity argument: the signal system already solves "re-render when locale changes" once `t` touches the signal.

### D3: Catalog format — nested dicts, dot-path keys, CLDR plural dicts

Catalogs are `{locale: {nested dicts}}`; keys resolve by dot path (`"nav.home"` walks nesting). Leaf values are strings (interpolated with `{param}` placeholders) or plural dicts keyed by CLDR categories (`{"one": "{count} item", "other": "{count} items"}`); a pipe shorthand (`"{count} item|{count} items"`) maps to the two most common categories for brevity. `t(key, count=N, **params)` selects the plural category from `count` and interpolates. Rationale: nested dicts are plain Python data (no file-format dependency), dot paths are the vue-i18n/i18next norm, and CLDR categories (not positional forms) are the correct plural model for arbitrary locales.

### D4: Plural rules — built-in minimal table + opt-in Babel adapter

A compact built-in table maps common locales (~30: en, ja, zh, ko, fr, de, es, pt, it, ru, uk, pl, cs, ar, tr, nl, sv, da, no, fi, vi, th, id, hi, he, el, ro, hu, ...) to their CLDR plural category selectors. Unknown locales fall back to `one/other` Germanic rules with a warning. Projects needing full CLDR add Babel and register the adapter, which replaces the rule source (and unlocks formatting in later work). Rationale: mirrors the CodeBlock/Pygments precedent exactly — zero-dependency default, heavy data opt-in; full Babel locale data would bloat the Pyodide bundle for every app.

### D5: Fallback chain and missing keys

Resolution order for a key: exact locale (`de-AT`) → language (`de`) → `fallback_locale` → return the key string itself. Missing interpolation params render the placeholder literally. Rationale: matches vue-i18n behavior; returning the key (not blank) makes missing translations visible in the UI during development.

### D6: Locale resolution and persistence

Browser: initial locale from the locale cookie via `COOKIE_PORT_KEY`, else `navigator.language`-style default, else the configured default; switching writes the cookie (theme cookie pattern, `path=/`, `SameSite=Lax`). SSR: resolve from the request cookie header (same parsing helper shape as `read_theme_from_cookie`), then the Accept-Language header (highest-q supported locale), then the default. SSR-resolved locale seeds the manager so first render and hydration agree. Rationale: cookie-first gives user choice precedence over browser headers on repeat visits; Accept-Language covers first visits.

### D7: Package placement — webcompy.i18n top-level

i18n is core application infrastructure (like router, forms), not a visual toolkit piece; it ships as `webcompy.i18n` with `I18nManager`, `use_i18n`, catalog types, and the plural-rule registry. The opt-in Babel adapter lives in the package but is never imported by default (Pygments adapter precedent).

## Risks / Trade-offs

- **Built-in table coverage**: locales outside the table get Germanic rules + warning. Mitigation: adapter path; table growth is cheap data.
- **Accept-Language parsing edge cases**: malformed headers fall back to default; q-value sorting implemented conservatively with tests.
- **SSR/browser locale mismatch**: if the cookie changes between SSR and hydration (rare), the client locale wins post-hydration; the manager is seeded from SSR resolution to keep first paint consistent.
- **Plural category correctness**: the minimal table must be right for the locales it claims; each entry is data-tested against known CLDR examples (e.g. ru few/many boundaries, ar categories).
