# Design: feat-teleport

## Context

WebComPy's element system mounts every node under its logical parent: `ElementAbstract._mount_node()` inserts into `self._parent._get_node()` at the child's `_node_idx` (`elements/types/_abstract.py:39-58`), and `DynamicElement` containers position children via `_position_element_nodes` against `self._parent._get_node()` (`elements/types/_dynamic.py:237-258`). Overlay UI (modals, dropdowns, toasts) needs its DOM nodes under a different container — typically `<body>` — to escape ancestor clipping and stacking contexts.

Grounded facts (verified in codebase):

- **Out-of-tree rendering precedent exists**: `HeadElement` (`elements/_head.py`) contributes `_node_count == 0` to its logical parent and renders imperatively into `<head>` through `DOMPort`, with SSR injection via `get_head_content_html()` and disposal-time cleanup (`_remove_emitted_style_elements`).
- **Container indirection point**: children resolve their DOM container exclusively through `self._parent._get_node()`. An element that overrides `_get_node()` redirects where its children mount.
- **Hydration marking is scoped to the app root**: `RootComponent._mark_as_prerendered` walks only the mount-point subtree (`app/_root_component.py:150-153`). Nodes SSR-rendered outside the app root (e.g. direct `<body>` children) are not adopted as prerendered.
- **Placeholder precedent**: `ElementAbstract._detach_node()` replaces a node with an empty text node (`_remount_to`) to preserve the slot (`_abstract.py:60-66`).
- **Template engine resolves only components and plain HTML tags** (`template/_binder.py:581-598`); there is no special-element hook, so `Teleport` ships as a Python API element like `ClientOnly` (`elements/__init__.py:21`).
- **docs_app demand**: the navbar dropdown (`docs_app/components/navigation.py:254-266`) works around the missing primitive with `position: absolute` + `z-index`, which breaks under ancestor `overflow`, stacking contexts, or `transform`.

## Goals / Non-Goals

**Goals:**

- `Teleport({"to": "<selector>"}, *children)` element that mounts children under the resolved target node.
- One static anchor node at the logical position so sibling node-index accounting is never disturbed.
- SSR emits only the anchor (no teleported content); the browser renders children under the target after hydration.
- Graceful degradation (warning + inline rendering) when the target selector matches nothing.
- Full cleanup on removal: teleported child nodes and the anchor.
- Fake-DOM testing support and a docs_app demo page.

**Non-Goals:**

- Reactive `to` (target re-parenting), `disabled` prop, template-engine syntax, SSR rendering of teleported content (see proposal Non-goals).

## Decisions

### D1: SSR strategy — anchor-only (no teleported content in SSR HTML)

Three strategies were evaluated:

- **Option 1 (inline + move)**: SSR renders children at the logical position; the client moves them to the target after hydration. Rejected: the anchor/placeholder count at the logical position would have to track the children's dynamic node count (conditional children, `repeat`, `Suspense`, async setup inside the teleport), forcing sibling re-indexing on every change. Node-index drift is precisely the bug class this codebase guards with strict `is None` node-cache checks and reconciliation specs.
- **Option 2 (render at target during SSR)**: SSR injects teleported content at the end of `<body>` (HeadElement-style injection). Rejected for v1: prerendered marking is scoped to the app root (`_mark_as_prerendered`), so adoption would require marking extensions plus index tracking inside the target container — cross-environment cost disproportionate to the benefit.
- **Option 3 (anchor-only)** — adopted: SSR emits one anchor placeholder; the client mounts children under the target after hydration. The anchor is static (`_node_count == 1` forever), so index accounting is trivially stable. Cost: teleported content is absent from SSR HTML until hydration. Accepted because overlays are almost invariably closed in initial SSR state, are never SEO content, and WebComPy pages are non-interactive until PyScript boots anyway. The upgrade path to Option 1 remains open for a future change if real demand appears.

### D2: Single static anchor at the logical position

`TeleportElement` contributes exactly one DOM node — an empty text placeholder — at its logical position, and reports `_node_count == 1`. Sibling `_node_idx` computation therefore sees a constant occupant regardless of how many nodes the teleported subtree contains or how that count changes. The anchor is created during normal mounting and removed with the element.

### D3: Container redirection via `_get_node()` override

`TeleportElement` is a `DynamicElement` whose `_on_set_parent()` sets `child._parent = self` for each child (unlike `FragmentElement`, which passes children through to the grandparent). `TeleportElement._get_node()` returns the resolved target node once teleported, so the standard child mounting path (`child._mount_node()` → `self._parent._get_node()`) places children under the target with no changes to the generic machinery. `_render()` is overridden to position children against the target node. Before teleportation completes (and in the inline-fallback mode) `_get_node()` returns the logical parent's node.

### D4: Target resolution and fallback

The target is resolved through `DOMPort.query_selector(to)` at mount time. Resolution failure (no match) logs a warning and falls back to inline rendering: children mount at the logical position as with a fragment, and the element keeps working. This mirrors the codebase's established degrade-with-warning pattern (e.g. `HeadElement`'s `query_selector("head")` guards) rather than raising into the render tree.

### D5: Multiple teleports to one target append in mount order

When several `Teleport` elements target the same node, each appends its children when it mounts; no reordering pass runs later. This matches Vue's observable behavior and keeps the implementation free of cross-element registries. The ordering rule is specified so users can rely on it.

### D6: Cleanup on removal

`_remove_element` removes the teleported child nodes (which live under the target, so recursive child removal via `_node_cache.remove()` already reaches them) and additionally removes the anchor node from the logical parent. Callback consumers are destroyed through the standard path. No app-lifecycle disposal hook is needed beyond element removal because all teleported nodes are owned by the element tree.

### D7: Python API only, static `to`

`Teleport` is exported from `webcompy.elements` alongside `ClientOnly` and used in component code. The template engine has no special-element hook (see Context), so template syntax is deferred. `to` is a plain `str`; accepting `Computed[str]` would require node re-parenting on target change and is deferred with the reactive-target work.

## Risks / Trade-offs

- **SSR fidelity gap** (accepted, D1): content open at SSR time appears only after hydration. Documented in the spec; revisit only if real demand surfaces.
- **Target stability**: if the target node itself is removed by application code or reconciliation, teleported nodes are detached with it. The spec requires targets to be stable nodes outside the app's reactive tree (e.g. `body`); no runtime guard is added.
- **Scoped CSS and events**: unaffected — scoped styles use `[webcompy-cid-...]` attribute selectors (document-global), and event listeners travel with the DOM nodes. Verified expectations are encoded as spec scenarios.
- **Hydration timing**: children mount under the target during the post-hydration render pass; until then only the anchor exists. Interactions with `Suspense`/async setup inside the teleport follow the existing `DynamicElement` pending-render machinery unchanged.
