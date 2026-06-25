## 1. Design Tokens and CSS Architecture

- [ ] 1.1 Create `webcompy/ui/_styles/` directory with `tokens.css`, `tokens-dark.css`, `reset.css`, `components.css`, `code-block.css`, `syntax-theme.css`, and `index.css` (the aggregator that declares `@layer reset, tokens, components, webcompy-scope;`)
- [ ] 1.2 Define light-theme values for all color, spacing, typography, radius, shadow, and syntax tokens in `tokens.css` (GitHub-style reference values)
- [ ] 1.3 Define dark-theme overrides under `:root[data-theme="dark"]` and the `prefers-color-scheme: dark` media query in `tokens-dark.css`
- [ ] 1.4 Declare `color-scheme: light dark` on `:root` and add `<meta name="color-scheme" content="light dark">` to the HTML template for older browser support
- [ ] 1.5 Write the minimal CSS reset (box-sizing, body background/color via tokens) in `reset.css` inside the `reset` layer
- [ ] 1.6 Write `components.css` with framework-level `<pre>`, `<code>`, and form-control styles inside the `components` layer
- [ ] 1.7 Add unit tests verifying that all token names are defined in both light and dark themes and that `index.css` declares the layer order

## 2. Theme System

- [ ] 2.1 Create `webcompy/ui/theme/_theme.py` with the `Theme` enum (`LIGHT`, `DARK`, `SYSTEM`) and the `THEME_KEY` DI key constant
- [ ] 2.2 Create `webcompy/ui/theme/_cookie.py` with browser-side cookie read/write helpers (parse `webcompy-theme` value, write with `Max-Age=31536000`, `Path=/`, `SameSite=Lax`; clear with `Max-Age=0`)
- [ ] 2.3 Create `webcompy/ui/theme/_manager.py` with the `ThemeManager` class: constructor takes `WebComPyApp` and `initial: Theme`; `signal` property; `set/toggle/cycle` methods; on each change, applies via `app.set_html_attr("data-theme", ...)` and writes/clears the cookie
- [ ] 2.4 Create `webcompy/ui/theme/_server.py` with `read_theme_from_cookie(headers)` that parses the `webcompy-theme` cookie from an ASGI headers list, falling back to `Theme.SYSTEM` for missing or invalid values
- [ ] 2.5 Add `ThemeManager` instantiation to the app's DI-scope provider in `webcompy/app/_lifecycle.py` (or equivalent) so the manager is available via `inject(THEME_KEY)` in any component
- [ ] 2.6 In `webcompy/cli/_server.py`, read the theme cookie from the ASGI scope and provide the `ThemeManager` with the corresponding initial value before SSR rendering
- [ ] 2.7 In `webcompy/cli/_generate.py`, instantiate `ThemeManager` with `Theme.SYSTEM` (no cookie available at SSG time) and ensure `<html>` has no `data-theme` attribute by default
- [ ] 2.8 In `webcompy/cli/_html.py`, ensure the initial `<html>` element has its `data-theme` attribute set when a `ThemeManager` is in scope
- [ ] 2.9 Write unit tests for `ThemeManager` (set updates attribute + cookie; system removes attribute + clears cookie; toggle; cycle)

## 3. use_theme Composable

- [ ] 3.1 Create `webcompy/ui/_composables/_theme.py` with the `use_theme()` function returning `(Signal[Theme], ThemeController)`; resolve the `ThemeManager` via `inject(THEME_KEY)`
- [ ] 3.2 Create the `ThemeController` class with `set`, `toggle`, and `cycle` methods; ensure `toggle` resolves the `prefers-color-scheme` preference when called from `Theme.SYSTEM`
- [ ] 3.3 Re-export `use_theme` from `webcompy/ui/theme/__init__.py` for ergonomic import
- [ ] 3.4 Write unit tests for `use_theme` returning the live signal from the active `ThemeManager` and for `ThemeController` methods (set, toggle, cycle)

## 4. Scoped Style @layer Integration

- [ ] 4.1 Investigate the existing `scoped_style` injection code in `webcompy/components/_scoped_style.py` (or equivalent) to identify the function that builds the final CSS text
- [ ] 4.2 Modify the injection function to wrap the rule body in `@layer webcompy-scope { ... }` for both runtime-injected and SSR-emitted `<style data-webcompy-cid="...">` elements
- [ ] 4.3 Update existing component tests in `tests/components/` to assert the `@layer webcompy-scope { ... }` wrapper is present
- [ ] 4.4 Verify that the framework's CSS layer order (`@layer reset, tokens, components, webcompy-scope;`) is emitted by SSG and the dev server, and that all existing components continue to render correctly

## 5. CodeBlock Lexer Framework

- [ ] 5.1 Create `webcompy/ui/code_block/_tokens.py` with the `TokenType` enum (`KEYWORD`, `STRING`, `NUMBER`, `COMMENT`, `FUNCTION`, `BUILTIN`, `DECORATOR`, `OPERATOR`, `PUNCTUATION`, `IDENTIFIER`) and the `Token` frozen dataclass
- [ ] 5.2 Create `webcompy/ui/code_block/_compatibility.py` with the `PYGMENTS_SHORT_CLASS` dict mapping `TokenType` to Pygments short class strings (`k`, `s`, `m`, `c`, `nf`, `nb`, `nd`, `o`, `p`, `""`)
- [ ] 5.3 Create `webcompy/ui/code_block/lexers/_base.py` with the `Lexer` `Protocol` (name, aliases, file_extensions, tokenize) and the `LexerInfo` frozen dataclass
- [ ] 5.4 Create `webcompy/ui/code_block/lexers/_python.py` with the `PythonLexer` class using `tokenize.tokenize`; implement keyword, builtin, function-name (after `def`/`class`), decorator, and identifier detection
- [ ] 5.5 Create `webcompy/ui/code_block/lexers/_bash.py` with the `BashLexer` class using regexes for builtins, strings (single and double-quoted), comments (`#`), variables (`$VAR`), and operators
- [ ] 5.6 Create `webcompy/ui/code_block/lexers/_toml.py` with the `TomlLexer` class using regexes for sections, keys, strings, numbers, booleans, and comments
- [ ] 5.7 Create `webcompy/ui/code_block/lexers/_registry.py` with `LexerNotFoundError`, `_REGISTRY`, `register_lexer`, `get_lexer` (with alias and file-extension fallback), `list_lexers`, and `register_builtin_lexers`
- [ ] 5.8 Create `webcompy/ui/code_block/lexers/_adapters/_pygments.py` with the `PygmentsLexerWrapper` class and `register_pygments_lexer` function; the file SHALL NOT be imported by other framework modules
- [ ] 5.9 Create `webcompy/ui/code_block/lexers/_adapters/__init__.py` as an empty file
- [ ] 5.10 Write unit tests for each built-in lexer using known input/output pairs (tokenize sample Python/Bash/TOML snippets and assert the expected token sequence)

## 6. CodeBlock Component and highlight Function

- [ ] 6.1 Create `webcompy/ui/code_block/_highlight.py` with the `highlight(code, lang) -> str` function: look up the lexer, iterate tokens, emit `<span class="tok-X [pyg]">escaped_value</span>`, join with `\n`
- [ ] 6.2 Investigate `webcompy/elements/` for an existing raw-HTML insertion primitive (e.g., `RawHTML` or a `:innerHTML` attribute); if absent, add the minimum primitive needed
- [ ] 6.3 Create `webcompy/ui/code_block/_component.py` with the `CodeBlock` component: accept `code: str | Signal[str]` and `lang: str`; for static code, render pre-highlighted HTML as a child; for `Signal[str]`, use a `computed` to recompute highlighted HTML reactively
- [ ] 6.4 Write `webcompy/ui/code_block/__init__.py` exporting `CodeBlock`, `highlight`, `Token`, `TokenType`, `register_lexer`, `get_lexer`, `list_lexers`, `LexerInfo`, `LexerNotFoundError`, and `Theme` (re-exported)
- [ ] 6.5 Write unit tests for `highlight`: empty input returns empty string; HTML in input is escaped; unknown language raises `LexerNotFoundError`; output contains both `tok-*` and Pygments short classes

## 7. docs_app Local UI Components

- [ ] 7.1 Create `docs_app/components/ui.py` with five `@define_component` functions: `InlineCode`, `Card`, `Section`, `Link`, `Button`
- [ ] 7.2 Add `scoped_style` to `docs_app/components/ui.py` that defines `.ui-inline-code`, `.ui-card`, `.ui-section`, `.ui-section-heading`, `.ui-section-body`, `.ui-link`, `.ui-button`, `.ui-button-primary`, `.ui-button-danger` using `var(--*)` tokens only
- [ ] 7.3 Create `docs_app/static/styles/tokens.css` and `docs_app/static/styles/components.css` mirroring the framework's design tokens (for standalone development without the framework CSS being served)
- [ ] 7.4 Update `docs_app/app.py` to remove all Bootstrap and highlight.js links and scripts, and add `<link rel="stylesheet">` tags for the new static CSS files

## 8. docs_app Navigation and Theme Toggle

- [ ] 8.1 Create `docs_app/components/theme_toggle.py` with a `ThemeToggle` component that uses `use_theme()` and renders a button with `aria-label`, `role="switch"`, and `aria-checked` based on the current theme
- [ ] 8.2 Rewrite `docs_app/components/navigation.py` `scoped_style` to use only `var(--*)` references; preserve the existing dropdown and mobile-menu behavior
- [ ] 8.3 Add the `ThemeToggle` to the rendered navbar in `docs_app/components/navigation.py`
- [ ] 8.4 Verify the navigation still passes the existing component tests after the rewrite

## 9. docs_app Template and Page Migration

- [ ] 9.1 Rewrite `docs_app/templates/home.py` `scoped_style` to use only `var(--*)` references
- [ ] 9.2 Replace inline `<code>` elements, class-string repetition, and ad-hoc section markup in `templates/home.py` with the new `InlineCode`, `Card`, and `Section` components
- [ ] 9.3 Rewrite `docs_app/pages/not_found.py` to use design-token-based styles via the new local components
- [ ] 9.4 Update `docs_app/components/demo_display.py` to use `CodeBlock` from `webcompy.ui.code_block` instead of the existing `SyntaxHighlighting`
- [ ] 9.5 Replace `docs_app/components/syntax_highlighting.py` with a thin wrapper around `CodeBlock` (preserving the existing API for any other callers)
- [ ] 9.6 Update `docs_app/router.py` and any other docs_app file that imports `SyntaxHighlighting` to import from the new wrapper or directly from `webcompy.ui.code_block`

## 10. Verification

- [ ] 10.1 Run `uv run pytest` and ensure all unit tests pass (including the new tests for tokens, theme system, use_theme, lexers, highlight, and CodeBlock)
- [ ] 10.2 Run `uv run pyright` and resolve any type errors
- [ ] 10.3 Run `uv run ruff check .` and `uv run ruff format .` and resolve any lint or format issues
- [ ] 10.4 Manually start the dev server with `uv run python -m webcompy start --dev --app docs_app.bootstrap:app` and verify: (a) the page loads with the OS-preference theme (or the cookie-persisted theme), (b) the `ThemeToggle` button cycles through light/dark/system, (c) code blocks render with syntax highlighting, (d) no console errors and no external network requests in the Network tab
- [ ] 10.5 Generate a static site with `uv run python -m webcompy generate --app docs_app.bootstrap:app` and verify: (a) all CSS files are present in the output, (b) no external CDN references remain in the rendered HTML, (c) the `<html>` element has the correct `data-theme` attribute based on a request with a `webcompy-theme` cookie
- [ ] 10.6 Run any existing E2E tests (or update them) to confirm the new docs_app markup matches the expected selectors

## 11. Process and Documentation

- [ ] 11.1 Update `.opencode/agents/ci-review.md` to add a "Framework Friction Signals" review checklist category: runtime CSS generation, repeated class strings, FOUC tolerance, `<html>` selectors in scoped CSS, DOM re-injection hacks
- [ ] 11.2 Mark `openspec/changes/feat-docs-tailwind-modernization/proposal.md` as superseded with a note pointing to `feat-ui-toolkit-foundation`
- [ ] 11.3 Add a short docs section (in `docs_app/pages/` or as a `README.md` under `webcompy/ui/`) describing how to register a custom `Lexer` and how to opt into Pygments
- [ ] 11.4 Add a CHANGELOG entry under `CHANGELOG.md` (or equivalent) describing the framework API additions (`webcompy.ui.theme`, `webcompy.ui.code_block`, `use_theme()`) and the breaking change to `scoped_style` (now wrapped in `@layer webcompy-scope`)
