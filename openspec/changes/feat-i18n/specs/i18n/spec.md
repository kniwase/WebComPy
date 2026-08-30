# I18n Specification (delta)

## ADDED Requirements

### Requirement: I18nManager shall be DI-managed and accessed via use_i18n

The framework SHALL provide an `I18nManager` in the application DI scope holding the locale signal, message catalogs, and fallback locale. `use_i18n()` SHALL inject the manager and return the locale signal, the translation function `t`, and a controller for switching locales; when no manager is provided it SHALL raise a lookup error naming the requirement. Locale state SHALL be per application scope with no module-global state.

#### Scenario: Composable returns the i18n interface

- **WHEN** a component calls `use_i18n()` inside an app with a provided I18nManager
- **THEN** it SHALL receive the locale signal, a callable `t`, and a controller
- **AND** calling `use_i18n()` without a provided manager SHALL raise a lookup error

### Requirement: Translations shall re-render automatically on locale switch

`t(key, **params)` SHALL resolve messages against the current `locale` signal value at call time, so template interpolations using `t` SHALL register a dependency on the locale signal through normal reactive tracking. Switching locale SHALL re-render all rendered translations without additional subscription APIs.

#### Scenario: Locale switch updates rendered translations

- **WHEN** a template renders `{{ t("nav.home") }}` showing "Home" and the locale switches from `en` to `ja`
- **THEN** the rendered text SHALL become the Japanese message without any manual refresh call

### Requirement: Catalogs shall use nested dicts with dot-path keys and placeholder interpolation

Message catalogs SHALL be mappings of locale to nested dictionaries; keys SHALL resolve through nesting by dot path (e.g. `nav.home`). String messages SHALL interpolate `{param}` placeholders from keyword arguments passed to `t`. Missing interpolation parameters SHALL render the placeholder literally.

#### Scenario: Dot-path resolution and interpolation

- **WHEN** the catalog contains `{"en": {"greeting": "Hello, {name}!"}}` and `t("greeting", name="Alice")` is called with locale `en`
- **THEN** the result SHALL be "Hello, Alice!"

### Requirement: Pluralization shall use CLDR categories with a pipe shorthand

Plural messages SHALL be dictionaries keyed by CLDR plural categories (e.g. `one`, `other`, `few`, `many`); `t(key, count=N)` SHALL select the category for `count` using the active plural rules and interpolate `count` along with other parameters. A pipe-separated string shorthand SHALL map onto the two-category form for languages with `one`/`other` rules.

#### Scenario: English plural selection

- **WHEN** the catalog contains `{"en": {"items": {"one": "{count} item", "other": "{count} items"}}}` and `t("items", count=1)` / `t("items", count=3)` are called
- **THEN** the results SHALL be "1 item" and "3 items" respectively

#### Scenario: Pipe shorthand

- **WHEN** the catalog contains `{"en": {"items": "{count} item|{count} items"}}` and `t("items", count=3)` is called
- **THEN** the result SHALL be "3 items"

### Requirement: Plural rules shall ship as a built-in minimal table with an opt-in Babel adapter

The framework SHALL include a built-in CLDR plural-rule table covering common locales; locales absent from the table SHALL fall back to `one`/`other` rules with a warning. An opt-in adapter backed by the Babel library SHALL be shipped without being imported by default; projects that add the Babel dependency and register the adapter SHALL obtain full CLDR plural coverage.

#### Scenario: Unknown locale falls back with warning

- **WHEN** a locale not present in the built-in table is used with plural messages
- **THEN** `one`/`other` rules SHALL apply and a warning SHALL be logged

#### Scenario: Babel adapter replaces the rule source

- **WHEN** a project registers the Babel adapter and uses a locale with rich plural categories (e.g. Russian few/many boundaries)
- **THEN** category selection SHALL follow full CLDR rules for sample values including boundary cases

### Requirement: Missing keys shall resolve through the fallback chain

Key resolution SHALL try the exact locale (e.g. `de-AT`), then its language (`de`), then the configured fallback locale, and finally SHALL return the key string itself when no catalog provides the key.

#### Scenario: Region falls back to language

- **WHEN** locale is `de-AT`, the key exists only under the `de` catalog
- **THEN** the `de` message SHALL be returned

#### Scenario: Missing key returns the key

- **WHEN** a key exists in no catalog along the chain
- **THEN** `t` SHALL return the key string itself

### Requirement: Locale shall persist via cookie and resolve on SSR from the request cookie

In the browser, the initial locale SHALL be read from a locale cookie via the cookie port, falling back to the configured default when the cookie is absent, and switching locales SHALL write the cookie. During SSR, the manager's initial locale SHALL resolve from the request's Cookie header (surfaced through the cookie port), falling back to the configured default. Both sides SHALL apply the same normalization so first render and hydration agree, and neither side SHALL consult `Accept-Language` or `navigator.language`.

#### Scenario: Repeat visit honors the cookie on both sides

- **WHEN** a request carries a locale cookie `ja` and SSR renders the page, then the browser hydrates it
- **THEN** both the server-rendered page and the hydrated page SHALL use `ja`

#### Scenario: Cookie-less first visit uses the default

- **WHEN** an SSR request carries no locale cookie and the browser has none either
- **THEN** the rendered page and the hydrated page SHALL both use the configured default locale

#### Scenario: Unsupported cookie value normalizes to the default

- **WHEN** the locale cookie holds a value not among the supported locales and no language match exists
- **THEN** resolution SHALL fall back to the configured default locale identically on both sides
