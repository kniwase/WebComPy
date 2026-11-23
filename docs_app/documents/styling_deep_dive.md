---
title: Styling Deep Dive
description: Master WebComPy's full CSS @layer cascade, css_text_template(), reactive component styles, unlayered app.append_style() helpers, incremental style injection, and :host patterns.
---

# Styling Deep Dive

Beyond static `.scoped_style` dictionaries and design tokens, WebComPy lets you parse external CSS files, bind component stylesheets directly to reactive signals (`reactive_scoped_style`), inject unlayered dynamic app-wide variables (`app.append_style`), and style custom-element host boundaries (`:host`).

Use these APIs when component styling needs dynamic theme computation, per-instance host state, or app-wide CSS custom-property control without specificity battles or `!important`.

## The full CSS `@layer` cascade model

Framework stylesheets declare an explicit layer order at the top of `/_webcompy-ui/index.css` and `/_webcompy-ui/prose.css`:

```text
@layer reset, tokens, components, prose, webcompy-scope;

Lowest priority                                                  Highest priority
──────────────────────────────────────────────────────────────────────────────────
reset ──► tokens ──► components ──► prose ──► webcompy-scope ──► Unlayered CSS
                       │                        │                    │
                       ├─ webcompy.ui defaults  ├─ .scoped_style     ├─ app.append_style()
                       └─ [webcompy-component]  └─ reactive_scoped   └─ global links loaded after
                          { display: contents }                       framework stylesheets
```

Because **unlayered rules always outrank any `@layer` rule in CSS**, `app.append_style(...)` beats every layered framework and component rule cleanly regardless of selector specificity—no `!important` needed.

Ordering guarantees across SSR and the browser:

- **SSR/SSG `<head>` emission**: HTML generation emits `<link rel="stylesheet" href=".../_webcompy-ui/index.css">` *before* all `<style data-webcompy-cid="...">` and `<style data-webcompy-cid-rx="...">` blocks so the `@layer` declaration always defines the canonical priority order first in document order.
- **Browser default component style**: Even on apps that do not link `index.css`, WebComPy injects `<style id="webcompy-component-defaults">@layer components { [webcompy-component] { display: contents; } }</style>` *ahead* of any component `webcompy-scope` `<style>` element so `@define_component(display=...)` and `:host` overrides always win cleanly.

## `css_text()` and `css_text_template()`

Import `css_text` and `css_text_template` from `webcompy.template` to write standard CSS syntax—including CSS loaded from package resource files—instead of nested Python dicts:

```python
from webcompy import load_text
from webcompy.components import ComponentContext, define_component
from webcompy.elements import html
from webcompy.template import css_text


@define_component(display="block")
async def ExternalStyledCard(context: ComponentContext[None]):
    css_src = await load_text("styles/card.css")
    ExternalStyledCard.scoped_style = css_text(css_src)
    return html.DIV({"class": "card-body"}, "Styled from styles/card.css")
```

For reactive CSS strings with `{{ var }}` or `{{ a.b.c }}` interpolations, combine `css_text_template(source, context)` with `reactive_scoped_style(...)`:

```python
from webcompy import use_state
from webcompy.components import ComponentContext, define_component, reactive_scoped_style
from webcompy.elements import html
from webcompy.template import css_text_template


@define_component()
def SwatchBox(context: ComponentContext[None]):
    accent = use_state(lambda: "#2563eb")
    padding = use_state(lambda: "1rem")

    context.use_reactive_scoped_style(
        reactive_scoped_style(
            css_text_template(
                """
                .box {
                    border: 2px solid {{ accent }};
                    padding: {{ pad }};
                }
                """,
                {"accent": accent, "pad": padding},
            )
        )
    )

    return html.DIV({"class": "box"}, "Reactive swatch")
```

`css_text_template()` returns a synchronous factory that resolves holes when `reactive_scoped_style` evaluates its internal `Computed`. When loading templates from disk via `await load_text(...)`, await the file before passing the string into `css_text_template()`.

## Reactive component styles (`reactive_scoped_style`)

Declare signal-driven component CSS inside setup using `reactive_scoped_style(func)` and `context.use_reactive_scoped_style(style)`:

```python
from webcompy import use_state
from webcompy.components import ComponentContext, define_component, reactive_scoped_style
from webcompy.elements import html


@define_component()
def ProgressMeter(context: ComponentContext[None]):
    percent = use_state(lambda: 40)

    style = reactive_scoped_style(
        lambda: {
            ".fill": {"width": f"{percent.value}%", "background": "var(--color-accent)"},
        }
    )
    context.use_reactive_scoped_style(style)

    return html.DIV({"class": "track"}, html.DIV({"class": "fill"}))
```

Runtime behavior and lifecycle:

- **Dedicated `<style>` elements**: Static `.scoped_style` emits `<style data-webcompy-cid="{cid}">`; each registered reactive style emits `<style data-webcompy-cid-rx="{cid}-{index}">`. Static and reactive rules coexist independently and both wrap inside `@layer webcompy-scope`.
- **No component re-render**: When a signal read inside `func` changes, WebComPy recomputes the CSS and updates the `<style data-webcompy-cid-rx>` element's `textContent` synchronously—preserving child DOM state.
- **Identical selector scoping**: Combinators, pseudo-classes (such as `:nth-child(2n+1)`), at-rules (`@media`), and leading combinators (`> .child`) follow the exact same scoping rules as static `.scoped_style` without leaking across nested components.
- **SSR + cleanup**: During SSR/SSG, reactive styles are evaluated after the component tree and async setups settle so initial HTML reflects settled signal values. Subscriptions are disposed automatically on component destruction (`on_before_destroy`), or explicitly via `context.remove_reactive_scoped_style(style)`.

## Unlayered app styles: `append_style`, `reactive_style`, `reactive_block`

To inject global rules or app-wide reactive design tokens, use `app.append_style(...)` together with the helpers in `webcompy.app` / `webcompy.app.styles`:

```python
from webcompy.app import WebComPyApp, reactive_block, reactive_style
from webcompy.signal import Computed, Signal

accent_color = Signal("#0969da")
body_fg = Signal("#111827")

app = WebComPyApp(root_component=AppRoot)

# 1. Reactive CSS custom properties on :root
app.append_style(
    reactive_style(
        ":root",
        {
            "--color-accent": accent_color,
            "--surface-radius": "8px",
            "--badge-bg": lambda: accent_color.value,
        },
    )
)

# 2. Arbitrary reactive CSS declarations block
app.append_style(
    reactive_block(
        "body",
        Computed(lambda: f"  color: {body_fg.value};"),
    )
)
```

Each `app.append_style(...)` call emits `<style data-webcompy-dynamic="{idx}">` into `<head>` **without** any `@layer` wrapper, making it highest-priority unlayered CSS. `reactive_style(selector, vars_dict)` accepts plain `str`, `SignalBase[str]`, or `Callable[[], str]` values; `reactive_block(selector, content)` accepts a `str`, `SignalBase[str]`, or callable producing CSS declarations. All dynamic style subscriptions clean up automatically when `RenderContext.dispose()` runs.

## Incremental scoped styles & lazy routes

Instead of concatenating one monolithic stylesheet, WebComPy tracks scoped styles per component inside each context's `ComponentStore` (alongside the shared `<style id="webcompy-scoped-styles">*[hidden]{display: none;}</style>` utility element):

- On every render cycle (including after navigating to a `lazy()` route), `HeadElement._render()` checks `<head>` via `style[data-webcompy-cid="..."]` and injects missing stylesheets idempotently—never creating duplicates across hydration or repeated renders.
- Across SSR/SSG requests, component generators remain visible to newly created render contexts even if lazily imported on an earlier route, keeping per-route CSS output deterministic regardless of route generation order.

## Advanced `:host` host-wrapper patterns

Every `@define_component()` component has a named Light DOM wrapper (`<my-card>`), so both static `.scoped_style` and `reactive_scoped_style` can target the wrapper directly using `:host` and compound host selectors like `:host(.active)` or `:host([data-state="open"])`:

```python
@define_component(display="block")
def AccordionCard(context: ComponentContext[None]):
    expanded = use_state(lambda: False)

    context.use_reactive_scoped_style(
        reactive_scoped_style(
            lambda: {
                ":host": {
                    "border-color": "var(--color-accent)" if expanded.value else "var(--color-border)",
                },
            }
        )
    )
    return html.DIV({"class": "inner"}, "...")
```

WebComPy rewrites `:host` selectors to target the component's custom-element tag paired with its `webcompy-cid-*` attribute, working identically in SSR HTML and browser runtime updates. Display precedence on the wrapper is strictly layered: framework default (`contents` in `components`) < `@define_component(display=...)` < component `:host` rules in `webcompy-scope` < unlayered `app.append_style`.

## Pitfalls

- **`async def` functions fail in `reactive_scoped_style`**: Passing an async callable to `reactive_scoped_style` raises `TypeError` because `Computed` dependencies must evaluate synchronously. Run `await load_text(...)` before constructing `css_text_template` or `reactive_scoped_style`.
- **Calling `use_reactive_scoped_style()` outside setup**: Invoking `context.use_reactive_scoped_style(...)` outside an active `@define_component` setup raises `WebComPyException`.
- **Global unlayered overrides trump component styles**: Because `app.append_style` emits unlayered CSS, generic selectors (like `button { ... }`) added there override every component's `.scoped_style`. Keep `app.append_style` focused on `:root` tokens or intentional top-level overrides.

## Next steps

- Revisit theme switching with `use_theme()` and static `css_text()` in [Styling & Themes](/documents/basic/styling-and-themes).
- Review custom-element wrapper behavior and `display` options in [Custom Elements](/documents/advanced/custom-elements).
- Pair box-generating wrapper styles with enter/leave animations in [Transition](/documents/advanced/transition).
- Inspect how first-party design tokens structure the `components` layer in [UI Primitives](/documents/basic/ui-primitives).
