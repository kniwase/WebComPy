# Changelog

All notable changes to WebComPy are documented in this file. Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- **New module: `webcompy.ui.theme`** — first-party 3-state (light/dark/system) theme system
  - `Theme` enum (`LIGHT`, `DARK`, `SYSTEM`) and `THEME_KEY` DI key
  - `ThemeManager` (DI-managed) for application-wide theme state
  - `use_theme()` composable returning `(Signal[Theme], ThemeController)` tuple
  - Cookie persistence (`webcompy-theme`, 1-year lifetime, `Path=/`, `SameSite=Lax`)
  - SSR-safe initial render via `app.create_render_context(path, initial_theme=...)`
  - HTML attribute `data-theme` as the single source of truth

- **New module: `webcompy.ui.code_block`** — first-party code highlighting
  - `CodeBlock` component accepting `code: str | Signal[str]` and `lang: str`
  - `Lexer` protocol with a registry (lookup by name, alias, or file extension)
  - Built-in lexers: Python (built on `tokenize`), Bash, TOML (regex-based)
  - `highlight()` function producing dual-class output (`.tok-kw k` for Pygments compatibility)
  - Pygments adapter skeleton at `webcompy/ui/code_block/lexers/_adapters/_pygments.py` (not imported; opt-in)

- **New directory: `webcompy/ui/_styles/`** — framework-provided CSS
  - `tokens.css`, `tokens-dark.css` (light/dark design tokens as CSS custom properties)
  - `reset.css` (minimal box-sizing/body reset)
  - `components.css` (framework-level `<pre>`, `<code>`, `<a>`, form-control styles)
  - `code-block.css`, `syntax-theme.css` (code-block container and syntax token colors)
  - `index.css` (aggregator declaring `@layer reset, tokens, components, webcompy-scope;`)
  - Auto-served at `/_webcompy-ui/{filename}` and auto-injected into `<head>` with zero application configuration

- **Framework CSS bundling** — `webcompy/ui/_styles/*.css` files are now bundled into the framework browser wheel, fixing a defect where framework CSS was unreachable at runtime (the wheel builder previously filtered non-Python files out).

- **Dev server route** — `/_webcompy-ui/{filename}` serves framework CSS with path-traversal protection.

- **SSG integration** — `webcompy generate` copies `webcompy/ui/_styles/*.css` into `dist/_webcompy-ui/` and links `index.css` in the HTML head.

### Changed

- **BREAKING**: `scoped_style` rules are now automatically wrapped in `@layer webcompy-scope { ... }`. Components that depended on the previous unwrapped behavior will see different cascade resolution. The framework cascade order is fixed at `reset, tokens, components, webcompy-scope`. Application components can opt into higher priority via `!important` or by adding their own `@layer` declaration. **No external consumers exist**; this is a permitted breaking change.

- **`RawHTMLElement` and `raw_html()`** — new public API in `webcompy.elements` for inserting raw HTML into a parent element. Used by `CodeBlock` to insert the highlighted HTML inside a `<pre><code>` element.

- **`<html>` element** — `color-scheme: light dark` declared in `:root` and `<meta name="color-scheme" content="light dark">` added to the HTML template for older browser support.

### Removed

- `Bootstrap 5` CDN dependency from `docs_app` — replaced by `webcompy/ui/_styles/` and local `docs_app/static/styles/`.
- `highlight.js` CDN dependency from `docs_app` — replaced by `CodeBlock` highlighting at render time.

### Non-Goals (for this release)

The following are explicitly NOT in this release. If any appear during implementation or review, the design should be reconsidered:

- Adding Pygments (or any other syntax highlighting library) as a runtime dependency. The adapter skeleton exists for future use.
- Runtime CSS generation (e.g., Tailwind CDN-style utility compilation in the browser).
- Flash-of-unstyled-content (FOUC) tolerance in any new component.
- Selecting the `<html>` or `<body>` element from `scoped_style` (use framework-provided global CSS instead).
- Client-side `<script>` re-injection hacks for asset refresh.
- Streaming incremental SSR (the theme is set in a single initial render payload).
- Animations and page transitions (reserved for a future change).
- Multi-app theme isolation on a single document.
- New lexers beyond Python, Bash, and TOML (users can register their own lexers).
