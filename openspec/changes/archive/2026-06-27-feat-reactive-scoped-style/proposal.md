# Proposal: Reactive Scoped Style

## Why

WebComPy's `scoped_style` attribute on components allows per-component CSS injection. Today it is **a static dictionary assigned after the component definition** (`MyComponent.scoped_style = {".x": {"color": "red"}}`). The values are processed once at class definition time and rendered into a single `<style data-webcompy-cid="...">` element during initial render.

This static model has two structural problems:

1. **No signal reactivity.** Values can only be plain strings. There is no way to make a scoped style react to a `Signal` change (e.g., a dynamic theme color, a hover/active state driven by user interaction, a progress-driven bar width). Today, the only path to reactive styling is the HTML-attribute dance (`app.set_html_attr("data-theme", ...)`) which scopes to the `<html>` element and forces the CSS to live in static `:root[data-theme="..."]` rules.
2. **Awkward composition.** The current API forces users to assign `scoped_style` from outside the component definition. Reactive state held inside the component (signals, computed values) cannot naturally close over the style definition. A user wanting `{"color": local_signal.value}` has to either (a) define the signal as a module-level global, or (b) compute the CSS string in a separate pass and assign it as a static value, which loses reactivity entirely.

This change introduces **`reactive_scoped_style(func)`** — a function (and matching class) that:

- Takes a callable returning the existing style-dict shape
- Closes over signals defined inside the component setup function
- Evaluates as a `Computed` (automatic dependency tracking and re-evaluation on signal change)
- Renders into a per-component `<style data-webcompy-cid-rx="...">` element
- Updates that element's `textContent` on every change, with no DOM-API dance

The static `scoped_style` attribute continues to work unchanged. The two systems coexist.

## What Changes

- **NEW** `webcompy.components.reactive_scoped_style` (function) and `ReactiveScopedStyle` (class) — public API for declaring reactive per-component styles inside the component definition.
- **NEW** `ComponentContext.use_reactive_scoped_style(style)` — register a reactive style for the current component. Multiple reactive styles per component SHALL be allowed.
- **NEW** `ComponentGenerator._reactive_styles` — list of reactive styles registered for the generator. Initialized empty.
- **NEW** `<style data-webcompy-cid-rx="{cid}-{index}">` element — emitted into `<head>` for each reactive style. Distinct attribute (`-rx` suffix) to avoid conflict with the static `data-webcompy-cid` element. Index in the attribute allows multiple reactive styles per component to coexist.
- **NEW** `HeadElement._render()` extension — for each registered component, iterate over `_reactive_styles` and create the `<style data-webcompy-cid-rx>` element if not already present. Initial value is `reactive_style.render_css(cid)`.
- **NEW** Subscription wiring — each reactive style subscribes to its inner `Computed[str]` via `on_after_updating(callback)`. The callback updates the matching `<style>` element's `textContent` in the browser. The subscription is torn down with the component.
- **NEW** `HeadElement.get_head_content_html()` extension — emit one `<style data-webcompy-cid-rx>` per reactive style during SSR, populated with the current `Computed` value.

## Capabilities

### New Capabilities

- `reactive-scoped-style`: A function (or class) that takes a callable returning the scoped-style dictionary shape, closes over signals inside the component setup, evaluates as a `Computed`, and updates the corresponding `<style>` element on every change. Multiple reactive styles per component are allowed.

### Modified Capabilities

- `components`: `ComponentContext` gains a `use_reactive_scoped_style(style)` method. `ComponentGenerator` gains a `_reactive_styles` list. `HeadElement` is extended to render and subscribe to reactive styles. The static `scoped_style` API is **unchanged** and the two systems coexist.

## Non-goals

- **No replacement of the static `scoped_style` API.** The current `MyComponent.scoped_style = {...}` pattern continues to work identically.
- **No replacement of `app.set_html_attr("data-theme", ...)`** for theme switching. The existing 3-state theme system stays as-is; a follow-up change may opt to migrate it to `reactive_scoped_style` if desired.
- **No async style functions.** `reactive_scoped_style` only accepts sync callables (matching the existing `Computed` contract).
- **No global / `:root` reactive style.** Reactive styles are scoped to a single component. Global reactive styling (e.g., changing the document-level `--color-bg` from a signal) is out of scope for this change.
- **No CSS-in-JS parsing or templating.** The callable must return the existing nested-dict shape. No string-template sugar, no f-string injection — those are separate concerns.
- **No animation or transition helpers.** Reactive styles update on signal change; smooth visual transitions are the CSS layer's responsibility.

## Impact

- `webcompy/components/_reactive_scoped_style.py` — new private module containing `ReactiveScopedStyle` and `reactive_scoped_style`.
- `webcompy/components/_libs.py` (or `_component.py`) — `ComponentContext` gains `use_reactive_scoped_style`.
- `webcompy/components/_generator.py` — `ComponentGenerator.__init__` initializes `_reactive_styles: list[ReactiveScopedStyle] = []`.
- `webcompy/elements/_head.py` — `_render()` iterates over reactive styles; `get_head_content_html()` emits them.
- `webcompy/components/__init__.py` — re-export `reactive_scoped_style` and `ReactiveScopedStyle`.
- Tests: new `tests/test_reactive_scoped_style.py`.
- No CSS file changes; no `@layer` additions.
- No runtime dependencies added.

## Dependencies

- None. This change builds on the existing `Computed` primitive and the existing `scoped_style` rendering pipeline.

## Supersedes

- None.

## Known Issues Addressed

- None directly. This is a new capability.
