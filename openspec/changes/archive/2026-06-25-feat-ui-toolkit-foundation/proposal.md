## Why

The `docs_app` is currently built on Bootstrap 5 (loaded from CDN) plus a client-side `highlight.js` dependency for code blocks. This approach has three structural problems: (1) CDN-loaded assets break the standalone build mode, (2) the `highlight.js` model conflicts with WebComPy's SSR/SSG-first design and causes flash-of-unstyled-content, and (3) the existing one-off `scoped_style` blocks in `docs_app/components/navigation.py` (~312 lines) and `templates/home.py` (~255 lines) are difficult to maintain and do not contribute reusable framework assets. A prior spike (`feat-docs-tailwind-modernization`) attempted to migrate to Tailwind CSS but was abandoned after a retrospective in another worktree identified fatal framework friction: runtime CSS generation, SPA-routing DOM re-injection hacks, and uncontrolled class-string duplication. This change pivots to a Web-standards-only design system that fits WebComPy's existing strengths (component model, `scoped_style`, SSR/SSG) and lays the foundation for a future first-party UI toolkit.

## What Changes

- **NEW** `webcompy/ui/theme/` module — `Theme` enum (3 states: `light`, `dark`, `system`), `ThemeManager` class, `use_theme()` composable, Cookie-based persistence on the client, and DI-scope-based initial-value injection on the server.
- **NEW** `webcompy/ui/code_block/` module — A `CodeBlock` component with a `Lexer` protocol, a self-implemented Python lexer (built on `tokenize`), self-implemented Bash and TOML lexers (regex-based), a lexer registry, and HTML output that emits both semantic classes (`.tok-kw`) and Pygments-compatible short classes (`.k`) for future library interchangeability. Includes a Pygments adapter skeleton (no Pygments dependency added).
- **NEW** `webcompy/ui/_styles/` directory — Static CSS files (`tokens.css`, `reset.css`, `components.css`, `code-block.css`, `syntax-theme.css`) providing design tokens as CSS custom properties, a CSS reset, theme variants (light, dark, system via `prefers-color-scheme`), and `color-scheme: light dark` for native form control theming.
- **MODIFIED** `webcompy/components/` — `scoped_style` rules SHALL be automatically wrapped in `@layer webcompy-scope` to participate in the framework-wide cascade order. **BREAKING**: any application that depended on the previous unwrapped behavior of `scoped_style` will see different cascade resolution. No external consumers exist.
- **MODIFIED** `docs_app/` — Remove all Bootstrap 5 CDN links and `highlight.js` scripts and theme CSS; remove the `eruda` dev-only script. Add 5 new local UI components (`InlineCode`, `Card`, `Section`, `Link`, `Button`) in a new `docs_app/components/ui.py` to replace inline class-string repetition. Replace the existing `SyntaxHighlighting` component with a thin wrapper around `webcompy.ui.code_block.CodeBlock`. Add a `ThemeToggle` button in the navigation bar.
- **MODIFIED** `docs_app/static/styles/` — New directory of static CSS files linked from `docs_app/app.py`.
- **MODIFIED** `docs_app/components/navigation.py` and `docs_app/templates/home.py` — Rewrite `scoped_style` blocks to reference design tokens via `var(--*)` instead of hardcoded color values.
- **MODIFIED** `webcompy/cli/_server.py` and related server-side rendering code — Read the `webcompy-theme` cookie during request handling and provide the initial `Theme` value through the app's DI scope.
- **MODIFIED** `openspec/changes/feat-docs-tailwind-modernization/` — Superseded by this change.
- **MODIFIED** `.opencode/agents/ci-review.md` — Add "Framework Friction Signals" as a review checklist (runtime CSS generation, repeated class strings, FOUC tolerance, `<html>` selectors in scoped CSS, DOM re-injection hacks).

## Capabilities

### New Capabilities

- `design-tokens`: A defined set of CSS custom properties (color, space, typography, radius, shadow, syntax tokens) for use across all WebComPy applications, with light and dark variants and a system-preference fallback.
- `theme-system`: A 3-state (light/dark/system) reactive theme system that persists user choice in a Cookie, supports SSR-safe initial value via the cookie, and uses the `data-theme` attribute on `<html>` as the single source of truth.
- `ui-composables`: A `use_theme()` composable that returns a `(Signal[Theme], ThemeController)` tuple for use in component setup functions, including `set`, `toggle`, and `cycle` operations.
- `code-block`: A `CodeBlock` component that highlights source code at render time (Python-side, no client-side JS), with a `Lexer` protocol, a registry supporting lookup by name, alias, and file extension, and HTML output compatible with Pygments short class names.
- `syntax-highlight-lexers`: A built-in set of lexers (Python, Bash, TOML) with a Pygments adapter skeleton, allowing users to register their own lexers.
- `css-architecture`: Framework-provided CSS files in `webcompy/ui/_styles/`, `@layer` cascade ordering, and automatic `@layer webcompy-scope` wrapping of component `scoped_style`.

### Modified Capabilities

- `app-config`: The `AppConfig.assets` field usage pattern is extended to include local CSS file references. `AppConfig` gains a `theme` field for default theme and persistence configuration.
- `components`: `scoped_style` rules are automatically wrapped in `@layer webcompy-scope`. The framework's CSS cascade order is fixed: `reset, tokens, components, webcompy-scope`.
- `composables`: A new built-in composable `use_theme()` is added alongside `useAsyncResult` and `useAsync`.

## Impact

- `webcompy/ui/` — New package containing `theme/`, `code_block/`, `_styles/`, and `_composables/` submodules.
- `webcompy/components/` — `scoped_style` injection logic updated to wrap output in `@layer`. Tests updated to reflect new layer behavior.
- `webcompy/cli/_server.py` — Cookie parsing and DI scope population for theme state.
- `webcompy/cli/_html.py` — Initial render of the `<html>` `data-theme` attribute when a theme cookie is present.
- `docs_app/app.py` — Bootstrap and `highlight.js` references removed; static CSS files added.
- `docs_app/components/navigation.py` — `scoped_style` rewritten with `var(--*)` references; `ThemeToggle` added.
- `docs_app/components/demo_display.py` — Dynamic code loading now flows through `CodeBlock` rather than `highlight.js`.
- `docs_app/components/syntax_highlighting.py` — Replaced with a thin wrapper around `webcompy.ui.code_block.CodeBlock`.
- `docs_app/components/ui.py` (new) — `InlineCode`, `Card`, `Section`, `Link`, `Button` components.
- `docs_app/pages/not_found.py` — Tailwind classes replaced with `var(--*)`-based styles.
- `docs_app/templates/home.py` — `scoped_style` rewritten; repeated patterns replaced with new UI components.
- `docs_app/static/styles/` (new) — 5 static CSS files.
- `docs_app/static/_demos/` — Unchanged.
- `.opencode/agents/ci-review.md` — New review checklist category.
- `openspec/changes/feat-docs-tailwind-modernization/` — Marked as superseded.
- No new runtime dependencies are added to `pyproject.toml` (Pygments adapter is a skeleton only).

## Supersedes

- `feat-docs-tailwind-modernization` — The Tailwind CSS approach was abandoned after a retrospective in another worktree identified framework friction signals. This change is its successor under a different design philosophy.

## Known Issues Addressed

- **Bootstrap CDN dependency breaks standalone mode** — All Bootstrap CSS/JS links and `highlight.js` CDN references are removed. All visual assets become local static files in `docs_app/static/styles/` and `webcompy/ui/_styles/`.
- **`<html>` element cannot be targeted by `scoped_style`** — Resolved by using `:root[data-theme]` and `:root[data-theme="dark"]` (non-scoped, in framework-provided CSS) instead of attempting to scope-theme from component-level `scoped_style`. The `scoped_style` CID attribute machinery only applies to elements rendered through the component tree, so `<html>` (which is the document root) was never a valid `scoped_style` target.
- **Class-string duplication across components** — 13 repetitions of inline-code class strings and 5 repetitions of card class strings in the spike branch are replaced with named `InlineCode` and `Card` components in `docs_app/components/ui.py`. The components can be promoted to `webcompy/ui/` in a future toolkit expansion.
- **highlight.js FOUC on first paint** — Eliminated by moving highlighting to the render step (SSR/SSG includes the highlighted HTML directly). No client-side JS is required for code blocks.
- **Runtime CSS generation conflicts with SSR** — Tailwind CDN scans the DOM at runtime and misses classes added after client-side routing. The new design uses only static CSS files, eliminating the conflict.
- **CSS variables scattered across 55 `dark:` class variants** — Replaced with a single set of CSS custom properties in `:root` and `:root[data-theme="dark"]`, with components referencing them via `var(--*)`.

## Non-goals

The following are explicitly out of scope for this change. **If any of the following "Framework Friction Signals" appear during implementation or review, the design should be reconsidered before proceeding:**

- Runtime CSS generation (e.g., Tailwind CDN-style utility compilation in the browser).
- Flash-of-unstyled-content (FOUC) tolerance in any new component.
- Selecting the `<html>` or `<body>` element from `scoped_style` (use framework-provided global CSS instead).
- Client-side `<script>` re-injection hacks for asset refresh.
- Adding Pygments (or any other syntax highlighting library) as a runtime dependency. The adapter skeleton exists for future use but no library is added now.
- Streaming incremental SSR (the theme is set in a single initial render payload).
- Animations and page transitions (reserved for a future change).
- A reusable Tailwind-integration plugin or component library.
- Removing the `scoped_style` framework feature; it is preserved and used.
- Supporting system-level dark mode preference as the *only* theme source (a manual toggle is always available, but `prefers-color-scheme` is used for the "system" state).
- Custom Tailwind configuration (no Tailwind is used).
- Multi-app theme isolation on a single document (only one `<html>` element exists per document; this is a known model limitation and is documented in the theme-system spec).
- New lexers beyond Python, Bash, and TOML (users can register their own lexers; built-in coverage is limited to these three).
- Migration of the docs-e2e test infrastructure (existing E2E tests are updated to match the new markup, but no new E2E infrastructure is introduced).
