# webcompy.ui

First-party UI toolkit for WebComPy applications. This package provides the theme system, the `CodeBlock` component with a pluggable lexer protocol, and a set of CSS design tokens that the framework auto-serves at `/_webcompy-ui/`.

## Submodules

- `webcompy.ui.theme` — `Theme` enum (LIGHT/DARK/SYSTEM), `ThemeManager` (DI-managed), `use_theme()` composable, cookie persistence, and SSR-safe initial render.
- `webcompy.ui.code_block` — `CodeBlock` component, `highlight()` function, `Lexer` protocol, built-in lexers (Python, Bash, TOML), and a Pygments adapter skeleton.
- `webcompy.ui.headless` — behavior-only primitives: state management, ARIA roles/attributes, and focus logic with no visual styling.
- `webcompy.ui.components` — themed primitives composed from the headless layer, styled with the design tokens.
- `webcompy.ui._styles` — static CSS files (`tokens.css`, `reset.css`, `components.css`, `primitives.css`, `code-block.css`, `syntax-theme.css`, `index.css`). The framework auto-injects `/_webcompy-ui/index.css` into the page head.

## UI primitives: the two-layer model

Reusable components ship in two layers with the same component name in each:

```
webcompy.ui.headless.Spinner     behavior core  (state, ARIA, focus; no styling)
webcompy.ui.components.Spinner   themed skin    (token-based defaults)
webcompy.ui.Spinner              the themed variant (default import path)
```

**Headless layer** — owns all behavior: state management, ARIA roles and attributes, keyboard interaction, and focus management. It never emits visual styles (colors, spacing, typography, borders, shadows, decorative animation); only structural CSS required by behavior (positioning, display toggling, visibility) is allowed. Interaction state is exposed on the DOM through `data-state` attributes with a per-component vocabulary (e.g. `data-state="loading"` for `Spinner`), so user CSS can react to state declaratively:

```css
.my-spinner[data-state="loading"] { /* user styling */ }
```

**Themed layer** — renders the corresponding headless component and adds default class names whose rules live in the shipped stylesheet (`primitives.css`, inside the `@layer components` cascade) and consume design tokens (`var(--color-*)`, `var(--space-*)`, ...). The themed layer carries zero behavior logic. `prefers-reduced-motion` is honored by themed components that animate.

**Styling hooks** — every component accepts a `class_name` prop applied to its root element (named `class_name` because `class` is a Python keyword; it maps to the DOM `class` attribute). Multi-part components expose part-specific class props (`class_panel`, `class_overlay`, ...). User classes are appended after framework classes, so user rules win at equal specificity:

```python
from webcompy.ui import Spinner          # themed (default)
from webcompy.ui.headless import Spinner  # headless, full control

Spinner({"label": "Loading data"})
Spinner({"label": "Loading data", "size": "lg"})
Spinner({"label": "Loading data", "class_name": "my-spinner"})
```

**Cascade note** — themed defaults live inside `@layer components`. Unlayered user CSS always overrides them without specificity escalation. User CSS placed inside `@layer components` competes by source order (framework stylesheets are imported first).

## Registering a custom Lexer

Built-in coverage is intentionally small (Python, Bash, TOML). To add support for a new language — or to override the built-in lexers for higher accuracy — implement the `Lexer` protocol and register it during application startup.

```python
from webcompy.ui.code_block import Lexer, Token, TokenType, register_lexer
from webcompy.signal import SignalBase


class MyLexer(Lexer):
    name = "mylang"
    aliases: tuple[str, ...] = ("ml",)
    file_extensions: tuple[str, ...] = (".ml",)

    def tokenize(self, code: str) -> list[Token]:
        # ... custom tokenization ...
        return []


register_lexer(MyLexer())
```

After registration, `<MyLexer-instance>` is available via `get_lexer("mylang")` and `<CodeBlock lang="mylang" ... />` will use it.

## Opting into Pygments

The file `webcompy/ui/code_block/lexers/_adapters/_pygments.py` ships a complete Pygments adapter implementation. It is **not imported** by any other framework module by default, so adding Pygments to your project is opt-in:

1. Add Pygments to your dependencies: `uv add pygments`.
2. At application startup (e.g., in your `app.py`), import the adapter and register the languages you need:

    ```python
    from webcompy.ui.code_block.lexers._adapters._pygments import register_pygments_lexer

    register_pygments_lexer("javascript")
    register_pygments_lexer("typescript")
    ```

3. The Pygments lexer is registered with the same name Pygments uses, so `CodeBlock` automatically picks it up.

The dual-class output (`.tok-kw k`) means Pygments stylesheets work without any framework-side changes.

## Theme system

The `Theme` enum is `light`, `dark`, or `system`. `system` defers to the OS preference, implemented as a `@media (prefers-color-scheme: dark)` block in the reactive style generated by `ThemeManager` (see `webcompy.ui.theme._tokens`). The browser-side state is stored in a `webcompy-theme` cookie (1-year lifetime, `Path=/`, `SameSite=Lax`).

```python
from webcompy.ui.composables import use_theme
from webcompy.ui.theme import Theme

def MyComponent():
    signal, controller = use_theme()
    # signal.value is a Theme enum
    # controller.set(Theme.DARK), controller.toggle(), controller.cycle()
```

SSR safety is provided by reading the cookie server-side and passing the value to `app.create_render_context(path, initial_theme=...)`. The default when no cookie is present is `Theme.SYSTEM`.

## CSS design tokens

The framework auto-serves `webcompy/ui/_styles/index.css` at `/_webcompy-ui/index.css`. The file declares `@layer reset, tokens, components, webcompy-scope;` and aggregates the individual stylesheets. Applications typically only need to add `var(--*)` references in their `scoped_style` blocks.

Key tokens:

| Token | Purpose |
|-------|---------|
| `--color-bg`, `--color-bg-elevated`, `--color-bg-card` | Backgrounds |
| `--color-fg`, `--color-fg-muted`, `--color-fg-subtle` | Foregrounds |
| `--color-link`, `--color-link-hover`, `--color-accent` | Accents |
| `--color-border`, `--color-border-muted` | Borders |
| `--color-success`, `--color-danger`, `--color-warning` | Status |
| `--space-1` ... `--space-8` | Spacing scale |
| `--font-size-sm` ... `--font-size-2xl` | Type scale |
| `--font-sans`, `--font-mono` | Font families |
| `--radius-sm`, `--radius-md`, `--radius-lg` | Border radii |
| `--shadow-sm`, `--shadow-md` | Box shadows |
| `--tok-kw`, `--tok-str`, `--tok-num`, `--tok-comment`, `--tok-fn`, `--tok-builtin`, `--tok-decorator`, `--tok-op`, `--tok-punct`, `--tok-ident` | Syntax highlighting |

All tokens have light and dark variants; the dark variants are activated by `:root[data-theme="dark"]` (set server-side or by the theme system).
