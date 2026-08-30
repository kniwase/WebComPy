# Tasks: feat-i18n

## 0. Template interpolation reactive tracking

- [x] 0.1 Extend `webcompy/template/_expression.py` `evaluate()` so that when a `_EvalState` is supplied, expression evaluation runs under a transient probe consumer; set `state.saw_signal = True` when any producer edge was created, and tear the probe down (no leaks) afterward
- [x] 0.2 Add unit tests: an interpolation `{{ f() }}` where `f` reads a Signal re-renders on change; an interpolation where the function reads no Signal stays static

## 1. Core manager and composable

- [x] 1.1 Create `packages/webcompy/src/webcompy/i18n/` package: `I18nManager` (locale `Signal[str]`, catalogs, fallback locale, `t` implementation, `set_locale`), DI key, and app-level wiring following the ThemeManager pattern
- [x] 1.2 Implement `use_i18n()` composable returning `(locale, t, controller)` with lookup-error behavior when no manager is provided (theme composable pattern)

## 2. Catalog resolution

- [x] 2.1 Implement dot-path key resolution over nested catalog dicts and `{param}` interpolation (missing params render literally)
- [x] 2.2 Implement the fallback chain: exact locale → language → fallback locale → return the key
- [x] 2.3 Implement plural selection: CLDR-category dicts, pipe shorthand mapping, `count` parameter interpolation

## 3. Plural rules

- [x] 3.1 Implement the built-in minimal CLDR plural-rule table (~30 common locales incl. category-rich ones: ru few/many boundaries, ar categories) as data with per-locale selector functions; unknown locales fall back to one/other with a warning
- [x] 3.2 Implement the opt-in Babel adapter (shipped unimported, Pygments-adapter pattern): registration API replacing the rule source; guard imports so Babel remains an optional dependency

## 4. Locale resolution and persistence

- [x] 4.1 Browser: initial locale from the locale cookie via `COOKIE_PORT_KEY`; `set_locale` writes the cookie (theme cookie pattern: `path=/`, `SameSite=Lax`); cookie-absent default handling
- [x] 4.2 SSR: header resolution helper (cookie header → Accept-Language with q-value sorting among supported locales → default), mirroring `read_theme_from_cookie`'s Mapping/Sequence header handling; seed the manager with the SSR-resolved locale

## 5. Unit tests (`tests/test_i18n.py`, browserless)

- [x] 5.1 Manager/composable: provided manager returns (locale, t, controller); missing manager raises lookup error
- [x] 5.2 Catalog resolution: dot-path nesting, interpolation incl. missing-param literal rendering, fallback chain (region→language→fallback→key)
- [x] 5.3 Pluralization: en one/other via dict and pipe shorthand; ru/ar boundary cases from the built-in table; unknown-locale fallback warning
- [x] 5.4 Reactivity: locale switch updates `t` results through signal tracking (TestRenderer render assertion; relies on task 0.1)
- [x] 5.5 Resolution/persistence: cookie read/write via fake cookie port; SSR header resolution order (cookie beats Accept-Language; q-value sorting; default fallback)

## 6. Docs and dogfooding

- [x] 6.1 Add a docs_app multilingual demo (EN/JA): locale switcher via `use_i18n`, interpolation and plural examples; link from docs navigation
- [x] 6.2 Document catalog format, plural rules (built-in table coverage, Babel adapter opt-in), fallback chain, and SSR resolution order in the docs guide

## 7. Validation

- [x] 7.1 `uv run ruff check .` and `uv run ruff format --check .` pass
- [x] 7.2 `uv run pyright` passes
- [x] 7.3 `uv run python -m pytest tests/ --tb=short` passes (includes the full `test_template_*` / `test_markdown_*` regression suites for task 0)

## 8. Cookie-only locale resolution revision (hydration-safe, per D6)

- [x] 8.1 `i18n/_server.py`: drop Accept-Language parsing; `resolve_locale` becomes cookie → supported match → default (keep `read_locale_from_cookie` and Mapping/Sequence header handling)
- [x] 8.2 `i18n/_manager.py`: remove `navigator.language` detection (`_browser_language`, `HOST_PORT_KEY` use); `_resolve_initial` = initial_locale → cookie → default; update docstrings
- [x] 8.3 `tests/test_i18n.py`: replace Accept-Language tests with cookie-only contract tests (cookie wins, no cookie → default, unsupported cookie → default, Accept-Language ignored); add parity test using `ServerCookiePort`
- [x] 8.4 `docs_app/documents/i18n.md`: update the resolution/persistence and SSR sections to the cookie-only model and note the deferred negotiation
- [x] 8.5 Add `e2e/docs/test_i18n.py` (guide renders; demo switch en→ja updates text) and register it in the `docs-documents` group in `scripts/run-e2e-tests.sh` and `.github/workflows/ci.yml`; update `test_readonly_signal.py` pager expectation for the inserted guide
- [ ] 8.6 Re-run validation: static checks, full `pytest tests/`, SSG generate, E2E `docs-documents` (both modes) then the full suite
