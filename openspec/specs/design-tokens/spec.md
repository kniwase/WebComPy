# design-tokens Specification

## Purpose
CSS custom property design tokens (`tokens.css` and `webcompy.ui.theme._tokens`), color-scheme defaults, native form-control styling baselines, and WCAG 2.1 AA contrast guarantees across light and dark themes.
## Requirements
### Requirement: The framework SHALL provide a CSS custom property file with light and dark token values

The framework SHALL provide a CSS file (`tokens.css`) under `webcompy/ui/_styles/` that defines a fixed set of CSS custom properties on `:root` with light-theme values by default, and exports the matching dark-theme overrides through the theme token map consumed by `ThemeManager`'s injected `:root` CSS (as direct `:root` overrides in `Theme.DARK` and inside `@media (prefers-color-scheme: dark) { :root { ... } }` in `Theme.SYSTEM`). Neither `tokens.css` nor `ThemeManager` SHALL rely on `data-theme` attributes to switch theme values.

#### Scenario: Application uses a token

- **WHEN** a component's `scoped_style` references `var(--color-bg)` in a CSS property
- **THEN** the resolved value SHALL be the light-theme value when the active theme is `Theme.LIGHT` (or `Theme.SYSTEM` with a light OS preference)
- **AND** the resolved value SHALL be the dark-theme value when the active theme is `Theme.DARK`
- **AND** the resolved value SHALL be the dark-theme value when the active theme is `Theme.SYSTEM` and the user's OS preference is `prefers-color-scheme: dark`

### Requirement: The token set SHALL cover color, spacing, typography, radius, shadow, and syntax token categories

The framework SHALL provide tokens in at least the following categories, with names prefixed by category, kept in parity between `tokens.css` and `webcompy.ui.theme._tokens`:
- Color tokens: `--color-bg`, `--color-bg-elevated`, `--color-bg-code`, `--color-bg-card`, `--color-fg`, `--color-fg-muted`, `--color-fg-subtle`, `--color-link`, `--color-link-hover`, `--color-accent`, `--color-on-accent`, `--color-border`, `--color-border-muted`, `--color-success`, `--color-danger`, `--color-warning`.
- Spacing tokens: `--space-1` through `--space-8` on a rem-based scale.
- Typography tokens: `--font-size-sm`, `--font-size-base`, `--font-size-lg`, `--font-size-xl`, `--font-size-2xl`, `--font-sans`, `--font-mono`.
- Radius tokens: `--radius-sm`, `--radius-md`, `--radius-lg`.
- Shadow tokens: `--shadow-sm`, `--shadow-md`, `--shadow-lg`.
- Syntax token colors: `--tok-kw`, `--tok-str`, `--tok-num`, `--tok-comment`, `--tok-fn`, `--tok-builtin`, `--tok-decorator`, `--tok-op`, `--tok-punct`, `--tok-ident`.

#### Scenario: Component references a typography token

- **WHEN** a component's `scoped_style` sets `font-size: var(--font-size-base)`
- **THEN** the rendered font size SHALL match the value of `--font-size-base` defined in the active theme

#### Scenario: Overlay or card references --shadow-lg

- **WHEN** a component or framework stylesheet references `var(--shadow-lg)`
- **THEN** `--shadow-lg` SHALL resolve to a non-empty shadow value in both light and dark themes

#### Scenario: Component references an undefined token

- **WHEN** a component's `scoped_style` references a token name that is not defined in `tokens.css`
- **THEN** the CSS property SHALL be treated as invalid by the browser
- **AND** the developer SHALL see a clear visual indication that the style is not applied

### Requirement: The token file SHALL declare `color-scheme: light dark` on `:root`

The `tokens.css` file SHALL set `color-scheme: light dark` on `:root` as the default system baseline, while explicit `Theme.LIGHT` and `Theme.DARK` modes emitted by `ThemeManager` SHALL override `color-scheme` to `light` and `dark` respectively. Additionally, the framework reset/base stylesheet SHALL provide tokenized surface, text, border, and inherited `color-scheme` defaults for native form controls (`<button>`, `<input>`, `<select>`, `<textarea>`) so unstyled native controls maintain legible foreground-background contrast under every combination of OS preference and site theme.

#### Scenario: Native form control follows the theme

- **WHEN** the user activates the dark theme or light theme (regardless of OS preference)
- **THEN** native form controls rendered inside the application SHALL appear in their matching variant with explicit active `color-scheme` and tokenized surface/text defaults
- **AND** this SHALL happen without any application-level CSS

#### Scenario: Native form control follows the active site theme under inverted OS preference

- **WHEN** the OS preference is `prefers-color-scheme: light` and the user activates `Theme.DARK` (or OS preference is `dark` and the user activates `Theme.LIGHT`)
- **THEN** `<button>`, `<input>`, `<select>`, and `<textarea>` elements SHALL render with foreground and background colors matching the site's active theme
- **AND** contrast between text and surface on those controls SHALL be at least 4.5:1 without application-level overrides

### Requirement: The token file SHALL be served as a static asset in standalone mode

When the application's `AppConfig.standalone` is `True`, the `tokens.css` file SHALL be included in the build output and reachable at a known URL so the application can `<link rel="stylesheet" href="...">` it without external network requests.

#### Scenario: Standalone build links tokens.css

- **WHEN** an application is built with `standalone=True`
- **THEN** the build output SHALL contain a `tokens.css` (or equivalent) file
- **AND** the application's HTML SHALL include a `<link rel="stylesheet">` tag pointing at it
- **AND** no external network request SHALL be made to fetch tokens

### Requirement: Token values SHALL follow the GitHub visual reference for light and dark

The light and dark token values SHALL follow GitHub's color palette for primary surfaces, text, borders, accents, and syntax highlighting while enforcing WCAG 2.1 AA contrast ratios (`>= 4.5:1` for normal body/button/syntax text and `>= 3:1` for large text and UI boundaries) in both light and dark themes. In particular, primary accent surfaces paired with `--color-on-accent` (such as `.btn-primary`) SHALL meet `>= 4.5:1` in both themes, and `--tok-comment` against `--color-bg-code` SHALL meet `>= 4.5:1` in both light and dark themes.

#### Scenario: Default appearance matches the reference

- **WHEN** a developer adds `tokens.css` to a new application and writes no other CSS
- **THEN** the application SHALL render with a light or dark GitHub-style background, text, and code highlighting
- **AND** primary text (`--color-fg` on `--color-bg` and `--color-bg-card`), muted text (`--color-fg-muted`), links (`--color-link`), accent foreground (`--color-on-accent` on `--color-accent`), and syntax comments (`--tok-comment` on `--color-bg-code`) SHALL all meet WCAG 2.1 AA (`>= 4.5:1`) in both themes

