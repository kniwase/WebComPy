# Proposal: Reactive App-Level Style

## Why

`feat-reactive-scoped-style` (Phase 1) introduces per-component reactive styles that update a `<style data-webcompy-cid-rx>` element when signals change. That primitive is excellent for component-scoped concerns (a dynamic bar width, a hover/active state on a single widget), but it cannot reach the global level: there is no per-component generator for the `<html>` element or the document root.

The existing 3-state theme system (light / dark / system) sidesteps this by storing the active theme in `app.set_html_attr("data-theme", ...)` and using static `:root[data-theme="..."]` CSS rules. This works, but the bridge between the Python `Signal[Theme]` and the CSS depends on:

1. The dev server / SSG generating the right `data-theme` attribute at request time
2. The browser updating that attribute on `ThemeManager.set()`
3. CSS selectors like `:root[data-theme="dark"]` matching correctly

Any failure in this chain (which we have observed in the docs_app) silently breaks the theme switch with no diagnostic signal. The architecture is correct in principle but fragile in practice.

This change adds a **reactive app-level style** primitive:

- `app.append_style(content)` accepts a `str | Computed[str]`
- The framework injects a single `<style data-webcompy-dynamic="{id}">` element per call
- The element's `textContent` is updated reactively when the `Computed` changes
- An optional `reactive_style(selector, vars_dict)` helper builds a `Computed[str]` from a mapping of `var-name → Signal/str`

A subsequent, separate change may migrate the theme system to use this primitive. This change ships the primitive itself and one small example (e.g., a runtime CSS-variable override demo) but does **not** touch the existing theme system.

## What Changes

- **NEW** `webcompy.app.styles` module — exports `reactive_style(selector, vars_dict)` and `reactive_block(selector, content)` helpers.
- **NEW** `WebComPyApp.append_style(content: str | Computed[str])` method — registers an app-level reactive style.
- **NEW** `RenderContext.append_style(content)` method — delegates to root.
- **NEW** `AppDocumentRoot.append_style(content)` method — delegates to head.
- **NEW** `HeadElement._styles: list[str | Computed[str]]` and `append_style(content)` method.
- **NEW** `<style data-webcompy-dynamic="{id}">` element — emitted into `<head>` per registration. ID is the position in `_styles` (0-based).
- **NEW** Subscription wiring — each `Computed[str]` style subscribes via `on_after_updating(callback)` to update its element's `textContent`. Subscription is disposed on app teardown.
- **NEW** SSR support — `HeadElement.get_head_content_html()` emits one `<style data-webcompy-dynamic>` per registered style with the current `Computed` value.
- **NEW** `@layer webcompy-dynamic` — new layer declared in `webcompy/ui/_styles/index.css`. The dynamic style is wrapped in this layer so it has higher cascade priority than `tokens`, `components`, and `webcompy-scope`, but remains inside the explicit layer system (predictable, debuggable).

## Capabilities

### New Capabilities

- `app-styles`: The framework SHALL provide `app.append_style(content)` for app-level reactive style injection. `content` is a plain string (static) or a `Computed[str]` (reactive). The framework SHALL render and update a single `<style data-webcompy-dynamic>` element per registration.
- `reactive-style-helper`: The framework SHALL provide a `reactive_style(selector, vars_dict)` helper that returns a `Computed[str]` suitable for `app.append_style`. The dict values may be plain strings, `SignalBase[str]`, or callables returning strings.

### Modified Capabilities

- `app`: `WebComPyApp` gains an `append_style(content)` method. `RenderContext` and `AppDocumentRoot` gain matching methods. `HeadElement` is extended.
- `css-architecture`: A new `@layer webcompy-dynamic` is added to the framework cascade. The full cascade becomes `reset, tokens, components, webcompy-scope, webcompy-dynamic`.

## Non-goals

- **No migration of the existing theme system.** `ThemeManager`, `use_theme()`, `data-theme` attribute, and `tokens-dark.css` continue to work unchanged. Migrating them is a follow-up change.
- **No replacement of `set_html_attr`.** Both primitives coexist.
- **No async style functions.** `Computed` contract requires sync evaluation.
- **No scoping orcid-based selectors.** App-level styles use raw selectors the user provides (e.g., `:root`, `.my-class`).
- **No inline `<style>` injection from component setup.** This is a per-component concern (covered by `feat-reactive-scoped-style`).

## Impact

- `webcompy/app/styles.py` — new module: `reactive_style`, `reactive_block` helpers.
- `webcompy/app/_app.py` — `append_style` method.
- `webcompy/app/_render_context.py` — `append_style` method.
- `webcompy/app/_root_component.py` — `append_style` method.
- `webcompy/elements/_head.py` — `_styles` list, `append_style` method, `_render` and `get_head_content_html` extensions.
- `webcompy/app/__init__.py` — re-export `reactive_style` / `reactive_block`.
- `webcompy/ui/_styles/index.css` — add `webcompy-dynamic` to the layer declaration.
- Tests: new `tests/test_reactive_app_style.py`.
- No new runtime dependencies.
- One CSS file change (single line in `index.css`).

## Dependencies

- None directly. The `Computed` primitive and `HeadElement` exist.
- Conceptually follows `feat-reactive-scoped-style` (Phase 1). The two can be developed in parallel and shipped in the same release cycle.

## Supersedes

- None.

## Known Issues Addressed

- None directly. The change introduces a new primitive. The docs_app theme-switching bug (if confirmed) is a separate concern that this change enables fixing in a follow-up.
