---
title: Teleport
description: Relocate modals, drawers, and overlays to external DOM containers like body with Teleport, preserving reactive bindings, SSR block emission, and hydration order.
---

# Teleport

`Teleport` (`webcompy.elements`) renders a component subtree into a different DOM container—most commonly `document.body`—instead of inside the component's own DOM parent. Relocating the real DOM nodes lets modals, drawers, tooltips, and menus escape ancestor `overflow: hidden`, `transform`, or `z-index` stacking contexts while staying inside the Python component's logical, reactive, and DI tree.

Use `Teleport` whenever overlay UI should logically belong to the triggering component (sharing its signals, slots, and scoped CSS) yet visually sit outside constrained layout wrappers.

## How anchoring and relocation work

```text
Logical Component Tree                     Actual DOM Document
────────────────────────                   ──────────────────────────────
<div class="sidebar-card">                 <div class="sidebar-card">
  <h2>Settings</h2>                          <h2>Settings</h2>
  Teleport({"to": "body"}, modal)   ────►    <!--webcompy-teleport-anchor-->   (node count = 1)
  <button>Done</button>                      <button>Done</button>
</div>                                     </div>

                                           <body>
                                             <div id="webcompy-app">...</div>
                                             <!--wc-teleport-block:0:body-->
                                             <div class="modal-backdrop">...</div>
                                             <!--wc-teleport-block-end:0-->
                                           </body>
```

At its logical position in the component tree, `Teleport` owns **exactly one placeholder node**: a `<!--webcompy-teleport-anchor-->` comment node. No matter how many nodes live inside `Teleport` or how `repeat()`/`switch()` dynamically adds or removes children inside it, `Teleport` always reports one logical node to its parent so trailing sibling positions never drift.

Because relocation moves the actual DOM nodes rather than re-serializing HTML:

- Component scoped-style `webcompy-cid-*` attributes travel with the relocated elements, so component CSS still matches under `<body>`.
- Signal text interpolations, reactive attributes, and `@click` / `@keydown` event handlers keep working without re-binding.
- Removing the `Teleport` cleanly removes **both** the relocated nodes under the target and the anchor comment at the logical site.

## Basic usage

```python
from webcompy import use_state
from webcompy.components import ComponentContext, define_component
from webcompy.elements import Teleport, html, switch


@define_component()
def SettingsTrigger(context: ComponentContext[None]):
    open_modal = use_state(lambda: False)

    return html.DIV(
        {"class": "card"},
        html.BUTTON({"type": "button", "@click": lambda _ev: setattr(open_modal, "value", True)}, "Open Modal"),
        switch(
            {
                "case": open_modal,
                "generator": lambda: Teleport(
                    {"to": "body"},
                    html.DIV(
                        {"class": "modal-backdrop"},
                        html.DIV(
                            {"class": "modal-panel"},
                            html.H2({}, "Settings"),
                            html.BUTTON(
                                {"type": "button", "@click": lambda _ev: setattr(open_modal, "value", False)},
                                "Close",
                            ),
                        ),
                    ),
                ),
            },
            default=None,
        ),
    )
```

## SSR block emission and hydration

By default, `Teleport` **emits its relocated subtree on the server** (`"ssr": True` default) and adopts it seamlessly during hydration:

| Prop | Type | Default | Meaning |
|---|---|---|---|
| `to` | `str` | Required | Non-empty static CSS selector (`"body"`, `"#modal-root"`, etc.). Raises `ValueError` if missing or empty |
| `ssr` | `bool` | `True` | When `True`, emits children into the resolved target during SSR/SSG; set `False` to emit only the anchor comment on the server and mount exclusively in the browser |

How server emission and browser adoption stay deterministic:

1. **Server queue & emission**: During SSR/SSG, each rendered `Teleport` enqueues itself once in document traversal order into a per-`RenderContext` registry. After the full HTML scaffold and component tree finish rendering and async work settles, HTML assembly resolves each `to` selector against the completed virtual document tree and emits its children between comment markers:
   `<!--wc-teleport-block:<ordinal>:<encoded-selector>-->` … `<!--wc-teleport-block-end:<ordinal>-->`.
   Markers are emitted even when the children initially produce zero nodes so deferred updates land inside the right slot.
2. **Hydration adoption**: In the browser, each `Teleport` locates its unclaimed start marker in document ordinal order under the resolved target and adopts those nodes in place—keeping initial overlay state (such as a closed dropdown's `display: none`) intact with zero flash. If HTML was stale or markers diverged, `Teleport` logs a warning and falls back to normal client mounting.

Set `"ssr": False` when a teleported widget shouldn't exist in SSR HTML at all:

```python
Teleport({"to": "body", "ssr": False}, ClientDebugHUD(None))
```

## Target rules and rejection diagnostics

The `to` selector must point to a **stable static node outside the application's reactive component tree**—typically `"body"` or a dedicated container element authored in the host page outside `#webcompy-app`.

WebComPy enforces target safety across environments:

- **Targets rejected during SSR**: If `to` resolves on the server to `<head>`, the app mount container itself (such as `#webcompy-app`), or any node inside the application's own rendered subtree, WebComPy logs a warning naming the selector, skips emitting the block at the target, and emits only the anchor comment (allowing client mount if that target is created in the browser).
- **Unresolvable target on SSR**: If no node in the document scaffold matches `to`, SSR logs a warning and falls back to anchor-only emission.
- **Missing target in the browser**: If `query_selector(to)` returns nothing when mounting in the browser, `Teleport` logs a warning and degrades gracefully to **inline rendering** at its logical position rather than crashing the render tree.
- **No dynamic targets or automatic re-homing**: `to` must be a static string; reactive selectors are not supported, and if external JavaScript removes the target element later, relocated nodes detach with it rather than re-resolving.

## Multiple Teleports sharing a target

When multiple `Teleport` elements target the same container (e.g. `body`):

- Relocated blocks preserve **mount / document ordinal order** (Teleport A precedes Teleport B).
- Shared-target tracking anchors directly at each block's boundaries, so external scripts appending nodes to `<body>` (such as `#__webcompy_data__` or third-party widgets) or dynamic growth inside Teleport A (`repeat()`, async children) stays isolated within Teleport A's block without interleaving into Teleport B.

## Pitfalls

- **Never nest a `Teleport` targeting the same node as its ancestor**: Placing a `Teleport({"to": "body"}, ...)` inside another `Teleport({"to": "body"}, ...)` violates the contiguous block model. Restructure them as sibling `Teleport`s instead.
- **Targeting an element rendered inside another component**: If a `Teleport` targets an ID rendered by another component, SSR will reject server emission because that container isn't part of the stable outer document. Keep shared portal roots directly under `<body>` outside `#webcompy-app`.

## Next steps

- Inspect a modal and dropdown relocated into `<body>` in the [Teleport](/documents/examples/teleport) example.
- Use built-in teleported overlays (`Modal`, `Drawer`, `Dropdown`, `Toast`) in [Overlay Components](/documents/basic/overlay).
- Animate teleported modals with [Transition](/documents/advanced/transition).
- See how SSR blocks and hydration adoption work end to end in [SSR & SSG](/documents/advanced/ssr-and-ssg) and [Hydration & Data Transfer](/documents/advanced/hydration-and-transfer).
- Full API: [Elements, Routing & DI API](/documents/api/elements-and-routing).
