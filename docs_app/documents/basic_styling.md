---
title: Styling & Themes
description: Style components with scoped dicts or css_text(), understand the CSS @layer cascade, register app-level styles, and toggle themes with use_theme().
---

# Styling & Themes

WebComPy combines component-scoped CSS with a layered design-token stylesheet so component styles stay isolated while remaining easy to override cleanly — without `!important` wars.

## At a glance

```python
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.template import css_text


@define_component(display="block")
def FeatureBox(context: ComponentContext[dict[str, str]]):
    return html.DIV(
        {"class": "box"},
        html.H3({"class": "title"}, context.props["title"]),
    )


FeatureBox.scoped_style = css_text(
    """
    :host {
        padding: var(--space-4);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-md);
        background: var(--color-bg-card);
    }
    .title {
        margin: 0;
        color: var(--color-fg);
    }
    """
)
```

## Scoped styles: Python dicts vs `css_text()`

Every component accepts a `.scoped_style` attribute holding a `dict[str, StyleDict]`. You can write it either as a Python dictionary or parse standard CSS syntax with `css_text()` from `webcompy.template`:

```python
# Option A: Python dictionary
FeatureBox.scoped_style = {
    ".title": {
        "font-size": "var(--font-size-lg)",
        "color": "var(--color-accent)",
    },
    "@media (max-width: 640px)": {
        ".title": {"font-size": "var(--font-size-base)"},
    },
}

# Option B: CSS string parsed via css_text()
FeatureBox.scoped_style = css_text("""
    .title {
        font-size: var(--font-size-lg);
        color: var(--color-accent);
    }
""")
```

WebComPy rewrites selectors under a unique `webcompy-cid-*` attribute automatically so styles apply only inside that component (while `:host` targets the component's custom element tag itself). Notice in [Components](/documents/basic/components) that `display="block"` gives the custom element wrapper a real CSS box instead of the default `display: contents` (precedence: framework `contents` < `display=` argument < `:host` rules).

## How the CSS `@layer` cascade works

WebComPy declares an explicit cascade layer order at the top of `/_webcompy-ui/index.css` (and `prose.css`):

```text
Lowest priority                                              Highest priority
-----------------------------------------------------------------------------
reset  -->  tokens  -->  components  -->  prose  -->  webcompy-scope  -->  unlayered user CSS
```

| Layer | What lives here |
|---|---|
| `reset` | Box-sizing and minimal base defaults |
| `tokens` | Semantic CSS variables (`--color-*`, `--space-*`, `--radius-*`, `--font-*`) |
| `components` | First-party `webcompy.ui` themed component styles and `CodeBlock` styles |
| `prose` | Opt-in `.prose` typography rules (`/_webcompy-ui/prose.css`) |
| `webcompy-scope` | Component `.scoped_style` rules |
| Unlayered | Global stylesheets linked after framework styles and `app.append_style(...)` |

Because unlayered CSS always outranks any `@layer` rule regardless of selector specificity, global rules in your static stylesheets or `app.append_style(...)` override framework defaults cleanly without specificity escalation.

## Switching light, dark, and system themes with `use_theme()`

First-party design tokens adapt automatically when the active theme changes between `Theme.LIGHT`, `Theme.DARK`, and `Theme.SYSTEM` (which tracks the OS `prefers-color-scheme` media query). Use `use_theme()` from `webcompy.ui.theme`:

```python
from webcompy import use_computed
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.ui.theme import Theme, use_theme


@define_component()
def ThemeSwitchButton(context: ComponentContext[None]):
    theme_signal, controller = use_theme()

    label = use_computed(
        lambda: f"Theme: {theme_signal.value.value}"
    )

    return html.BUTTON(
        {"type": "button", "@click": lambda _ev: controller.cycle()},
        label,
    )
```

`controller` offers three methods:

- `controller.set(Theme.DARK)` — set an explicit `Theme` (`LIGHT`, `DARK`, or `SYSTEM`).
- `controller.toggle()` — alternate between `LIGHT` and `DARK`.
- `controller.cycle()` — step `LIGHT` → `DARK` → `SYSTEM` → `LIGHT`.

Using semantic token variables such as `var(--color-bg)`, `var(--color-bg-card)`, `var(--color-fg)`, `var(--color-border)`, and `var(--color-accent)` in your own CSS ensures custom components switch themes alongside `webcompy.ui` components.

## App-level stylesheets and head links

Include external or static stylesheets via `app.set_head({"link": [...]})` and inject inline global CSS at app setup with `app.append_style(...)`:

```python
app.set_head(
    {
        "title": "My App",
        "link": [
            {"rel": "stylesheet", "href": "/styles/app.css"},
        ],
    }
)
app.append_style(":root { --color-accent: #2563eb; }")
```

## Notes & caveats

- Put selectors scoped to `.scoped_style` without manual `cid` prefixes — WebComPy handles scoping automatically (prefix selectors with `" .foo"` or `".foo"` as shown above; use `:host` for the component wrapper element).
- `use_theme()` requires WebComPy's theme manager to be active in the app DI scope (provided automatically by `WebComPyApp` unless explicitly disabled in `WebComPyAppConfig(theme=...)`).

## Next steps

- Review how `webcompy.ui` uses design tokens and cascade layers in [UI Primitives](/documents/basic/ui-primitives).
- See `:host` and `display` wrapper rules in [Custom Elements](/documents/advanced/custom-elements).
- Continue to [Styling Deep Dive](/documents/advanced/styling-deep-dive) for `reactive_scoped_style`, `css_text_template`, app-level `reactive_style` / `reactive_block`, and the full cascade model.
