---
title: i18n Playground
description: Reactive internationalization demo showing webcompy.i18n factory provisioning, use_i18n() catalogs, parameter interpolation, and CLDR pluralization.
---

# i18n Playground

This example lets you switch between English (`en`) and Japanese (`ja`) live and adjust a reactive item counter to observe parameter interpolation and locale-specific CLDR plural rules update the DOM automatically.

Use `webcompy.i18n` whenever an application needs reactive localized strings, plural forms, fallback chains, and SSR-consistent initial locale resolution.

## What this demonstrates

- **Factory injection in component setup**: `I18nPlaygroundRoot` calls `context.provide(I18N_KEY, make_i18n_manager)` so `I18nManager` is instantiated lazily inside each render context without sharing mutable locale state across SSR requests (`app.provide(I18N_KEY, make_i18n_manager)` also works for routed child views; `persist=False` keeps this embedded demo self-contained without mutating the parent docs cookie).
- **Reactive `t(...)` lookups**: Calling `t("demo.current", locale=controller.locale)` or `t("demo.items", count=count.value)` inside `use_computed(...)` tracks both the manager's locale signal and local state signals together.
- **Built-in CLDR plurals**: English switches automatically between `"1 item"` (`"one"`) and `"2 items"` (`"other"`), while Japanese resolves `"{count} 個のアイテム"` cleanly via its `"other"` template.

## Key mechanisms and how to adapt

1. **Enable cookie persistence in full apps**: Omit `persist=False` (default `persist=True`) in standalone applications so calling `controller.set("ja")` persists the `webcompy-locale` cookie for SSR/hydration parity across page loads.
2. **Add regional overrides**: Provide `supported_locales={"en", "en-GB", "ja"}` and rely on WebComPy's fallback chain (`locale -> language subtag -> fallback_locale`).
3. **Always wrap `t(...)` in reactive bindings**: Pass `use_computed(lambda: t(...))` (or render via `render_template("{{ t(...) }}", {"t": t})`) instead of evaluating `t(...)` eagerly as a plain string.

## Next steps

- Read the full SSR/hydration cookie parity walkthrough and plural-adapter guide in [Internationalization](/documents/advanced/i18n).
- Compare cookie-based locale persistence with browser storage in [Storage Sync](/documents/examples/storage-sync) and [Persistence Patterns](/documents/advanced/persistence-patterns).
- Understand per-request factory scopes in [Dependency Injection Deep Dive](/documents/advanced/dependency-injection-deep-dive).
