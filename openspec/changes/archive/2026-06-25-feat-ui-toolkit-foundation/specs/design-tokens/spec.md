# Design Tokens

## Purpose

Provide a canonical set of CSS custom properties (design tokens) for use across all WebComPy applications, with light, dark, and system-preference variants. Tokens give application code a single source of truth for colors, spacing, typography, radii, shadows, and syntax-highlighting colors, so theme switching is implemented in one file rather than scattered across component styles.

## ADDED Requirements

### Requirement: The framework SHALL provide a CSS custom property file with light and dark token values

The framework SHALL provide a CSS file (`tokens.css`) under `webcompy/ui/_styles/` that defines a fixed set of CSS custom properties on `:root` with light-theme values, and overrides those properties under `:root[data-theme="dark"]` and `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { ... } }` with dark-theme values.

#### Scenario: Application uses a token

- **WHEN** a component's `scoped_style` references `var(--color-bg)` in a CSS property
- **THEN** the value SHALL be the light-theme value when the `<html>` element has no `data-theme` attribute or `data-theme="light"`
- **AND** the value SHALL be the dark-theme value when `<html>` has `data-theme="dark"`
- **AND** the value SHALL be the dark-theme value when `<html>` has `data-theme="system"` AND the user's OS preference is `prefers-color-scheme: dark`

### Requirement: The token set SHALL cover color, spacing, typography, radius, shadow, and syntax token categories

The framework SHALL provide tokens in at least the following categories, with names prefixed by category:
- Color tokens: `--color-bg`, `--color-bg-elevated`, `--color-bg-code`, `--color-bg-card`, `--color-fg`, `--color-fg-muted`, `--color-fg-subtle`, `--color-link`, `--color-link-hover`, `--color-accent`, `--color-border`, `--color-border-muted`, `--color-success`, `--color-danger`, `--color-warning`.
- Spacing tokens: `--space-1` through `--space-8` on a rem-based scale.
- Typography tokens: `--font-size-sm`, `--font-size-base`, `--font-size-lg`, `--font-size-xl`, `--font-size-2xl`, `--font-sans`, `--font-mono`.
- Radius tokens: `--radius-sm`, `--radius-md`, `--radius-lg`.
- Shadow tokens: `--shadow-sm`, `--shadow-md`.
- Syntax token colors: `--tok-kw`, `--tok-str`, `--tok-num`, `--tok-comment`, `--tok-fn`, `--tok-builtin`, `--tok-decorator`, `--tok-op`, `--tok-punct`, `--tok-ident`.

#### Scenario: Component references a typography token

- **WHEN** a component's `scoped_style` sets `font-size: var(--font-size-base)`
- **THEN** the rendered font size SHALL match the value of `--font-size-base` defined in the active theme

#### Scenario: Component references an undefined token

- **WHEN** a component's `scoped_style` references a token name that is not defined in `tokens.css`
- **THEN** the CSS property SHALL be treated as invalid by the browser
- **AND** the developer SHALL see a clear visual indication that the style is not applied

### Requirement: The token file SHALL declare `color-scheme: light dark` on `:root`

The `tokens.css` file SHALL set `color-scheme: light dark` on `:root` so that native form controls (scrollbars, `<input>`, `<button>`, `<select>`, `<textarea>`) automatically render in the appropriate variant for the active theme.

#### Scenario: Native form control follows the theme

- **WHEN** the user activates the dark theme
- **THEN** native form controls rendered inside the application SHALL appear in their dark variant
- **AND** this SHALL happen without any application-level CSS

### Requirement: The token file SHALL be served as a static asset in standalone mode

When the application's `AppConfig.standalone` is `True`, the `tokens.css` file SHALL be included in the build output and reachable at a known URL so the application can `<link rel="stylesheet" href="...">` it without external network requests.

#### Scenario: Standalone build links tokens.css

- **WHEN** an application is built with `standalone=True`
- **THEN** the build output SHALL contain a `tokens.css` (or equivalent) file
- **AND** the application's HTML SHALL include a `<link rel="stylesheet">` tag pointing at it
- **AND** no external network request SHALL be made to fetch tokens

### Requirement: Token values SHALL follow the GitHub visual reference for light and dark

The light and dark token values SHALL approximate GitHub's documented color palette for primary surfaces, text, borders, and syntax highlighting, so that applications adopting the tokens have a familiar, accessible default appearance.

#### Scenario: Default appearance matches the reference

- **WHEN** a developer adds `tokens.css` to a new application and writes no other CSS
- **THEN** the application SHALL render with a light or dark GitHub-style background, text, and code highlighting
- **AND** contrast ratios SHALL meet WCAG AA for body text against the background in both themes
