## Context

The `_Loadscreen` class in `webcompy/cli/_html.py` generates the loading screen markup embedded in every generated `index.html`. The current structure uses:

```html
<div id="webcompy-loading">
  <style>
    body { ... }          /* global body override */
    .container { ... }    /* overlay wrapper */
    .loader { ... }       /* spinner */
  </style>
  <div class="container">
    <div class="loader"></div>
  </div>
</div>
```

This works in isolation but breaks when user stylesheets (e.g. Bootstrap) provide conflicting rules for `.container` (Bootstrap adds `max-width`, `margin: auto`). It also injects a global `body` selector which can override the page's expected body styles.

## Goals / Non-Goals

**Goals:**
- Eliminate CSS class name collision risk between the loading screen and any user-provided or third-party CSS.
- Remove the global `body` style rule from the loading screen inline `<style>` block.
- Keep the same visual appearance (50% dark overlay, centered animated spinner).
- Ensure `#webcompy-loading` removal logic in `AppDocumentRoot._render()` still works without changes.

**Non-Goals:**
- Making the loading screen configurable by users.
- Changing loading screen removal timing or lifecycle.
- Changing visual spinner design (colors, animation).

## Decisions

### Decision 1: Make `#webcompy-loading` the overlay root instead of an inner wrapper

Remove the intermediate `<div class="container">` wrapper. Attach `position: fixed; inset: 0` directly to `#webcompy-loading`.

**Rationale:** Fewer DOM nodes, zero collision surface. The element already has a unique ID guaranteed by the framework. `inset: 0` is equivalent to `top/right/bottom/left: 0` and guarantees full viewport coverage regardless of parent sizing.

**Alternative considered:** Keep the wrapper but rename its class to something unique like `.wc-loading-overlay`. Rejected — extra unnecessary nesting.

### Decision 2: Rename `.loader` to `.wc-loader`

The inner spinner div changes from `class="loader"` to `class="wc-loader"`.

**Rationale:** `loader` is a common class name used by many component libraries and CSS frameworks. `wc-loader` is an internal prefix that will not collide with user styles.

**Alternative considered:** `webcompy-loader`. Rejected — longer without adding meaning; `wc-` is a standard prefix used elsewhere in the framework.

### Decision 3: Remove the `body` CSS selector entirely

The inline style block will no longer contain `body { margin:0; padding:0; ... }`.

**Rationale:** `body` styling is the responsibility of the application's own stylesheet, not the loading screen. This rule was likely added defensively but causes interference (e.g. overriding Bootstrap's expected `body` typography).

**Alternative considered:** Scope `body` under `#webcompy-loading` (which doesn't make sense syntactically) or apply it only during loading. Rejected — unnecessary complexity; modern browsers handle initial body margins fine.

### Decision 4: Keep the inline `<style>` element inside `#webcompy-loading`

The styles will be attached as a child `<style>` node inside `#webcompy-loading`, just like today.

**Rationale:** This ensures styles exist only when the loading screen is in the DOM. When the element is removed by `AppDocumentRoot._render()`, the styles disappear automatically, preventing any leftover CSS pollution.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| `position: fixed; inset: 0` on `#webcompy-loading` may be affected by CSS `transform` on a parent. The `body` is the only parent and should have no transform. | The element is a direct child of `<body>`, which has no transform. Risk is negligible. |
| `inset` shorthand is relatively modern (supported in all evergreen browsers, but not IE). WebComPy targets PyScript users, who are on modern browsers. | No action needed — acceptable. |
| Removing global `body` styles might marginally affect apps that relied on the reset. | Unlikely — the reset was undocumented and incidental. Bootstrap and normalize.css users already override it. |

## Migration Plan

No migration required. This is a transparent change: the generated HTML structure changes, but `#webcompy-loading` element ID is preserved, so existing JavaScript/Python removal code in `AppDocumentRoot` continues to work. E2E tests do not need updates.
