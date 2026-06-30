## Context

The `docs_app` is the canonical WebComPy application: it is the documentation site, the primary framework demonstration, and the testbed for new framework features. Today it loads Bootstrap 5 CSS, jQuery-style DOM utilities, and `highlight.js` from external CDNs. The CDN dependency breaks `standalone=True` (a primary WebComPy build mode that ships zero external requests) and forces a flash-of-unstyled-content on first paint because the JavaScript-driven code highlighter cannot run before the page is interactive. A prior spike (`feat-docs-tailwind-modernization`) attempted to migrate to Tailwind CSS as a single-tool solution, but a retrospective in another worktree identified that the Tailwind CDN's runtime-CSS-generation model is fundamentally incompatible with WebComPy's SPA routing (Tailwind scans the DOM once on first load; client-side route changes add classes that are never generated, requiring 40 lines of `<script>` re-injection hacks) and that the class-string-based design encouraged uncontrolled duplication (55 `dark:` variants and 13 copies of the same inline-code class string).

This change pivots to a Web-standards-only design that fits WebComPy's existing strengths. The key insight is that a Component-based framework with a scoped-CSS primitive already has all the building blocks needed for a maintainable UI: components own their styles via `scoped_style`, and CSS custom properties + `@layer` provide a single source of truth for theming. No utility-first library, no runtime CSS compiler, no client-side code highlighter.

The new architecture introduces a first-party UI toolkit at `webcompy/ui/` with `theme/` and `code_block/` submodules. `docs_app` becomes the first consumer, replacing Bootstrap, highlight.js, and one-off `scoped_style` blocks with theme-aware design tokens, named local UI components, and a server-rendered `CodeBlock`.

The change is cross-cutting: it touches the framework's element system (raw HTML insertion for static `CodeBlock`), the DI system (theme state injection), the CLI server (cookie parsing), the SSG/SSR pipeline (initial render of the `data-theme` attribute), and the entire `docs_app` UI layer. A new `lexers/` extension point is added that prepares the framework for future Pygments adoption without adding a runtime dependency today.

## Goals / Non-Goals

**Goals:**

- Eliminate all CDN dependencies from `docs_app` (Bootstrap, highlight.js, `eruda`).
- Provide a 3-state theme system (`light` / `dark` / `system`) that is SSR-safe, cookie-persistent, and renders the correct theme on first paint with zero JavaScript.
- Provide a `CodeBlock` component that highlights code at render time using Python (no client-side JS) with a `Lexer` protocol and a built-in set of self-implemented lexers (Python, Bash, TOML).
- Provide a `use_theme()` composable and a `Theme` enum that any component can use to participate in the theme.
- Provide a documented set of CSS design tokens (color, space, typography, radius, shadow, syntax tokens) with light, dark, and `prefers-color-scheme` variants and a `color-scheme: light dark` declaration for native form controls.
- Wrap all `scoped_style` rules in `@layer webcompy-scope` so that framework CSS and application CSS have a predictable cascade order.
- Demonstrate the new primitives in `docs_app` with 5 new local UI components (`InlineCode`, `Card`, `Section`, `Link`, `Button`) that replace class-string duplication.
- Prepare a Pygments adapter skeleton so a future change can add Pygments support without changing the public API.

**Non-Goals:**

- Adding Pygments (or any other syntax highlighting library) as a runtime dependency.
- Implementing lexers for languages other than Python, Bash, and TOML in this change.
- A general-purpose animation, transition, or page-transition system.
- Custom Tailwind integration or any other utility-first CSS system.
- Multi-app theme isolation on a single document (one `<html>` per document is a hard model limit).
- Streaming SSR of theme state (a single initial render payload is used).
- Removing or replacing the `scoped_style` framework feature.
- A reusable UI component library; this change ships only `CodeBlock` and the local `docs_app` UI components, with a clear promotion path for future toolkit expansions.
- New browser-automation testing infrastructure; existing E2E tests are updated to match the new markup.

## Decisions

### Decision: Use Web-standards-only CSS (custom properties, `@layer`, `@media (prefers-color-scheme)`, `color-scheme`)

The spike's retrospective identified Tailwind CDN's runtime CSS generation as the root cause of three framework-friction signals (DOM re-injection, FOUC, and SPA-routing incompatibility). The new design uses only static CSS files served from `docs_app/static/styles/` and `webcompy/ui/_styles/`. Theme switching happens via a single `<html data-theme="...">` attribute (set on the server when a cookie is present) and a `@media (prefers-color-scheme: dark)` rule for the "system" state.

**Alternatives considered:**
- *Tailwind CLI build step* — Requires Node.js; contradicts WebComPy's Python-only philosophy.
- *light-dark() function (Chrome 123+)* — Just a syntactic sugar over the simple `:root` / `:root[data-theme="dark"]` pattern; adds a 2-year-old feature requirement without structural benefit. Rejected; can be added as a follow-up.
- *`@scope` for all new CSS* — Useful for CodeBlock internal styles where it is adopted; not adopted for general use because `scoped_style` already provides scoping for components.

### Decision: Self-implemented lexers using `tokenize` for Python and regex for Bash/TOML

The docs site uses only Python, Bash, and TOML code blocks. A self-implemented lexer set is small (~500 lines total), has zero runtime dependencies, and is faster than a library in the browser. The Python lexer uses the standard library `tokenize` module for 100% accurate tokenization of the language; Bash and TOML use carefully chosen regexes. The `Lexer` protocol accepts an optional `aliases` and `file_extensions` tuple so future lexers (Pygments-backed or user-supplied) integrate without changing the registry.

**Alternatives considered:**
- *Pygments* — Battle-tested, 500+ languages, but adds a 3 MB+ runtime dependency in Pyodide. The retrospective identified that most apps do not need that surface area. A Pygments adapter is included as a skeleton so it can be adopted in a future change without API churn.
- *rich* — A terminal-focused library that depends on Pygments; same trade-off with extra weight.
- *CodeMirror 6 / Monaco / Prism* — Client-side JavaScript highlighters; reintroduce the FOUC problem the new design solves.

### Decision: HTML attribute `data-theme` as the single source of truth

Theme state is stored in three places — a `Signal[Theme]` for reactive components, a `webcompy-theme` cookie for persistence, and a `data-theme` attribute on `<html>`. The `<html>` attribute is the source of truth for the rendered page. The browser reads it via the CSS selector `:root[data-theme="..."]`; the server reads the cookie to decide which value to write; the client uses the `Signal` to drive user interactions and to update the attribute via `app.set_html_attr("data-theme", ...)`. This avoids the signal-transfer limitation of `feat-hydration-data-transfer` (which only transfers `AsyncResult` and `FetchPort` state) and gives a SSR-safe, FOUC-free first paint.

**Alternatives considered:**
- *localStorage only* — Not available during SSR; would force a flash of light theme before the user's preference applied.
- *Pure CSS `prefers-color-scheme` with no manual override* — Originally listed as a non-goal in the Tailwind proposal; the new design keeps the override available while still using the media query for the "system" state.
- *Signal value transfer via the hydration payload* — `feat-hydration-data-transfer` explicitly excludes Signal values from its payload; deferring theme transfer to the HTML attribute avoids that limitation entirely.

### Decision: Automatic `@layer webcompy-scope` wrapping of all `scoped_style` rules

The framework declares a global cascade order `@layer reset, tokens, components, webcompy-scope;` and wraps every component's `scoped_style` output in `@layer webcompy-scope { ... }`. This gives framework CSS (`reset`, `tokens`, `components`) deterministic priority over component CSS, while still allowing a component to opt into higher priority by using `!important` or by adding its own `@layer` declaration. The user has confirmed that no external consumers exist, so this is a permitted breaking change.

**Alternatives considered:**
- *Opt-in via `scoped_style_layer` parameter* — Safer for backward compatibility but unnecessary given the absence of external users; rejected to keep the API minimal.
- *No layers* — Keeps the current behavior; rejected because `@layer` is a mature (~3 years in all major browsers) feature that solves the cascade ordering problem cleanly.

### Decision: Static CSS files in `webcompy/ui/_styles/` and `docs_app/static/styles/`, no CSS in Python source

Framework-provided CSS lives in real `.css` files, not as Python string constants inside `scoped_style`. This keeps the cascade layer declarations (`@layer reset, tokens, components, webcompy-scope;`) as a single editable file, allows the files to be served by any static file server, and lets users fork or override individual files at the application level. The framework's `_styles/` files are copied into the build output by the existing `static_files_dir` mechanism.

**Alternatives considered:**
- *Inline `@layer` in framework Python source* — Harder to read and edit; rejected.
- *Single bundled CSS file* — Rejected; layered files are easier to override and reason about.

### Decision: Dual class output (`.tok-kw k`) for Pygments compatibility without runtime cost

Every `<span>` emitted by the `CodeBlock` includes both the semantic class (`.tok-kw`) and the Pygments short class (`.k`) when one exists. The output is therefore usable both with the framework's design-token CSS (`.tok-kw { color: var(--tok-kw) }`) and with any Pygments stylesheet a user might add later (`.k { color: #cf222e }`). The cost is two short tokens per element, which is negligible.

**Alternatives considered:**
- *Semantic classes only* — Cleaner output, but forces users to write their own CSS for any new theme. Rejected because the dual-class approach costs nothing and preserves an upgrade path.
- *Pygments short classes only* — Matches the library's output exactly but ties the API to Pygments' class scheme and makes framework CSS less readable. Rejected.

### Decision: Pygments adapter as a skeleton (no import) so a future change can adopt Pygments with zero API churn

The file `webcompy/ui/code_block/lexers/_adapters/_pygments.py` is created with the full adapter implementation, but the file is not imported from any other module. The adapter depends on `pygments`, which is *not* added to `pyproject.toml`. If a future change decides to adopt Pygments, it needs only to (a) add `pygments` to dependencies, (b) call `register_pygments_lexer("javascript")` (or similar) during application startup, and (c) optionally import the adapter module to silence linter warnings. The public API (`CodeBlock`, `register_lexer`, `get_lexer`, `Token`, `TokenType`) does not change.

**Alternatives considered:**
- *Add Pygments as an optional dependency* — Adds a `[pygments]` extra in `pyproject.toml`. Deferred; the skeleton approach is the same outcome at lower risk.
- *Skip the skeleton* — Forces the future change to design the adapter from scratch and re-test the `CodeBlock` contract. Rejected.

### Decision: Theme persistence via `webcompy-theme` cookie, lifetime 1 year, `SameSite=Lax`, `Path=/`

Cookies (rather than `localStorage`) are required because the server needs to read the value during SSR. The cookie name `webcompy-theme` is namespaced to avoid collisions with application cookies. Lifetime of 1 year matches common UX expectations (a returning user sees their last theme). `SameSite=Lax` is sufficient because the cookie is read on first-party requests only. `Path=/` ensures it is sent for all routes.

**Alternatives considered:**
- *localStorage + JS-based theme application before first paint* — Still produces FOUC for the duration of the script execution; rejected.
- *Server-side session storage* — Heavier than necessary for a UI preference; rejected.

## Risks / Trade-offs

- **[Risk]** Automatic `@layer webcompy-scope` wrapping of `scoped_style` is a breaking change for any user that has hand-tuned CSS cascade order around framework-injected styles. → **Mitigation:** The user has confirmed no external consumers exist. The cascade order is documented in `webcompy/ui/_styles/tokens.css` and a `CHANGELOG` note is added. Users who need a different order can wrap their overrides in `@layer` themselves.

- **[Risk]** Self-implemented Bash and TOML lexers are regex-based and may mis-highlight edge cases (e.g., nested quotes, multi-line strings). → **Mitigation:** The lexers ship with a unit test suite that covers the patterns actually used in `docs_app` (the lexers' own test files are included). The `Lexer` protocol allows users to register a more accurate lexer (Pygments-backed or otherwise) for the same language name if needed.

- **[Risk]** `CodeBlock` re-runs the lexer for every signal update in the dynamic case (`demo_display.py` loading source code at runtime). For large code samples this can be slow. → **Mitigation:** A length cap of 100,000 characters (matching the existing limit) and a `strip_multiline_text` step prevent the worst cases. The Python lexer uses the C-accelerated `tokenize` module and runs in ~10ms for typical snippets. A future change can add memoization keyed on `(code, lang)`.

- **[Risk]** Reading the `webcompy-theme` cookie during SSR requires a hook in `webcompy/cli/_server.py` and `webcompy/cli/_generate.py` (for SSG). The SSG case produces no cookie, so the initial theme defaults to `system`. → **Mitigation:** The `webcompy-theme` cookie is read at the boundary of the request handler via the existing DI scope mechanism; SSG simply does not provide a cookie and gets the `system` default. The behavior is documented in the `theme-system` spec.

- **[Risk]** Dual class output (`.tok-kw k`) slightly increases rendered HTML size and may conflict with user CSS that targets `.k` for unrelated purposes. → **Mitigation:** The cost is ~6 characters per token, negligible. Users with unrelated `.k` rules can either rename theirs or override the framework's CSS with higher specificity.

- **[Risk]** The framework's `code-block` HTML must be inserted as raw HTML inside a `<pre><code>` element. If the framework's element system does not already support raw HTML children, this requires a small extension. → **Mitigation:** Investigate `webcompy.elements.html.RawHTML` (or equivalent) during task implementation. If the primitive does not exist, add it as a tracked task in `tasks.md`. The implementation must preserve text-node semantics for accessibility (the `<span>` elements are not focusable).

- **[Risk]** The 5 new local UI components in `docs_app/components/ui.py` may be too tightly coupled to GitHub's visual style to promote directly to `webcompy/ui/` later. → **Mitigation:** The components are designed to use only design tokens (`var(--*)`) for all visual properties, so the GitHub-ness lives in the token values, not in the components. A future change can re-skin the tokens without touching the components.

## Migration Plan

The change is implemented as a single atomic PR with the following high-level sequence (full breakdown in `tasks.md`):

1. Add the design-token CSS files to `webcompy/ui/_styles/` and a `_styles/index.css` aggregator that establishes the layer order.
2. Add the `Theme` enum, `ThemeManager`, `use_theme()` composable, and Cookie persistence to `webcompy/ui/theme/`. Register the manager in `app.di_scope` and the cookie reader in `webcompy/cli/_server.py`.
3. Add the `Lexer` protocol, registry, and self-implemented Python, Bash, and TOML lexers to `webcompy/ui/code_block/`. Add the `CodeBlock` component, the `highlight()` function, and the Pygments adapter skeleton.
4. Update `scoped_style` injection in `webcompy/components/` to wrap output in `@layer webcompy-scope`. Update existing component tests to reflect the new layer.
5. Add the 5 local UI components in `docs_app/components/ui.py` and the static CSS files in `docs_app/static/styles/`.
6. Migrate `docs_app/components/navigation.py` (rewrite `scoped_style`, add `ThemeToggle`), `docs_app/templates/home.py` (use new UI components), `docs_app/pages/not_found.py`, `docs_app/components/demo_display.py`, and `docs_app/app.py` (remove Bootstrap, remove `highlight.js`).
7. Run the test suite (`uv run pytest`), the type checker (`uv run pyright`), the linter (`uv run ruff check .` and `uv run ruff format .`), and a manual dev-server smoke test for light/dark/system switching and SSG output.
8. Update `.opencode/agents/ci-review.md` with the "Framework Friction Signals" checklist.
9. Mark `feat-docs-tailwind-modernization` as superseded in its `proposal.md`.

**Rollback:** Because the change is delivered as a single PR that supersedes `feat-docs-tailwind-modernization` (which is in-progress and not yet merged), rollback is `git revert <merge-commit>`. No data migration is required.

## Open Questions

- **Q1.** Does `webcompy/elements/` already provide a primitive for inserting raw HTML into an element (e.g., `RawHTML` or a `:innerHTML` attribute)? If not, what is the minimal addition needed? — *To be resolved during task 2.7 implementation.*
- **Q2.** Should the framework's CSS file path (e.g., `webcompy/ui/_styles/tokens.css`) be discoverable by applications (e.g., via `pkgutil.get_data`) or copied into each application at scaffold time? — *Current intent: served from the framework's static-files location; documented in the `css-architecture` spec.*
- **Q3.** For the `system` theme, should the rendered HTML contain a `<meta name="color-scheme" content="light dark">` tag in addition to the CSS `color-scheme: light dark` property? — *Likely yes for older browsers; to be confirmed during task 1.4.*
- **Q4.** What is the lifetime and rotation policy for the `webcompy-theme` cookie when the user changes themes? — *Current intent: refresh the cookie on every `set` call to maintain the 1-year-from-now expiry.*
- **Q5.** Should `CodeBlock` accept a `code: str | Signal[str]` prop (current design) or always require a `Signal` (to force consistency)? — *Current design keeps the union for ergonomics; tests cover both paths.*
