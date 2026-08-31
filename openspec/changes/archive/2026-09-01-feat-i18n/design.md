# Design: feat-i18n

## Context

WebComPy's theme system provides the exact architectural pattern i18n needs: `ThemeManager` is DI-managed under a key, injected by the `use_theme()` composable (raising `LookupError` when absent) and returning `(signal, controller)` (`ui/composables/_theme.py`); persistence uses `COOKIE_PORT_KEY` (`ui/theme/_cookie.py`); SSR-safe initial resolution parses request headers (`read_theme_from_cookie(headers)` in `ui/theme/_server.py`, accepting Mapping or Sequence header forms). The CodeBlock lexer system provides the opt-in heavy-dependency pattern: small built-in coverage, with the Pygments adapter shipped but never imported unless the user adds the dependency and registers it.

Grounded facts (verified in codebase):

- DI provide/inject with app-scoped managers and composable accessors is the established state-sharing pattern (theme).
- Cookie read/write ports exist for both browser (`COOKIE_PORT_KEY`) and SSR (`ServerCookiePort` seeded from the request Cookie header and provided to `COOKIE_PORT_KEY` by `ServerRenderContext`, `webcompy-server/.../_context.py:51`).
- Template interpolations track signal dependencies only when a Signal appears as an expression value; a plain function that reads a Signal internally (returning a non-Signal) is NOT tracked at bind time. `t()` falls in this second category, so D2 requires a small interpolation-binder enhancement (D8) to become reactive.
- The theme system resolves a "system" preference through a client-side `prefers-color-scheme` CSS media query, so it never produces hydrated text and cannot hydration-mismatch; i18n locale drives rendered text and must agree at hydration (see D6 exclusion).
- `webcompy.i18n` does not exist; `ui/` holds visual toolkit concerns, so i18n ships as its own top-level package (core infrastructure, not UI).

## Goals / Non-Goals

**Goals:**

- Reactive locale state with automatic re-render of translations on switch.
- Catalogs with dot-path keys, interpolation, CLDR pluralization.
- Built-in minimal plural rules + opt-in Babel adapter.
- Fallback chains and missing-key behavior.
- Cookie persistence + SSR cookie resolution (cookie → default), with first render and hydration guaranteed to agree.

**Non-Goals:**

- Formatting (number/date), lazy catalogs, RTL, translation tooling (see proposal Non-goals).

## Decisions

### D1: I18nManager in DI, use_i18n() composable (theme pattern)

`I18nManager` is provided in the app DI scope under an i18n key; `use_i18n()` injects it (raising `LookupError` when absent, matching `use_theme`) and returns `(locale, t, controller)`. The manager holds catalogs, fallback locale, and the `locale: Signal[str]`. Rationale: identical lifecycle/scope semantics to the theme system — per-app state, SSR-safe, testable with the testing scope helpers. Alternative (module-global registry) rejected: violates the no-new-globals invariant.

### D2: Reactive translation via t() reading locale.value

`t(key, **params)` resolves the catalog for `locale.value` at call time, so every translation reads the locale signal. Because the interpolation binder tracks *any* signal read during expression evaluation once D8 lands — not just signals appearing as expression values — template interpolations (`{{ t("nav.home") }}`) register a dependency on the locale signal through the existing reactive graph; switching locale re-renders all translations. No subscription registry and no per-key reactive wrapper are needed.

### D8: Interpolation tracks signal reads inside called functions

The interpolation binder's eager evaluation pass installs a transient probe consumer (a bare `SignalNode`) while evaluating the expression, then tears it down. If any producer edge was created during evaluation — including reads inside called functions like `t()` — the binder marks the interpolation reactive and wraps it in a `Computed`, exactly as it already does for signals that appear as expression values. Expressions that read no signal are unchanged. Rationale: `Computed` re-evaluation already runs with the computed node as the active consumer, so internal reads are tracked correctly there; this change only fixes the initial "is this expression reactive?" decision.

### D3: Catalog format — nested dicts, dot-path keys, CLDR plural dicts

Catalogs are `{locale: {nested dicts}}`; keys resolve by dot path (`"nav.home"` walks nesting). Leaf values are strings (interpolated with `{param}` placeholders) or plural dicts keyed by CLDR categories (`{"one": "{count} item", "other": "{count} items"}`); a pipe shorthand (`"{count} item|{count} items"`) maps to the two most common categories for brevity. `t(key, count=N, **params)` selects the plural category from `count` and interpolates. Rationale: nested dicts are plain Python data (no file-format dependency), dot paths are the vue-i18n/i18next norm, and CLDR categories (not positional forms) are the correct plural model for arbitrary locales.

### D4: Plural rules — built-in minimal table + opt-in Babel adapter

A compact built-in table maps common locales (~30: en, ja, zh, ko, fr, de, es, pt, it, ru, uk, pl, cs, ar, tr, nl, sv, da, no, fi, vi, th, id, hi, he, el, ro, hu, ...) to their CLDR plural category selectors. Unknown locales fall back to `one/other` Germanic rules with a warning. Projects needing full CLDR add Babel and register the adapter, which replaces the rule source (and unlocks formatting in later work). Rationale: mirrors the CodeBlock/Pygments precedent exactly — zero-dependency default, heavy data opt-in; full Babel locale data would bloat the Pyodide bundle for every app.

### D5: Fallback chain and missing keys

Resolution order for a key: exact locale (`de-AT`) → language (`de`) → `fallback_locale` → return the key string itself. Missing interpolation params render the placeholder literally. Rationale: matches vue-i18n behavior; returning the key (not blank) makes missing translations visible in the UI during development.

### D6: Locale resolution and persistence (cookie-only, hydration-safe)

Both sides consume the *same* information and run the *same* normalization, so first render and hydration cannot diverge:

- Browser: initial locale = `initial_locale` (if the app seeds one) → locale cookie via `COOKIE_PORT_KEY` → `default_locale`. `set_locale` writes the cookie (theme pattern: `path=/`, `SameSite=Lax`).
- SSR/SSG: the `ServerRenderContext` already provides `COOKIE_PORT_KEY` backed by `ServerCookiePort(self._cookie_header)` (`webcompy-server/.../_context.py:51`), so the manager factory reads the *request* cookie automatically — the same cookie the browser will see. Unsupported values normalize to `default_locale` identically on both sides via `_normalize`. The standalone `read_locale_from_cookie` / `resolve_locale` helpers in `webcompy.i18n` mirror `read_theme_from_cookie`'s Mapping/Sequence handling for app authors who seed explicitly.

**Explicitly excluded — first-visit negotiation.** `navigator.language` (browser) and `Accept-Language` (server) are mutually invisible across the SSR/client boundary; using either as a fallback makes SSR/SSG output and browser hydration disagree whenever the server can't see the same signal the client uses (e.g. SSG with no header, non-default browser locale — observed as a 5-text-node hydration mismatch in E2E). Unlike the theme, whose "system" preference resolves through a client-side `prefers-color-scheme` CSS media query and therefore never touches hydrated text nodes, i18n locale drives rendered text and must be agreed at hydration. Negotiation is deferred to a follow-up change that pairs it with an app-scoped locale hydration transfer so the browser inherits the server-resolved value.

### D7: Package placement — webcompy.i18n top-level

i18n is core application infrastructure (like router, forms), not a visual toolkit piece; it ships as `webcompy.i18n` with `I18nManager`, `use_i18n`, catalog types, and the plural-rule registry. The opt-in Babel adapter lives in the package but is never imported by default (Pygments adapter precedent).

## Risks / Trade-offs

- **Built-in table coverage**: locales outside the table get Germanic rules + warning. Mitigation: adapter path; table growth is cheap data.
- **No first-visit language negotiation**: users get `default_locale` on their first visit (cookie-less) even if their browser/server headers suggest otherwise. Mitigation: documented follow-up change adds negotiation together with an app-scoped locale transfer; sites can set a culturally sensible `default_locale` or seed `initial_locale` explicitly.
- **SSG returning visitors**: a static document was baked with `default_locale` while the visitor's cookie holds a later choice; hydration logs a text mismatch and the client value wins post-hydration. This is the same accepted trade-off as the theme on static hosts; dynamic SSR avoids it because both sides read the same request cookie via `ServerCookiePort`.
- **Plural category correctness**: the minimal table must be right for the locales it claims; each entry is data-tested against known CLDR examples (e.g. ru few/many boundaries, ar categories).
- **Template engine regression surface**: the D8 probe touches every interpolation bind path (text, attributes, markdown `for`). The full `test_template_*` and `test_markdown_*` suites must pass unchanged.
