# Design: Reactive App-Level Style

## Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│ User code                                                                │
│                                                                          │
│   from webcompy.app.styles import reactive_style                         │
│                                                                          │
│   app = WebComPyApp(...)                                                  │
│   accent = Signal("#0969da")                                             │
│   app.append_style(reactive_style(":root", {                             │
│       "--color-accent": accent,                                           │
│   }))                                                                    │
│                                                                          │
│   # UI updates accent.value → CSS variable updates → all elements         │
│   # using var(--color-accent) repaint                                    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Framework internal                                                       │
│                                                                          │
│   reactive_style(selector, vars)                                         │
│     ├ builds Computed[str] = computed(lambda: _render_css(sel, vars))    │
│     └ _render_css: ":root { --x: v; --y: w; }"                           │
│                                                                          │
│   WebComPyApp.append_style(content)                                      │
│     ├ ctx.append_style(content)                                          │
│     └ AppDocumentRoot.append_style(content)                              │
│       └ HeadElement.append_style(content)                                │
│         ├ self._styles.append(content)                                   │
│         └ if pyscript + Computed: subscribe on_after_updating             │
│                                                                          │
│   HeadElement._render()                                                  │
│     └ for i, content in enumerate(self._styles):                         │
│         create <style data-webcompy-dynamic="{i}">                        │
│         wrap content in @layer webcompy-dynamic { ... }                  │
│         subscribe to Computed updates                                    │
│                                                                          │
│   HeadElement.get_head_content_html() (SSR)                               │
│     └ for i, content in enumerate(self._styles):                         │
│         render <style data-webcompy-dynamic="{i}"> with current value    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

## Decisions

### Decision 1: New `@layer webcompy-dynamic` (not unlayered, not in `webcompy-scope`)

The dynamic style is wrapped in a new explicit layer. The full cascade becomes:

```css
/* webcompy/ui/_styles/index.css */
@layer reset, tokens, components, webcompy-scope, webcompy-dynamic;
```

**Why a layer and not unlayered**:
- Predictable cascade order (explicit, documented)
- User-defined `!important` rules can still override (intentional override path)
- Future framework changes can add layers without breaking the dynamic style position

**Why not `webcompy-scope`**:
- `webcompy-scope` is for per-component scoped styles. Adding app-level global rules there would muddy the semantics.
- A separate layer keeps each layer's purpose clear.

### Decision 2: Element attribute is `data-webcompy-dynamic="{id}"` (numeric ID)

Each `app.append_style` call gets a numeric ID (0, 1, 2, ...) used as the element attribute value. This is distinct from `data-webcompy-cid` (per-component) and `data-webcompy-cid-rx` (per-component reactive) to avoid selector collision and to make intent clear.

**Trade-off accepted**: ID stability across calls. If users add/remove styles dynamically, the IDs may shift. This is acceptable because:
- `append_style` is typically called once at app setup, not dynamically
- If a style is removed (not in this change's scope), the framework would manage the cleanup

### Decision 3: Helper functions `reactive_style` and `reactive_block`

Two helpers are provided to cover the common cases:

```python
def reactive_style(
    selector: str,
    vars: Mapping[str, str | SignalBase[str] | Callable[[], str]],
) -> Computed[str]:
    """Build ':root { --x: ...; --y: ...; }' from a var name → value mapping."""

def reactive_block(
    selector: str,
    content: str | SignalBase[str] | Callable[[], str],
) -> Computed[str]:
    """Build ':root { <content> }' where content is a whole CSS block."""
```

**Why both**: `reactive_style` is the common case (override CSS variables). `reactive_block` is the escape hatch (any CSS, not just variables). `reactive_style` is more constrained but type-safe; `reactive_block` is more flexible.

**Why not just one function**: Conflating the two would force users to either pass a dict (awkward for `reactive_block`) or a string (lossy for `reactive_style`).

### Decision 4: Subscription is `Computed.on_after_updating`

The existing pattern in `set_html_attr` uses `Computed.on_after_updating(callback)`. The same pattern is reused for consistency. The callback is the only `CallbackConsumerNode` per dynamic style.

The subscription is registered with the active effect scope at `append_style` time. When the head element is disposed, all subscriptions are torn down via `_cleanup_consumers`.

### Decision 5: SSR output uses `Computed.value` at generation time

During `get_head_content_html()`, the framework calls `content.value` on each `Computed`. This evaluates the function with the current signal values. The output is a static `<style>` element in the generated HTML.

**Caveat**: If a signal changes between SSR and client hydration, there is a flash. This is the same flash the current `data-theme` approach has, and is out of scope here.

### Decision 6: No new layer helper API (e.g., `app.append_style_in_layer`)

The user can wrap their CSS in `@layer foo { ... }` manually if they need a different layer. The default layer is `webcompy-dynamic`. This avoids API proliferation.

**Alternative considered**: Allow the user to specify a layer name. Rejected for now; can be added later if needed.

## Alternatives Considered

### A. Reuse `set_html_attr` with a CSS-style attribute — rejected

A `data-style` attribute or similar cannot drive dynamic CSS variable values. The CSS variables live in `<style>` elements (or inline `style=""` attributes), not in data attributes.

### B. Inline `style="..."` attribute binding — limited

The existing `{"style": computed(lambda: "...")}` pattern works for inline styles. But it does not affect `var(--*)` references and cannot be scoped to `:root`. Useful for per-element dynamic styles; insufficient for app-wide design tokens.

### C. CSS `@property` declarations — deferred

`@property` is a CSS Houdini feature that allows typed custom properties. It is not yet widely supported (Safari, older browsers lack it). Out of scope for this change; can be combined later.

### D. Use Shadow DOM for style isolation — rejected

Adds complexity. The existing `scoped_style` + cid attribute approach already isolates component styles. App-level styles are intentionally global.

## File Layout

```
webcompy/app/
├── __init__.py                  # export reactive_style, reactive_block
├── _app.py                      # append_style method
├── _render_context.py           # ctx.append_style method
├── _root_component.py           # root.append_style method
└── styles.py                    # NEW: reactive_style, reactive_block helpers

webcompy/elements/
└── _head.py                     # _styles, append_style, _render + SSR extensions

webcompy/ui/_styles/
└── index.css                    # add webcompy-dynamic layer

tests/
└── test_reactive_app_style.py   # NEW

openspec/
├── changes/feat-reactive-app-style/
│   ├── proposal.md
│   ├── design.md (this file)
│   ├── tasks.md
│   └── specs/
│       ├── app-styles/spec.md (NEW)
│       └── app/spec.md (delta: append_style method)
│       └── css-architecture/spec.md (delta: new layer)
```

## OpenSpec Spec Locations

- `openspec/specs/app-styles/spec.md` (NEW) — describes the `app.append_style` primitive
- `openspec/specs/app/spec.md` (delta) — adds `append_style` to the `WebComPyApp` API
- `openspec/specs/css-architecture/spec.md` (delta) — adds `webcompy-dynamic` to the cascade

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `webcompy-dynamic` layer interferes with user CSS | low | low | The layer is explicitly declared in `index.css`. Users can override via unlayered rules or their own `@layer` declarations. |
| `Computed` re-evaluation cost on every signal change | low | low | The CSS string is typically small. Recomputing is O(n) declarations. |
| `append_style` called many times creates many `<style>` elements | low | low | Browsers handle thousands of style elements. No upper bound enforced. |
| User-defined selector collides with framework selectors | low | medium | The framework uses `:root` and `[data-webcompy-*]` attributes. User selectors that target these should be tested. |
| Subscription leak on app teardown | low | medium | Reuse `HeadElement._cleanup_consumers` pattern from existing `set_html_attr`. |

## Cross-Reference: Phase 1 (`feat-reactive-scoped-style`)

The two changes are conceptually paired:

| Phase 1 (per-component) | Phase 2 (app-level) |
|------------------------|---------------------|
| `context.use_reactive_scoped_style(...)` | `app.append_style(...)` |
| `<style data-webcompy-cid-rx="{cid}-{index}">` | `<style data-webcompy-dynamic="{id}">` |
| `@layer webcompy-scope` (existing) | `@layer webcompy-dynamic` (new) |
| Inside component setup | At app setup |
| Scoped to component | Global / app-level |

They can be developed in parallel and shipped in the same release. The two OpenSpec changes are independent and can be archived independently.
